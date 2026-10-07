"use client";
import { Check, Clock, Plug, ToggleLeft, X, HelpCircle } from "lucide-react";
import type { IntegrationStatus } from "@/app/lib/api";
import { cn } from "@/app/lib/utils";

const colors: Record<string, string> = {
  gray: "border-border bg-muted text-muted-foreground",
  yellow: "border-yellow-500/40 bg-yellow-500/10 text-yellow-600 dark:text-yellow-400",
  green: "border-green-500/40 bg-green-500/10 text-green-700 dark:text-green-400",
  red: "border-red-500/40 bg-red-500/10 text-red-600 dark:text-red-400",
};

export function statusIcon(status: IntegrationStatus) {
  switch (status.state) {
    case "connected": return <Check className="h-3 w-3" aria-hidden="true" />;
    case "configured": return <Clock className="h-3 w-3" aria-hidden="true" />;
    case "not_configured": return <Plug className="h-3 w-3" aria-hidden="true" />;
    case "disabled": return <ToggleLeft className="h-3 w-3" aria-hidden="true" />;
    case "error": return <X className="h-3 w-3" aria-hidden="true" />;
    default: return <HelpCircle className="h-3 w-3" aria-hidden="true" />;
  }
}

export function StatusPill({ status }: { status: IntegrationStatus }) {
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1 rounded-full border px-2.5 py-0.5 text-xs font-medium",
        colors[status.color] || colors.gray
      )}
      title={status.detail}
    >
      {statusIcon(status)}
      {status.label}
    </span>
  );
}
