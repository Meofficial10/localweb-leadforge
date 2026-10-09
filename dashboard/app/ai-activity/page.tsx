"use client";

import * as React from "react";
import { useQuery } from "@tanstack/react-query";
import { Sparkles, Clock, AlertTriangle, RefreshCw } from "lucide-react";
import { aiApi } from "@/app/lib/api";
import { PageHeader } from "@/app/components/shared/page-header";
import { Card, CardContent, CardHeader, CardTitle } from "@/app/components/ui/card";
import { Badge } from "@/app/components/ui/badge";
import { Button } from "@/app/components/ui/button";
import { Skeleton } from "@/app/components/ui/skeleton";

const PURPOSE_LABEL: Record<string, string> = {
  profile: "Profile", demo: "Demo site", draft: "Email draft", test: "Test connection", playground: "Playground",
};

function PurposeBadge({ purpose }: { purpose: string }) {
  return <Badge variant="secondary">{PURPOSE_LABEL[purpose] || purpose}</Badge>;
}

export default function AiActivityPage() {
  const { data, isLoading, isError, refetch } = useQuery({
    queryKey: ["ai-activity"],
    queryFn: aiApi.activity,
    staleTime: 5000,
  });
  const calls = data?.calls ?? [];
  return (
    <div>
      <PageHeader title="AI activity" description="Every LLM call LeadForge made: model, latency, tokens, and the actual prompt and response." actions={<Button size="sm" variant="outline" onClick={() => refetch()}><RefreshCw className="h-3.5 w-3.5" /> Refresh</Button>} />
      {isLoading ? <Skeleton className="mt-4 h-40" /> : null}
      {isError ? <p className="mt-4 text-sm text-destructive">Could not load AI activity - is the backend on :8000 up?</p> : null}
      {data ? (
        <>
          <div className="mt-4 grid gap-4 sm:grid-cols-4">
            <Card><CardHeader className="pb-1"><CardTitle className="text-xs text-muted-foreground">Calls today</CardTitle></CardHeader><CardContent><p className="text-2xl font-bold">{data.calls_today}</p><p className="text-xs text-muted-foreground">{data.total_calls} total all-time</p></CardContent></Card>
            <Card><CardHeader className="pb-1"><CardTitle className="text-xs text-muted-foreground">Avg latency</CardTitle></CardHeader><CardContent><p className="text-2xl font-bold">{data.avg_latency_ms != null ? (data.avg_latency_ms / 1000).toFixed(1) + "s" : "-"}</p><p className="text-xs text-muted-foreground">today</p></CardContent></Card>
            <Card><CardHeader className="pb-1"><CardTitle className="text-xs text-muted-foreground">Failures today</CardTitle></CardHeader><CardContent><p className={"text-2xl font-bold " + (data.failures_today ? "text-destructive" : "")}>{data.failures_today}</p><p className="text-xs text-muted-foreground">today</p></CardContent></Card>
            <Card><CardHeader className="pb-1"><CardTitle className="text-xs text-muted-foreground">Active model</CardTitle></CardHeader><CardContent><p className="truncate text-sm font-medium">{data.active.model || "(none)"}</p><p className="text-xs text-muted-foreground">{data.active.provider}</p></CardContent></Card>
          </div>
          <Card className="mt-4">
            <CardHeader className="pb-2"><CardTitle className="text-sm"><Sparkles className="mr-1 inline h-4 w-4" /> Recent LLM calls</CardTitle></CardHeader>
            <CardContent className="max-h-[560px] space-y-2 overflow-y-auto">
              {calls.length === 0 ? <p className="text-sm text-muted-foreground">No LLM calls recorded yet. Turn on a real model or use the Playground.</p> : null}
              {calls.map((c) => (
                <div key={c.id} className="rounded-md border p-3 text-sm">
                  <div className="flex flex-wrap items-center gap-2">
                    <PurposeBadge purpose={c.purpose} />
                    <Badge variant="outline">{c.provider}</Badge>
                    {c.model ? <Badge variant="outline">{c.model}</Badge> : null}
                    {c.status === "ok" ? <Badge variant="secondary"><span className="text-emerald-600">ok</span></Badge> : <Badge variant="destructive"><AlertTriangle className="h-3 w-3" /> {c.status}</Badge>}
                    {c.latency_ms != null ? <span className="ml-auto inline-flex items-center gap-1 text-xs text-muted-foreground"><Clock className="h-3 w-3" /> {(c.latency_ms / 1000).toFixed(1)}s</span> : null}
                    {c.total_tokens != null ? <span className="text-xs text-muted-foreground">{c.total_tokens} tokens</span> : null}
                    {c.created_at ? <span className="text-xs text-muted-foreground">{new Date(c.created_at).toLocaleString()}</span> : null}
                  </div>
                  {c.error ? <p className="mt-2 text-xs text-destructive">{c.error}</p> : null}
                  {c.prompt ? <p className="mt-2 whitespace-pre-wrap text-xs text-muted-foreground">{c.prompt.slice(0, 240)}</p> : null}
                  {c.response ? <p className="mt-1 whitespace-pre-wrap rounded bg-muted/40 p-2 font-mono text-xs">{c.response.slice(0, 240)}</p> : null}
                </div>
              ))}
            </CardContent>
          </Card>
        </>
      ) : null}
    </div>
  );
}