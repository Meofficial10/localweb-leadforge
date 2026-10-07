"use client";

import * as React from "react";
import { ShieldCheck, ShieldAlert } from "lucide-react";
import { useQuery } from "@tanstack/react-query";
import { systemApi } from "@/app/lib/api";
import { Badge } from "@/app/components/ui/badge";

export function ModeBadge({ campaignId }: { campaignId?: string | null }) {
  const { data } = useQuery({
    queryKey: ["system-status"],
    queryFn: systemApi.status,
  });

  const emailMode = data?.channels?.email?.effective_mode ?? "dry_run";

  // never show live if force_dry_run
  const isLive = emailMode === "live" && data?.force_dry_run !== true;
  const label = isLive ? "LIVE" : "DRY-RUN";

  return (
    <Badge variant={isLive ? "destructive" : "secondary"} className="gap-1.5 px-3 py-1 text-xs font-bold tracking-wider">
      {isLive ? <ShieldAlert className="h-3 w-3" /> : <ShieldCheck className="h-3 w-3" />}
      {label}
      <span className="sr-only">Effective mode: {isLive ? "live" : "dry-run"}</span>
    </Badge>
  );
}
