"use client";

export const dynamic = "force-dynamic";

import * as React from "react";
import { useQuery } from "@tanstack/react-query";
import { Plus, Megaphone } from "lucide-react";
import { campaignsApi, type Campaign } from "@/app/lib/api";
import { PageHeader } from "@/app/components/shared/page-header";
import { EmptyState } from "@/app/components/shared/empty-state";
import { CampaignCard } from "@/app/components/campaign-card";
import { CampaignForm } from "@/app/components/campaign-form";
import { Skeleton } from "@/app/components/ui/skeleton";
import { Button } from "@/app/components/ui/button";
import {
  Dialog, DialogContent, DialogHeader, DialogTitle,
} from "@/app/components/ui/dialog";

export default function CampaignsPage() {
  const { data, isLoading, isError } = useQuery({ queryKey: ["campaigns"], queryFn: campaignsApi.list });
  const [creating, setCreating] = React.useState(false);
  const [editing, setEditing] = React.useState<Campaign | null>(null);

  return (
    <div>
      <PageHeader
        title="Campaigns"
        description="Create targeting campaigns for discovery, enrichment, AI-written demos and dry-run outreach."
        actions={
          <Button onClick={() => setCreating(true)}>
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
          {data.map((c) => (<CampaignCard key={c.id} campaign={c} onEdit={setEditing} />))}
        </div>
      ) : (
        <EmptyState
          icon={<Megaphone className="h-6 w-6" />}
          title="No campaigns yet"
          description="Create your first campaign to start discovering leads in a city. Everything runs in dry-run by default."
          action={<Button onClick={() => setCreating(true)}><Plus className="h-4 w-4" /> New campaign</Button>}
        />
      )}

      <Dialog open={creating} onOpenChange={setCreating}>
        <DialogContent className="max-h-[90vh] overflow-y-auto sm:max-w-xl">
          <DialogHeader>
            <DialogTitle>New campaign</DialogTitle>
          </DialogHeader>
          {creating && <CampaignForm onDone={() => setCreating(false)} />}
        </DialogContent>
      </Dialog>

      <Dialog open={!!editing} onOpenChange={(o) => !o && setEditing(null)}>
        <DialogContent className="max-h-[90vh] overflow-y-auto sm:max-w-xl">
          <DialogHeader>
            <DialogTitle>Edit campaign</DialogTitle>
          </DialogHeader>
          {editing && <CampaignForm campaign={editing} onDone={() => setEditing(null)} />}
        </DialogContent>
      </Dialog>
    </div>
  );
}
