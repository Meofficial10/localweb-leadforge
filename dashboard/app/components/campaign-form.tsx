"use client";

import * as React from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { toast } from "sonner";
import { Loader2, Sparkles } from "lucide-react";
import { campaignsApi, type Campaign } from "@/app/lib/api";
import { Button } from "@/app/components/ui/button";
import { Input } from "@/app/components/ui/input";
import { Label } from "@/app/components/ui/label";
import {
  Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle,
} from "@/app/components/ui/dialog";
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from "@/app/components/ui/select";
import { asError } from "@/app/lib/utils";

const schema = z.object({
  name: z.string().min(2, "Name is required (min 2 chars)"),
  city: z.string().min(2, "City is required"),
  country: z.string().default("Singapore"),
  categories: z.string().default(""),
  area_radius_km: z.string().or(z.literal("")).default("5"),
  lead_source: z.string().default("both"),
  lead_sources: z.array(z.string()).default([]),
  daily_email_cap: z.string().default("50"),
  daily_call_cap: z.string().default("10"),
  max_leads_per_run: z.string().or(z.literal("")),
  followup_delay_days: z.string().default("4"),
  approval_mode: z.string().default("manual"),
  timezone: z.string().default("Asia/Singapore"),
  send_window: z.string().default("09:00,18:00"),
});

type FormValues = z.input<typeof schema> & Record<string, any>;

function toDefault(cam?: Campaign | null): FormValues {
  return {
    name: cam?.name ?? "",
    city: cam?.city ?? "",
    country: cam?.country ?? "Singapore",
    categories: (cam?.categories ?? []).join(", "),
    area_radius_km: cam?.area_radius_km != null ? String(cam.area_radius_km) : "5",
    lead_source: cam?.lead_source ?? "both",
    lead_sources: cam?.lead_sources?.length ? cam.lead_sources : (cam?.lead_source === "google" ? ["google"] : cam?.lead_source === "osm" ? ["osm"] : ["google", "osm"]),
    daily_email_cap: String(cam?.daily_email_cap ?? 50),
    daily_call_cap: String(cam?.daily_call_cap ?? 10),
    max_leads_per_run: cam?.max_leads_per_run != null ? String(cam.max_leads_per_run) : "",
    followup_delay_days: String(cam?.followup_delay_days ?? 4),
    approval_mode: cam?.approval_mode ?? "manual",
    timezone: cam?.timezone ?? "Asia/Singapore",
    send_window: cam?.send_window
      ? (cam.send_window.start || "09:00") + "," + (cam.send_window.end || "18:00")
      : "09:00,18:00",
  };
}

