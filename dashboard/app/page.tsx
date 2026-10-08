"use client";

import * as React from "react";
import { useQuery } from "@tanstack/react-query";
import { Users, Mail, MousePointerClick, CheckCircle2, Phone, ShieldAlert, Loader2, Activity, Gauge } from "lucide-react";
import { systemApi, settingsApi } from "@/app/lib/api";
import { PageHeader } from "@/app/components/shared/page-header";
import { Skeleton } from "@/app/components/ui/skeleton";
import dynamic from "next/dynamic";

import { Card, CardContent, CardHeader, CardTitle } from "@/app/components/ui/card";
import { Badge } from "@/app/components/ui/badge";

const ReadsPerDay = dynamic(() => import("@/app/components/overview-charts").then((m) => ({ default: m.LeadsPerDayChart })), { ssr: false, loading: () => <div className="flex h-[260px] items-center justify-center text-sm text-muted-foreground">Loading chart…</div> });
const FunnelChartDyn = dynamic(() => import("@/app/components/overview-charts").then((m) => ({ default: m.FunnelChart })), { ssr: false, loading: () => <div className="flex h-[260px] items-center justify-center text-sm text-muted-foreground">Loading chart…</div> });
import OnboardingChecklist from "@/app/components/onboarding-checklist";
import { DemoDataBanner } from "@/app/components/demo-data-banner";

function KpiCard({ icon, label, value, suffix, accent }: { icon: React.ReactNode; label: string; value: number | string; suffix?: string; accent?: string }) {
  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
        <CardTitle className="text-xs font-medium text-muted-foreground">{label}</CardTitle>
        <span className="text-primary">{icon}</span>
      </CardHeader>
      <CardContent>
        <p className={"text-2xl font-bold " + (accent || "")}>
          {value}
          {suffix ? <span className="text-sm font-normal text-muted-foreground"> {suffix}</span> : null}
        </p>
      </CardContent>
    </Card>
  );
}


function CapBar({ label, used, cap, unit }: { label: string; used: number; cap?: number; unit: string }) {
  const c = typeof cap === "number" && cap > 0 ? cap : 1;
  const pct = Math.min(100, Math.round((used / c) * 100));
  return (
    <div>
      <div className="mb-1 flex items-center justify-between text-xs">
        <span className="font-medium text-muted-foreground">{label}</span>
        <span className="tabular-nums">{used} / {typeof cap === "number" ? cap : "—"} {unit}</span>
      </div>
      <div className="h-2 w-full overflow-hidden rounded-full bg-muted" role="progressbar" aria-valuenow={pct} aria-valuemin={0} aria-valuemax={100} aria-label={label + " usage"}>
        <div className={"h-full rounded-full " + (pct >= 100 ? "bg-destructive" : "bg-primary")} style={{ width: pct + "%" }} />
      </div>
    </div>
  );
}


