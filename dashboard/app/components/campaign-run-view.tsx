"use client";


import * as React from "react";
import { useQuery } from "@tanstack/react-query";
import { toast } from "sonner";
import { CheckCircle2, Loader2, XCircle, Clock, Search, ListChecks, ScrollText, Info } from "lucide-react";
import { campaignsApi, type Campaign, type CampaignRuns } from "@/app/lib/api";
import { Badge } from "@/app/components/ui/badge";
import { Button } from "@/app/components/ui/button";
import { Progress } from "@/app/components/ui/progress";
import { Separator } from "@/app/components/ui/separator";
import { Skeleton } from "@/app/components/ui/skeleton";

const STAGE_META: Record<string, { label: string }> = {
  discover: { label: "Discover" },
  enrich: { label: "Enrich" },
  profile: { label: "Profile" },
  demo: { label: "Demo" },
  draft: { label: "Draft" },
  send: { label: "Send" },
  followup: { label: "Follow-up" },
  call: { label: "Call" },
};

function stageBadge(status: string, count?: number | null) {
  if (status === "running") return <Badge variant="warning"><Loader2 className="h-3 w-3 animate-spin" /> running</Badge>;
  if (status === "done") return <Badge variant="secondary"><CheckCircle2 className="h-3 w-3 text-emerald-500" /> done{count ? " (" + count + ")" : ""}</Badge>;
  if (status === "failed") return <Badge variant="destructive"><XCircle className="h-3 w-3" /> failed</Badge>;
  if (status === "skipped") return <Badge variant="outline"><Clock className="h-3 w-3" /> skipped</Badge>;
  return <Badge variant="outline">{status}</Badge>;
}

function EventLog({ events }: { events: CampaignRuns["events"] }) {
  const [shown, setShown] = React.useState(18);
  const all = Object.entries(events || {}).flatMap(([runId, list]) =>
    (list || []).map((e) => ({ runId, ...e }))).sort((a, b) => String(a.ts || "").localeCompare(String(b.ts || "")));
  const items = all.slice(-shown).reverse();
  if (!all.length) {
    return <p className="text-sm text-muted-foreground">No run events logged yet. Press "Run" to start a pipeline run.</p>;
  }
  return (
    <div className="max-h-56 space-y-1 overflow-y-auto rounded-md border bg-muted/40 p-2 font-mono text-xs">
      {items.map((e, i) => (
        <div key={"" + (e.ts || "") + i} className="flex items-center gap-2">
          <span className="text-muted-foreground">{e.ts ? e.ts.slice(11, 19) : "--:--:--"}</span>
          <span className="w-16 uppercase text-muted-foreground">{e.stage}</span>
          {stageBadge(e.status, e.count)}
          <span className="truncate">{e.message || ""}</span>
          {e.elapsed_ms != null ? <span className="ml-auto shrink-0 text-muted-foreground">{e.elapsed_ms}ms</span> : null}
        </div>
      ))}
      {all.length > shown ? (
        <button className="text-muted-foreground underline" onClick={() => setShown((s) => s + 30)}>show more</button>
      ) : null}
    </div>
  );
}

