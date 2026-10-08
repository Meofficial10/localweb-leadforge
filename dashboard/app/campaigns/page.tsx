"use client";

export const dynamic = "force-dynamic";

import * as React from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { Plus, Megaphone } from "lucide-react";
import { campaignsApi, type Campaign } from "@/app/lib/api";
import { PageHeader } from "@/app/components/shared/page-header";
import { EmptyState } from "@/app/components/shared/empty-state";
import { CampaignCard } from "@/app/components/campaign-card";
import { CampaignWizard } from "@/app/campaigns/_components/campaign-wizard";
import { Skeleton } from "@/app/components/ui/skeleton";
import { Button } from "@/app/components/ui/button";

export default function CampaignsPage() {
  const qc = useQueryClient();
  const { data, isLoading, isError } = useQuery({ queryKey: ["campaigns"], queryFn: campaignsApi.list });
  const [wiz, setWiz] = React.useState<{ open: boolean; mode: "create" | "edit"; campaign: Campaign | null }>({ open: false, mode: "create", campaign: null });

  const openCreate = () => setWiz({ open: true, mode: "create", campaign: null });
  const openEdit = (c: Campaign) => setWiz({ open: true, mode: "edit", campaign: c });
  const openDuplicate = async (c: Campaign) => {
    setWiz({ open: true, mode: "create", campaign: c });
  };

  return (
    <div>
      <PageHeader
        title="Campaigns"
        description="Create targeting campaigns for discovery, enrichment, AI-written demos and dry-run outreach."
        actions={
          <Button onClick={openCreate}>
            <Plus className="h-4 w-4" /> New campaign
          </Button>
        }
      />
      {isLoading ? (
        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
          {[1, 2, 3].map((i) => (<Skeleton key={i} className="h-44" />))}
        </div>
      ) : isError ? (
        <p className="text-sm text-destructive">Couldn&apos;t load campaigns — is the backend running on port 8000?</p>
      ) : (data && data.length > 0) ? (
        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
          {data.map((c) => (<CampaignCard key={c.id} campaign={c} onEdit={openEdit} onDuplicate={openDuplicate} />))}
        </div>
      ) : (
        <EmptyState
          icon={<Megaphone className="h-6 w-6" />}
          title="No campaigns yet"
          description="Create your first campaign to start discovering leads in a city. Everything runs in dry-run by default."
          action={<Button onClick={openCreate}><Plus className="h-4 w-4" /> New campaign</Button>}
        />
      )}

      <CampaignWizard
        open={wiz.open}
        onOpenChange={(v) => setWiz((p) => ({ ...p, open: v }))}
        campaign={wiz.campaign}
        mode={wiz.mode}
        onDone={() => { setWiz((p) => ({ ...p, open: false })); qc.invalidateQueries({ queryKey: ["campaigns"] }); }}
      />
    </div>
  );
}