export default function OverviewPage() {
  // M5: single combined endpoint (metrics + status + caps + recent audit) with a short TTL cache
  const { data: overview, isLoading, isError } = useQuery({
    queryKey: ["overview"],
    queryFn: systemApi.overview,
    staleTime: 5_000,
  });
  const data = overview?.metrics;
  const status = { data: overview?.status };
  const caps = { data: overview?.caps };
  const activity = overview?.audit ?? [];
  const activityLoading = isLoading;
  const k = data?.kpis;
  const dry = status.data?.force_dry_run !== false;

  return (
    <div>
      <PageHeader
        title="Overview"
        description="Pipeline health at a glance. Everything runs in dry-run until you explicitly enable live."
        actions={dry ? <Badge variant="secondary">Global dry-run active</Badge> : null}
      />
      <DemoDataBanner />
      {isLoading ? (
        <div className="space-y-6">
          <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">{[]}</div>
          <Skeleton className="h-64" />
        </div>
      ) : (
        <>
          <OnboardingChecklist />
          <div className="mt-4 grid gap-4 sm:grid-cols-2 xl:grid-cols-5">
            <KpiCard icon={<Users className="h-4 w-4" />} label="Leads found" value={k?.leads_found ?? 0} />
            <KpiCard icon={<Mail className="h-4 w-4" />} label="Emails drafted" value={k?.emails_drafted ?? 0} />
            <KpiCard icon={<CheckCircle2 className="h-4 w-4" />} label="Emails sent" value={k?.emails_sent ?? 0} />
            <KpiCard icon={<MousePointerClick className="h-4 w-4" />} label="Replies" value={k?.replies ?? 0} />
            <KpiCard icon={<Phone className="h-4 w-4" />} label="Calls placed" value={k?.calls_made ?? 0} />
          </div>
          <div className="mt-4 grid gap-4 lg:grid-cols-5">
            <Card className="lg:col-span-3">
              <CardHeader>
                <CardTitle className="text-sm">Leads discovered per day</CardTitle>
              </CardHeader>
              <CardContent className="p-0">
                <ReadsPerDay data={data?.leads_per_day || []} />
              </CardContent>
            </Card>
            <Card className="lg:col-span-2">
              <CardHeader>
                <CardTitle className="text-sm">Funnel</CardTitle>
              </CardHeader>
              <CardContent className="p-0">
                <FunnelChartDyn data={funnelData(data?.funnel)} />
              </CardContent>
            </Card>
          </div>
          <div className="mt-4 grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
            <KpiCard icon={<ShieldAlert className="h-4 w-4" />} label="Bounce rate" value={k?.bounce_rate != null ? (k.bounce_rate * 100).toFixed(2) : 0} suffix="%" />
            <KpiCard icon={<ShieldAlert className="h-4 w-4" />} label="Complaint rate" value={k?.complaint_rate != null ? (k.complaint_rate * 100).toFixed(2) : 0} suffix="%" />
            <KpiCard icon={<Users className="h-4 w-4" />} label="Opted out" value={k?.opted_out ?? 0} />
            <KpiCard icon={<Users className="h-4 w-4" />} label="With contact info" value={k?.with_contact ?? 0} />
          </div>

          <div className="mt-4 grid gap-4 lg:grid-cols-2">
            <Card className="min-w-0">
              <CardHeader>
                <CardTitle className="text-sm inline-flex items-center gap-2"><Gauge className="h-4 w-4" /> Usage vs daily caps</CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <CapBar label="Emails (sent + drafted)" used={(k?.emails_sent ?? 0) + (k?.emails_drafted ?? 0)} cap={caps?.data?.daily_email_cap} unit="emails" />
                <CapBar label="Calls today" used={k?.calls_made ?? 0} cap={caps?.data?.daily_call_cap} unit="calls" />
                <p className="text-xs text-muted-foreground">Caps gate the sending pipeline; with the global dry-run nothing is ever delivered. Warm-up ramp: {caps?.data?.warm_up_schedule?.start ?? 5}/day growing to the cap over {caps?.data?.warm_up_schedule?.days ?? 21} days.</p>
              </CardContent>
            </Card>
            <Card className="min-w-0">
              <CardHeader>
                <CardTitle className="text-sm inline-flex items-center gap-2"><Activity className="h-4 w-4" /> Recent activity</CardTitle>
              </CardHeader>
              <CardContent>
                {activityLoading ? (
                  <Skeleton className="h-24" />
                ) : (activity || []).length === 0 ? (
                  <p className="text-sm text-muted-foreground">No activity yet.</p>
                ) : (
                  <ul className="space-y-2">
                    {(activity || []).slice(0, 8).map((a: any) => (
                      <li key={a.id} className="flex items-start gap-2 text-sm">
                        <Badge variant="outline" className="mt-0.5 shrink-0 font-mono text-[10px]">{a.action}</Badge>
                        <span className="min-w-0">
                          <span className="block truncate text-muted-foreground">{a.detail ? JSON.stringify(a.detail).slice(0, 80) : ""}</span>
                          <span className="block text-xs text-muted-foreground/70">{a.created_at}</span>
                        </span>
                      </li>
                    ))}
                  </ul>
                )}
              </CardContent>
            </Card>
          </div>
        </>
      )}
    </div>
  );
}

function funnelData(funnel: any) {
  const order = ["discovered", "with_contact", "profiled", "demo_built", "emails_drafted", "emails_sent", "replied"];
  const labelM: Record<string, string> = {
    discovered: "Discovered",
    with_contact: "With contact",
    profiled: "Profiled",
    demo_built: "Demo built",
    emails_drafted: "Drafted",
    emails_sent: "Sent",
    replied: "Replied",
  };
  return order.map((key) => ({ name: labelM[key], value: funnel?.[key] ?? 0 }));
}
