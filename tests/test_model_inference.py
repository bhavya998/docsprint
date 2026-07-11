"""Test actual VL model inference — downloads Qwen3.5-0.8B, processes a real image."""
from __future__ import annotations

import sys
from pathlib import Path

# Add src to path so we can import docsprint
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from PIL import Image


def main() -> None:
    print("=" * 60)
    print("  DocSprint VL Model Inference Test")
    print("  Loading Qwen3.5-0.8B and processing images...")
    print("=" * 60)

    # Create a test image with text-like content (simulates a document)
    img = Image.new("RGB", (200, 100), "white")
    from PIL import ImageDraw
    draw = ImageDraw.Draw(img)
    draw.text((10, 10), "Invoice #INV-001", fill="black")
    draw.text((10, 30), "Total: $150.00", fill="black")
    draw.text((10, 50), "Date: 2026-01-15", fill="black")

    # Save to a temp file (model service expects file path)
    tmp_path = Path("data/test_invoice.png")
    tmp_path.parent.mkdir(exist_ok=True)
    img.save(tmp_path)

    print(f"\n[1] Created test image: {tmp_path} ({img.size})")
    print("[2] Loading VLModelService (model will download on first use)...")

    from docsprint.services.model_service import VLModelService

    try:
        model = VLModelService(
            model_id="Qwen/Qwen3.5-0.8B",
            quantize_4bit=True,
            max_tokens=256,
        )
        print("[3] Model service created. Running inference...")

        # Test extract mode
        print("\n--- EXTRACT MODE ---")
        result = model.process_document(str(tmp_path), mode="extract")
        print(f"Result: {result}")
        if "pages" in result:
            for p in result["pages"]:
                content = p.get("content", "")[:200]
                print(f"  Page {p['page']}: {content}")

        # Test describe mode
        print("\n--- DESCRIBE MODE ---")
        result2 = model.process_document(str(tmp_path), mode="describe")
        desc = result2.get("description", "N/A")
        print(f"Description: {desc[:300]}")

        # Test ask mode
        print("\n--- ASK MODE ---")
        result3 = model.process_document(
            str(tmp_path),
            mode="ask",
            prompt="What is the invoice number and total amount?",
        )
        answer = result3.get("answer", "N/A")
        print("Question: What is the invoice number and total amount?")
        print(f"Answer: {answer[:300]}")

        print("\n" + "=" * 60)
        print("  ALL INFERENCE TESTS PASSED")
        print("=" * 60)

    except Exception as e:
        print(f"\n[ERROR] {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        # Cleanup
        if tmp_path.exists():
            tmp_path.unlink()


if __name__ == "__main__":
    main()