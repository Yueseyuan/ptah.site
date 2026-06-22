import { ReactNode } from "react";

type BadgeVariant = "default" | "success" | "warn" | "danger" | "info" | "purple";

const variants: Record<BadgeVariant, string> = {
  default: "bg-[--surface-2] text-[--text-secondary] border-[--border]",
  success: "bg-green-500/10 text-green-400 border-green-500/20",
  warn: "bg-amber-500/10 text-amber-400 border-amber-500/20",
  danger: "bg-red-500/10 text-red-400 border-red-500/20",
  info: "bg-blue-500/10 text-blue-400 border-blue-500/20",
  purple: "bg-violet-500/10 text-violet-400 border-violet-500/20",
};

export function Badge({ children, variant = "default", className = "" }: { children: ReactNode; variant?: BadgeVariant; className?: string }) {
  return (
    <span className={`inline-flex items-center px-2 py-0.5 rounded-md text-xs font-medium border ${variants[variant]} ${className}`}>
      {children}
    </span>
  );
}

export function statusBadgeVariant(status: string): BadgeVariant {
  const map: Record<string, BadgeVariant> = {
    active: "success",
    completed: "success",
    pass: "success",
    use_directly: "success",
    pending: "warn",
    running: "info",
    planning: "info",
    building: "info",
    warn: "warn",
    modify_first: "warn",
    draft: "default",
    proposed: "default",
    failed: "danger",
    fail: "danger",
    do_not_use: "danger",
    reference_only: "purple",
    accepted: "success",
  };
  return map[status] ?? "default";
}
