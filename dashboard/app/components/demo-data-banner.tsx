"use client";

import * as React from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { AlertTriangle, Eraser, Loader2, X } from "lucide-react";
import { systemApi } from "@/app/lib/api";
import { Button } from "@/app/components/ui/button";
import { asError } from "@/app/lib/utils";
import {
  AlertDialog, AlertDialogAction, AlertDialogCancel, AlertDialogContent, AlertDialogDescription,
  AlertDialogFooter, AlertDialogHeader, AlertDialogTitle, AlertDialogTrigger,
} from "@/app/components/ui/alert-dialog";
import { toast } from "sonner";

/** Banner shown while demo data is present. */
export function DemoDataBanner({ compact = false }: { compact?: boolean }) {
  const qc = useQueryClient();
  const { data } = useQuery({ queryKey: ["demo-data"], queryFn: systemApi.demoData, staleTime: 15_000 });
  const clear = useMutation({
    mutationFn: () => systemApi.clearDemoData(),
    onSuccess: () => {
      toast.success("Demo data cleared");
      qc.invalidateQueries();
      qc.setQueryData(["demo-data"], { present: false, campaigns: 0, leads: 0, drafts: 0, calls: 0, integrations: 0, message: "No demo data." });
    },
    onError: (e) => toast.error(asError(e)),
  });
  const [hidden, setHidden] = React.useState(false);
  if (!data?.present || hidden) return null;
  return (
    <div role="alert" aria-label="Demo data present" className={"mb-5 flex flex-col gap-3 rounded-xl border-2 border-destructive/50 bg-destructive/10 p-4 " + (compact ? "lg:flex-row lg:items-center" : "")}>
      <div className="flex items-start gap-3">
        <AlertTriangle className="mt-0.5 h-5 w-5 shrink-0 text-destructive" aria-hidden="true" />
        <div className="text-sm">
          <p className="font-semibold text-foreground">Demo data is present</p>
          <p className="text-muted-foreground">
            Seeded campaign ({String(data.campaigns)}), leads ({String(data.leads)}), drafts ({String(data.drafts)}) and calls ({String(data.calls)}).
            This is only for trying things out — nothing here is real.
          </p>
          <button type="button" onClick={() => setHidden(true)} className="mt-1 inline-flex items-center gap-1 text-xs text-muted-foreground underline hover:text-foreground" aria-label="Dismiss demo data banner">
            <X className="h-3 w-3" aria-hidden="true" /> Dismiss
          </button>
        </div>
      </div>
      <div className="lg:ml-auto">
        <AlertDialog>
          <AlertDialogTrigger asChild>
            <Button type="button" variant="destructive" size="sm" disabled={clear.isPending}>
              {clear.isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : <Eraser className="h-4 w-4" />}
              Clear demo data
            </Button>
          </AlertDialogTrigger>
          <AlertDialogContent>
            <AlertDialogHeader>
              <AlertDialogTitle>Remove all demo data?</AlertDialogTitle>
              <AlertDialogDescription>
                Deletes the seeded campaign, its leads, drafts and calls. Real (non-demo) records are kept. This cannot be undone.
              </AlertDialogDescription>
            </AlertDialogHeader>
            <AlertDialogFooter>
              <AlertDialogCancel>Cancel</AlertDialogCancel>
              <AlertDialogAction onClick={() => clear.mutate()} className="bg-destructive text-destructive-foreground hover:bg-destructive/90">Clear demo data</AlertDialogAction>
            </AlertDialogFooter>
          </AlertDialogContent>
        </AlertDialog>
      </div>
    </div>
  );
}