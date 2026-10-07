import * as React from "react";
import { Badge } from "@/app/components/ui/badge";

export function ModeChip({ mode }: { mode: string | null | undefined }) {
  if (!mode) return <Badge variant="outline">unknown</Badge>;
  if (mode === "live") return <Badge variant="destructive">live</Badge>;
  if (mode === "paused") return <Badge variant="warning">paused</Badge>;
  return <Badge variant="success">dry-run</Badge>;
}

export function StatusChip({ status }: { status: string | null | undefined }) {
  if (!status) return <Badge variant="secondary">—</Badge>;
  const s = status.toLowerCase();
  if (s.includes("error") || s.includes("failed") || s === "bounced") return <Badge variant="destructive">{status}</Badge>;
  if (s === "sent" || s === "completed" || s === "delivered" || s === "approved" || s === "interested") return <Badge variant="success">{status}</Badge>;
  if (s.includes("pause") || s === "skipped" || s === "unsubscribe") return <Badge variant="warning">{status}</Badge>;
  return <Badge variant="secondary">{status}</Badge>;
}
