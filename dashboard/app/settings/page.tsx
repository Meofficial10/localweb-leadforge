"use client";

export const dynamic = "force-dynamic";

import * as React from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Save, Loader2, Settings as SettingsIcon, Mail, ShieldCheck, Wallet, Megaphone } from "lucide-react";
import { settingsApi, type AppSettings } from "@/app/lib/api";
import { PageHeader } from "@/app/components/shared/page-header";
import { Skeleton } from "@/app/components/ui/skeleton";
import { Button } from "@/app/components/ui/button";
import { Input } from "@/app/components/ui/input";
import { Label } from "@/app/components/ui/label";
import { Card, CardContent, CardHeader, CardTitle } from "@/app/components/ui/card";
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from "@/app/components/ui/select";
import { toast } from "sonner";
import { asError } from "@/app/lib/utils";

function Field({ label, hint, children }: { label: string; hint?: string; children: React.ReactNode }) {
  return (
    <div className="space-y-1.5">
      <Label>{label}</Label>
      {children}
      {hint ? <p className="text-xs text-muted-foreground">{hint}</p> : null}
    </div>
  );
}

function NumberField({ value, onChange, min, max }: { value: number; onChange: (n: number) => void; min?: number; max?: number }) {
  return (
    <Input
      type="number"
      value={Number.isFinite(value) ? value : 0}
      min={min}
      max={max}
      onChange={(e) => onChange(Number(e.target.value))}
    />
  );
}

function SectionCard({ icon, title, children }: { icon: React.ReactNode; title: string; children: React.ReactNode }) {
  return (
    <Card>
      <CardHeader className="flex flex-row items-center gap-2 space-y-0 pb-4">
        <span className="flex h-8 w-8 items-center justify-center rounded-md bg-accent text-accent-foreground">{icon}</span>
        <CardTitle className="text-base">{title}</CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">{children}</CardContent>
    </Card>
  );
}

