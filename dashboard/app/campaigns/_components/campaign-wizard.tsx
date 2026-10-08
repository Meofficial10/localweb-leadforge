"use client";

import * as React from "react";
import { useQuery } from "@tanstack/react-query";
import { toast } from "sonner";
import { Loader2, ChevronLeft, ChevronRight, X, Check, Search, AlertTriangle, MapPin, ShieldCheck } from "lucide-react";
import { Button } from "@/app/components/ui/button";
import { Input } from "@/app/components/ui/input";
import { Label } from "@/app/components/ui/label";
import { Textarea } from "@/app/components/ui/textarea";
import { Badge } from "@/app/components/ui/badge";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/app/components/ui/select";
import { Switch } from "@/app/components/ui/switch";
import { Checkbox } from "@/app/components/ui/checkbox";
import { campaignsApi, locationsApi, integrationsApi, type Campaign } from "@/app/lib/api";
import { asError } from "@/app/lib/utils";

export const STEPS = ["Basics", "Location", "Business types", "Outreach & limits"] as const;

const cx = (...xs: Array<string | false | null | undefined>) => xs.filter(Boolean).join(" ");

const SECTORS: Array<[string, string[]]> = [
  ["Beauty & wellness", ["Salon", "Barber", "Nail salon", "Spa"]],
  ["Food & drink", ["Cafe", "Restaurant", "Bakery", "Florist"]],
  ["Health & fitness", ["Gym", "Clinic", "Dentist", "Pharmacy"]],
  ["Education", ["Tuition centre", "Language school", "Music school"]],
  ["Home & repairs", ["Repair shop", "Laundry", "Cleaning service", "Locksmith"]],
  ["Retail", ["Boutique", "Gift shop", "Convenience store"]],
];

type WizardState = {
  name: string; description: string; country: string; state: string; city: string;
  towns: string[]; wholeTown?: string; area_radius_km: number;
  categories: string[]; customTags: string[];
  min_rating: number | null; min_review_count: number | null;
  only_phone: boolean; only_email: boolean;
  lead_sources: string[]; channels: string[];
  daily_email_cap: number; daily_call_cap: number;
  send_window: { start: string; end: string; days: string[] }; timezone: string;
  warm_up_enabled: boolean; followup_delay_days: number;
  approval_mode: string; run_schedule: string;
  max_leads_per_run: number | null; budget_cap: number | null; mode: string;
};

function emptyWizard(cam?: Campaign | null): WizardState {
  return {
    name: cam?.name ?? "", description: cam?.description ?? "",
    country: cam?.country ?? "SG", state: "", city: cam?.city ?? "",
    towns: [], wholeTown: undefined, area_radius_km: cam?.area_radius_km ?? 2,
    categories: cam?.categories ?? [], customTags: [],
    min_rating: null, min_review_count: null, only_phone: false, only_email: false,
    lead_sources: cam?.lead_sources?.length ? (cam.lead_sources as string[]) : ["google", "osm"],
    channels: cam?.channels?.length ? (cam.channels as string[]) : ["email", "voice"],
    daily_email_cap: cam?.daily_email_cap ?? 20, daily_call_cap: cam?.daily_call_cap ?? 10,
    send_window: { start: cam?.send_window?.start ?? "09:00", end: cam?.send_window?.end ?? "18:00", days: (cam?.send_window?.days as string[]) ?? ["mon","tue","wed","thu","fri"] },
    timezone: cam?.timezone ?? "Asia/Singapore", warm_up_enabled: !!cam?.warm_up_schedule,
    followup_delay_days: cam?.followup_delay_days ?? 4, approval_mode: cam?.approval_mode ?? "manual",
    run_schedule: "manual", max_leads_per_run: cam?.max_leads_per_run ?? null,
    budget_cap: cam?.budget_cap ?? null, mode: cam?.mode ?? "dry_run",
  };
}

