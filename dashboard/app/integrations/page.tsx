"use client";
export const dynamic = "force-dynamic";

import * as React from "react";
import { useQuery } from "@tanstack/react-query";
import { CircleCheck, CircleX, ShieldCheck, ShieldAlert } from "lucide-react";
import { integrationsApi, type IntegrationCard } from "@/app/lib/api";
import { PageHeader } from "@/app/components/shared/page-header";
import { Skeleton } from "@/app/components/ui/skeleton";
import { ConfigureDrawer } from "./_components/configure-drawer";
import { IntegrationCardView } from "./_components/integration-card";

export default function IntegrationsPage() {
  const { data, isLoading, isError } = useQuery({ queryKey: ["integrations"], queryFn: integrationsApi.list });
  const [drawerCard, setDrawerCard] = React.useState<IntegrationCard | null>(null);
  const [open, setOpen] = React.useState(false);

  const health = data?.health ?? null;
  const cards = data?.cards ?? [];

  return (
    <div className="space-y-6">
      <PageHeader
        title="Integrations"
        description="Connect the systems that power LeadForge: lead sources, the LLM writer, demo hosting, email, voice, and DNC. Everything runs in dry-run by default; every secret is encrypted at rest."
      />

      {isLoading ? (
        <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3" aria-busy="true">
          {[1, 2, 3, 4, 5, 6, 7, 8, 9].map((i) => <Skeleton key={i} className="h-48" />)}
        </div>
      ) : isError ? (
        <p role="alert" className="rounded-md border border-destructive/40 bg-destructive/10 px-3 py-2 text-sm text-destructive">Couldn&apos;t load integrations. Check that the backend is running.</p>
      ) : (
        <>
          {/* health summary */}
          <section aria-label="Integration health" className={"rounded-xl border p-4 sm:p-5 " + (health?.ok ? "border-green-500/30 bg-green-500/5" : "border-amber-500/30 bg-amber-500/5")}>
            <div className="flex flex-wrap items-center justify-between gap-3">
              <div className="flex items-center gap-3">
                {health?.ok ? <ShieldCheck className="h-6 w-6 text-green-600 dark:text-green-400" aria-hidden="true" /> : <ShieldAlert className="h-6 w-6 text-amber-600 dark:text-amber-400" aria-hidden="true" />}
                <div>
                  <h2 className="text-base font-semibold">{health?.message}</h2>
                  <p className="text-sm text-muted-foreground">What&apos;s still needed before a campaign can run:</p>
                </div>
              </div>
            </div>
            <ul className="mt-3 grid gap-2 sm:grid-cols-3">
              {health?.checklist.map((item) => (
                <li key={item.id} className={"flex items-start gap-2 rounded-md border bg-background/60 px-3 py-2 text-sm " + (item.ok ? "border-green-500/30" : "border-border")}>
                  {item.ok ? <CircleCheck className="mt-0.5 h-4 w-4 shrink-0 text-green-600 dark:text-green-400" aria-hidden="true" /> : <CircleX className="mt-0.5 h-4 w-4 shrink-0 text-amber-600 dark:text-amber-400" aria-hidden="true" />}
                  <div className="min-w-0">
                    <p className="font-medium">{item.name}</p>
                    <p className="text-xs text-muted-foreground">{item.ok ? "Ready" : item.detail}</p>
                  </div>
                </li>
              ))}
            </ul>
          </section>

          {/* card grid */}
          <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
            {cards.map((card) => (
              <IntegrationCardView key={card.id} card={card} onConfigure={(c) => { setDrawerCard(c); setOpen(true); }} />
            ))}
          </div>
        </>
      )}

      <ConfigureDrawer card={drawerCard} open={open} onOpenChange={setOpen} />
    </div>
  );
}