export default function SettingsPage() {
  const { data, isLoading, isError } = useQuery({ queryKey: ["settings"], queryFn: settingsApi.get });
  const [form, setForm] = React.useState<AppSettings | null>(null);
  React.useEffect(() => { if (data) setForm(JSON.parse(JSON.stringify(data))); }, [data]);
  const qc = useQueryClient();
  const save = useMutation({
    mutationFn: () => settingsApi.update(buildPatch(form!)),
    onSuccess: () => { toast.success("Settings saved"); qc.invalidateQueries({ queryKey: ["settings"] }); },
    onError: (e) => toast.error(asError(e)),
  });

  function buildPatch(f: AppSettings): Record<string, unknown> {
    return {
      daily_email_cap: f.daily_email_cap,
      daily_call_cap: f.daily_call_cap,
      followup_delay_days: f.followup_delay_days,
      approval_mode: f.approval_mode,
      bounce_tolerance: f.bounce_tolerance,
      complaint_tolerance: f.complaint_tolerance,
      send_window: f.send_window,
      warm_up_schedule: f.warm_up_schedule,
      budgets: f.budgets,
      branding: f.branding,
    };
  }

  if (isLoading) return <div className="space-y-4">{[1,2,3,4].map((i) => <Skeleton key={i} className="h-40" />)}</div>;
  if (isError || !form) return <p className="text-sm text-destructive">Couldn&apos;t load settings.</p>;

  const patch = (fn: (f: AppSettings) => void) => setForm((p) => { if (!p) return p; const n = JSON.parse(JSON.stringify(p)); fn(n); return n; });

  return (
    <div>
      <PageHeader
        title="Settings"
        description="Global defaults for outreach caps, warm-up ramp, budgets, and sender branding."
        actions={
          <Button onClick={() => save.mutate()} disabled={save.isPending}>
            {save.isPending && <Loader2 className="h-4 w-4 animate-spin" />} Save changes
          </Button>
        }
      />
      <div className="grid gap-6 lg:grid-cols-2">
        <div className="space-y-6">
          <SectionCard icon={<Mail className="h-4 w-4" />} title="Daily caps & send window">
            <div className="grid grid-cols-2 gap-4">
              <Field label="Email cap / day" hint="Ramped up by the warm-up schedule.">
                <NumberField value={form.daily_email_cap} min={1} onChange={(n) => patch((f) => { f.daily_email_cap = n; })} />
              </Field>
              <Field label="Call cap / day">
                <NumberField value={form.daily_call_cap} min={0} onChange={(n) => patch((f) => { f.daily_call_cap = n; })} />
              </Field>
            </div>
            <Field label="Send window (start,end)">
              <div className="flex gap-2">
                <Input value={(form.send_window?.start ?? "09:00") as string} onChange={(e) => patch((f) => { f.send_window = { ...(f.send_window || {}), start: e.target.value }; })} />
                <Input value={(form.send_window?.end ?? "18:00") as string} onChange={(e) => patch((f) => { f.send_window = { ...(f.send_window || {}), end: e.target.value }; })} />
              </div>
            </Field>
            <Field label="Warm-up schedule (start emails/day, days, target)">
              <div className="grid grid-cols-3 gap-2">
                <NumberField value={form.warm_up_schedule?.start ?? 5} min={1} onChange={(n) => patch((f) => { f.warm_up_schedule = { ...(f.warm_up_schedule || {}), start: n }; })} />
                <NumberField value={form.warm_up_schedule?.days ?? 21} min={1} onChange={(n) => patch((f) => { f.warm_up_schedule = { ...(f.warm_up_schedule || {}), days: n }; })} />
                <NumberField value={form.warm_up_schedule?.target ?? form.daily_email_cap} min={1} onChange={(n) => patch((f) => { f.warm_up_schedule = { ...(f.warm_up_schedule || {}), target: n }; })} />
              </div>
            </Field>
            <Field label="Follow-up delay (days)">
              <NumberField value={form.followup_delay_days} min={0} max={30} onChange={(n) => patch((f) => { f.followup_delay_days = n; })} />
            </Field>
            <Field label="Approval mode">
              <Select value={form.approval_mode} onValueChange={(v) => patch((f) => { f.approval_mode = v; })}>
                <SelectTrigger><SelectValue /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="manual">Manual approval</SelectItem>
                  <SelectItem value="auto">Auto-approved</SelectItem>
                </SelectContent>
              </Select>
            </Field>
          </SectionCard>

          <SectionCard icon={<Wallet className="h-4 w-4" />} title="Budgets (monthly caps, USD)">
            <p className="text-xs text-muted-foreground">LeadForge pauses spend on a source when its monthly cap is reached.</p>
            <div className="grid grid-cols-2 gap-4">
              <Field label="Places API"><NumberField value={form.budgets?.places ?? 0} min={0} onChange={(n) => patch((f) => { f.budgets = { ...(f.budgets || {}), places: n }; })} /></Field>
              <Field label="LLM"><NumberField value={form.budgets?.llm ?? 0} min={0} onChange={(n) => patch((f) => { f.budgets = { ...(f.budgets || {}), llm: n }; })} /></Field>
              <Field label="Voice"><NumberField value={form.budgets?.voice ?? 0} min={0} onChange={(n) => patch((f) => { f.budgets = { ...(f.budgets || {}), voice: n }; })} /></Field>
              <Field label="Email"><NumberField value={form.budgets?.email ?? 0} min={0} onChange={(n) => patch((f) => { f.budgets = { ...(f.budgets || {}), email: n }; })} /></Field>
            </div>
          </SectionCard>
        </div>

        <div className="space-y-6">
          <SectionCard icon={<ShieldCheck className="h-4 w-4" />} title="Compliance tolerances">
            <Field label="Bounce rate auto-pause threshold (%)">
              <NumberField value={form.bounce_tolerance ? Math.round(form.bounce_tolerance * 1000) / 10 : 5} min={0} max={50} onChange={(n) => patch((f) => { f.bounce_tolerance = n / 100; })} />
            </Field>
            <Field label="Spam complaint auto-pause threshold (%)">
              <NumberField value={form.complaint_tolerance ? Math.round(form.complaint_tolerance * 10000) / 100 : 0.3} min={0} max={5} onChange={(n) => patch((f) => { f.complaint_tolerance = n / 100; })} />
            </Field>
            <div className="rounded-md border border-muted bg-muted/40 p-3 text-xs text-muted-foreground">
              Exceeding these rates automatically pauses sending and records an audit event. Restarting requires a manual resume.
            </div>
          </SectionCard>

          <SectionCard icon={<Megaphone className="h-4 w-4" />} title="Sender branding (CAN-SPAM / PDPA)">
            <Field label="Sender name"><Input value={form.branding?.sender_name ?? ""} onChange={(e) => patch((f) => { f.branding = { ...(f.branding || {}), sender_name: e.target.value }; })} /></Field>
            <Field label="Sender email"><Input value={form.branding?.sender_email ?? ""} onChange={(e) => patch((f) => { f.branding = { ...(f.branding || {}), sender_email: e.target.value }; })} /></Field>
            <Field label="Physical address (required by CAN-SPAM)">
              <Input value={form.branding?.physical_address ?? ""} onChange={(e) => patch((f) => { f.branding = { ...(f.branding || {}), physical_address: e.target.value }; })} />
            </Field>
            <Field label="Demo banner text">
              <Input value={form.branding?.demo_banner ?? ""} onChange={(e) => patch((f) => { f.branding = { ...(f.branding || {}), demo_banner: e.target.value }; })} />
            </Field>
            <Field label="Unsubscribe line">
              <Input value={form.branding?.unsubscribe_text ?? ""} onChange={(e) => patch((f) => { f.branding = { ...(f.branding || {}), unsubscribe_text: e.target.value }; })} />
            </Field>
          </SectionCard>

          <SectionCard icon={<SettingsIcon className="h-4 w-4" />} title="Access tokens">
            <p className="text-xs text-muted-foreground">Configured via the backend environment (.env). Rotate them there and restart the API.</p>
            <div>
              <Label>Auth tokens</Label>
              <p className="mt-1 break-all font-mono text-xs text-muted-foreground">{(form.tokens?.auth_tokens || []).join(", ") || "none"}</p>
            </div>
            <div>
              <Label>Admin tokens</Label>
              <p className="mt-1 break-all font-mono text-xs text-muted-foreground">{(form.tokens?.admin_tokens || []).join(", ") || "none"}</p>
            </div>
          </SectionCard>
        </div>
      </div>
    </div>
  );
}
