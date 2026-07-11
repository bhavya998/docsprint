"""VL model service — wraps Qwen3.5-0.8B for document processing.

Runs INSIDE the RQ worker process (not the API server). Handles loading
the vision-language model on GPU with 4-bit quantization, and provides
extract/describe/ask modes.

CRITICAL: Uses Qwen3_5ForConditionalGeneration, NOT Qwen3VLForConditionalGeneration.
The model architecture is qwen3_5 (hybrid linear+full attention VL model).
"""

from __future__ import annotations

import io
import json
import time
from typing import Any

import fitz  # pymupdf
from PIL import Image

from docsprint.config import settings


class VLModelService:
    """Loads Qwen3.5-0.8B in 4-bit on GPU, provides extract/describe/ask.

    The model is loaded lazily on first use (not at import time) so the
    module can be imported on API servers without GPU memory overhead.
    """

    def __init__(
        self,
        model_id: str | None = None,
        quantize_4bit: bool = True,
        max_tokens: int = 2048,
    ) -> None:
        """Initialize the VL model service.

        Args:
            model_id: HuggingFace model ID. Defaults to settings.MODEL_ID.
            quantize_4bit: Whether to load in 4-bit quantization.
            max_tokens: Maximum tokens for generation.
        """
        self._model_id = model_id or settings.MODEL_ID
        self._quantize = quantize_4bit
        self._max_tokens = max_tokens
        self._model: Any = None
        self._processor: Any = None

    def _load(self) -> None:
        """Load the model and processor if not already loaded.

        Uses 4-bit BitsAndBytes quantization when CUDA is available.
        Falls back to fp16 on CPU if CUDA is not available.
        """
        if self._model is not None:
            return

        import torch
        from transformers import Qwen3_5ForConditionalGeneration, AutoProcessor

        has_cuda = torch.cuda.is_available()
        load_kwargs: dict[str, Any] = {"trust_remote_code": True, "device_map": "auto"}

        if self._quantize and has_cuda:
            from transformers import BitsAndBytesConfig

            load_kwargs["quantization_config"] = BitsAndBytesConfig(
                load_in_4bit=True,
                bnb_4bit_compute_dtype=torch.float16,
                bnb_4bit_use_double_quant=True,
                bnb_4bit_quant_type="nf4",
            )
            print(f"[DocSprint] Loading {self._model_id} in 4-bit on GPU")
        elif has_cuda:
            load_kwargs["torch_dtype"] = torch.float16
            print(f"[DocSprint] Loading {self._model_id} fp16 on GPU")
        else:
            load_kwargs["torch_dtype"] = torch.float16
            load_kwargs["device_map"] = "cpu"
            print(f"[DocSprint] No CUDA — loading {self._model_id} fp16 on CPU")

        self._processor = AutoProcessor.from_pretrained(
            self._model_id, trust_remote_code=True
        )
        # CRITICAL: Qwen3_5ForConditionalGeneration, NOT Qwen3VLForConditionalGeneration
        self._model = Qwen3_5ForConditionalGeneration.from_pretrained(
            self._model_id, **load_kwargs
        )
        if not has_cuda:
            self._model.to("cpu")
        self._model.eval()
        print("[DocSprint] Model loaded successfully")

    def query(
        self,
        image: Image.Image,
        prompt: str,
        *,
        system: str | None = None,
        temperature: float = 0.0,
    ) -> str:
        """Send an image + text prompt to the VL model.

        Args:
            image: PIL Image to analyze.
            prompt: Text instruction/prompt.
            system: Optional system message.
            temperature: Generation temperature (0 = deterministic).

        Returns:
            Model's text response.
        """
        import torch

        self._load()

        content: list[dict[str, Any]] = [
            {"type": "image", "image": image},
            {"type": "text", "text": prompt},
        ]
        messages: list[dict[str, Any]] = []
        if system:
            messages.append(
                {"role": "system", "content": [{"type": "text", "text": system}]}
            )
        messages.append({"role": "user", "content": content})

        text = self._processor.apply_chat_template(
            messages, tokenize=False, add_generation_prompt=True
        )
        inputs = self._processor(text=[text], images=[image], return_tensors="pt")
        device = next(self._model.parameters()).device
        inputs = {k: v.to(device) for k, v in inputs.items()}

        with torch.no_grad():
            outputs = self._model.generate(
                **inputs,
                max_new_tokens=self._max_tokens,
                temperature=temperature,
                do_sample=temperature > 0,
                pad_token_id=self._processor.tokenizer.eos_token_id,
            )
        prompt_len = inputs["input_ids"].shape[1]
        return self._processor.decode(
            outputs[0][prompt_len:], skip_special_tokens=True
        ).strip()

    def describe(self, image: Image.Image, temperature: float = 0.0) -> str:
        """Describe what the image/page depicts in 1-2 sentences.

        Args:
            image: PIL Image to describe.
            temperature: Generation temperature.

        Returns:
            Concise description string.
        """
        return self.query(
            image,
            "Describe what this image depicts or conveys in 1-2 concise sentences.",
            system="You are an image analyst. Be concise and factual.",
            temperature=temperature,
        )

    def extract_json(
        self,
        image: Image.Image,
        schema_description: str,
        temperature: float = 0.0,
    ) -> dict[str, Any]:
        """Extract structured data matching the described schema.

        Args:
            image: PIL Image of a document page.
            schema_description: Natural language description of what to extract.
            temperature: Generation temperature.

        Returns:
            Parsed JSON dict with extracted data.
        """
        system = (
            "You are a document data extractor. Respond ONLY with valid JSON."
            " No markdown fences, no explanation."
        )
        prompt = f"Extract the following information as JSON:\n{schema_description}"
        raw = self.query(image, prompt, system=system, temperature=temperature)
        clean = raw.strip()
        if clean.startswith("```"):
            clean = clean.split("```")[1]
            if clean.startswith("json"):
                clean = clean[4:]
        try:
            return json.loads(clean.strip())
        except json.JSONDecodeError:
            return {"raw_output": raw}

    def process_document(
        self,
        file_path: str,
        mode: str = "extract",
        prompt: str = "",
    ) -> dict[str, Any]:
        """Process a document file through the VL model.

        Renders PDF pages or loads images, then runs the model on each page.

        Args:
            file_path: Path to the document file.
            mode: Processing mode: "extract", "describe", or "ask".
            prompt: Custom extract schema or question (used for extract/ask).

        Returns:
            Dict with structured results:
            - extract: {"pages": [{page, content, has_extracted_text}, ...]}
            - describe: {"description": "page1 desc\\npage2 desc"}
            - ask: {"answer": "page1 answer\\n\\npage2 answer"}
        """
        start_time = time.time()

        # Load document pages
        pages = self._load_document_pages(file_path)

        if not pages:
            return {"error": "No pages found in document", "pages": []}

        if mode == "describe":
            return self._run_describe(pages, start_time)

        if mode == "ask":
            return self._run_ask(pages, prompt, start_time)

        # Default: extract mode
        return self._run_extract(pages, prompt, start_time)

    def _load_document_pages(self, file_path: str) -> list[tuple[Image.Image, str]]:
        """Load document as list of (PIL image, extracted_text) pairs.

        Args:
            file_path: Path to the document.

        Returns:
            List of (PIL Image, extracted text string) tuples, one per page.
        """
        from pathlib import Path

        suffix = Path(file_path).suffix.lower()

        if suffix == ".pdf":
            return self._load_pdf(file_path)
        if suffix == ".gif":
            return self._load_gif(file_path)
        # All other image formats
        img = Image.open(file_path).convert("RGB")
        return [(img, "")]

    @staticmethod
    def _load_pdf(file_path: str) -> list[tuple[Image.Image, str]]:
        """Render PDF pages as PIL images with extracted text.

        Args:
            file_path: Path to the PDF file.

        Returns:
            List of (PIL Image, extracted text) tuples.
        """
        doc = fitz.open(file_path)
        pages: list[tuple[Image.Image, str]] = []
        for i in range(len(doc)):
            page = doc[i]
            pix = page.get_pixmap(dpi=200)
            img_data = pix.tobytes("png")
            image = Image.open(io.BytesIO(img_data))
            text = page.get_text().strip()
            pages.append((image, text))
        doc.close()
        return pages

    @staticmethod
    def _load_gif(file_path: str) -> list[tuple[Image.Image, str]]:
        """Load GIF frames as individual images.

        Args:
            file_path: Path to the GIF file.

        Returns:
            List of (PIL Image, "") tuples, one per frame.
        """
        gif = Image.open(file_path)
        frames: list[tuple[Image.Image, str]] = []
        for i in range(getattr(gif, "n_frames", 1)):
            gif.seek(i)
            frame = gif.copy().convert("RGB")
            frames.append((frame, ""))
        return frames

    def _run_extract(
        self,
        pages: list[tuple[Image.Image, str]],
        schema: str,
        start_time: float,
    ) -> dict[str, Any]:
        """Run extraction mode: extract structured data from each page.

        Args:
            pages: List of (image, text) tuples.
            schema: Natural language description of data to extract.
            start_time: Processing start timestamp.

        Returns:
            Dict with pages array and timing info.
        """
        extract_system = (
            "You are a document data extractor. Extract ALL information visible on this page."
            " Include tables as arrays, key-value pairs as objects, text as strings."
            " Do NOT summarize — include every data point."
            " Respond ONLY with valid JSON. No markdown, no explanation."
        )

        extraction_prompt = schema or (
            "Extract all information visible on this page as structured JSON."
            " Include headers, body text, tables, form fields, signatures, stamps, and any metadata."
        )

        results: list[dict[str, Any]] = []
        for i, (image, text) in enumerate(pages):
            content = self.query(
                image,
                extraction_prompt,
                system=extract_system,
                temperature=0.0,
            )
            # Try to parse as JSON, fall back to raw text
            try:
                clean = content.strip()
                if clean.startswith("```"):
                    clean = clean.split("```")[1]
                    if clean.startswith("json"):
                        clean = clean[4:]
                parsed = json.loads(clean.strip())
            except (json.JSONDecodeError, ValueError):
                parsed = {"raw_content": content}

            results.append({
                "page": i + 1,
                "content": json.dumps(parsed) if isinstance(parsed, dict) else str(parsed),
                "has_extracted_text": bool(text),
                "data": parsed,
            })

        elapsed = time.time() - start_time
        return {
            "pages": results,
            "processing_time_seconds": round(elapsed, 2),
            "page_count": len(pages),
        }

    def _run_describe(
        self,
        pages: list[tuple[Image.Image, str]],
        start_time: float,
    ) -> dict[str, Any]:
        """Run describe mode: summarize each page.

        Args:
            pages: List of (image, text) tuples.
            start_time: Processing start timestamp.

        Returns:
            Dict with description text and timing info.
        """
        label = "page" if len(pages) > 1 else "image"
        descriptions: list[str] = []
        for i, (image, _) in enumerate(pages):
            desc = self.describe(image)
            prefix = f"[{label.capitalize()} {i + 1}]"
            descriptions.append(f"{prefix} {desc}")

        elapsed = time.time() - start_time
        return {
            "description": "\n".join(descriptions),
            "processing_time_seconds": round(elapsed, 2),
        }

    def _run_ask(
        self,
        pages: list[tuple[Image.Image, str]],
        question: str,
        start_time: float,
    ) -> dict[str, Any]:
        """Run ask mode: answer questions about each page.

        Args:
            pages: List of (image, text) tuples.
            question: The question to answer.
            start_time: Processing start timestamp.

        Returns:
            Dict with answer text and timing info.
        """
        ask_system = (
            "You are a document analyst. Answer questions based ONLY on what is visible on the page."
            " Be precise. If the answer is not on the page, say so."
        )

        answers: list[str] = []
        for i, (image, _) in enumerate(pages):
            answer = self.query(image, question, system=ask_system, temperature=0.0)
            answers.append(f"[Page {i + 1}] {answer}")

        elapsed = time.time() - start_time
        return {
            "answer": "\n\n".join(answers),
            "processing_time_seconds": round(elapsed, 2),
        }