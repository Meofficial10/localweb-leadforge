"use client";

export const dynamic = "force-dynamic";

import * as React from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Inbox as InboxIcon, MailCheck, UserCheck, Loader2 } from "lucide-react";
import { inboxApi, type InboxItem } from "@/app/lib/api";
import { PageHeader } from "@/app/components/shared/page-header";
import { EmptyState } from "@/app/components/shared/empty-state";
import { Badge } from "@/app/components/ui/badge";
import { Button } from "@/app/components/ui/button";
import { Card, CardContent } from "@/app/components/ui/card";
import { Skeleton } from "@/app/components/ui/skeleton";
import { toast } from "sonner";
import { asError, formatDateTime } from "@/app/lib/utils";

const intentColor: Record<string, string> = {
  interested: "bg-success/15 text-success",
  not_interested: "bg-muted text-muted-foreground",
  question: "bg-primary/15 text-primary",
  opt_out: "bg-destructive/15 text-destructive",
  neutral: "bg-secondary text-secondary-foreground",
};

function InboxRow({ item }: { item: InboxItem }) {
  const qc = useQueryClient();
  const invalidate = () => qc.invalidateQueries({ queryKey: ["inbox"] });
  const handle = useMutation({
    mutationFn: () => inboxApi.handle(item.id),
    onSuccess: () => { toast.success("Marked handled"); invalidate(); },
    onError: (e) => toast.error(asError(e)),
  });
  const takeOver = useMutation({
    mutationFn: () => inboxApi.takeOver(item.id),
    onSuccess: () => { toast.success("Noted — reply manually"); invalidate(); },
    onError: (e) => toast.error(asError(e)),
  });
  return (
    <Card>
      <CardContent className="space-y-2 p-4">
        <div className="flex flex-wrap items-center gap-2">
          <span className="font-semibold">{item.lead_name || "(unknown lead)"}</span>
          {item.lead_email && <span className="font-mono text-xs text-muted-foreground">{item.lead_email}</span>}
          <Badge className={intentColor[item.intent] || "bg-muted"}>{item.intent}</Badge>
          {item.handled ? <Badge variant="secondary">handled</Badge> : <Badge variant="warn">new</Badge>}
          <span className="ml-auto text-xs text-muted-foreground">{formatDateTime(item.received_at)}</span>
        </div>
        <p className="text-sm font-medium text-primary">{item.subject || "(no subject)"}</p>
        <p className="whitespace-pre-wrap text-sm text-muted-foreground">{item.content || ""}</p>
        {!item.handled && (
          <div className="flex gap-1.5">
            <Button size="sm" onClick={() => handle.mutate()}>
              <MailCheck className="h-3.5 w-3.5" /> Mark handled
            </Button>
            <Button size="sm" variant="outline" onClick={() => takeOver.mutate()}>
              <UserCheck className="h-3.5 w-3.5" /> Take over manually
            </Button>
          </div>
        )}
      </CardContent>
    </Card>
  );
}

export default function InboxPage() {
  const [scope, setScope] = React.useState("unhandled");
  const { data, isLoading, isError } = useQuery({ queryKey: ["inbox", scope], queryFn: () => inboxApi.list(scope) });
  return (
    <div>
      <PageHeader
        title="Inbox"
        description="Inbound replies from leads, auto-classified by intent. Opt-outs are auto-suppressed."
      />
      <div className="mb-4 inline-flex rounded-lg bg-muted p-1" role="tablist" aria-label="Inbox scope">
        {([["unhandled", "Unhandled"], ["handled", "Handled"], ["all", "All"]] as const).map(([k, label2]) => (
          <button
            key={k}
            role="tab"
            aria-selected={scope === k}
            onClick={() => setScope(k)}
            className={
              "rounded-md px-3 py-1 text-sm font-medium transition-colors " +
              (scope === k ? "bg-background text-foreground shadow" : "text-muted-foreground hover:text-foreground")
            }
          >
            {label2}
          </button>
        ))}
      </div>
      {isLoading ? (
        <div className="space-y-3">{[1, 2, 3].map((i) => <Skeleton key={i} className="h-32" />)}</div>
      ) : isError ? (
        <p className="text-sm text-destructive">Couldn&apos;t load the inbox.</p>
      ) : !data || data.length === 0 ? (
        <EmptyState
          icon={<InboxIcon className="h-6 w-6" />}
          title="Inbox is clear"
          description="Replies from leads will appear here, classified by intent. Leave the default scope to see unhandled messages."
        />
      ) : (
        <div className="space-y-3">{data.map((m) => <InboxRow key={m.id} item={m} />)}</div>
      )}
    </div>
  );
}
