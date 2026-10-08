"use client";

import * as React from "react";
import { useQueryClient } from "@tanstack/react-query";
import { Loader2, PlugZap, Info } from "lucide-react";
import { toast } from "sonner";
import {
  Sheet, SheetContent, SheetHeader, SheetTitle, SheetDescription,
} from "@/app/components/ui/sheet";
import { Button } from "@/app/components/ui/button";
import { Input } from "@/app/components/ui/input";
import { Label } from "@/app/components/ui/label";
import { Textarea } from "@/app/components/ui/textarea";
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from "@/app/components/ui/select";
import { Badge } from "@/app/components/ui/badge";
import { integrationsApi, type IntegrationCard, type ProviderDef } from "@/app/lib/api";
import { asError } from "@/app/lib/utils";
import { KindIcon } from "./kind-icons";
import { StatusPill } from "./status-pill";

export function ConfigureDrawer({ card, open, onOpenChange }: {
  card: IntegrationCard | null; open: boolean; onOpenChange: (o: boolean) => void;
}) {
  const qc = useQueryClient();
  const [providerId, setProviderId] = React.useState<string>("");
  const [baseUrl, setBaseUrl] = React.useState<string>("");
  const [apiKey, setApiKey] = React.useState<string>("");
  const [fieldVals, setFieldVals] = React.useState<Record<string, string>>({});
  const [models, setModels] = React.useState<string[]>([]);
  const [fetchingModels, setFetchingModels] = React.useState(false);
  const [saving, setSaving] = React.useState(false);
  const [testing, setTesting] = React.useState(false);
  const [testResult, setTestResult] = React.useState<{ ok: boolean; message: string; detail?: string; fix_hint?: string; at?: string } | null>(null);

  React.useEffect(() => {
    if (!open || !card) return;
    const cfg = card.config || {};
    setProviderId(String(cfg.provider || card.provider || ""));
    setBaseUrl(String(cfg.base_url || ""));
    setApiKey("");
    setFieldVals(Object.fromEntries(card.fields.map((f) => [
      f.key,
      String((cfg[f.key] !== undefined && cfg[f.key] !== null) ? cfg[f.key] : (f.default ?? "")),
    ])));
    setModels([]);
    setTestResult(null);
  }, [open, card]);

  if (!card) return null;

  const provider: ProviderDef | undefined = card.providers.find((p) => p.id === providerId) || card.providers[0];
  const isLlm = card.id === "llm";
  const needsKey = provider?.needs_key ?? false;

  const fetchModels = async () => {
    if (!provider) return;
    setFetchingModels(true);
    try {
      const res = await integrationsApi.models(provider.id, baseUrl || provider.base_url_default);
      setModels(res.models || []);
      if (!res.models || !res.models.length) toast.info("Could not fetch models — type a custom model name.");
    } catch (e) {
      toast.error(asError(e));
    } finally {
      setFetchingModels(false);
    }
  };

  const collectValues = (): Record<string, unknown> => {
    const v: Record<string, unknown> = {};
    if (provider) v.provider = provider.id;
    if (provider?.base_url_editable) v.base_url = baseUrl.trim();
    if (needsKey) v.api_key = apiKey.trim();
    Object.entries(fieldVals).forEach(([k, val]) => {
      if (val !== "" && val !== undefined) v[k] = (!isNaN(Number(val)) && val.trim() !== "") ? Number(val) : val;
    });
    return v;
  };

  const testConnection = async () => {
    if (!card) return;
    setTesting(true);
    setTestResult(null);
    try {
      const res = await integrationsApi.test(card.id, collectValues());
      setTestResult({
        ok: res.ok,
        message: res.message || (res.ok ? "Connection OK" : "Connection failed"),
        detail: res.detail,
        fix_hint: (res as any).fix_hint,
        at: res.at,
      });
      (res.ok ? toast.success : toast.error)(res.message || (res.ok ? "Connection OK" : "Connection failed"));
      qc.invalidateQueries({ queryKey: ["integrations"] });
    } catch (e) {
      setTestResult({ ok: false, message: asError(e) });
      toast.error(asError(e));
    } finally {
      setTesting(false);
    }
  };

  const save = async () => {
    if (!card || !provider) return;
    setSaving(true);
    const values: Record<string, unknown> = { provider: provider.id };
    if (provider.base_url_editable && baseUrl.trim()) values.base_url = baseUrl.trim();
    if (needsKey && apiKey.trim()) values.api_key = apiKey.trim();
    Object.entries(fieldVals).forEach(([k, v]) => {
      if (v !== "" && v !== undefined) values[k] = (!isNaN(Number(v)) && v.trim() !== "") ? Number(v) : v;
    });
    try {
      const res = await integrationsApi.configureIntegration(card.id, values);
      (res.test.ok ? toast.success : toast.error)(res.test.message || "Saved", { description: res.test.detail });
      qc.invalidateQueries({ queryKey: ["integrations"] });
      if (res.test.ok) onOpenChange(false);
    } catch (e) {
      toast.error(asError(e));
    } finally {
      setSaving(false);
    }
  };

  const onProviderChange = (pid: string) => {
    setProviderId(pid);
    const prov = card!.providers.find((p) => p.id === pid);
    setBaseUrl(prov?.base_url_editable ? (prov.base_url_default || "") : "");
    setModels([]);
  };

  const modelVal = fieldVals["model"] || "";

  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetContent side="right" className="overflow-y-auto">
        <SheetHeader>
          <div className="flex items-center gap-2">
            <span className="flex h-9 w-9 items-center justify-center rounded-md bg-accent text-accent-foreground">
              <KindIcon kind={card.kind} />
            </span>
            <SheetTitle>Configure {card.name}</SheetTitle>
          </div>
          <SheetDescription>{card.description}</SheetDescription>
        </SheetHeader>

        <div className="mt-6 space-y-5">
          <div className="flex items-center justify-between rounded-lg border bg-muted/40 px-3 py-2">
            <StatusPill status={card.status} />
            <span className="text-xs text-muted-foreground">Last checked: {card.status.last_checked ? new Date(card.status.last_checked).toLocaleString() : "never"}</span>
          </div>

          {card.providers.length > 1 && (
            <div className="space-y-1.5">
              <Label htmlFor="provider">Provider</Label>
              <Select value={providerId} onValueChange={onProviderChange}>
                <SelectTrigger id="provider" className="w-full"><SelectValue placeholder="Select provider" /></SelectTrigger>
                <SelectContent>
                  {card.providers.map((p) => (
                    <SelectItem key={p.id} value={p.id}>{p.label}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
              {provider?.note ? <p className="text-xs text-muted-foreground">{provider.note}</p> : null}
            </div>
          )}

          {provider?.base_url_editable && (
            <div className="space-y-1.5">
              <Label htmlFor="base-url">Base URL</Label>
              <Input id="base-url" value={baseUrl} onChange={(e) => setBaseUrl(e.target.value)} placeholder={provider.base_url_default || "https://..."} />
              {provider.probe_url ? <p className="text-xs text-muted-foreground">Probe: GET {provider.base_url_default}{provider.probe_url}</p> : null}
            </div>
          )}

          {needsKey && (
            <div className="space-y-1.5">
              <Label htmlFor="api-key">{card.secret?.is_set ? "API key (replace — leave blank to keep)" : "API key"}</Label>
              <Input id="api-key" type="password" autoComplete="new-password" value={apiKey} onChange={(e) => setApiKey(e.target.value)} placeholder={card.secret?.is_set ? "••••••••" : "Paste key — encrypted at rest"} />
              {card.secret?.is_set ? (
                <p className="text-xs text-muted-foreground"><Badge variant="secondary" className="mr-1">set</Badge>last 4: …{card.secret.masked}</p>
              ) : null}
            </div>
          )}

          {isLlm && (
            <div className="space-y-1.5">
              <Label htmlFor="model">Model</Label>
              <div className="flex gap-2">
                <Select value={modelVal || "__custom__"} onValueChange={(v) => setFieldVals((f) => ({ ...f, model: v === "__custom__" ? "" : v }))}>
                  <SelectTrigger id="model" className="w-full"><SelectValue placeholder="Select or type a model" /></SelectTrigger>
                  <SelectContent>
                    {models.map((m) => (<SelectItem key={m} value={m}>{m}</SelectItem>))}
                    <SelectItem value="__custom__">✎ Type a custom model name…</SelectItem>
                  </SelectContent>
                </Select>
                <Button variant="outline" size="icon" type="button" onClick={fetchModels} disabled={fetchingModels} title="Fetch model list from provider">
                  {fetchingModels ? <Loader2 className="h-4 w-4 animate-spin" /> : <PlugZap className="h-4 w-4" />}
                </Button>
              </div>
              <p className="text-xs text-muted-foreground">{models.length ? String(models.length) + " models available — pick one or type a custom name." : "Click the plug to fetch the provider's model list."}</p>
            </div>
          )}
          {isLlm && (provider?.id === "custom" || modelVal !== "") && (
            <div className="space-y-1.5">
              <Label htmlFor="custom-model">Model name</Label>
              <Input id="custom-model" value={modelVal} onChange={(e) => setFieldVals((f) => ({ ...f, model: e.target.value }))} placeholder="e.g. qwen2.5:7b" />
            </div>
          )}

          {card.fields.map((f) => {
            if (isLlm && f.key === "model") return null;
            if (isLlm && f.key === "headers" && provider?.id !== "custom") return null;
            if (f.type === "provider") {
              return (
                <div className="space-y-1.5" key={f.key}>
                  <Label htmlFor={f.key}>{f.label}</Label>
                  <Select value={fieldVals[f.key] || "__none__"} onValueChange={(v) => setFieldVals((x) => ({ ...x, [f.key]: v === "__none__" ? "" : v }))}>
                    <SelectTrigger id={f.key}><SelectValue placeholder="None" /></SelectTrigger>
                    <SelectContent>
                      <SelectItem value="__none__">(none)</SelectItem>
                      {card.providers.map((p) => (<SelectItem key={p.id} value={p.id}>{p.label}</SelectItem>))}
                    </SelectContent>
                  </Select>
                  {f.help ? <p className="text-xs text-muted-foreground">{f.help}</p> : null}
                </div>
              );
            }
            if (f.type === "textarea") {
              return (
                <div className="space-y-1.5" key={f.key}>
                  <Label htmlFor={f.key}>{f.label}</Label>
                  <Textarea id={f.key} rows={2} value={fieldVals[f.key] || ""} onChange={(e) => setFieldVals((x) => ({ ...x, [f.key]: e.target.value }))} placeholder={f.placeholder} />
                  {f.help ? <p className="text-xs text-muted-foreground">{f.help}</p> : null}
                </div>
              );
            }
            return (
              <div className="space-y-1.5" key={f.key}>
                <Label htmlFor={f.key}>{f.label}</Label>
                <Input id={f.key} type={f.type === "number" ? "number" : f.type === "email" ? "email" : "text"} step={f.type === "number" ? "any" : undefined} value={fieldVals[f.key] || ""} onChange={(e) => setFieldVals((x) => ({ ...x, [f.key]: e.target.value }))} placeholder={f.placeholder} />
                {f.help ? <p className="text-xs text-muted-foreground">{f.help}</p> : null}
              </div>
            );
          })}

          {testing && (
            <div role="status" aria-live="polite" className="flex items-center gap-2 rounded-md border bg-muted/40 px-3 py-2 text-sm">
              <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" />
              Testing connection…
            </div>
          )}
          {testResult && !testing && (
            <div role="status" aria-live="polite" className={"rounded-md border px-3 py-2 text-sm " + (testResult.ok ? "border-green-500/30 bg-green-500/5" : "border-red-500/30 bg-red-500/5")}>
              <p className={"font-medium " + (testResult.ok ? "text-green-700 dark:text-green-400" : "text-red-700 dark:text-red-400")}>
                {testResult.ok ? "✓ Connected" : "✕ Failed"}
                <span className="ml-2 font-normal text-foreground/80">{testResult.message}</span>
              </p>
              {testResult.detail ? <p className="mt-1 text-xs text-foreground/70">{testResult.detail}</p> : null}
              {testResult.fix_hint ? <p className="mt-1 text-xs font-medium text-amber-600">How to fix: {testResult.fix_hint}</p> : null}
              {testResult.at ? <p className="mt-1 text-[11px] text-foreground/50">Test at {new Date(testResult.at).toLocaleString()}</p> : null}
            </div>
          )}

          <div className="flex flex-col gap-2 pt-2">
            <Button onClick={save} disabled={saving}>
              {saving ? <Loader2 className="h-4 w-4 animate-spin" /> : <PlugZap className="h-4 w-4" />}
              Save & test connection
            </Button>
            <Button variant="outline" onClick={testConnection} disabled={testing}>
              {testing ? <Loader2 className="h-4 w-4 animate-spin" /> : null}
              Test connection
            </Button>
            <p className="flex items-start gap-1.5 text-xs text-muted-foreground">
              <Info className="mt-0.5 h-3.5 w-3.5 shrink-0" aria-hidden="true" />
              Secrets are encrypted at rest and never shown again. Dry-run mode is always on — no live sends here.
            </p>
          </div>
        </div>
      </SheetContent>
    </Sheet>
  );
}
