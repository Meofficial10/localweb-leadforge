"use client";

import * as React from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { Pause, Play, Copy, Trash2, Pencil, Settings2 } from "lucide-react";
import { toast } from "sonner";
import { campaignsApi, type Campaign } from "@/app/lib/api";
import { Card, CardContent, CardHeader, CardTitle } from "@/app/components/ui/card";
import { Button } from "@/app/components/ui/button";
import { Badge } from "@/app/components/ui/badge";
import { ModeChip } from "@/app/components/shared/status-badge";
import {
  AlertDialog, AlertDialogContent, AlertDialogDescription, AlertDialogFooter,
  AlertDialogHeader, AlertDialogTitle, AlertDialogTrigger, AlertDialogCancel, AlertDialogAction,
} from "@/app/components/ui/alert-dialog";
import { asError } from "@/app/lib/utils";

export function CampaignCard({ campaign, onEdit }: { campaign: Campaign; onEdit: (c: Campaign) => void }) {
  const qc = useQueryClient();
  const invalidate = () => qc.invalidateQueries({ queryKey: ["campaigns"] });

  const run = useMutation({
    mutationFn: () => campaignsApi.run(campaign.id),
    onSuccess: () => { toast.success("Campaign run triggered (dry-run)"); invalidate(); },
    onError: (e) => toast.error(asError(e)),
  });
  const pause = useMutation({
    mutationFn: (paused: boolean) => campaignsApi.pause(campaign.id, paused),
    onSuccess: () => { toast.success(campaign.is_paused ? "Campaign resumed" : "Campaign paused"); invalidate(); },
    onError: (e) => toast.error(asError(e)),
  });
  const duplicate = useMutation({
    mutationFn: () => campaignsApi.duplicate(campaign.id),
    onSuccess: () => { toast.success("Campaign duplicated (paused)"); invalidate(); },
    onError: (e) => toast.error(asError(e)),
  });
  const remove = useMutation({
    mutationFn: () => campaignsApi.del(campaign.id),
    onSuccess: () => { toast.success("Campaign deleted"); invalidate(); },
    onError: (e) => toast.error(asError(e)),
  });

  return (
    <Card className={campaign.is_paused ? "opacity-75" : undefined}>
      <CardHeader className="flex flex-row items-start justify-between space-y-0">
        <div className="space-y-1">
          <CardTitle>{campaign.name}</CardTitle>
          <p className="text-sm text-muted-foreground">
            {campaign.city}, {campaign.country} · {(campaign.categories || []).join(", ") || "all categories"}
          </p>
        </div>
        <ModeChip mode={campaign.mode} />
      </CardHeader>
      <CardContent className="space-y-3">
        <div className="flex flex-wrap gap-2 text-xs text-muted-foreground">
          <Badge variant="secondary">{campaign.daily_email_cap}/day email</Badge>
          <Badge variant="secondary">{campaign.daily_call_cap}/day call</Badge>
          <Badge variant="secondary">{campaign.approval_mode} approval</Badge>
          <Badge variant="secondary">Follow-up {campaign.followup_delay_days}d</Badge>
          {campaign.is_paused && <Badge variant="warning">paused</Badge>}
        </div>
        <div className="flex items-center gap-1.5">
          <Button size="sm" variant={campaign.is_paused ? "secondary" : "outline"} onClick={() => pause.mutate(!campaign.is_paused)}>
            {campaign.is_paused ? <Play className="h-3.5 w-3.5" /> : <Pause className="h-3.5 w-3.5" />}
            {campaign.is_paused ? "Resume" : "Pause"}
          </Button>
          <Button size="sm" variant="outline" onClick={() => onEdit(campaign)}>
            <Pencil className="h-3.5 w-3.5" /> Edit
          </Button>
          <Button size="sm" variant="outline" onClick={() => duplicate.mutate()}>
            <Copy className="h-3.5 w-3.5" /> Duplicate
          </Button>
          <Button size="sm" variant="outline" onClick={() => run.mutate()} title="Run discovery pipeline once (dry-run)">
            <Settings2 className="h-3.5 w-3.5" /> Run
          </Button>
          <div className="ml-auto">
            <AlertDialog>
              <AlertDialogTrigger asChild>
                <Button size="sm" variant="ghost" className="text-destructive hover:bg-destructive/10">
                  <Trash2 className="h-3.5 w-3.5" /> Delete
                </Button>
              </AlertDialogTrigger>
              <AlertDialogContent>
                <AlertDialogHeader>
                  <AlertDialogTitle>Delete campaign?</AlertDialogTitle>
                  <AlertDialogDescription>
                    This permanently removes "{campaign.name}". Its leads and messages remain in the database.
                  </AlertDialogDescription>
                </AlertDialogHeader>
                <AlertDialogFooter>
                  <AlertDialogCancel>Cancel</AlertDialogCancel>
                  <AlertDialogAction className="bg-destructive text-destructive-foreground hover:bg-destructive/90" onClick={() => remove.mutate()}>
                    Delete
                  </AlertDialogAction>
                </AlertDialogFooter>
              </AlertDialogContent>
            </AlertDialog>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
