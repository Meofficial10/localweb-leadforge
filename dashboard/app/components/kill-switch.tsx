"use client";

import * as React from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { Power } from "lucide-react";
import { toast } from "sonner";
import { complianceApi } from "@/app/lib/api";
import { Button } from "@/app/components/ui/button";
import {
  AlertDialog, AlertDialogContent, AlertDialogDescription, AlertDialogFooter,
  AlertDialogHeader, AlertDialogTitle, AlertDialogTrigger, AlertDialogAction, AlertDialogCancel,
} from "@/app/components/ui/alert-dialog";
import { asError } from "@/app/lib/utils";

export function KillSwitch({ enabled, onToggle }: { enabled: boolean; onToggle?: () => void }) {
  const qc = useQueryClient();
  const mutation = useMutation({
    mutationFn: (paused: boolean) => complianceApi.setPause(paused),
    onSuccess: () => {
      toast.success(enabled ? "Kill switch ENGAGED — all outbound paused" : "Kill switch released");
      qc.invalidateQueries({ queryKey: ["system-status"] });
      onToggle?.();
    },
    onError: (e) => toast.error(asError(e)),
  });

  return (
    <AlertDialog>
      <AlertDialogTrigger asChild>
        <Button
          variant={enabled ? "destructive" : "outline"}
          size="sm"
          className="border-destructive/50 text-destructive hover:bg-destructive hover:text-destructive-foreground"
        >
          <Power className="h-4 w-4" />
          {enabled ? "Resume" : "Kill switch"}
        </Button>
      </AlertDialogTrigger>
      <AlertDialogContent>
        <AlertDialogHeader>
          <AlertDialogTitle>{enabled ? "Release kill switch?" : "Engage kill switch?"}</AlertDialogTitle>
          <AlertDialogDescription>
            {enabled
              ? "This will allow outbound emails and calls to resume (subject to dry-run/live settings)."
              : "This immediately pauses ALL outbound emails and calls system-wide. Every channel is halted until you release it."}
          </AlertDialogDescription>
        </AlertDialogHeader>
        <AlertDialogFooter>
          <AlertDialogCancel>Cancel</AlertDialogCancel>
          <AlertDialogAction
            className={enabled ? "" : "bg-destructive text-destructive-foreground hover:bg-destructive/90"}
            onClick={() => mutation.mutate(!enabled)}
          >
            {enabled ? "Resume sending" : "Engage kill switch"}
          </AlertDialogAction>
        </AlertDialogFooter>
      </AlertDialogContent>
    </AlertDialog>
  );
}
