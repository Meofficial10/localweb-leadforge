"use client";
// BackendStatusBanner — shows a clear banner with a Retry button when the API is unreachable.
import * as React from "react";
import { API_BASE } from "@/app/lib/api";
import { AlertTriangle, RefreshCw } from "lucide-react";
import { Button } from "@/app/components/ui/button";

export function BackendStatusBanner() {
  const [down, setDown] = React.useState(false);
  const [loading, setLoading] = React.useState(true);

  const check = React.useCallback(async () => {
    setLoading(true);
    try {
      const res = await fetch(API_BASE + "/health", { headers: { Authorization: "Bearer " + (typeof window !== "undefined" ? (window as any).__LEADFORGE_TOKEN__ || "" : "") } });
      setDown(!res.ok);
    } catch {
      setDown(true);
    } finally {
      setLoading(false);
    }
  }, []);

  React.useEffect(() => {
    check();
    const id = window.setInterval(check, 30_000);
    return () => window.clearInterval(id);
  }, [check]);

  if (!down) return null;
  return (
    <div role="alert" className="sticky top-14 z-40 flex items-center gap-3 border-b border-destructive/40 bg-destructive/10 px-4 py-2 text-sm text-destructive">
      <AlertTriangle className="h-4 w-4 shrink-0" aria-hidden="true" />
      <div className="min-w-0 flex-1">
        <p className="font-medium">Backend not reachable at <code className="rounded bg-background/40 px-1">{API_BASE}</code></p>
        <p className="text-xs opacity-80">Start it with <code className="rounded bg-background/40 px-1">npm run dev</code> from the repo root (or open a terminal and run the backend).</p>
      </div>
      <Button size="sm" variant="outline" onClick={check} disabled={loading} className="shrink-0">
        <RefreshCw className={`h-3.5 w-3.5 mr-1${loading ? " animate-spin" : ""}`} />
        {loading ? "Checking…" : "Retry"}
      </Button>
    </div>
  );
}