function buildPayload(w: WizardState) {
  const city = w.wholeTown || w.city || w.towns[0] || "";
  const payload: Record<string, any> = {
    name: w.name, description: w.description || undefined,
    country: w.country, city, area_radius_km: w.area_radius_km,
    categories: [...w.categories, ...w.customTags],
    lead_sources: w.lead_sources.length ? w.lead_sources : undefined,
    channels: w.channels.length ? w.channels : undefined,
    daily_email_cap: w.daily_email_cap, daily_call_cap: w.daily_call_cap,
    max_leads_per_run: w.max_leads_per_run, budget_cap: w.budget_cap,
    send_window: { start: w.send_window.start, end: w.send_window.end, days: w.send_window.days },
    timezone: w.timezone,
    warm_up_schedule: w.warm_up_enabled ? { mode: "ramp", start: 5, days: 21, target: w.daily_email_cap } : undefined,
    followup_delay_days: w.followup_delay_days, approval_mode: w.approval_mode,
    cron_schedule: w.run_schedule === "manual" ? undefined : { preset: w.run_schedule },
    mode: w.mode || "dry_run",
  };
  return payload;
}


// ---------- Step components ----------
function toggle(list: string[], v: string) { return list.includes(v) ? list.filter(x => x !== v) : [...list, v]; }

interface StepProps { w: WizardState; set: (p: Partial<WizardState>) => void; forceDryRun: boolean; }

// (steps live above)

