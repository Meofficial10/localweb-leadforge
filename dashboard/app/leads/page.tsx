"use client";

export const dynamic = "force-dynamic";

import * as React from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useSearchParams } from "next/navigation";
import { Search, Users, Star, Loader2, Ban, Trash2, ExternalLink } from "lucide-react";
import { leadsApi, type Lead, type LeadDetail } from "@/app/lib/api";
import { PageHeader } from "@/app/components/shared/page-header";
import { EmptyState } from "@/app/components/shared/empty-state";
import { StatusChip } from "@/app/components/shared/status-badge";
import { Badge } from "@/app/components/ui/badge";
import { Button } from "@/app/components/ui/button";
import { Card, CardContent } from "@/app/components/ui/card";
import { Checkbox } from "@/app/components/ui/checkbox";
import { Input } from "@/app/components/ui/input";
import { Skeleton } from "@/app/components/ui/skeleton";
import {
  Table, TableBody, TableCell, TableHead, TableHeader, TableRow,
} from "@/app/components/ui/table";
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from "@/app/components/ui/select";
import { Sheet, SheetContent } from "@/app/components/ui/sheet";
import {
  AlertDialog, AlertDialogContent, AlertDialogDescription, AlertDialogFooter,
  AlertDialogHeader, AlertDialogTitle, AlertDialogTrigger, AlertDialogCancel, AlertDialogAction,
} from "@/app/components/ui/alert-dialog";
import { toast } from "sonner";
import { asError, formatNumber } from "@/app/lib/utils";

