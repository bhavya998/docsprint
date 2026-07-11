"use client";

import { useEffect, useState } from "react";
import { useAuth } from "@/lib/auth";
import { usageApi } from "@/lib/api";
import type { UsageResponse } from "@/lib/types";

export default function SettingsPage() {
  const { user } = useAuth();
  const [usage, setUsage] = useState<UsageResponse | null>(null);

  useEffect(() => {
    usageApi.get().then(setUsage).catch(console.error);
  }, []);

  return (
    <div>
      <h1 className="text-2xl font-bold mb-6">Settings</h1>

      {/* Account Info */}
      <div className="rounded-xl border border-[#262629] bg-[#141416] p-6 mb-6 max-w-2xl">
        <h2 className="text-lg font-semibold mb-4">Account</h2>
        <div className="space-y-3 text-sm">
          <div className="flex justify-between py-2 border-b border-[#262629]">
            <span className="text-[#a1a1aa]">Email</span>
            <span className="text-white">{user?.email}</span>
          </div>
          <div className="flex justify-between py-2 border-b border-[#262629]">
            <span className="text-[#a1a1aa]">Plan</span>
            <span className="text-white capitalize">{user?.plan}</span>
          </div>
          <div className="flex justify-between py-2 border-b border-[#262629]">
            <span className="text-[#a1a1aa]">Member since</span>
            <span className="text-white">
              {user?.created_at
                ? new Date(user.created_at).toLocaleDateString()
                : "—"}
            </span>
          </div>
        </div>
      </div>

      {/* Plan & Usage */}
      <div className="rounded-xl border border-[#262629] bg-[#141416] p-6 mb-6 max-w-2xl">
        <h2 className="text-lg font-semibold mb-4">Plan & Usage</h2>
        {usage && (
          <div className="space-y-4">
            <div>
              <div className="flex justify-between text-sm mb-1">
                <span className="text-[#a1a1aa]">Pages used this month</span>
                <span className="text-white">
                  {usage.pages_used} / {usage.pages_limit}
                </span>
              </div>
              <div className="h-2 rounded-full bg-[#262629] overflow-hidden">
                <div
                  className="h-full rounded-full bg-[#6366f1] transition-all"
                  style={{
                    width: `${Math.min(
                      (usage.pages_used / usage.pages_limit) * 100,
                      100
                    )}%`,
                  }}
                />
              </div>
            </div>
            <div className="pt-2 text-sm">
              <span className="text-[#a1a1aa]">Current period: </span>
              <span className="text-white">{usage.period}</span>
            </div>
          </div>
        )}
      </div>

      {/* Plans */}
      <div className="rounded-xl border border-[#262629] bg-[#141416] p-6 max-w-2xl">
        <h2 className="text-lg font-semibold mb-4">Available Plans</h2>
        <div className="grid gap-3 sm:grid-cols-3">
          {[
            { name: "Free", pages: "10", price: "$0" },
            { name: "Starter", pages: "500", price: "$29/mo" },
            { name: "Pro", pages: "2,000", price: "$99/mo" },
          ].map((plan) => (
            <div
              key={plan.name}
              className={`rounded-lg border p-4 text-center ${
                user?.plan?.toLowerCase() === plan.name.toLowerCase()
                  ? "border-[#6366f1] bg-[#6366f1]/5"
                  : "border-[#262629] bg-[#0a0a0b]"
              }`}
            >
              <div className="text-sm font-semibold text-white">
                {plan.name}
              </div>
              <div className="mt-1 text-xl font-bold">{plan.price}</div>
              <div className="mt-1 text-xs text-[#a1a1aa]">
                {plan.pages} pages/month
              </div>
              {user?.plan?.toLowerCase() === plan.name.toLowerCase() && (
                <div className="mt-2 inline-block rounded-full bg-[#22c55e]/10 px-2 py-0.5 text-xs text-[#22c55e]">
                  Current
                </div>
              )}
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}