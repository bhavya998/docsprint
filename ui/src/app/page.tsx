"use client";

import Link from "next/link";
import { useAuth } from "@/lib/auth";
import { AuthProvider } from "@/lib/auth";

function HomeContent() {
  const { user, loading } = useAuth();

  return (
    <div className="min-h-screen">
      {/* Nav */}
      <nav className="border-b border-[#262629]">
        <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
          <div className="flex h-16 items-center justify-between">
            <div className="flex items-center gap-2">
              <span className="text-xl font-bold text-[#6366f1]">DocSprint</span>
              <span className="rounded bg-[#6366f1]/10 px-2 py-0.5 text-xs text-[#818cf8]">
                Beta
              </span>
            </div>
            <div className="flex items-center gap-4">
              {loading ? (
                <div className="h-5 w-5 animate-spin rounded-full border-2 border-[#262629] border-t-[#6366f1]" />
              ) : user ? (
                <Link
                  href="/dashboard"
                  className="rounded-lg bg-[#6366f1] px-4 py-2 text-sm font-medium text-white hover:bg-[#818cf8] transition-colors"
                >
                  Dashboard
                </Link>
              ) : (
                <>
                  <Link
                    href="/login"
                    className="text-sm text-[#a1a1aa] hover:text-white transition-colors"
                  >
                    Sign in
                  </Link>
                  <Link
                    href="/register"
                    className="rounded-lg bg-[#6366f1] px-4 py-2 text-sm font-medium text-white hover:bg-[#818cf8] transition-colors"
                  >
                    Get Started
                  </Link>
                </>
              )}
            </div>
          </div>
        </div>
      </nav>

      {/* Hero */}
      <section className="py-24 sm:py-32">
        <div className="mx-auto max-w-4xl px-4 text-center">
          <h1 className="text-4xl font-bold tracking-tight sm:text-6xl">
            AI Document Processing
            <br />
            <span className="text-[#6366f1]">On Your Own GPU</span>
          </h1>
          <p className="mt-6 text-lg leading-8 text-[#a1a1aa] max-w-2xl mx-auto">
            Upload PDFs and images. Get structured JSON back. Powered by
            Qwen3.5-0.8B vision-language model running locally on your
            infrastructure.
          </p>
          <div className="mt-10 flex items-center justify-center gap-4">
            <Link
              href="/register"
              className="rounded-lg bg-[#6366f1] px-6 py-3 text-sm font-semibold text-white hover:bg-[#818cf8] transition-colors"
            >
              Start Free — 10 pages/month
            </Link>
            <Link
              href="/docs"
              className="rounded-lg border border-[#262629] px-6 py-3 text-sm font-semibold text-[#a1a1aa] hover:text-white hover:border-[#6366f1] transition-colors"
            >
              API Docs
            </Link>
          </div>
        </div>
      </section>

      {/* Features */}
      <section className="py-16 border-t border-[#262629]">
        <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
          <div className="grid gap-8 sm:grid-cols-3">
            <div className="rounded-xl border border-[#262629] bg-[#141416] p-6">
              <div className="mb-3 text-2xl">📄</div>
              <h3 className="text-lg font-semibold">Multi-Format Upload</h3>
              <p className="mt-2 text-sm text-[#a1a1aa]">
                PDF, PNG, JPG, GIF, TIFF, BMP, WebP — all supported. Up to 20MB
                per file.
              </p>
            </div>
            <div className="rounded-xl border border-[#262629] bg-[#141416] p-6">
              <div className="mb-3 text-2xl">🧠</div>
              <h3 className="text-lg font-semibold">VL Model on GPU</h3>
              <p className="mt-2 text-sm text-[#a1a1aa]">
                Qwen3.5-0.8B runs locally in 4-bit quantization. Your data never
                leaves your infrastructure.
              </p>
            </div>
            <div className="rounded-xl border border-[#262629] bg-[#141416] p-6">
              <div className="mb-3 text-2xl">🔌</div>
              <h3 className="text-lg font-semibold">REST API + SDK</h3>
              <p className="mt-2 text-sm text-[#a1a1aa]">
                Programmatic access with API keys. Drop-in replacement for
                Parseur or AWS Textract.
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* Pricing */}
      <section className="py-16 border-t border-[#262629]">
        <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8 text-center">
          <h2 className="text-3xl font-bold">Simple Pricing</h2>
          <p className="mt-4 text-[#a1a1aa]">
            Start free, scale as you grow.
          </p>
          <div className="mt-12 grid gap-6 sm:grid-cols-3 max-w-4xl mx-auto">
            {[
              { name: "Free", pages: "10", price: "$0" },
              { name: "Starter", pages: "500", price: "$29/mo" },
              { name: "Pro", pages: "2,000", price: "$99/mo" },
            ].map((plan) => (
              <div
                key={plan.name}
                className="rounded-xl border border-[#262629] bg-[#141416] p-6 text-center"
              >
                <h3 className="text-lg font-semibold">{plan.name}</h3>
                <p className="mt-2 text-3xl font-bold">{plan.price}</p>
                <p className="mt-1 text-sm text-[#a1a1aa]">
                  {plan.pages} pages/month
                </p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="border-t border-[#262629] py-8 text-center text-sm text-[#71717a]">
        <p>DocSprint — AI Document Processing SaaS</p>
      </footer>
    </div>
  );
}

export default function Home() {
  return (
    <AuthProvider>
      <HomeContent />
    </AuthProvider>
  );
}