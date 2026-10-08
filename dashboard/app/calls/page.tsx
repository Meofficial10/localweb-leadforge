"use client";

export const dynamic = "force-dynamic";

import * as React from "react";
import { useQuery } from "@tanstack/react-query";
import { Phone, Loader2 } from "lucide-react";
import { callsApi, type CallItem } from "@/app/lib/api";
import { PageHeader } from "@/app/components/shared/page-header";
import { DemoDataBadge } from "@/app/components/shared/demo-data-badge";
import { EmptyState } from "@/app/components/shared/empty-state";
import { Badge } from "@/app/components/ui/badge";
import { Card, CardContent } from "@/app/components/ui/card";
import { Skeleton } from "@/app/components/ui/skeleton";
import { formatDateTime } from "@/app/lib/utils";
import {
  Dialog, DialogContent, DialogHeader, DialogTitle,
} from "@/app/components/ui/dialog";

export default function CallsPage() {
  const { data, isLoading, isError } = useQuery({ queryKey: ["calls"], queryFn: callsApi.list });
  const [selected, setSelected] = React.useState<CallItem | null>(null);
  return (
    <div>
      <PageHeader
        title="Calls"
        description="AI voice agent calls placed (dry-run), with transcripts and disclosure flags."
      />
      {isLoading ? (
        <div className="space-y-3">{[1, 2, 3].map((i) => <Skeleton key={i} className="h-24" />)}</div>
      ) : isError ? (
        <p className="text-sm text-destructive">Couldn&apos;t load calls.</p>
      ) : !data || data.length === 0 ? (
        <EmptyState icon={<Phone className="h-6 w-6" />} title="No calls yet" description="Voice agent calls will appear here. All calls run in dry-run by default." />
      ) : (
        <div className="space-y-3">
          {data.map((call) => (
            <Card key={call.id}>
              <CardContent className="flex flex-wrap items-center gap-x-4 gap-y-2 p-4">
                <button className="font-semibold text-left hover:underline" onClick={() => setSelected(call)}>{call.lead_name}</button>
                {call.is_demo ? <DemoDataBadge /> : null}
                <Badge variant={call.ai_disclosed ? "success" : "warn"}>{call.ai_disclosed ? "AI-disclosed" : "disclosure pending"}</Badge>
                {call.outcome ? <Badge variant="secondary">{call.outcome}</Badge> : null}
                {call.duration_sec != null && <span className="text-xs text-muted-foreground">{call.duration_sec}s</span>}
                <span className="ml-auto text-xs text-muted-foreground">{formatDateTime(call.started_at)}</span>
              </CardContent>
            </Card>
          ))}
        </div>
      )}
      {selected && (
        <Dialog open onOpenChange={() => setSelected(null)}>
          <DialogContent className="sm:max-w-lg">
            <DialogHeader>
              <DialogTitle>Call transcript — {selected.lead_name ?? selected.lead_name}</DialogTitle>
            </DialogHeader>
            <p className="whitespace-pre-wrap text-sm">
              {(selected as any).transcript || (selected as any).transcription || "(no transcript available)"}
            </p>
          </DialogContent>
        </Dialog>
      )}
    </div>
  );
}
