"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import {
  Bot, Brain, GitBranch, Home, LogOut,
  Network, Settings, Star
} from "lucide-react";
import { clearToken } from "@/lib/auth";

const nav = [
  { href: "/dashboard", icon: Home, label: "Dashboard" },
  { href: "/agents", icon: Bot, label: "Agents" },
  { href: "/memory", icon: Brain, label: "Memory" },
  { href: "/knowledge", icon: Network, label: "Knowledge" },
  { href: "/workflows", icon: GitBranch, label: "Workflows" },
  { href: "/repo-reviews", icon: Star, label: "Repo Reviews" },
  { href: "/settings", icon: Settings, label: "Settings" },
];

export function Sidebar() {
  const path = usePathname();
  const router = useRouter();

  function logout() {
    clearToken();
    router.push("/login");
  }

  return (
    <aside className="w-56 flex-shrink-0 bg-[--surface] border-r border-[--border] flex flex-col h-full">
      {/* Logo */}
      <div className="px-5 py-5 border-b border-[--border]">
        <div className="flex items-center gap-2.5">
          <div className="w-7 h-7 rounded-lg bg-[--accent] flex items-center justify-center">
            <span className="text-white text-xs font-bold">A</span>
          </div>
          <div>
            <p className="text-sm font-bold text-[--text-primary] leading-none">APEX AI</p>
            <p className="text-[10px] text-[--text-muted] mt-0.5">Intelligence OS</p>
          </div>
        </div>
      </div>

      {/* Nav */}
      <nav className="flex-1 overflow-y-auto px-3 py-4 space-y-0.5">
        {nav.map(({ href, icon: Icon, label }) => {
          const active = path === href || path.startsWith(href + "/");
          return (
            <Link
              key={href}
              href={href}
              className={`flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm transition-all duration-100 ${
                active
                  ? "bg-[--accent-muted] text-[--accent] font-medium"
                  : "text-[--text-secondary] hover:text-[--text-primary] hover:bg-[--surface-2]"
              }`}
            >
              <Icon size={15} />
              {label}
            </Link>
          );
        })}
      </nav>

      {/* Logout */}
      <div className="px-3 pb-4">
        <button
          onClick={logout}
          className="w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm text-[--text-secondary] hover:text-red-400 hover:bg-red-500/10 transition-all duration-100"
        >
          <LogOut size={15} />
          Log out
        </button>
      </div>
    </aside>
  );
}