function LeadDetailView({ lead }: { lead: LeadDetail }) {
  return (
    <div className="space-y-5">
      <div className="flex items-start justify-between">
        <div>
          <h2 className="text-xl font-bold">{lead.name}</h2>
          <p className="text-sm text-muted-foreground">{lead.category}{lead.address ? " · " + lead.address : ""}</p>
        </div>
        <StatusChip status={lead.status} />
      </div>
      <div className="flex flex-wrap gap-2 text-xs text-muted-foreground">
        <Badge variant="secondary">Rating: {lead.rating != null ? lead.rating : "—"}</Badge>
        <Badge variant="secondary">{formatNumber(lead.review_count)} reviews</Badge>
        <Badge variant="secondary">{lead.contact_type || "no contact info"}</Badge>
      </div>
      <div>
        <h3 className="mb-2 text-sm font-semibold">Contact details</h3>
        {(lead.contacts || []).length ? (
          <ul className="space-y-1 text-sm">
            {(lead.contacts || []).map((c, i) => (
              <li key={i} className="flex items-center gap-2">
                <Badge variant="outline" className="uppercase">{c.kind}</Badge>
                <span className="font-mono text-xs">{c.value}</span>
              </li>
            ))}
          </ul>
        ) : <p className="text-sm text-muted-foreground">No contacts discovered yet.</p>}
      </div>
      {(lead.demo || []).length > 0 && (
        <div>
          <h3 className="mb-2 text-sm font-semibold">Generated demo</h3>
          {(lead.demo || []).map((demo, i) => (
            <div key={i} className="flex flex-col gap-2 rounded-md border p-2 text-sm">
              <div className="flex items-center gap-2">
                <Badge variant="outline">{demo.deploy_status}</Badge>
                {demo.preview_url ? (
                  <a href={demo.preview_url} target="_blank" rel="noreferrer" className="inline-flex items-center gap-1 text-primary hover:underline">
                    Open preview in new tab <ExternalLink className="h-3 w-3" />
                  </a>
                ) : <span className="text-muted-foreground">(no URL — demo not deployed)</span>}
              </div>
              {demo.preview_url && (
                <iframe
                  src={demo.preview_url}
                  title={"Demo preview for " + lead.name}
                  className="h-72 w-full rounded-md border bg-muted"
                  loading="lazy"
                />
              )}
            </div>
          ))}
        </div>
      )}
      {lead.profile && (
        <div>
          <h3 className="mb-2 text-sm font-semibold">AI profile</h3>
          <p className="text-sm text-muted-foreground">{lead.profile.summary || "—"}</p>
          {(lead.profile.selling_points || []).length > 0 && (
            <ul className="mt-2 flex flex-wrap gap-1.5">
              {(lead.profile.selling_points as string[]).map((pt: string, i: number) => (
                <li key={i}><Badge variant="outline">{pt}</Badge></li>
              ))}
            </ul>
          )}
          {lead.profile.services && (lead.profile.services as string[]).length > 0 && (
            <p className="mt-2 text-xs text-muted-foreground">Services: {(lead.profile.services as string[]).join(", ")}</p>
          )}
          {lead.profile.tone && <p className="mt-1 text-xs text-muted-foreground">Tone: {lead.profile.tone}</p>}
        </div>
      )}
      {(lead.messages || []).length > 0 && (
        <div>
          <h3 className="mb-2 text-sm font-semibold">Outreach timeline</h3>
          <ul className="space-y-1.5">
            {(lead.messages || []).map((m) => (
              <li key={m.id} className="flex items-center gap-2 rounded-md border px-3 py-2 text-xs">
                <Badge variant="outline">{m.channel}</Badge>
                <StatusChip status={m.status} />
                <span className="truncate font-medium">{m.subject || "(no subject)"}</span>
                {m.intent ? <Badge variant="secondary">{m.intent}</Badge> : null}
              </li>
            ))}
          </ul>
        </div>
      )}
      {(lead.calls || []).length > 0 && (
        <div>
          <h3 className="mb-2 text-sm font-semibold">Calls</h3>
          <ul className="space-y-1.5">
            {(lead.calls || []).map((c) => (
              <li key={c.id} className="flex items-center gap-2 rounded-md border px-3 py-2 text-xs">
                <Badge variant="outline">{(c.outcome || "completed").toUpperCase()}</Badge>
                <span className="text-muted-foreground">{c.duration_sec ? Math.round(c.duration_sec / 60) + " min" : "—"}</span>
                <span className="ml-auto text-muted-foreground">{c.started_at || ""}</span>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}

function LeadDrawer({ leadId, onClose }: { leadId: string | null; onClose: () => void }) {
  const { data, isLoading } = useQuery({
    queryKey: ["lead", leadId],
    queryFn: () => leadsApi.get(leadId as string),
    enabled: !!leadId,
  });
  return (
    <Sheet open={!!leadId} onOpenChange={(o) => !o && onClose()}>
      <SheetContent className="w-full overflow-y-auto sm:max-w-xl">
        {isLoading ? (
          <div className="space-y-3"><Skeleton className="h-6 w-1/2" /><Skeleton className="h-24" /><Skeleton className="h-24" /></div>
        ) : data ? (
          <LeadDetailView lead={data} />
        ) : null}
      </SheetContent>
    </Sheet>
  );
}

function LeadsPageInner() {
  const searchParams = useSearchParams();
  const focus = searchParams.get("focus");
  const qc = useQueryClient();
  const [selected, setSelected] = React.useState<Set<string>>(new Set());
  const [query, setQuery] = React.useState("");
  const [debounced, setDebounced] = React.useState("");
  const [status, setStatus] = React.useState("");
  const [category, setCategory] = React.useState("");
  const [sort, setSort] = React.useState("-created_at");
  const [page, setPage] = React.useState(1);
  const pageSize = 25;

  React.useEffect(() => {
    const t = setTimeout(() => { setDebounced(query); setPage(1); }, 300);
    return () => clearTimeout(t);
  }, [query]);

  const params: Record<string, string> = { page: String(page), page_size: String(pageSize), sort };
  if (debounced) params.search = debounced;
  if (status) params.status = status;
  if (category) params.category = category;

  const { data, isLoading, isFetching } = useQuery({
    queryKey: ["leads", params],
    queryFn: () => leadsApi.list(params),
  });

  const toggle = (id: string) => {
    setSelected((prev) => { const n = new Set(prev); if (n.has(id)) n.delete(id); else n.add(id); return n; });
  };
  const allSelected = !!data && data.items.length > 0 && data.items.every((l) => selected.has(l.id));
  const toggleAll = () => {
    if (!data) return;
    setSelected(allSelected ? new Set() : new Set(data.items.map((l) => l.id)));
  };

  const invalidate = () => { qc.invalidateQueries({ queryKey: ["leads"] }); qc.invalidateQueries({ queryKey: ["metrics"] }); };
  const bulkDelete = useMutation({
    mutationFn: () => leadsApi.bulkDelete(Array.from(selected)),
    onSuccess: () => { toast.success("Leads deleted"); setSelected(new Set()); invalidate(); },
    onError: (e) => toast.error(asError(e)),
  });
  const bulkSuppress = useMutation({
    mutationFn: () => leadsApi.bulkSuppress(Array.from(selected), "Bulk suppress from Leads console"),
    onSuccess: () => { toast.success("Contact emails suppressed"); setSelected(new Set()); invalidate(); },
    onError: (e) => toast.error(asError(e)),
  });

  const totalPages = data ? Math.max(1, Math.ceil(data.total / pageSize)) : 1;

  return (
    <div>
      <PageHeader
        title="Leads"
        description="Discovered businesses, their contact details, AI profiles and generated demos."
      />

      <div className="mb-4 flex flex-wrap items-center gap-2">
        <div className="relative">
          <Search className="absolute left-2.5 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" aria-hidden="true" />
          <Input
            type="search"
            placeholder="Search name, address, category…"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            className="w-64 pl-8"
            aria-label="Search leads"
          />
        </div>
        <Select value={status} onValueChange={(v) => { setStatus(v); setPage(1); }}>
          <SelectTrigger className="w-40" aria-label="Filter by status"><SelectValue placeholder="All statuses" /></SelectTrigger>
          <SelectContent>
            <SelectItem value="">All statuses</SelectItem>
            {["discovered", "enriched", "profiled", "demo_ready", "contacted"].map((s) => <SelectItem key={s} value={s}>{s}</SelectItem>)}
          </SelectContent>
        </Select>
        <Select value={category} onValueChange={(v) => { setCategory(v); setPage(1); }}>
          <SelectTrigger className="w-40" aria-label="Filter by category"><SelectValue placeholder="All categories" /></SelectTrigger>
          <SelectContent>
            <SelectItem value="">All categories</SelectItem>
            {["salon", "cafe", "auto repair", "spa", "clinic", "dentist"].map((c) => <SelectItem key={c} value={c}>{c}</SelectItem>)}
          </SelectContent>
        </Select>
        <Select value={sort} onValueChange={setSort}>
          <SelectTrigger className="w-44" aria-label="Sort leads"><SelectValue /></SelectTrigger>
          <SelectContent>
            <SelectItem value="-created_at">Newest first</SelectItem>
            <SelectItem value="created_at">Oldest first</SelectItem>
            <SelectItem value="name">Name A–Z</SelectItem>
            <SelectItem value="-rating">Highest rated</SelectItem>
            <SelectItem value="-review_count">Most reviews</SelectItem>
          </SelectContent>
        </Select>
        {selected.size > 0 && (
          <div className="flex items-center gap-2">
            <AlertDialog>
              <AlertDialogTrigger asChild>
                <Button size="sm" variant="outline" className="text-destructive"><Ban className="h-3.5 w-3.5" /> Suppress ({selected.size})</Button>
              </AlertDialogTrigger>
              <AlertDialogContent>
                <AlertDialogHeader>
                  <AlertDialogTitle>Suppress selected contacts?</AlertDialogTitle>
                  <AlertDialogDescription>Their emails/phones are added to the global suppression list and never contacted again.</AlertDialogDescription>
                </AlertDialogHeader>
                <AlertDialogFooter>
                  <AlertDialogCancel>Cancel</AlertDialogCancel>
                  <AlertDialogAction className="bg-destructive text-destructive-foreground hover:bg-destructive/90" onClick={() => bulkSuppress.mutate()}>Suppress</AlertDialogAction>
                </AlertDialogFooter>
              </AlertDialogContent>
            </AlertDialog>
            <AlertDialog>
              <AlertDialogTrigger asChild>
                <Button size="sm" variant="outline" className="text-destructive"><Trash2 className="h-3.5 w-3.5" /> Delete ({selected.size})</Button>
              </AlertDialogTrigger>
              <AlertDialogContent>
                <AlertDialogHeader>
                  <AlertDialogTitle>Delete selected leads?</AlertDialogTitle>
                  <AlertDialogDescription>This permanently removes them and their contacts, profiles, drafts and calls.</AlertDialogDescription>
                </AlertDialogHeader>
                <AlertDialogFooter>
                  <AlertDialogCancel>Cancel</AlertDialogCancel>
                  <AlertDialogAction className="bg-destructive text-destructive-foreground hover:bg-destructive/90" onClick={() => bulkDelete.mutate()}>Delete</AlertDialogAction>
                </AlertDialogFooter>
              </AlertDialogContent>
            </AlertDialog>
          </div>
        )}
        {isFetching && <Loader2 className="ml-auto h-4 w-4 animate-spin text-muted-foreground" aria-hidden="true" />}
      </div>

      {isLoading ? (
        <div className="space-y-2">{[1, 2, 3, 4].map((i) => <Skeleton key={i} className="h-12" />)}</div>
      ) : !data || data.items.length === 0 ? (
        <EmptyState icon={<Users className="h-5 w-5" />} title="No leads found" description="Run a campaign to discover leads, or clear your filters." />
      ) : (
        <Card>
          <CardContent className="p-0">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead className="w-10"><Checkbox checked={allSelected} onCheckedChange={toggleAll} aria-label="Select all leads" /></TableHead>
                  <TableHead>Name</TableHead>
                  <TableHead>Category</TableHead>
                  <TableHead className="hidden md:table-cell">Contact</TableHead>
                  <TableHead>Rating</TableHead>
                  <TableHead>Status</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {data.items.map((l: Lead) => (
                  <TableRow key={l.id}>
                    <TableCell><Checkbox checked={selected.has(l.id)} onCheckedChange={() => toggle(l.id)} aria-label={"Select " + l.name} /></TableCell>
                    <TableCell>
                      <button className="text-left font-medium text-primary hover:underline" onClick={() => window.history.replaceState(null, "", "?focus=" + l.id)}>
                        {l.name}
                      </button>
                    </TableCell>
                    <TableCell className="text-muted-foreground">{l.category || "—"}</TableCell>
                    <TableCell className="hidden text-muted-foreground md:table-cell">{(l.contacts || []).length ? (l.contacts as any[]).map((c) => c.value).join(", ") : "—"}</TableCell>
                    <TableCell>{l.rating != null ? <span className="inline-flex items-center gap-1">{l.rating} <Star className="h-3 w-3 text-warn" aria-hidden="true" /></span> : "—"}</TableCell>
                    <TableCell><StatusChip status={l.status} /></TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </CardContent>
        </Card>
      )}

      {data && totalPages > 1 && (
        <div className="mt-4 flex items-center justify-between text-sm">
          <span className="text-muted-foreground">{data.total} leads · page {data.page} of {totalPages}</span>
          <div className="flex gap-2">
            <Button size="sm" variant="outline" disabled={page <= 1} onClick={() => setPage(page - 1)}>Previous</Button>
            <Button size="sm" variant="outline" disabled={page >= totalPages} onClick={() => setPage(page + 1)}>Next</Button>
          </div>
        </div>
      )}

      <LeadDrawer leadId={focus} onClose={() => window.history.replaceState(null, "", window.location.pathname)} />
    </div>
  );
}

export default function LeadsPage() {
  return (
    <React.Suspense fallback={<Skeleton className="h-64" />}>
      <LeadsPageInner />
    </React.Suspense>
  );
}
