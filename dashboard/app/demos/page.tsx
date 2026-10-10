"use client";

import * as React from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Globe, RefreshCw, Trash2, RotateCw, FileText, ExternalLink } from "lucide-react";
import { PageHeader } from "@/app/components/shared/page-header";
import { Card, CardContent } from "@/app/components/ui/card";
import { Badge } from "@/app/components/ui/badge";
import { Button } from "@/app/components/ui/button";
import { demosApi, leadsApi, type DemoInfo, type DemoBuildLog, type DemoTheme } from "@/app/lib/api";

const THEME_LABELS: Record<string, string> = {
  clinical: "Clinical",
  salon: "Salon",
  cafe: "Cafe",
  boutique: "Boutique",
  repair: "Repair",
  education: "Education",
  fitness: "Fitness",
  generic: "Generic",
};

const buildStatusColor: Record<string, string> = {
  live: "bg-green-500/15 text-green-500",
  deploying: "bg-amber-500/15 text-amber-500",
  failed: "bg-red-500/15 text-red-500",
  draft: "bg-muted text-muted-foreground",
};

function fmtSize(minW?: number | null): string {
  return typeof minW === "number" ? (minW / 1024).toFixed(1) + " KB" : "—";
}

export default function DemoSitesPage() {
  const qc = useQueryClient();
  const [buildLog, setBuildLog] = React.useState<Record<string, DemoBuildLog | null | undefined>>({});
  const [err, setErr] = React.useState<string | null>(null);
  const [themes, setThemes] = React.useState<DemoTheme[]>([]);

  const { data, isLoading, isError, refetch, isFetching } = useQuery({
    queryKey: ["demosites"],
    queryFn: () => demosApi.list(),
    staleTime: 15000,
  });

  React.useEffect(() => {
    demosApi.themes().then(setThemes).catch(() => {});
  }, []);

  const regenerate = useMutation({
    mutationFn: (id: string) => leadsApi.regenerateDemo(id),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["demosites"] }); },
  });

  const switchTheme = useMutation({
    mutationFn: (p: { id: string; theme: string }) => demosApi.setTheme(p.id, p.theme),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["demosites"] }); },
  });

  const remove = useMutation({
    mutationFn: (id: string) => demosApi.deleteForLead(id),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["demosites"] }); },
  });

  const openLog = React.useCallback((id: string) => {
    demosApi.buildLog(id)
      .then((lg) => setBuildLog((m) => ({ ...m, [id]: lg })))
      .catch((e) => { if (e?.message) setErr(e.message); });
  }, []);

  const rows = data ?? [];

  return (
    <div>
      <PageHeader
        title="Demo sites"
        description="Demo websites per lead, served locally. Hosting mode: local files until a deploy provider is configured."
        actions={<Button variant="outline" size="sm" onClick={() => refetch()} disabled={isFetching}><RefreshCw className="h-3.5 w-3.5" /> Refresh</Button>}
      />
      {isLoading ? <Card><CardContent className="p-6 text-sm text-muted-foreground">Loading demo sites…</CardContent></Card> : null}
      {isError ? <Card><CardContent className="p-6 text-sm text-destructive">Could not load demo sites — is the backend up?</CardContent></Card> : null}
      {!isLoading && !isError && rows.length === 0 ? <Card><CardContent className="p-6 text-sm text-muted-foreground">No demo sites yet. Run a campaign to generate demo websites for leads.</CardContent></Card> : null}
      {rows.length > 0 ? (
        <Card><CardContent className="p-0"><div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b text-left text-xs uppercase tracking-wide text-muted-foreground">
                <th className="px-4 py-3">Business</th>
                <th className="px-4 py-3">Theme</th>
                <th className="px-4 py-3">Status</th>
                <th className="px-4 py-3">Hosting</th>
                <th className="px-4 py-3">Size</th>
                <th className="px-4 py-3">Created</th>
                <th className="px-4 py-3">Actions</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((d) => {
                const log = buildLog[d.lead_id];
                return (
                  <tr key={d.site_id} className="border-b last:border-0 align-top">
                    <td className="px-4 py-3 font-medium">{d.lead_name || d.lead_id}</td>
                    <td className="px-4 py-3">
                      <select
                        value={d.template ?? "generic"}
                        onChange={(e) => {
                          setErr(null);
                          switchTheme.mutateAsync({ id: d.lead_id, theme: e.target.value }).catch((x) => setErr(String((x as Error)?.message || x)));
                        }}
                        className="h-8 rounded-md border bg-transparent px-2 text-xs"
                        aria-label={"Switch theme for " + d.lead_name}
                      >
                        {(themes.length ? themes : Object.keys(THEME_LABELS).map((k) => ({ key: k, name: THEME_LABELS[k] }))).map((th) => (
                          <option key={th.key} value={th.key}>{th.name}</option>
                        ))}
                      </select>
                    </td>
                    <td className="px-4 py-3"><Badge className={buildStatusColor[d.deploy_status || "draft"] || ""}>{d.deploy_status || "draft"}</Badge>{log?.expired ? <span className="ml-2 text-xs text-amber-600">expired</span> : null}</td>
                    <td className="px-4 py-3 text-muted-foreground">{d.deploy_status === "live" && d.url?.startsWith("http") ? "Deployed" : "Local only"}</td>
                    <td className="px-4 py-3 text-muted-foreground">{fmtSize(d.size_kb)}</td>
                    <td className="px-4 py-3 text-muted-foreground">{d.created_at ? d.created_at.slice(0, 19) : "-"}</td>
                    <td className="px-4 py-3">
                      <div className="flex flex-wrap gap-2">
                        <a href={d.url || "/demos/" + d.slug + "/"} target="_blank" rel="noreferrer" className="inline-flex items-center gap-1 rounded-md border px-2 py-1 text-xs font-medium hover:bg-accent/60"><Globe className="h-3.5 w-3.5" /> Open</a>
                        <button type="button" onClick={() => { setErr(null); regenerate.mutateAsync(d.lead_id).catch((x) => setErr(String((x as Error)?.message || x))); }} className="inline-flex items-center gap-1 rounded-md border px-2 py-1 text-xs font-medium hover:bg-accent/60" aria-label={"Regenerate demo for " + d.lead_name}><RotateCw className="h-3.5 w-3.5" /> Regenerate</button>
                        <button type="button" onClick={() => openLog(d.lead_id)} className="inline-flex items-center gap-1 rounded-md border px-2 py-1 text-xs font-medium hover:bg-accent/60" aria-label={"Build log for " + d.lead_name}><FileText className="h-3.5 w-3.5" /> Log</button>
                        <button type="button" onClick={() => { if (window.confirm("Delete this demo site? The page and its storage are removed.")) { setErr(null); remove.mutateAsync(d.lead_id).catch((x) => setErr(String((x as Error)?.message || x))); } }} className="inline-flex items-center gap-1 rounded-md border border-destructive/40 px-2 py-1 text-xs font-medium text-destructive hover:bg-destructive/10" aria-label={"Delete demo for " + d.lead_name}><Trash2 className="h-3.5 w-3.5" /> Delete</button>
                      </div>
                      {log ? (
                        <details className="mt-2 rounded-md bg-muted/40 p-3 text-xs">
                          <summary className="cursor-pointer font-medium text-muted-foreground">Build log</summary>
                          <div className="mt-2 space-y-1 text-muted-foreground">
                            <p>template: {log.template ?? "—"} · status: {log.deploy_status ?? "—"}</p>
                            <p>created: {log.created_at ? log.created_at.slice(0, 19) : "—"} · expired: {log.expired ? "yes" : "no"}</p>
                            {log.preview_url ? <p>preview: <a href={log.preview_url} target="_blank" rel="noreferrer" className="underline"><ExternalLink className="inline h-3 w-3" /> {log.preview_url}</a></p> : null}
                            {log.facts && log.facts.length > 0 ? (
                              <div className="mt-1">
                                <p className="font-medium">Verified facts used ({log.facts.length})</p>
                                <ul className="ml-4 list-disc space-y-0.5">
                                  {log.facts.slice(0, 10).map((f, i) => <li key={i}><span className="font-medium">{f.field}:</span> {f.value} <span className="opacity-70">[src: {f.source}]</span></li>)}
                                </ul>
                              </div>
                            ) : <p>No verified facts recorded.</p>}
                          </div>
                        </details>
                      ) : null}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div></CardContent></Card>
      ) : null}
      {err ? <Card><CardContent className="mt-4 p-4 text-sm text-destructive">{err} <button type="button" onClick={() => setErr(null)} className="ml-2 underline">dismiss</button></CardContent></Card> : null}
      {regenerate.isPending ? <p className="mt-3 text-xs text-muted-foreground">Regenerating…</p> : null}
    </div>
  );
}
