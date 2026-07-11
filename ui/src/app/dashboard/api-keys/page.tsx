"use client";

import { useState } from "react";
import { useAuth } from "@/lib/auth";

export default function ApiKeysPage() {
  const { user } = useAuth();
  const [copied, setCopied] = useState(false);

  const copyApiKey = async () => {
    if (user?.api_key) {
      await navigator.clipboard.writeText(user.api_key);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  return (
    <div>
      <h1 className="text-2xl font-bold mb-6">API Keys</h1>

      <div className="rounded-xl border border-[#262629] bg-[#141416] p-6 max-w-2xl">
        <h2 className="text-lg font-semibold mb-2">Your API Key</h2>
        <p className="text-sm text-[#a1a1aa] mb-4">
          Use this key in the <code className="text-[#6366f1]">X-API-Key</code>{" "}
          header for programmatic access to the DocSprint API.
        </p>

        <div className="flex items-center gap-2">
          <code className="flex-1 rounded-lg border border-[#262629] bg-[#0a0a0b] px-4 py-3 text-sm font-mono text-[#22c55e] break-all">
            {user?.api_key || "Loading..."}
          </code>
          <button
            onClick={copyApiKey}
            className="rounded-lg bg-[#6366f1] px-4 py-3 text-sm font-medium text-white hover:bg-[#818cf8] transition-colors whitespace-nowrap"
          >
            {copied ? "Copied!" : "Copy"}
          </button>
        </div>

        <div className="mt-8">
          <h3 className="text-sm font-semibold mb-2">Example Usage</h3>
          <pre className="rounded-lg bg-[#0a0a0b] border border-[#262629] p-4 overflow-auto text-sm">
            <code className="text-[#a1a1aa]">{`curl -X POST http://localhost:8000/api/v1/documents/upload \\
  -H "X-API-Key: ${user?.api_key || "dsk_YOUR_KEY"}" \\
  -F "file=@invoice.pdf" \\
  -F "mode=extract"`}</code>
          </pre>
        </div>

        <div className="mt-8">
          <h3 className="text-sm font-semibold mb-2">API Base URL</h3>
          <code className="rounded-lg border border-[#262629] bg-[#0a0a0b] px-4 py-2 text-sm font-mono text-[#6366f1]">
            http://localhost:8000/api/v1
          </code>
        </div>
      </div>
    </div>
  );
}