export default function CampaignRunView({ campaign }: { campaign: Campaign }) {
  const lastStatus = React.useRef<string | null>(null);
  const toasted = React.useRef<string | null>(null);
  const { data, isLoading, isError, refetch } = useQuery({
    queryKey: ["campaign-runs", campaign.id],
    queryFn: () => campaignsApi.runs(campaign.id),
    staleTime: 0,
    refetchInterval: (q: any) => (q.state.data?.latest_run_status === "running" ? 2000 : false),
  });

  // toast when a run transitions to done/failed
  React.useEffect(() => {
    const status = data?.latest_run_status;
    if (status && status !== lastStatus.current && lastStatus.current) {
      if (status === "done" && toasted.current !== data?.summary_banner) {
        toasted.current = data?.summary_banner || "done";
        toast.success("Run finished: " + (data?.summary_banner || "pipeline complete"));
      } else if (status === "failed") {
        toasted.current = "failed-" + Date.now();
        toast.error("Campaign run failed. Check the run view for details.");
      }
    }
    if (status) lastStatus.current = status;
  }, [data?.latest_run_status, data?.summary_banner]);

  const runs: CampaignRuns | undefined = data;
  const leadTotal = runs?.lead_total ?? 0;
  const done = (runs?.stages ?? []).reduce((acc, s) => acc + s.count, 0);
  const progressPct = leadTotal ? Math.min(100, Math.round((done / leadTotal) * 100)) : 0;
  const live = runs?.latest_run_status === "running";

  return (
    <div className="space-y-5">
      <p className="text-sm text-muted-foreground">
        Live pipeline progress for <span className="font-medium text-foreground">{campaign.name}</span>.
        {live ? " Polling every 2s while the run is active…" : " All runs idle."}
      </p>
      {isLoading ? <Skeleton className="h-24" /> : null}
      {isError ? (
        <div className="flex items-center justify-between rounded-md border border-destructive/40 p-3 text-sm">
          <span className="inline-flex items-center gap-2 text-destructive"><XCircle className="h-4 w-4" /> Could not load run status.</span>
          <Button size="sm" variant="outline" onClick={() => refetch()}>Retry</Button>
        </div>
      ) : null}

      {!isLoading && runs ? (
        <>
          {/* summary banner */}
          {runs.summary_banner ? (
            <div className="rounded-md border border-emerald-500/30 bg-emerald-500/5 px-3 py-2 text-sm">
              <span className="inline-flex items-center gap-2"><Info className="h-4 w-4 text-emerald-500" /> {runs.summary_banner}</span>
            </div>
          ) : null}
          {runs.latest_run_status === "failed" ? (
            <div className="rounded-md border border-destructive/40 bg-destructive/10 px-3 py-2 text-sm text-destructive">
              Last run failed — check the log below and try again, or widen your area/categories.
            </div>
          ) : null}

          <div className="rounded-md border p-3">
            <div className="mb-2 flex items-center justify-between text-xs text-muted-foreground">
              <span className="font-medium text-foreground">Pipeline stages</span>
              <span>{leadTotal} leads</span>
            </div>
            <div className="mb-3 grid grid-cols-2 gap-2 sm:grid-cols-3 md:grid-cols-6">
              {(runs.stages || []).map((s) => {
                const meta = STAGE_META[s.stage] || { label: s.stage };
                return (
                  <div key={s.stage} className="rounded-md border p-2 text-center">
                    <div className="text-lg font-bold tabular-nums">{s.count}</div>
                    <div className="text-[11px] uppercase tracking-wide text-muted-foreground">{meta.label}</div>
                  </div>
                );
              })}
            </div>
            <Progress value={progressPct} />
            <p className="mt-1 text-right text-[11px] text-muted-foreground">{progressPct}% through pipeline</p>
          </div>

          <Separator />

          <div>
            <h3 className="mb-2 flex items-center gap-2 text-sm font-medium"><ScrollText className="h-4 w-4" /> Live run log</h3>
            <EventLog events={runs.events} />
          </div>

          <Separator />

          <div>
            <h3 className="mb-2 flex items-center gap-2 text-sm font-medium"><Search className="h-4 w-4" /> Apify runs</h3>
            {(runs.apify_runs || []).length === 0 ? (
              <p className="text-sm text-muted-foreground">No apify runs yet. Press Run on the campaign card to start one.</p>
            ) : (
              <ul className="space-y-2">
                {(runs.apify_runs || []).map((ar) => (
                  <li key={ar.id} className="flex flex-wrap items-center justify-between gap-2 rounded-md border p-2 text-sm">
                    <div className="min-w-0">
                      <div className="flex items-center gap-2">
                        <span className="font-medium">{ar.actor_id}</span>
                        {ar.search ? <span className="truncate text-muted-foreground">{ar.search}</span> : null}
                      </div>
                      <div className="mt-1 flex flex-wrap items-center gap-x-3 gap-y-1 text-xs text-muted-foreground">
                        <span>{ar.items_fetched} fetched</span>
                        <span>{ar.leads_imported} imported</span>
                        {ar.created_at ? <span>{new Date(ar.created_at).toLocaleString()}</span> : null}
                      </div>
                      {ar.error ? <p className="mt-1 text-xs text-destructive">{ar.error}</p> : null}
                    </div>
                    {stageBadge(ar.status)}
                  </li>
                ))}
              </ul>
            )}
          </div>

          <Separator />

          <div>
            <h3 className="mb-2 flex items-center gap-2 text-sm font-medium"><ListChecks className="h-4 w-4" /> Job health</h3>
            {Object.keys(runs.jobs || {}).length === 0 ? (
              <p className="text-sm text-muted-foreground">No worker jobs recorded yet.</p>
            ) : (
              <ul className="space-y-1 text-sm">
                {Object.entries(runs.jobs).map((entry) => {
                  const stage = entry[0];
                  const statuses = entry[1];
                  return (
                    <li key={stage} className="flex items-center gap-2">
                      <span className="w-28 font-mono text-xs text-muted-foreground">{stage}</span>
                      {Object.entries(statuses).map((kv) => <span key={kv[0]}>{stageBadge(kv[0])} {"x" + kv[1]}</span>)}
                    </li>
                  );
                })}
              </ul>
            )}
          </div>

          <p className="text-xs text-muted-foreground">Dry-run: this view never sends anything real.</p>
        </>
      ) : null}
    </div>
  );
}