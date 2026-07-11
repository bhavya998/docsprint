"use client";

import { useState, useEffect, useCallback } from "react";
import { documentsApi } from "@/lib/api";
import type { DocumentItem, DocumentDetailResponse } from "@/lib/types";

export default function DocumentsPage() {
  const [documents, setDocuments] = useState<DocumentItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState("");
  const [selected, setSelected] = useState<DocumentDetailResponse | null>(null);
  const [viewLoading, setViewLoading] = useState(false);
  const [mode, setMode] = useState("extract");
  const [prompt, setPrompt] = useState("");

  const refreshList = useCallback(() => {
    documentsApi
      .list(0, 50)
      .then((d) => setDocuments(d.documents))
      .catch((e) => console.error(e));
  }, []);

  useEffect(() => {
    refreshList();
    setLoading(false);
  }, [refreshList]);

  const handleUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    setError("");
    setUploading(true);
    try {
      await documentsApi.upload(file, mode, prompt || undefined);
      refreshList();
      e.target.value = "";
      setPrompt("");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Upload failed");
    } finally {
      setUploading(false);
    }
  };

  const viewDocument = async (id: number) => {
    setViewLoading(true);
    try {
      const doc = await documentsApi.get(id);
      setSelected(doc);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load document");
    } finally {
      setViewLoading(false);
    }
  };

  // Auto-poll for processing documents
  useEffect(() => {
    const hasProcessing = documents.some(
      (d) => d.status === "queued" || d.status === "processing"
    );
    if (!hasProcessing) return;

    const interval = setInterval(refreshList, 3000);
    return () => clearInterval(interval);
  }, [documents, refreshList]);

  return (
    <div>
      <h1 className="text-2xl font-bold mb-6">Documents</h1>

      {/* Upload Section */}
      <div className="rounded-xl border border-[#262629] bg-[#141416] p-6 mb-6">
        <h2 className="text-lg font-semibold mb-4">Upload Document</h2>
        {error && (
          <div className="mb-4 rounded-lg bg-[#ef4444]/10 border border-[#ef4444]/20 p-3 text-sm text-[#ef4444]">
            {error}
          </div>
        )}

        <div className="flex flex-wrap gap-4 items-end">
          <div>
            <label className="block text-sm text-[#a1a1aa] mb-1">Mode</label>
            <select
              value={mode}
              onChange={(e) => setMode(e.target.value)}
              className="rounded-lg border border-[#262629] bg-[#0a0a0b] px-3 py-2 text-sm text-white focus:border-[#6366f1] focus:outline-none"
            >
              <option value="extract">Extract (structured JSON)</option>
              <option value="describe">Describe (summary)</option>
              <option value="ask">Ask (Q&A)</option>
            </select>
          </div>

          {mode === "ask" && (
            <div className="flex-1 min-w-[200px]">
              <label className="block text-sm text-[#a1a1aa] mb-1">
                Question
              </label>
              <input
                type="text"
                value={prompt}
                onChange={(e) => setPrompt(e.target.value)}
                placeholder="What information do you want?"
                className="w-full rounded-lg border border-[#262629] bg-[#0a0a0b] px-3 py-2 text-sm text-white placeholder-[#71717a] focus:border-[#6366f1] focus:outline-none"
              />
            </div>
          )}

          <label className="cursor-pointer rounded-lg bg-[#6366f1] px-4 py-2 text-sm font-semibold text-white hover:bg-[#818cf8] transition-colors">
            {uploading ? "Uploading..." : "Upload File"}
            <input
              type="file"
              accept=".pdf,.png,.jpg,.jpeg,.gif,.tiff,.tif,.bmp,.webp"
              onChange={handleUpload}
              className="hidden"
              disabled={uploading}
            />
          </label>
        </div>
        <p className="mt-2 text-xs text-[#71717a]">
          PDF, PNG, JPG, GIF, TIFF, BMP, WebP — max 20MB
        </p>
      </div>

      {/* Document List */}
      <div className="grid gap-6 lg:grid-cols-3">
        <div className="lg:col-span-1 rounded-xl border border-[#262629] bg-[#141416] p-6">
          <h2 className="text-lg font-semibold mb-4">
            All Documents ({documents.length})
          </h2>
          {loading ? (
            <div className="flex justify-center py-8">
              <div className="h-6 w-6 animate-spin rounded-full border-2 border-[#262629] border-t-[#6366f1]" />
            </div>
          ) : documents.length === 0 ? (
            <p className="text-sm text-[#71717a] py-4">
              No documents uploaded yet.
            </p>
          ) : (
            <div className="space-y-2 max-h-[60vh] overflow-y-auto">
              {documents.map((doc) => (
                <button
                  key={doc.id}
                  onClick={() => viewDocument(doc.id)}
                  className={`w-full text-left rounded-lg border border-[#262629] p-3 hover:border-[#6366f1] transition-colors ${
                    selected?.id === doc.id ? "border-[#6366f1] bg-[#6366f1]/5" : "bg-[#0a0a0b]"
                  }`}
                >
                  <div className="flex items-center justify-between">
                    <span className="text-sm font-medium text-white truncate max-w-[180px]">
                      {doc.filename}
                    </span>
                    <span
                      className={`inline-block rounded-full px-2 py-0.5 text-xs font-medium status-${doc.status}`}
                    >
                      {doc.status}
                    </span>
                  </div>
                  <div className="mt-1 flex gap-3 text-xs text-[#71717a]">
                    <span className="uppercase">{doc.file_format}</span>
                    <span>{doc.page_count} pages</span>
                    <span>{new Date(doc.created_at).toLocaleDateString()}</span>
                  </div>
                </button>
              ))}
            </div>
          )}
        </div>

        {/* Result Viewer */}
        <div className="lg:col-span-2 rounded-xl border border-[#262629] bg-[#141416] p-6">
          <h2 className="text-lg font-semibold mb-4">Document Result</h2>
          {viewLoading ? (
            <div className="flex justify-center py-12">
              <div className="h-6 w-6 animate-spin rounded-full border-2 border-[#262629] border-t-[#6366f1]" />
            </div>
          ) : selected ? (
            <div>
              <div className="mb-4 flex gap-4 text-sm">
                <div>
                  <span className="text-[#71717a]">Status: </span>
                  <span className={`font-medium status-${selected.status} rounded-full px-2 py-0.5`}>
                    {selected.status}
                  </span>
                </div>
                <div>
                  <span className="text-[#71717a]">Mode: </span>
                  <span className="text-white capitalize">{selected.mode}</span>
                </div>
              </div>

              {selected.error && (
                <div className="mb-4 rounded-lg bg-[#ef4444]/10 border border-[#ef4444]/20 p-3 text-sm text-[#ef4444]">
                  {selected.error}
                </div>
              )}

              {selected.result ? (
                <pre className="rounded-lg bg-[#0a0a0b] border border-[#262629] p-4 overflow-auto max-h-[60vh]">
                  <code className="text-sm text-[#22c55e]">
                    {JSON.stringify(selected.result, null, 2)}
                  </code>
                </pre>
              ) : selected.status === "queued" || selected.status === "processing" ? (
                <div className="flex items-center gap-3 py-8 text-sm text-[#a1a1aa]">
                  <div className="h-4 w-4 animate-spin rounded-full border-2 border-[#262629] border-t-[#6366f1]" />
                  Processing... (auto-refreshes every 3s)
                </div>
              ) : (
                <p className="text-sm text-[#71717a] py-8">
                  No result available.
                </p>
              )}
            </div>
          ) : (
            <p className="text-sm text-[#71717a] py-8">
              Select a document from the list to view its result.
            </p>
          )}
        </div>
      </div>
    </div>
  );
}