"use client";

export const dynamic = "force-dynamic";

import * as React from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Send, CheckCircle2, SkipForward, RefreshCw, PenSquare, Loader2 } from "lucide-react";
import { queueApi, type Draft } from "@/app/lib/api";
import { PageHeader } from "@/app/components/shared/page-header";
import { EmptyState } from "@/app/components/shared/empty-state";
import { StatusChip } from "@/app/components/shared/status-badge";
import { DemoDataBadge } from "@/app/components/shared/demo-data-badge";
import { Badge } from "@/app/components/ui/badge";
import { Button } from "@/app/components/ui/button";
import { Card, CardContent } from "@/app/components/ui/card";
import { Textarea } from "@/app/components/ui/textarea";
import { Input } from "@/app/components/ui/input";
import {
  Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle,
} from "@/app/components/ui/dialog";
import { Skeleton } from "@/app/components/ui/skeleton";
import { toast } from "sonner";
import { asError, truncate } from "@/app/lib/utils";

function EditDraftDialog({ draft, onDone }: { draft: Draft | null; onDone: () => void }) {
  const [subject, setSubject] = React.useState(draft?.subject || "");
  const [body, setBody] = React.useState(draft?.body || "");
  const qc = useQueryClient();
  const save = useMutation({
    mutationFn: () => queueApi.edit(draft!.id, { subject, body }),
    onSuccess: () => { toast.success("Draft updated"); qc.invalidateQueries({ queryKey: ["queue"] }); onDone(); },
    onError: (e) => toast.error(asError(e)),
  });
  React.useEffect(() => { if (draft) { setSubject(draft.subject || ""); setBody(draft.body || ""); } }, [draft]);
  return (
    <Dialog open={!!draft} onOpenChange={(o) => !o && onDone()}>
      <DialogContent className="sm:max-w-2xl">
        <DialogHeader>
          <DialogTitle>Edit outreach draft</DialogTitle>
          <DialogDescription>To: {draft?.lead_name} · step {draft?.sequence_step}</DialogDescription>
        </DialogHeader>
        <div className="space-y-3">
          <div className="space-y-1.5">
            <label htmlFor="draft-subject" className="text-sm font-medium">Subject</label>
            <Input id="draft-subject" value={subject} onChange={(e) => setSubject(e.target.value)} />
          </div>
          <div className="space-y-1.5">
            <label htmlFor="draft-body" className="text-sm font-medium">Body</label>
            <Textarea id="draft-body" value={body} onChange={(e) => setBody(e.target.value)} className="min-h-[260px]" />
          </div>
          <div className="flex justify-end gap-2">
            <Button variant="outline" onClick={onDone}>Cancel</Button>
            <Button onClick={() => save.mutate()} disabled={save.isPending}>
              {save.isPending && <Loader2 className="h-4 w-4 animate-spin" />} Save
            </Button>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
}

function DraftRow({ draft, onEdit }: { draft: Draft; onEdit: (d: Draft) => void }) {
  const qc = useQueryClient();
  const invalidate = () => qc.invalidateQueries({ queryKey: ["queue"] });
  const approve = useMutation({
    mutationFn: () => queueApi.approve(draft.id),
    onSuccess: () => { toast.success("Approved"); invalidate(); },
    onError: (e) => toast.error(asError(e)),
  });
  const skip = useMutation({
    mutationFn: () => queueApi.skip(draft.id),
    onSuccess: () => { toast.success("Skipped"); invalidate(); },
    onError: (e) => toast.error(asError(e)),
  });
  const regen = useMutation({
    mutationFn: () => queueApi.regenerate(draft.id),
    onSuccess: () => { toast.success("Regenerated"); invalidate(); },
    onError: (e) => toast.error(asError(e)),
  });
  const ok = !!draft.compliance && draft.compliance.ok !== false;
  return (
    <Card className="overflow-hidden">
      <CardContent className="space-y-2 p-4">
        <div className="flex flex-wrap items-center gap-2">
          <span className="font-semibold">{draft.lead_name}</span>
          {draft.is_demo ? <DemoDataBadge /> : null}
          {draft.lead_category && <Badge variant="secondary">{draft.lead_category}</Badge>}
          <Badge variant="outline">step {draft.sequence_step}</Badge>
          <div className="ml-auto flex items-center gap-2">
            {!ok && draft.compliance && draft.compliance.reasons && (
              <Badge variant="warning" title="Approval only marks this draft ready; the send gate still applies (dry-run never sends).">compliance: {draft.compliance.reasons.join(", ")}</Badge>
            )}
            <StatusChip status={draft.status} />
          </div>
        </div>
        <div>
          <p className="text-sm font-medium text-primary">{draft.subject || "(no subject)"}</p>
          <p className="mt-1 whitespace-pre-wrap text-sm text-muted-foreground">{truncate(draft.body || "", 400)}</p>
        </div>
        {draft.status === "draft" && (
          <div className="flex flex-wrap gap-1.5">
            <Button size="sm" onClick={() => approve.mutate()} disabled={approve.isPending}>
              <CheckCircle2 className="h-3.5 w-3.5" /> Approve
            </Button>
            <Button size="sm" variant="outline" onClick={() => skip.mutate()}>
              <SkipForward className="h-3.5 w-3.5" /> Skip
            </Button>
            <Button size="sm" variant="outline" onClick={() => regen.mutate()}>
              <RefreshCw className="h-3.5 w-3.5" /> Regenerate
            </Button>
            <Button size="sm" variant="outline" onClick={() => onEdit(draft)}>
              <PenSquare className="h-3.5 w-3.5" /> Edit
            </Button>
          </div>
        )}
      </CardContent>
    </Card>
  );
}

export default function OutreachPage() {
  const { data, isLoading, isError } = useQuery({ queryKey: ["queue"], queryFn: queueApi.list });
  const [editing, setEditing] = React.useState<Draft | null>(null);
  const [tab, setTab] = React.useState<"draft" | "approved" | "sent">("draft");
  const all = data || [];
  const drafts = all.filter((q) => {
    if (tab === "sent") return q.status === "sent";
    if (tab === "approved") return q.status === "approved";
    return q.status === "draft" || q.status === "pending";
  });
  return (
    <div>
      <PageHeader
        title="Outreach Queue"
        description="AI-drafted outreach messages awaiting review. Approve to send (dry-run by default), skip, regenerate or edit."
      />
      <div className="mb-4 inline-flex rounded-lg bg-muted p-1" role="tablist" aria-label="Queue view">
        {([["draft", "Needs review"], ["approved", "Approved"], ["sent", "Sent"]] as const).map(([k, label2]) => (
          <button
            key={k}
            role="tab"
            aria-selected={tab === k}
            onClick={() => setTab(k as any)}
            className={
              "rounded-md px-3 py-1 text-sm font-medium transition-colors " +
              (tab === k ? "bg-background text-foreground shadow" : "text-muted-foreground hover:text-foreground")
            }
          >
            {label2}
          </button>
        ))}
      </div>
      {isLoading ? (
        <div className="space-y-3">{[1, 2, 3].map((i) => <Skeleton key={i} className="h-28" />)}</div>
      ) : isError ? (
        <p className="text-sm text-destructive">Couldn&apos;t load the queue.</p>
      ) : drafts.length === 0 ? (
        <EmptyState
          icon={<Send className="h-6 w-6" />}
          title={"No " + tab + " messages"}
          description="Once a campaign discovers leads, AI drafts appear here for your approval."
        />
      ) : (
        <div className="space-y-3">{drafts.map((x) => <DraftRow key={x.id} draft={x} onEdit={setEditing} />)}</div>
      )}
      <EditDraftDialog draft={editing} onDone={() => setEditing(null)} />
    </div>
  );
}
