"use client";

export const dynamic = "force-dynamic";

import * as React from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { ShieldCheck, DatabaseZap, Plus, Search, Trash2, Loader2 } from "lucide-react";
import { complianceApi, systemApi, type SuppressionItem, type AuditItem } from "@/app/lib/api";
import { PageHeader } from "@/app/components/shared/page-header";
import { EmptyState } from "@/app/components/shared/empty-state";
import { KillSwitch } from "@/app/components/kill-switch";
import { Button } from "@/app/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/app/components/ui/card";
import { Badge } from "@/app/components/ui/badge";
import { Input } from "@/app/components/ui/input";
import { Textarea } from "@/app/components/ui/textarea";
import { Label } from "@/app/components/ui/label";
import {
  Table, TableBody, TableCell, TableHead, TableHeader, TableRow,
} from "@/app/components/ui/table";
import { Skeleton } from "@/app/components/ui/skeleton";
import {
  Dialog, DialogContent, DialogHeader, DialogTitle,
} from "@/app/components/ui/dialog";
import {
  AlertDialog, AlertDialogContent, AlertDialogDescription, AlertDialogFooter,
  AlertDialogHeader, AlertDialogTitle, AlertDialogTrigger, AlertDialogCancel, AlertDialogAction,
} from "@/app/components/ui/alert-dialog";
import { toast } from "sonner";
import { asError, formatDateTime, formatNumber } from "@/app/lib/utils";

function AddSuppressionDialog({ onDone }: { onDone: () => void }) {
  const [kind, setKind] = React.useState("email");
  const [value, setValue] = React.useState("");
  const [reason, setReason] = React.useState("");
  const qc = useQueryClient();
  const add = useMutation({
    mutationFn: () => complianceApi.suppress({ kind, value: value.trim(), reason: reason || undefined }),
    onSuccess: () => { toast.success("Added to suppression list"); setValue(""); setReason(""); qc.invalidateQueries({ queryKey: ["suppression"] }); onDone(); },
    onError: (e) => toast.error(asError(e)),
  });
  return (
    <DialogContent>
      <DialogHeader>
        <DialogTitle>Add to suppression list</DialogTitle>
      </DialogHeader>
      <form
        className="space-y-4"
        onSubmit={(e) => { e.preventDefault(); add.mutate(); }}
      >
        <div className="space-y-1.5">
          <Label htmlFor="suppres-kind">Kind</Label>
          <select
            id="suppres-kind"
            className="flex h-9 w-full rounded-md border border-input bg-transparent px-3 py-1 text-sm"
            value={kind}
            onChange={(e) => setKind(e.target.value)}
          >
            <option value="email">Email</option>
            <option value="phone">Phone</option>
            <option value="domain">Domain</option>
            <option value="name">Name</option>
          </select>
        </div>
        <div className="space-y-1.5">
          <Label htmlFor="suppres-value">Address / value *</Label>
          <Input id="suppres-value" value={value} onChange={(e) => setValue(e.target.value)} placeholder="someone@example.com" required />
        </div>
        <div className="space-y-1.5">
          <Label htmlFor="suppres-reason">Reason (optional)</Label>
          <Textarea id="suppres-reason" value={reason} onChange={(e) => setReason(e.target.value)} className="min-h-[70px]" />
        </div>
        <div className="flex justify-end gap-2">
          <Button type="button" variant="outline" onClick={onDone}>Cancel</Button>
          <Button type="submit"><Plus className="h-4 w-4" /> Add</Button>
        </div>
      </form>
    </DialogContent>
  );
}

