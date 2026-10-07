"use client";

import * as React from "react";
import { useQueryClient } from "@tanstack/react-query";
import { Loader2, CheckCircle2, XCircle, Settings2, Zap } from "lucide-react";
import { toast } from "sonner";
import { Button } from "@/app/components/ui/button";
import { Card, CardContent } from "@/app/components/ui/card";
import { Switch } from "@/app/components/ui/switch";
import { integrationsApi, type IntegrationCard as CardT, type IntegrationStatus } from "@/app/lib/api";
import { asError } from "@/app/lib/utils";
import { KindIcon } from "./kind-icons";
import { StatusPill } from "./status-pill";

export function IntegrationCardView({ card, onConfigure }: { card: CardT; onConfigure: (c: CardT) => void }) {
  const qc = useQueryClient();
  const [testing, setTesting] = React.useState(false);
  const [toggling, setToggling] = React.useState(false);
  const [testOutcome, setTestOutcome] = React.useState<IntegrationStatus | null>(null);
  const enabled = card.config?.enabled !== false;

  const runTest = async () => {
    setTesting(true);
    setTestOutcome(null);
    try {
      const res = await integrationsApiTest(card.id);
      setTestOutcome({
        state: res.ok ? "connected" : "error",
        label: res.ok ? "Connected" : "Error",
        color: res.ok ? "green" : "red",
        icon: res.ok ? "check" : "x",
        detail: res.detail || res.message,
        last_checked: res.at,
      });
      (res.ok ? toast.success : toast.error)(res.message || (res.ok ? "Connection OK" : "Connection failed"));
    } catch (e) {
      setTestOutcome({ state: "error", label: "Error", color: "red", icon: "x", detail: asError(e), last_checked: null });
      toast.error(asError(e));
    } finally {
      setTesting(false);
    }
  };

  const toggle = async (checked: boolean) => {
    setToggling(true);
    try {
      await integrationsApi.configureIntegration(card.id, { enabled: checked });
      qc.invalidateQueries?.({ queryKey: ["integrations"] });
      qc.invalidateQueries?.({ queryKey: ["health"] });
    } catch (e) {
      toast.error(asError(e));
    } finally {
      setToggling(false);
    }
  };

  return (
    <Card data-testid={"integration-" + card.id} className={"h-full transition-shadow hover:shadow-md " + (card.status.state === "connected" ? " ring-1 ring-green-500/30" : card.status.state === "error" ? " ring-1 ring-red-500/30" : "")}>
      <CardContent className="space-y-3 p-5">
        <div className="flex items-start justify-between gap-2">
          <div className="flex items-center gap-2.5">
            <span className="flex h-9 w-9 items-center justify-center rounded-lg bg-accent text-accent-foreground" aria-hidden="true">
              <KindIcon kind={card.kind} />
            </span>
            <div>
              <h3 className="text-sm font-semibold leading-tight">{card.name}</h3>
              {card.required ? <p className="text-[11px] uppercase tracking-wide text-muted-foreground">required</p> : <p className="text-[11px] text-muted-foreground">{card.kind}</p>}
            </div>
          </div>
          <label className="flex items-center gap-2" title={enabled ? "Integration enabled" : "Integration disabled"}>
            <Switch checked={enabled} onCheckedChange={toggle} disabled={toggling} aria-label={"Toggle " + card.name} />
          </label>
        </div>

        <p className="text-sm text-muted-foreground line-clamp-2">{card.description}</p>

        <div className="flex flex-wrap items-center gap-2">
          <StatusPill status={testOutcome || card.status} />
        </div>
        {card.status.detail ? <p className="text-xs text-muted-foreground">{card.status.detail}</p> : null}
        {testOutcome?.detail ? <p className="text-xs text-muted-foreground">{testOutcome.detail}</p> : null}

        {card.status.last_checked ? (
          <p className="text-[11px] text-muted-foreground">Last checked: {new Date(card.status.last_checked).toLocaleString()}</p>
        ) : null}

        <div className="flex gap-2 pt-1">
          <Button size="sm" variant="outline" onClick={runTest} disabled={testing}>
            {testing ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Zap className="h-3.5 w-3.5" />}
            Test connection
          </Button>
          <Button size="sm" onClick={() => onConfigure(card)}>
            <Settings2 className="h-3.5 w-3.5" /> Configure
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}

// small indirection so the component has a local, consistent name
async function integrationsApiTest(id: string) {
  return integrationsApi.test(id);
}
