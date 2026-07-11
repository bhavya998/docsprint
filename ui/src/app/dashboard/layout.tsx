"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { AuthProvider, useAuth } from "@/lib/auth";

const navItems = [
  { href: "/dashboard", label: "Overview", icon: "📊" },
  { href: "/dashboard/documents", label: "Documents", icon: "📄" },
  { href: "/dashboard/api-keys", label: "API Keys", icon: "🔑" },
  { href: "/dashboard/settings", label: "Settings", icon: "⚙️" },
];

function Sidebar() {
  const pathname = usePathname();
  const { user, logout } = useAuth();

  return (
    <div className="flex h-screen w-64 flex-col border-r border-[#262629] bg-[#0a0a0b]">
      <div className="p-4 border-b border-[#262629]">
        <Link href="/" className="text-xl font-bold text-[#6366f1]">
          DocSprint
        </Link>
      </div>

      <nav className="flex-1 p-3 space-y-1">
        {navItems.map((item) => {
          const active = pathname === item.href;
          return (
            <Link
              key={item.href}
              href={item.href}
              className={`flex items-center gap-3 rounded-lg px-3 py-2 text-sm transition-colors ${
                active
                  ? "bg-[#6366f1]/10 text-white"
                  : "text-[#a1a1aa] hover:text-white hover:bg-[#141416]"
              }`}
            >
              <span>{item.icon}</span>
              {item.label}
            </Link>
          );
        })}
      </nav>

      <div className="border-t border-[#262629] p-4">
        <div className="text-sm text-[#a1a1aa] truncate">{user?.email}</div>
        <div className="text-xs text-[#71717a] capitalize">{user?.plan} plan</div>
        <button
          onClick={logout}
          className="mt-2 text-xs text-[#71717a] hover:text-[#ef4444] transition-colors"
        >
          Sign out
        </button>
      </div>
    </div>
  );
}

export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <AuthProvider>
      <div className="flex h-screen overflow-hidden">
        <Sidebar />
        <main className="flex-1 overflow-y-auto bg-[#0a0a0b] p-6">
          {children}
        </main>
      </div>
    </AuthProvider>
  );
}