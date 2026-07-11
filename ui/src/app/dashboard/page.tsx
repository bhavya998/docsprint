"use client";

import { useEffect, useState } from "react";
import { useAuth } from "@/lib/auth";
import { documentsApi, usageApi } from "@/lib/api";
import type { UsageResponse, DocumentItem } from "@/lib/types";
import Link from "next/link";

export default function DashboardOverview() {
  const { user } = useAuth();
  const [usage, setUsage] = useState<UsageResponse | null>(null);
  const [recentDocs, setRecentDocs] = useState<DocumentItem[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([usageApi.get(), documentsApi.list(0, 5)])
      .then(([u, d]) => {
        setUsage(u);
        setRecentDocs(d.documents);
      })
      .catch(console.error)
      .finally(() => setLoading(false));
  }, []);

  if (loading) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="h-8 w-8 animate-spin rounded-full border-2 border-[#262629] border-t-[#6366f1]" />
      </div>
    );
  }

  return (
    <div>
      <h1 className="text-2xl font-bold mb-6">Overview</h1>

      {/* Usage Card */}
      <div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-3 mb-8">
        <div className="rounded-xl border border-[#262629] bg-[#141416] p-6">
          <p className="text-sm text-[#a1a1aa]">Pages Used</p>
          <p className="mt-2 text-3xl font-bold">
            {usage?.pages_used ?? 0}
            <span className="text-lg text-[#a1a1aa] font-normal">
              {" "}
              / {usage?.pages_limit ?? 0}
            </span>
          </p>
          <div className="mt-3 h-2 rounded-full bg-[#262629] overflow-hidden">
            <div
              className="h-full rounded-full bg-[#6366f1] transition-all"
              style={{
                width: `${
                  usage
                    ? Math.min(
                        (usage.pages_used / usage.pages_limit) * 100,
                        100
                      )
                    : 0
                }%`,
              }}
            />
          </div>
          <p className="mt-2 text-xs text-[#71717a] capitalize">
            {usage?.plan} plan — {usage?.period}
          </p>
        </div>

        <div className="rounded-xl border border-[#262629] bg-[#141416] p-6">
          <p className="text-sm text-[#a1a1aa]">Total Documents</p>
          <p className="mt-2 text-3xl font-bold">{recentDocs.length}</p>
        </div>

        <div className="rounded-xl border border-[#262629] bg-[#141416] p-6">
          <p className="text-sm text-[#a1a1aa]">API Key</p>
          <p className="mt-2 text-sm font-mono text-[#a1a1aa] truncate">
            {user?.api_key}
          </p>
        </div>
      </div>

      {/* Recent Documents */}
      <div className="rounded-xl border border-[#262629] bg-[#141416] p-6">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-semibold">Recent Documents</h2>
          <Link
            href="/dashboard/documents"
            className="text-sm text-[#6366f1] hover:text-[#818cf8]"
          >
            View all
          </Link>
        </div>
        {recentDocs.length === 0 ? (
          <p className="text-sm text-[#71717a]">
            No documents yet.{" "}
            <Link
              href="/dashboard/documents"
              className="text-[#6366f1] hover:text-[#818cf8]"
            >
              Upload your first document
            </Link>
          </p>
        ) : (
          <table className="w-full text-sm">
            <thead>
              <tr className="text-left text-[#a1a1aa] border-b border-[#262629]">
                <th className="pb-2 font-medium">File</th>
                <th className="pb-2 font-medium">Format</th>
                <th className="pb-2 font-medium">Pages</th>
                <th className="pb-2 font-medium">Status</th>
              </tr>
            </thead>
            <tbody>
              {recentDocs.map((doc) => (
                <tr key={doc.id} className="border-b border-[#262629]/50">
                  <td className="py-2 text-white">{doc.filename}</td>
                  <td className="py-2 text-[#a1a1aa] uppercase text-xs">
                    {doc.file_format}
                  </td>
                  <td className="py-2 text-[#a1a1aa]">{doc.page_count}</td>
                  <td className="py-2">
                    <span
                      className={`inline-block rounded-full px-2 py-0.5 text-xs font-medium status-${doc.status}`}
                    >
                      {doc.status}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}