export function CampaignForm({ campaign, onDone }: { campaign?: Campaign | null; onDone: () => void }) {
  const isEdit = !!campaign;
  const { register, handleSubmit, setValue, watch, formState: { errors, isSubmitting } } =
    useForm<FormValues>({ resolver: zodResolver(schema), defaultValues: toDefault(campaign) });
  const watchLeadSources = watch("lead_sources");

  const onSubmit = async (v: FormValues) => {
    try {
      const [sendStart, sendEnd] = (v.send_window || "09:00,18:00").split(",").map((s: string) => s.trim());
      const payload = {
        name: v.name,
        city: v.city,
        country: v.country,
        categories: (v.categories || "").split(",").map((s: string) => s.trim()).filter(Boolean),
        lead_source: (v.lead_source || "both") as "google" | "osm" | "both",
        lead_sources: v.lead_sources?.length ? v.lead_sources : undefined,
        area_radius_km: v.area_radius_km ? Number(v.area_radius_km) : undefined,
        daily_email_cap: Number(v.daily_email_cap || 50),
        daily_call_cap: Number(v.daily_call_cap || 10),
        max_leads_per_run: v.max_leads_per_run ? Number(v.max_leads_per_run) : undefined,
        followup_delay_days: Number(v.followup_delay_days || 4),
        approval_mode: (v.approval_mode || "manual") as "manual" | "auto",
        timezone: v.timezone || "Asia/Singapore",
        send_window: { start: sendStart || "09:00", end: sendEnd || "18:00" },
      };
      const res = isEdit && campaign
        ? await campaignsApi.update(campaign.id, payload)
        : await campaignsApi.create(payload as any);
      toast.success(isEdit ? "Campaign updated" : "Campaign created");
      if (res.mode === "dry_run") toast.info("Saved (dry-run)");
      onDone();
    } catch (e) {
      toast.error(asError(e));
    }
  };

  return (
    <form onSubmit={handleSubmit(onSubmit)} className="space-y-5" noValidate>
      <div className="grid gap-4 sm:grid-cols-2">
        <div className="space-y-1.5">
          <Label htmlFor="name">Campaign name *</Label>
          <Input id="name" placeholder="Queensway Clinics" {...register("name")} />
          {errors.name && <p className="text-xs text-destructive">{errors.name.message}</p>}
        </div>
        <div className="space-y-1.5">
          <Label htmlFor="city">City *</Label>
          <Input id="city" placeholder="Singapore" {...register("city")} />
          {errors.city && <p className="text-xs text-destructive">{errors.city.message}</p>}
        </div>
      </div>
      <div className="space-y-1.5">
        <Label htmlFor="categories">Categories (comma separated)</Label>
        <Input id="categories" placeholder="dentist, clinic, salon" {...register("categories")} />
      </div>
      <div className="grid gap-4 sm:grid-cols-3">
        <div className="space-y-1.5">
          <Label htmlFor="area_radius_km">Radius (km)</Label>
          <Input id="area_radius_km" type="number" min={0} max={100} {...register("area_radius_km")} />
        </div>
        <div className="space-y-1.5">
          <Label htmlFor="daily_email_cap">Email cap / day</Label>
          <Input id="daily_email_cap" type="number" min={1} {...register("daily_email_cap")} />
        </div>
        <div className="space-y-1.5">
          <Label htmlFor="daily_call_cap">Call cap / day</Label>
          <Input id="daily_call_cap" type="number" min={0} {...register("daily_call_cap")} />
        </div>
      </div>
      <div className="grid gap-4 sm:grid-cols-2">
        <div className="space-y-2">
          <Label>Lead sources (multi-select)</Label>
          <div className="flex flex-wrap gap-2">
            {[
              ["google", "Google Maps"],
              ["osm", "OpenStreetMap"],
              ["apify", "Apify (scraper)"],
            ].map(([val, label]) => {
              const active = (watchLeadSources?.includes(val as string)) ?? (val === "google" || val === "osm" ? ((toDefault(campaign))?.lead_sources?.includes(val as string) ?? false) : false);
              return (
                <button
                  key={val}
                  type="button"
                  onClick={() => {
                    const cur = watch("lead_sources") as string[];
                    const next = cur.includes(val as string) ? cur.filter((x) => x !== val) : [...cur, val as string];
                    setValue("lead_sources", next);
                  }}
                  aria-pressed={active}
                  className={`inline-flex items-center gap-2 rounded-md border px-3 py-1.5 text-sm transition-colors ${
                    active ? "border-primary bg-primary/10 text-primary" : "border-border text-muted-foreground hover:bg-muted"
                  }`}
                >
                  <span className={`inline-block h-2.5 w-2.5 rounded-sm border border-current ${
                    active ? "bg-primary" : "bg-transparent"
                  }`} aria-hidden="true" />
                  {label}
                </button>
              );
            })}
          </div>
        </div>
        <div className="space-y-1.5">
          <Label>Approval mode</Label>
          <Select value={undefined} onValueChange={(v) => setValue("approval_mode", v)}>
            <SelectTrigger><SelectValue placeholder="Approval" /></SelectTrigger>
            <SelectContent>
              <SelectItem value="manual">Manual approval</SelectItem>
              <SelectItem value="auto">Auto-approved</SelectItem>
            </SelectContent>
          </Select>
        </div>
      </div>
      <div className="grid gap-4 sm:grid-cols-2">
        <div className="space-y-1.5">
          <Label htmlFor="followup_delay_days">Follow-up delay (days)</Label>
          <Input id="followup_delay_days" type="number" min={0} max={30} {...register("followup_delay_days")} />
        </div>
        <div className="space-y-1.5">
          <Label htmlFor="send_window">Send window</Label>
          <Input id="send_window" placeholder="09:00,18:00" {...register("send_window")} />
        </div>
      </div>
      <div className="flex items-center gap-2 rounded-md border border-warn/40 bg-warn/10 px-3 py-2 text-xs text-warn">
        <Sparkles className="h-3.5 w-3.5" aria-hidden="true" />
        <span>New campaigns are created in <strong>dry-run</strong> — nothing is sent until you explicitly enable LIVE (and the backend's global dry-run always wins).</span>
      </div>
      <div className="flex justify-end gap-2">
        <Button type="button" variant="outline" onClick={onDone}>Cancel</Button>
        <Button type="submit" disabled={isSubmitting}>
          {isSubmitting && <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" />}
          {isEdit ? "Save changes" : "Create campaign"}
        </Button>
      </div>
    </form>
  );
}