export function CampaignWizard({ open, onOpenChange, campaign, mode = "create", onDone }: { open: boolean; onOpenChange: (v: boolean) => void; campaign?: Campaign | null; mode?: "create" | "edit"; onDone: () => void }) {
  const [step, setStep] = React.useState(0);
  const [w, setW] = React.useState<WizardState>(() => emptyWizard(campaign));
  const [busy, setBusy] = React.useState(false);
  const [serverErrors, setServerErrors] = React.useState<Record<string, { ok: boolean; errors: string[] }>>({});
  const isEdit = mode === "edit" && !!campaign;
  const setW2 = React.useCallback((patch: Partial<WizardState>) => {
    setW((prev) => ({ ...prev, ...patch }));
  }, []);
  
  const healthQ = useQuery({ queryKey: ["integrations"], queryFn: () => integrationsApi.list(), staleTime: 60000 });
  const force_dry_run_q = !!(healthQ.data as any)?.force_dry_run;

  // lazy per-country dataset fetch (M4: lazy-load per country, no API calls at import)
  const countriesQ = useQuery({ queryKey: ["geo", "countries"], queryFn: () => locationsApi.countries(), staleTime: 5 * 60 * 1000 });
  const statesQ = useQuery({ queryKey: ["geo", w.country, "states"], queryFn: () => locationsApi.states(w.country), enabled: open && !!w.country && step >= 1, staleTime: 5 * 60 * 1000 });
  const citiesQ = useQuery({
    queryKey: ["geo", w.country, w.state, "cities"],
    queryFn: () => locationsApi.cities(w.country, w.state && w.state !== "" ? w.state : ""),
    enabled: open && !!w.country && step >= 1,
    staleTime: 5 * 60 * 1000,
  });
  const statesArr = (statesQ.data as any)?.states ?? [];
  const citiesArr = (citiesQ.data as any)?.cities ?? [];
  const statesForChoice = statesArr.length ? statesArr : [""];

  const submitWizard = async (runNow: boolean) => { await submit(runNow); };
  if (!open) return null;

  const totalSteps = 4;
  const valid = (s: number): boolean => {
    if (s === 0) return w.name.trim().length >= 2 && w.lead_sources.length > 0;
    if (s === 1) return (w.city.length > 0) || (!!w.wholeTown || w.towns.length > 0);
    if (s === 2) return w.categories.length > 0;
    return true;
  };

  const next = async (s: number) => {
    const okCur = valid(s);
    if (s === 3) {
      try {
        const res: any = await campaignsApi.validate({ ...w });
        const errs: Record<string, { ok: boolean; errors: string[] }> = {};
        for (const [k, v] of Object.entries(res ?? {})) {
          if (!(v as any).ok) errs[k] = (v as any).errors || [];
        }
        setServerErrors(errs);
        if (Object.keys(errs).length === 0) {
          setStep(4);
          return;
        }
      } catch {
        setStep(4);
      }
      return;
    }
    if (!okCur) return;
    setStep(s + 1);
  };

  const submit = async (runNow: boolean) => {
    setBusy(true);
    try {
      const payload = buildPayload(w);
      const res = isEdit && campaign
        ? await campaignsApi.update(campaign.id, payload)
        : await campaignsApi.create(payload as any);
      toast.success(isEdit ? "Campaign updated" : "Campaign created");
      if (runNow && !isEdit && (res as any).id) {
        await campaignsApi.run((res as any).id).catch(() => undefined);
        toast.info("Dry-run started (nothing was sent)");
      }
      onDone();
    } catch (e) {
      toast.error(asError(e));
    } finally {
      setBusy(false);
    }
  };


function StepBasics({ w, set }: { w: WizardState; set: (p: Partial<WizardState>) => void }) {
  const srcs: Array<[string, string]> = [["google", "Google Maps"], ["osm", "OpenStreetMap"], ["apify", "Apify scraper"]];
  return (
    <div className="space-y-4 py-1">
      <div className="space-y-1.5">
        <Label htmlFor="wiz-name">Campaign name *</Label>
        <Input id="wiz-name" value={w.name} onChange={(e) => set({ name: e.target.value })} placeholder="Queensway Clinics" />
        {w.name && w.name.length < 2 && <p className="text-xs text-destructive">At least 2 characters.</p>}
      </div>
      <div className="space-y-1.5">
        <Label htmlFor="wiz-desc">Description</Label>
        <Textarea id="wiz-desc" value={w.description} onChange={(e) => set({ description: e.target.value })} placeholder="Dental clinics without a website" rows={2} />
        <p className="text-xs text-muted-foreground">Shown on the campaign card to help you remember intent.</p>
      </div>
      <div className="space-y-1.5">
        <Label>Lead sources</Label>
        <div className="flex flex-wrap gap-2">
          {srcs.map(([val, label]) => {
            const active = w.lead_sources.includes(val);
            return (
              <button key={val} type="button" role="checkbox" aria-checked={active} onClick={() => set({ lead_sources: toggle(w.lead_sources, val) })}
                data-testid={"src-" + val} className={cx(
                  "inline-flex items-center gap-1.5 rounded-md border px-3 py-1.5 text-sm transition-colors",
                  active ? "border-primary bg-primary/5 text-primary" : "border-border text-muted-foreground hover:bg-muted",
                )}>
                <span className={cx("inline-block h-2.5 w-2.5 rounded-sm border border-current", active && "bg-primary")} aria-hidden="true" />
                {label}
              </button>
            );
          })}
        </div>
        {w.lead_sources.length === 0 && <p className="text-xs text-destructive">Pick at least one source.</p>}
      </div>
    </div>
  );
}

function StepLocation({ w, set, countries, states, cities, loading }: { w: WizardState; set: (p: Partial<WizardState>) => void; countries: any[]; states: string[]; cities: string[]; loading: boolean }) {
  const [q, setQ] = React.useState("");
  const [manual, setManual] = React.useState("");
  const filteredCities = (cities || []).filter((c) => !q || c.toLowerCase().includes(q.toLowerCase()));
  const selected = w.wholeTown ? [w.wholeTown] : w.towns;
  return (
    <div className="space-y-4 py-1">
      <div className="grid gap-4 sm:grid-cols-2">
        <div className="space-y-1.5">
          <Label>Country</Label>
          <Select value={w.country} onValueChange={(v) => set({ country: v, state: "", city: "", towns: [] })}>
            <SelectTrigger data-testid="wiz-country"><SelectValue placeholder="Country" /></SelectTrigger>
            <SelectContent>
              {(countries || []).map((c) => (
                <SelectItem key={c.code} value={c.code}>{c.flag} {c.name}</SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
        <div className="space-y-1.5">
          <Label>State / region</Label>
          <Select value={w.state || "__none__"} onValueChange={(v) => set({ state: v, city: "", towns: [] })}>
            <SelectTrigger data-testid="wiz-state"><SelectValue placeholder="State" /></SelectTrigger>
            <SelectContent>
              <SelectItem value="__none__">Whole country</SelectItem>
              {states.map((s) => (
                <SelectItem key={s} value={s}>{s}</SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
      </div>
      <div className="space-y-1.5">
        <Label>City or town area</Label>
        {loading ? <p className="text-xs text-muted-foreground">Loading local areas…</p> : (
          <div className="rounded-md border border-border">
            <div className="flex items-center gap-2 border-b border-border px-3 py-2">
              <Search className="h-4 w-4 text-muted-foreground" aria-hidden="true" />
              <input className="w-full bg-transparent text-sm outline-none" placeholder="Search areas…" value={q} onChange={(e) => setQ(e.target.value)} data-testid="wiz-area-search" />
            </div>
            <div className="max-h-72 overflow-y-auto p-2">
              {selected.length > 0 && (
                <div className="mb-2 flex flex-wrap gap-1.5 border-b border-border pb-2">
                  {selected.map((t) => (
                    <Badge key={t} variant="secondary" className="gap-1 bg-primary/10 text-primary">
                      <span>{t}</span>
                      <X className="h-3 w-3 cursor-pointer" aria-label={"remove " + t} onClick={() => {
                        if (w.wholeTown === t) set({ wholeTown: undefined });
                        set({ towns: w.towns.filter((x) => x !== t), wholeTown: undefined });
                      }} />
                    </Badge>
                  ))}
                </div>
              )}
              <p className="px-1 pb-1 text-[11px] uppercase tracking-wider text-muted-foreground">Suggested areas</p>
              {filteredCities.length === 0 && <p className="px-2 py-2 text-sm text-muted-foreground">No matches — type your own area below.</p>}
              {filteredCities.map((c) => {
                const active = selected.includes(c);
                return (
                  <button key={c} type="button" aria-pressed={active} onClick={() => set({ towns: toggle(selected, c), wholeTown: undefined })}
                    className={cx("flex w-full items-center justify-between rounded-md px-3 py-2 text-sm hover:bg-muted", active && "bg-primary/10 text-primary")}>
                    <span>{c}</span>
                    {active && <Check className="h-4 w-4" aria-hidden="true" />}
                  </button>
                );
              })}
              <div className="flex gap-2 border-t border-border pt-2">
                <Input value={manual} placeholder="Type your own area…" onChange={(e) => setManual(e.target.value)} data-testid="wiz-manual-area" />
                <Button variant="outline" size="sm" onClick={() => { if (manual.trim()) { set({ towns: [...w.towns, manual.trim()], wholeTown: manual.trim() }); setManual(""); } }}>Add</Button>
              </div>
            </div>
          </div>
        )}
      </div>
      <div className="grid gap-4 sm:grid-cols-2">
        <div className="space-y-1.5">
          <Label htmlFor="wiz-radius">Radius (km)</Label>
          <input id="wiz-radius" type="range" min={0.5} max={20} step={0.5} value={w.area_radius_km}
            onChange={(e) => set({ area_radius_km: Number(e.target.value) })} className="w-full accent-primary" />
          <p className="text-xs text-muted-foreground">{w.area_radius_km.toFixed(1)} km around the chosen area</p>
        </div>
        <div className="space-y-1.5 rounded border border-dashed p-3">
          <p className="text-xs font-medium text-foreground">Map preview</p>
          <div className="flex items-end gap-1 text-[10px] text-muted-foreground">
            <MapPin className="h-3 w-3 shrink-0" aria-hidden="true" />
            <span>Search ring</span>
            <span style={{ width: Math.min(60, w.area_radius_km * 10), height: 2+6, background: "oklch(0.62 0.15 0)", borderRadius: 4 }} />
          </div>
          <p className="text-[11px] text-muted-foreground">Static preview for the mock flow — no map tiles are fetched.</p>
        </div>
      </div>
    </div>
  );
}


function StepBusiness({ w, set }: { w: WizardState; set: (p: Partial<WizardState>) => void }) {
  const [q, setQ] = React.useState("");
  const [custom, setCustom] = React.useState("");
  return (
    <div className="space-y-4 py-1">
      <div className="flex items-center gap-2 rounded-md border border-border px-3 py-2">
        <Search className="h-4 w-4 text-muted-foreground" aria-hidden="true" />
        <input className="w-full bg-transparent text-sm outline-none" placeholder="Search business types…" value={q} onChange={(e) => setQ(e.target.value)} data-testid="wiz-cat-search" />
      </div>
      {SECTORS.map(([sector, items]) => {
        const visible = items.filter((it) => !q || it.toLowerCase().includes(q.toLowerCase()));
        if (visible.length === 0) return null;
        return (
          <div key={sector} className="space-y-1.5">
            <p className="text-[11px] uppercase tracking-wider text-muted-foreground">{sector}</p>
            <div className="flex flex-wrap gap-2">
              {visible.map((it) => {
                const active = w.categories.includes(it);
                return (
                  <button key={it} type="button" role="checkbox" aria-checked={active} onClick={() => set({ categories: toggle(w.categories, it) })}
                    className={cx("inline-flex items-center gap-1.5 rounded-md border px-3 py-1.5 text-sm", active ? "border-primary bg-primary/5 text-primary" : "border-border text-muted-foreground hover:bg-muted")}>
                    {active && <Check className="h-3.5 w-3.5" aria-hidden="true" />}{it}
                  </button>
                );
              })}
            </div>
          </div>
        );
      })}
      <div className="flex gap-2 pt-1">
        <Input value={custom} placeholder="Add a custom tag…" onChange={(e) => setCustom(e.target.value)} data-testid="wiz-custom-cat" />
        <Button variant="outline" size="sm" onClick={() => { const t = custom.trim(); if (t && !w.customTags.includes(t)) { set({ customTags: [...w.customTags, t] }); setCustom(""); } }}>Add tag</Button>
      </div>
      {w.customTags.length > 0 && (
        <div className="flex flex-wrap gap-2">
          {w.customTags.map((t) => (<Badge key={t} variant="secondary" className="gap-1"><span>{t}</span><X className="h-3 w-3 cursor-pointer" onClick={() => set({ customTags: w.customTags.filter((x) => x !== t) })} aria-label={"remove " + t} /></Badge>))}
        </div>
      )}
      <div className="grid gap-3 sm:grid-cols-2 rounded-md border p-3">
        <label className="flex items-center gap-2 text-sm">
          <Checkbox checked={w.only_phone} onCheckedChange={(v) => set({ only_phone: !!v })} id="wiz-only-phone" />
          Only phone-verified leads
        </label>
        <label className="flex items-center gap-2 text-sm">
          <Checkbox checked={w.only_email} onCheckedChange={(v) => set({ only_email: !!v })} id="wiz-only-email" />
          Only leads with a contact email
        </label>
        <label className="flex items-center gap-2 text-sm">
          <span>Min rating</span>
          <Select value={w.min_rating == null ? "any" : String(w.min_rating)} onValueChange={(v) => set({ min_rating: v === "any" ? null : Number(v) })}>
            <SelectTrigger><SelectValue /></SelectTrigger>
            <SelectContent>
              <SelectItem value="any">Any rating</SelectItem>
              <SelectItem value="3">3.0+</SelectItem>
              <SelectItem value="4">4.0+</SelectItem>
              <SelectItem value="4.5">4.5+</SelectItem>
            </SelectContent>
          </Select>
        </label>
        <label className="flex items-center gap-2 text-sm">
          <span>Min reviews</span>
          <Select value={w.min_review_count == null ? "any" : String(w.min_review_count)} onValueChange={(v) => set({ min_review_count: v === "any" ? null : Number(v) })}>
            <SelectTrigger><SelectValue /></SelectTrigger>
            <SelectContent>
              <SelectItem value="any">Any count</SelectItem>
              <SelectItem value="5">5+</SelectItem>
              <SelectItem value="20">20+</SelectItem>
              <SelectItem value="50">50+</SelectItem>
            </SelectContent>
          </Select>
        </label>
      </div>
    </div>
  );
}


const DAYS: Array<[string, string]> = [["mon","Mon"],["tue","Tue"],["wed","Wed"],["thu","Thu"],["fri","Fri"],["sat","Sat"],["sun","Sun"]];
const TIMEZONES = ["Asia/Singapore", "Asia/Kuala_Lumpur", "Asia/Jakarta", "Asia/Bangkok", "Asia/Ho_Chi_Minh", "Asia/Manila", "Asia/Kolkata", "Asia/Shanghai", "Asia/Tokyo", "Asia/Seoul", "Europe/London", "America/New_York", "America/Los_Angeles"];

function StepOutreach({ w, set, forceDryRun }: { w: WizardState; set: (p: Partial<WizardState>) => void; forceDryRun: boolean }) {
  const [confirm, setConfirm] = React.useState("");
  return (
    <div className="space-y-4 py-1">
      <div className="space-y-1.5">
        <Label>Channels</Label>
        <div className="flex gap-3">
          {[["email","Email"],["voice","Voice"],["demo","Demo site"]].map(([val,label]) => {
            const active = w.channels.includes(val);
            return (
              <button key={val} type="button" role="checkbox" aria-checked={active} onClick={() => set({ channels: toggle(w.channels, val) })}
                className={cx("inline-flex items-center gap-1.5 rounded-md border px-3 py-1.5 text-sm", active ? "border-primary bg-primary/5 text-primary" : "border-border text-muted-foreground hover:bg-muted")}>
                <span className={cx("inline-block h-2.5 w-2.5 rounded-sm border border-current", active && "bg-primary")} aria-hidden="true" />{label}
              </button>
            );
          })}
        </div>
      </div>
      <div className="grid gap-4 sm:grid-cols-2">
        <div className="space-y-1.5">
          <Label htmlFor="wiz-email-cap">Daily email cap</Label>
          <Input id="wiz-email-cap" type="number" min={0} value={String(w.daily_email_cap)} onChange={(e) => set({ daily_email_cap: Number(e.target.value) })} />
        </div>
        <div className="space-y-1.5">
          <Label htmlFor="wiz-call-cap">Daily call cap</Label>
          <Input id="wiz-call-cap" type="number" min={0} value={String(w.daily_call_cap)} onChange={(e) => set({ daily_call_cap: Number(e.target.value) })} />
        </div>
      </div>
      <div className="grid gap-4 sm:grid-cols-2">
        <div className="space-y-1.5">
          <Label>Send window</Label>
          <div className="flex items-center gap-2">
            <Input type="time" value={w.send_window.start} onChange={(e) => set({ send_window: { ...w.send_window, start: e.target.value } })} aria-label="Window start" />
            <span className="text-muted-foreground">→</span>
            <Input type="time" value={w.send_window.end} onChange={(e) => set({ send_window: { ...w.send_window, end: e.target.value } })} aria-label="Window end" />
          </div>
        </div>
        <div className="space-y-2">
          <Label>Days</Label>
          <div className="flex flex-wrap gap-1.5">
            {DAYS.map(([v, lab]) => {
              const on = w.send_window.days.includes(v);
              return (<button key={v} type="button" aria-pressed={on} onClick={() => set({ send_window: { ...w.send_window, days: toggle(w.send_window.days, v) } })}
                className={cx("rounded-md border px-2 py-1 text-xs", on ? "border-primary bg-primary/10 text-primary" : "border-border text-muted-foreground")}>{lab}</button>);
            })}
          </div>
        </div>
      </div>
      <div className="grid gap-4 sm:grid-cols-2">
        <div className="space-y-1.5">
          <Label htmlFor="wiz-timezone">Timezone</Label>
          <Select value={w.timezone} onValueChange={(v) => set({ timezone: v })}>
            <SelectTrigger id="wiz-timezone"><SelectValue /></SelectTrigger>
            <SelectContent>{TIMEZONES.map((t) => <SelectItem key={t} value={t}>{t.replace("_", " ")}</SelectItem>)}</SelectContent>
          </Select>
        </div>
        <div className="space-y-1.5">
          <Label>Run schedule</Label>
          <Select value={w.run_schedule} onValueChange={(v) => set({ run_schedule: v })}>
            <SelectTrigger data-testid="wiz-schedule"><SelectValue /></SelectTrigger>
            <SelectContent>
              <SelectItem value="manual">Manual (Run button)</SelectItem>
              <SelectItem value="daily">Daily</SelectItem>
              <SelectItem value="weekdays">Weekdays only</SelectItem>
            </SelectContent>
          </Select>
        </div>
      </div>
      <div className="flex items-center justify-between rounded-md border p-3">
        <div>
          <p className="text-sm font-medium">Warm-up ramp</p>
          <p className="text-xs text-muted-foreground">Slowly ramp daily email volume over 21 days.</p>
        </div>
        <Switch checked={w.warm_up_enabled} onCheckedChange={(v) => set({ warm_up_enabled: !!v })} aria-label="Enable warm-up ramp" />
      </div>
      <div className="grid gap-4 sm:grid-cols-3">
        <div className="space-y-1.5">
          <Label htmlFor="wiz-followup">Follow-up delay (days)</Label>
          <Input id="wiz-followup" type="number" min={0} max={30} value={String(w.followup_delay_days)} onChange={(e) => set({ followup_delay_days: Number(e.target.value) })} />
        </div>
        <div className="space-y-1.5">
          <Label htmlFor="wiz-maxleads">Max leads / run</Label>
          <Input id="wiz-maxleads" type="number" min={0} value={w.max_leads_per_run == null ? "" : String(w.max_leads_per_run)} placeholder="Unlimited" onChange={(e) => set({ max_leads_per_run: e.target.value ? Number(e.target.value) : null })} />
        </div>
        <div className="space-y-1.5">
          <Label htmlFor="wiz-budget">Budget cap (US$)</Label>
          <Input id="wiz-budget" type="number" min={0} value={w.budget_cap == null ? "" : String(w.budget_cap)} placeholder="None" onChange={(e) => set({ budget_cap: e.target.value ? Number(e.target.value) : null })} />
        </div>
      </div>
      <div className="space-y-1.5">
        <Label>Approval mode</Label>
        <Select value={w.approval_mode} onValueChange={(v) => set({ approval_mode: v })}>
          <SelectTrigger data-testid="wiz-approval"><SelectValue /></SelectTrigger>
          <SelectContent>
            <SelectItem value="manual">Manual — drafts need your approval</SelectItem>
            <SelectItem value="auto">Auto — queue straight into send queue</SelectItem>
          </SelectContent>
        </Select>
      </div>
      <div className="rounded-md border p-3">
        <p className="text-sm font-medium">Campaign mode</p>
        <div className="mt-2 flex items-center gap-3">
          <label className="flex items-center gap-2 text-sm">
            <input type="radio" name="wiz-mode" checked={w.mode !== "live"} onChange={() => set({ mode: "dry_run" })} />
            Dry-run (recommended) — nothing is sent
          </label>
          <label className="flex items-center gap-2 text-sm">
            <input type="radio" name="wiz-mode" checked={w.mode === "live"} disabled={forceDryRun} onChange={() => set({ mode: "live" })} />
            Live
          </label>
        </div>
        {forceDryRun ? (
          <p className="mt-2 flex items-center gap-1.5 text-xs text-warn"><ShieldCheck className="h-3.5 w-3.5" aria-hidden="true" /> Live is disabled by the backend FORCE_DRY_RUN flag. This campaign will run in dry-run and nothing will be sent.</p>
        ) : w.mode === "live" ? (
          <div className="mt-2 space-y-2">
            <p className="text-xs text-destructive">Type <strong>CONFIRM</strong> to allow live sending for this campaign.</p>
            <Input value={confirm} onChange={(e) => setConfirm(e.target.value)} placeholder="CONFIRM" data-testid="wiz-confirm-live" />
          </div>
        ) : null}
      </div>
    </div>
  );
}


function StepReview({ w, forceDryRun }: { w: WizardState; forceDryRun: boolean }) {
  const rows: Array<[string, string]> = [
    ["Name", w.name || "✕"],
    ["Where", (w.wholeTown || w.city || w.towns.join(", ") || "✕") + ", " + (w.country || "SG") + (w.area_radius_km ? " (+" + w.area_radius_km.toFixed(1) + " km)" : "")],
    ["Business types", w.categories.concat(w.customTags).join(", ") || "✕"],
    ["Sources", (w.lead_sources.length ? w.lead_sources.join(" + ") : "✕")],
    ["Channels", (w.channels.length ? w.channels.join(" + ") : "✕")],
    ["Limits", "email " + w.daily_email_cap + "/day · calls " + w.daily_call_cap + "/day" + (w.budget_cap ? " · budget $" + w.budget_cap : "")],
    ["Follow-up", w.followup_delay_days + " days"],
    ["Approval", w.approval_mode],
    ["Mode", w.mode === "live" ? "LIVE sending" : "dry-run (nothing sent)"],
  ];
  return (
    <div className="space-y-3 py-1">
      <h3 className="text-base font-semibold">Review your campaign</h3>
      <dl className="divide-y divide-border rounded-md border border-border text-sm">
        {rows.map(([k, v]) => (
          <div key={k} className="flex justify-between gap-4 px-4 py-2">
            <dt className="shrink-0 text-muted-foreground">{k}</dt>
            <dd className="text-right font-medium">{v}</dd>
          </div>
        ))}
      </dl>
      {w.mode === "live" && !forceDryRun && (
        <p className="flex items-center gap-1.5 rounded-md border border-warn/40 bg-warn/10 px-3 py-2 text-xs text-warn">
          <AlertTriangle className="h-3.5 w-3.5" aria-hidden="true" /> LIVE mode: this campaign will actually send when run.
        </p>
      )}
      {forceDryRun && w.mode === "live" && (
        <p className="text-xs text-muted-foreground">Note: even though you selected Live, the backend FORCE_DRY_RUN flag means it will still run dry.</p>
      )}
    </div>
  );
}


  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4" role="presentation" onMouseDown={(e) => { if (e.target === e.currentTarget) onOpenChange(false); }}>
      <div className="flex max-h-[90vh] w-full max-w-3xl flex-col overflow-hidden rounded-xl border border-border bg-background shadow-xl" role="dialog" aria-modal="true" aria-label="Campaign wizard">
        <div className="border-b border-border px-6 py-4">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-lg font-semibold">{isEdit ? "Edit campaign" : "New campaign"}</h2>
              <p className="text-sm text-muted-foreground">{STEPS[step]} — step {step + 1} of {totalSteps}</p>
            </div>
            <Button variant="ghost" size="icon" onClick={() => onOpenChange(false)} aria-label="Close"><X className="h-4 w-4" /></Button>
          </div>
          <div className="mt-4 flex gap-1">
            {STEPS.map((label, i) => (
              <div key={label} className="flex flex-1 items-center gap-2">
                <span className={cx("flex h-5 w-5 shrink-0 items-center justify-center rounded-full text-[10px] font-semibold", i < step ? "bg-primary text-primary-foreground" : i === step ? "bg-primary/15 text-primary" : "bg-muted text-muted-foreground")} aria-hidden="true">
                  {i < step ? <Check className="h-3 w-3" /> : i + 1}
                </span>
                <span className={cx("text-xs font-medium", i === step ? "text-foreground" : "text-muted-foreground")}>{label}</span>
              </div>
            ))}
          </div>
        </div>

        <div className="flex-1 overflow-y-auto px-6 py-5">
          {step === 0 && <StepBasics w={w} set={setW2} />}
          {step === 1 && <StepLocation w={w} set={setW2} countries={countriesQ.data?.countries ?? []} states={statesArr} cities={citiesArr} loading={citiesQ.isLoading} />}
          {step === 2 && <StepBusiness w={w} set={setW2} />}
          {step === 3 && <StepOutreach w={w} set={setW2} forceDryRun={force_dry_run_q} />}
          {step === 4 && <StepReview w={w} forceDryRun={force_dry_run_q} />}
          {Object.keys(serverErrors).length > 0 && (
            <div className="mt-3 space-y-1 rounded-md border border-destructive/40 bg-destructive/10 p-3 text-xs text-destructive">
              {Object.entries(serverErrors).map(([k, v]) => (v.errors || []).map((e, i) => <p key={k + i}>{e}</p>))}
            </div>
          )}
        </div>

        <div className="flex items-center justify-between gap-2 border-t border-border px-6 py-4">
          {step === 4 ? (
            <Button variant="ghost" disabled={busy} onClick={() => onOpenChange(false)}>Cancel</Button>
          ) : (
            <Button variant="ghost" onClick={() => onOpenChange(false)}>Cancel</Button>
          )}
          <div className="flex items-center gap-2">
            {step > 0 && step < 4 && (
              <Button variant="outline" size="sm" onClick={() => setStep((s) => Math.max(0, s - 1))}><ChevronLeft className="h-4 w-4 mr-1" /> Back</Button>
            )}
            {step < 3 && (
              <Button size="sm" onClick={() => next(step)} data-testid="wiz-next">
                Next <ChevronRight className="h-4 w-4 ml-1" />
              </Button>
            )}
            {step === 3 && (
              <Button size="sm" onClick={() => next(3)} data-testid="wiz-review">
                Review <ChevronRight className="h-4 w-4 ml-1" />
              </Button>
            )}
            {step === 4 && (<>
              <Button variant="outline" size="sm" disabled={busy} onClick={() => setStep(3)}><ChevronLeft className="h-4 w-4 mr-1" /> Back</Button>
              <Button size="sm" disabled={busy} onClick={() => submitWizard(false)} data-testid="wiz-create">
                {busy && <Loader2 className="h-4 w-4 animate-spin mr-1" aria-hidden="true" />} Create campaign
              </Button>
              <Button size="sm" variant="secondary" disabled={busy} onClick={() => submitWizard(true)} data-testid="wiz-create-run">
                {busy && <Loader2 className="h-4 w-4 animate-spin mr-1" aria-hidden="true" />} Create & start (dry-run)
              </Button>
            </>)}
          </div>
        </div>
      </div>
    </div>
  );
}

export default CampaignWizard;