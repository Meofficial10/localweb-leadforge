"use client";

import * as React from "react";
import { useQuery } from "@tanstack/react-query";
import { CheckCircle2, Circle, ChevronRight } from "lucide-react";
import Link from "next/link";
import { integrationsApi, campaignsApi, queueApi, settingsApi } from "@/app/lib/api";

type Step = {
  id: string; label: string; desc: string; href: string;
  done: boolean;
};

export default function OnboardingChecklist() {
  const int = useQuery({ queryKey: ["integrations"], queryFn: () => integrationsApi.list() });
  const camps = useQuery({ queryKey: ["campaigns"], queryFn: () => campaignsApi.list() });
  const drafts = useQuery({ queryKey: ["queue"], queryFn: () => queueApi.list() });
  const settings = useQuery({ queryKey: ["settings"], queryFn: () => settingsApi.get() });
  const branding = settings.data?.branding || {};

  const health = int.data?.health?.checklist ?? [];
  const llmOk = health.some((h) => h.id === "llm" && h.ok);
  const leadSourceOk = health.some((h) => ["osm", "google", "apify", "lead_source"].includes(h.id) && h.ok);
  const identityOk = health.some((h) => h.id === "identity" && h.ok) || Boolean(branding.sender_email || branding.sender_phone);
  const campaignOk = (camps.data?.length ?? 0) > 0;
  const draftOk = (drafts.data?.length ?? 0) > 0;

  const steps: Step[] = [
    { id: "llm", label: "Connect an LLM writer", desc: "Add an OpenAI-compatible key so drafts can be written.", href: "/integrations", done: llmOk },
    { id: "source", label: "Connect a lead source", desc: "Hook up OSM or Apify to discover businesses.", href: "/integrations", done: leadSourceOk },
    { id: "identity", label: "Verify sender identity", desc: "Set your sender email or phone in the settings.", href: "/settings", done: identityOk },
    { id: "campaign", label: "Create your first campaign", desc: "Build a targeting plan in the wizard.", href: "/campaigns", done: campaignOk },
    { id: "draft", label: "Review drafts in the queue", desc: "Approve or edit generated outreach messages.", href: "/outreach", done: draftOk },
  ];

  const remaining = steps.filter((s) => !s.done).length;
  if (remaining === 0) return null;
  const pct = Math.round(((steps.length - remaining) / steps.length) * 100);

  const clsFor = (done: boolean) => (done ? "text-foreground line-through decoration-muted-foreground/40" : "text-foreground");

  return (
    <section aria-label="Getting started" className="rounded-xl border bg-card/60 p-4">
      <div className="mb-3 flex items-center justify-between gap-4">
        <div>
          <h2 className="text-sm font-semibold">Getting started</h2>
          <p className="text-xs text-muted-foreground">Finish {remaining} more step{remaining === 1 ? "" : "s"} to launch your first dry-run.</p>
        </div>
        <span className="text-xs font-medium tabular-nums text-muted-foreground">{pct}%</span>
      </div>
      <ol className="space-y-1">
        {steps.map((s) => (
          <li key={s.id}>
            <Link href={s.href} className="group flex items-start gap-3 rounded-md p-2 transition-colors hover:bg-muted/50" title={s.desc}>
              {s.done ? <CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0 text-emerald-500" /> : <Circle className="mt-0.5 h-4 w-4 shrink-0 text-muted-foreground/60" />}
              <span className="min-w-0 flex-1">
                <span className={"block text-sm font-medium " + clsFor(s.done)}>{s.label}</span>
                <span className="block text-xs text-muted-foreground">{s.desc}</span>
              </span>
              <ChevronRight className="mt-0.5 h-4 w-4 shrink-0 text-muted-foreground/40 transition-transform group-hover:translate-x-0.5" />
            </Link>
          </li>
        ))}
      </ol>
    </section>
  );
}
