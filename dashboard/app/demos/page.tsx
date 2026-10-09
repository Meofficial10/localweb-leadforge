"use client";

import * as React from "react";
import { useQuery } from "@tanstack/react-query";
import { Globe, RefreshCw } from "lucide-react";
import { PageHeader } from "@/app/components/shared/page-header";
import { Card, CardContent } from "@/app/components/ui/card";
import { Badge } from "@/app/components/ui/badge";
import { demosApi } from "@/app/lib/api";

export default function DemoSitesPage() {
  const { data, isLoading, isError, refetch } = useQuery({
    queryKey: ["demosites"],
    queryFn: demosApi.list,
    staleTime: 15000,
  });
  const rows = data ?? [];
  const statusColor: Record<string, string> = {
    live: "bg-green-500/15 text-green-500",
    deploying: "bg-amber-500/15 text-amber-500",
    failed: "bg-red-500/15 text-red-500",
    draft: "bg-muted text-muted-foreground",
  };
  return (
    <div>
      <PageHeader
        title="Demo sites"
        description="Built demo websites served locally at /demos/slug/ for each generated lead."
        actions={<button type="button" onClick={() => refetch()} className="inline-flex items-center gap-2 rounded-md border px-3 py-1.5 text-sm font-medium hover:bg-accent/60"><RefreshCw className="h-3.5 w-3.5" /> Refresh</button>}
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
                <th className="px-4 py-3">Template / theme</th>
                <th className="px-4 py-3">Status</th>
                <th className="px-4 py-3">Created</th>
                <th className="px-4 py-3">Preview</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((d) => (
                <tr key={d.site_id} className="border-b last:border-0">
                  <td className="px-4 py-3 font-medium">{d.lead_name || d.lead_id}</td>
                  <td className="px-4 py-3 text-muted-foreground">{d.template || "-"}</td>
                  <td className="px-4 py-3"><Badge className={statusColor[d.deploy_status || "draft"] || ""}>{d.deploy_status || "draft"}</Badge></td>
                  <td className="px-4 py-3 text-muted-foreground">{d.created_at ? d.created_at.slice(0, 19) : "-"}</td>
                  <td className="px-4 py-3"><a href={d.url || "/demos/" + d.slug + "/"} target="_blank" rel="noreferrer" className="inline-flex items-center gap-1 text-primary underline-offset-2 hover:underline"><Globe className="h-3.5 w-3.5" /> Open demo</a></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div></CardContent></Card>
      ) : null}
    </div>
  );
}