export default function CompliancePage() {
  const qc = useQueryClient();
  const [search, setSearch] = React.useState("");
  const [debounced, setDebounced] = React.useState("");
  const [adding, setAdding] = React.useState(false);
  const [auditOffset, setAuditOffset] = React.useState(0);
  const [delEmail, setDelEmail] = React.useState("");

  React.useEffect(() => {
    const t = setTimeout(() => { setDebounced(search); }, 300);
    return () => clearTimeout(t);
  }, [search]);

  const status = useQuery({ queryKey: ["system-status"], queryFn: systemApi.status });
  const suppression = useQuery({ queryKey: ["suppression", debounced], queryFn: () => complianceApi.listSuppression(debounced) });
  const audit = useQuery({ queryKey: ["audit"], queryFn: () => complianceApi.audit({ limit: "25" }) });

  const deleteReq = useMutation({
    mutationFn: () => complianceApi.suppress({ kind: "email", value: delEmail.trim(), reason: "Data deletion request (PDPA/GDPR)" }),
    onSuccess: () => { toast.success("Deletion request processed — address suppressed"); setDelEmail(""); qc.invalidateQueries({ queryKey: ["suppression"] }); },
    onError: (e) => toast.error(asError(e)),
  });

  const remove = (id: string) => complianceApi.removeSuppression(id, "Removed from console").then(() => {
    toast.success("Removed"); qc.invalidateQueries({ queryKey: ["suppression"] });
  }).catch((e) => toast.error(asError(e)));

  const s = status.data;
  const bounceOk = s ? s.bounce_rate < s.bounce_threshold : true;
  const complaintOk = s ? s.complaint_rate < s.complaint_threshold : true;

  return (
    <div>
      <PageHeader
        title="Compliance"
        description="Trust & safety for every outbound touchpoint: kill switch, suppression lists, deliverability thresholds and the audit trail."
        actions={<KillSwitch enabled={!!s?.paused} />}
      />

      <div className="mb-6 grid gap-4 md:grid-cols-3">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0">
            <CardTitle className="text-sm">System</CardTitle>
            <ShieldCheck className="h-4 w-4 text-muted-foreground" aria-hidden="true" />
          </CardHeader>
          <CardContent className="text-2xl font-bold">
            {s ? (s.paused ? "PAUSED" : "RUNNING") : "…"}
          </CardContent>
          <CardContent className="pt-1 text-sm text-muted-foreground">
            Kill switch {s?.paused ? "engaged" : "off"}
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0">
            <CardTitle className="text-sm">Email</CardTitle>
          </CardHeader>
          <CardContent className="space-y-1">
            <p className="text-2xl font-bold">{s ? (s as any).channels?.email?.effective_mode ?? s.force_dry_run ? "dry-run" : "off" : "…"}</p>
            <p className="text-sm text-muted-foreground">Effective mode (never shows live when dry-running)</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0">
            <CardTitle className="text-sm">Deliverability</CardTitle>
          </CardHeader>
          <CardContent className="space-y-2">
            <div className="flex items-center justify-between text-sm">
              <span className="text-muted-foreground">Bounce rate</span>
              <span className={bounceOk ? "": "font-bold text-red-500"}>{s ? formatNumber(Math.round(s.bounce_rate * 100) / 100) + "%" : "—"}</span>
            </div>
            <div className="flex items-center justify-between text-sm">
              <span className="text-muted-foreground">Complaint rate</span>
              <span className={complaintOk ? "" : "font-bold text-red-500"}>{s ? Math.round(s.complaint_rate * 1000) / 10 + "%" : "—"}</span>
            </div>
            <p className="text-xs text-muted-foreground">Auto-pause at &gt; {s ? s.bounce_threshold * 100 : 5}% bounce or &gt; {s ? s.complaint_threshold * 100 : 0.3}% complaints.</p>
          </CardContent>
        </Card>
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-3">
            <CardTitle className="text-base">Suppression list</CardTitle>
            <Button size="sm" onClick={() => setAdding(true)}><Plus className="h-3.5 w-3.5" /> Add</Button>
          </CardHeader>
          <CardContent>
            <div className="relative mb-3">
              <Search className="absolute left-2.5 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" aria-hidden="true" />
              <Input
                type="search"
                placeholder="Search suppression…"
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                className="pl-8"
                aria-label="Search suppression list"
              />
            </div>
            {suppression.isLoading ? (
              <div className="space-y-2">{[1,2,3,4].map((i) => <Skeleton key={i} className="h-9" />)}</div>
            ) : !suppression.data || suppression.data.length === 0 ? (
              <EmptyState icon={<DatabaseZap className="h-5 w-5" />} title="Suppression list empty" description="Addresses added here are never emailed or called. Opt-outs and bounces are added automatically." />
            ) : (
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Kind</TableHead>
                    <TableHead>Value</TableHead>
                    <TableHead>Added</TableHead>
                    <TableHead></TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {suppression.data.map((r: SuppressionItem) => (
                    <TableRow key={r.id}>
                      <TableCell><Badge variant="secondary" className="uppercase">{r.kind}</Badge></TableCell>
                      <TableCell className="font-mono text-xs">{r.value}</TableCell>
                      <TableCell className="text-xs text-muted-foreground">{formatDateTime(r.created_at)}</TableCell>
                      <TableCell className="text-right">
                        <AlertDialog>
                          <AlertDialogTrigger asChild>
                            <Button size="sm" variant="ghost" className="text-destructive"><Trash2 className="h-3.5 w-3.5" /></Button>
                          </AlertDialogTrigger>
                          <AlertDialogContent>
                            <AlertDialogHeader>
                              <AlertDialogTitle>Remove from suppression?</AlertDialogTitle>
                              <AlertDialogDescription>This will allow future messages to this address again.</AlertDialogDescription>
                            </AlertDialogHeader>
                            <AlertDialogFooter>
                              <AlertDialogCancel>Cancel</AlertDialogCancel>
                              <AlertDialogAction className="bg-destructive text-destructive-foreground hover:bg-destructive/90" onClick={() => remove(r.id)}>Remove</AlertDialogAction>
                            </AlertDialogFooter>
                          </AlertDialogContent>
                        </AlertDialog>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-base">Audit trail</CardTitle>
          </CardHeader>
          <CardContent className="max-h-[420px] space-y-2 overflow-y-auto">
            {audit.isLoading ? (
              <div className="space-y-2">{[1,2,3,4].map((i) => <Skeleton key={i} className="h-10" />)}</div>
            ) : !audit.data || audit.data.length === 0 ? (
              <EmptyState icon={<ShieldCheck className="h-5 w-5" />} title="No audit events" />
            ) : (
              audit.data.map((a: AuditItem) => (
                <div key={a.id} className="flex items-start justify-between gap-3 border-b py-2 text-sm last:border-0">
                  <div className="min-w-0">
                    <p className="truncate font-medium">{a.action}</p>
                    {a.detail && <p className="truncate text-xs text-muted-foreground">{JSON.stringify(a.detail)}</p>}
                  </div>
                  <span className="shrink-0 text-xs text-muted-foreground">{formatDateTime(a.created_at)}</span>
                </div>
              ))
            )}
          </CardContent>
        </Card>
      </div>

      <Card className="mt-6">
        <CardHeader>
          <CardTitle className="text-base">Request data deletion</CardTitle>
          <p className="text-sm text-muted-foreground">
            Submit an email address to process a PDPA/GDPR data deletion request — the address is suppressed from future outreach and an audit event is recorded.
          </p>
        </CardHeader>
        <CardContent>
          <form className="flex max-w-md gap-2" onSubmit={(e) => { e.preventDefault(); deleteReq.mutate(); }}>
            <Input
              aria-label="Email to delete"
              type="email"
              required
              placeholder="someone@example.com"
              value={delEmail}
              onChange={(e) => setDelEmail(e.target.value)}
            />
            <Button type="submit" disabled={deleteReq.isPending}>
              {deleteReq.isPending && <Loader2 className="h-4 w-4 animate-spin" />} Request deletion
            </Button>
          </form>
        </CardContent>
      </Card>

      <Dialog open={adding} onOpenChange={setAdding}>
        {adding && <AddSuppressionDialog onDone={() => setAdding(false)} />}
      </Dialog>
    </div>
  );
}
