"use client";

import { useState } from "react";
import Link from "next/link";
import { AuthProvider, useAuth } from "@/lib/auth";
import { useRouter } from "next/navigation";

function LoginForm() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const { login } = useAuth();
  const router = useRouter();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      await login(email, password);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Login failed");
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center px-4">
      <div className="w-full max-w-sm">
        <div className="text-center mb-8">
          <Link href="/" className="text-2xl font-bold text-[#6366f1]">
            DocSprint
          </Link>
          <h1 className="mt-2 text-xl font-semibold">Welcome back</h1>
          <p className="mt-1 text-sm text-[#a1a1aa]">
            Sign in to your account
          </p>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          {error && (
            <div className="rounded-lg bg-[#ef4444]/10 border border-[#ef4444]/20 p-3 text-sm text-[#ef4444]">
              {error}
            </div>
          )}
          <div>
            <label className="block text-sm font-medium text-[#a1a1aa] mb-1">
              Email
            </label>
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
              className="w-full rounded-lg border border-[#262629] bg-[#141416] px-3 py-2 text-sm text-white placeholder-[#71717a] focus:border-[#6366f1] focus:outline-none"
              placeholder="you@example.com"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-[#a1a1aa] mb-1">
              Password
            </label>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              className="w-full rounded-lg border border-[#262629] bg-[#141416] px-3 py-2 text-sm text-white placeholder-[#71717a] focus:border-[#6366f1] focus:outline-none"
              placeholder="••••••••"
            />
          </div>
          <button
            type="submit"
            disabled={loading}
            className="w-full rounded-lg bg-[#6366f1] px-4 py-2.5 text-sm font-semibold text-white hover:bg-[#818cf8] disabled:opacity-50 transition-colors"
          >
            {loading ? "Signing in..." : "Sign in"}
          </button>
        </form>

        <p className="mt-6 text-center text-sm text-[#a1a1aa]">
          Don't have an account?{" "}
          <Link href="/register" className="text-[#6366f1] hover:text-[#818cf8]">
            Sign up
          </Link>
        </p>
      </div>
    </div>
  );
}

export default function LoginPage() {
  return (
    <AuthProvider>
      <LoginForm />
    </AuthProvider>
  );
}