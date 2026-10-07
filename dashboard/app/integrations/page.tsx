"use client";

export const dynamic = "force-dynamic";

import * as React from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { MapPin, Server, Globe, Mail, Phone, ShieldCheck, KeyRound, CheckCircle2, XCircle, Loader2, Trash2 } from "lucide-react";
import { integrationsApi, type IntegrationCard, type SecretMeta } from "@/app/lib/api";
import { PageHeader } from "@/app/components/shared/page-header";
import { Skeleton } from "@/app/components/ui/skeleton";
import { Button } from "@/app/components/ui/button";
import { Input } from "@/app/components/ui/input";
import { Label } from "@/app/components/ui/label";
import { Card, CardContent, CardHeader, CardTitle } from "@/app/components/ui/card";
import { Badge } from "@/app/components/ui/badge";
import {
  Dialog, DialogContent, DialogHeader, DialogTitle,
} from "@/app/components/ui/dialog";
import {
  AlertDialog, AlertDialogContent, AlertDialogDescription, AlertDialogFooter,
  AlertDialogHeader, AlertDialogTitle, AlertDialogTrigger, AlertDialogCancel, AlertDialogAction,
} from "@/app/components/ui/alert-dialog";
import { toast } from "sonner";
import { asError } from "@/app/lib/utils";

function cardIconsFor(kind: string) {
  if (kind === "source") return <MapPin className="h-4 w-4" />;
  if (kind === "hosting") return <Globe className="h-4 w-4" />;
  if (kind === "ai") return <Server className="h-4 w-4" />;
  if (kind === "email") return <Mail className="h-4 w-4" />;
  if (kind === "voice") return <Phone className="h-4 w-4" />;
  return <ShieldCheck className="h-4 w-4" />;
}

function secretKeyFor(cardId: string): string {
  const map: Record<string, string> = {
    places: "places.api_key",
    llm: "llm.ollama.base_url",
    hosting: "hosting.netlify.api_key",
    email: "email.smtp.password",
    voice: "voice.vapi.api_key",
    dnc: "dnc.registry.api_key",
  };
  return map[cardId] || "";
}

function IntegrationCardView({ card, onSetKey, onTest }: { card: IntegrationCard; onSetKey: (key: string, name: string) => void; onTest: (id: string) => void }) {
  return (
    <Card className={card.configured ? "border-success/40" : undefined}>
      <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
        <div className="flex items-center gap-2">
          <span className="flex h-8 w-8 items-center justify-center rounded-md bg-accent text-accent-foreground">{cardIconsFor(card.kind)}</span>
          <CardTitle className="text-sm">{card.name}</CardTitle>
        </div>
        <Badge variant={card.configured ? "success" : "secondary"}>{card.configured ? "configured" : "not configured"}</Badge>
      </CardHeader>
      <CardContent className="space-y-3 text-sm text-muted-foreground">
        {card.detail ? <p>{card.detail}</p> : null}
        <div className="flex flex-wrap gap-1.5">
          <Button size="sm" variant="outline" onClick={() => onTest(card.id)}>
            Test connection
          </Button>
          <Button size="sm" variant="outline" onClick={() => onSetKey(secretKeyFor(card.id), card.name)}>
            <KeyRound className="h-3.5 w-3.5" /> Set key
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}

function SecretManageDialog({ secret, onDone }: { secret: SecretMeta | null; onDone: () => void }) {
  const [value, setValue] = React.useState("");
  const qc = useQueryClient();
  const invalidate = () => qc.invalidateQueries({ queryKey: ["integrations"] });
  const set = useMutation({
    mutationFn: () => integrationsApi.setSecret(secret!.key, value),
    onSuccess: () => { toast.success("Secret saved — encrypted at rest"); setValue(""); invalidate(); onDone(); },
    onError: (e) => toast.error(asError(e)),
  });
  const clear = useMutation({
    mutationFn: () => integrationsApi.clearSecret(secret!.key),
    onSuccess: () => { toast.success("Secret cleared"); invalidate(); onDone(); },
    onError: (e) => toast.error(asError(e)),
  });
  if (!secret) return null;
  return (
    <DialogContent>
      <DialogHeader>
        <DialogTitle>Manage secret</DialogTitle>
      </DialogHeader>
      <div className="space-y-4">
        <p className="break-all font-mono text-xs text-muted-foreground">{secret.key}</p>
        <div className="flex items-center gap-2 text-sm">
          <Badge variant={secret.is_set ? "success" : "secondary"}>{secret.is_set ? "set" : "not set"}</Badge>
          {secret.is_set && secret.masked ? <span className="font-mono text-xs">…{secret.masked}</span> : null}
        </div>
        <form className="space-y-1.5" onSubmit={(e) => { e.preventDefault(); set.mutate(); }}>
          <Label htmlFor="secret-value">New value</Label>
          <Input id="secret-value" type="password" value={value} onChange={(e) => setValue(e.target.value)} placeholder="(leave empty to keep current)" />
          <Button type="submit" className="w-full" disabled={set.isPending || !value}>
            {set.isPending && <Loader2 className="h-4 w-4 animate-spin" />} Save secret
          </Button>
        </form>
        {secret.is_set && (
          <AlertDialog>
            <AlertDialogTrigger asChild>
              <Button variant="ghost" size="sm" className="w-full text-destructive"><Trash2 className="h-3.5 w-3.5" /> Clear secret</Button>
            </AlertDialogTrigger>
            <AlertDialogContent>
              <AlertDialogHeader>
                <AlertDialogTitle>Clear this secret?</AlertDialogTitle>
                <AlertDialogDescription>The encrypted value is removed and the integration will stop using it.</AlertDialogDescription>
              </AlertDialogHeader>
              <AlertDialogFooter>
                <AlertDialogCancel>Cancel</AlertDialogCancel>
                <AlertDialogAction className="bg-destructive text-destructive-foreground hover:bg-destructive/90" onClick={() => clear.mutate()}>Clear</AlertDialogAction>
              </AlertDialogFooter>
            </AlertDialogContent>
          </AlertDialog>
        )}
      </div>
    </DialogContent>
  );
}

export default function IntegrationsPage() {
  const { data, isLoading, isError } = useQuery({ queryKey: ["integrations"], queryFn: integrationsApi.list });
  const [secret, setSecret] = React.useState<SecretMeta | null>(null);
  const [testResults, setTestResults] = React.useState<Record<string, { ok: boolean; message: string } | undefined>>({});

  const onTest = (id: string) => {
    setTestResults((r) => ({ ...r, [id]: undefined }));
    integrationsApi.test(id)
      .then((res) => { setTestResults((r) => ({ ...r, [id]: res })); (res.ok ? toast.success : toast.error)(res.message || (res.ok ? "Connection OK" : "Connection failed")); })
      .catch((e) => setTestResults((r) => ({ ...r, [id]: { ok: false, message: asError(e) } })));
  };

  return (
    <div>
      <PageHeader
        title="Integrations"
        description="Connect lead sources, the LLM writer, demo hosting, email, voice and DNC providers. All secrets are encrypted at rest."
      />
      {isLoading ? (
        <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">{[1, 2, 3, 4, 5, 6].map((i) => <Skeleton key={i} className="h-40" />)}</div>
      ) : isError ? (
        <p className="text-sm text-destructive">Couldn&apos;t load integrations.</p>
      ) : (
        <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
          {(data!.cards as IntegrationCard[]).map((card) => (
            <div key={card.id}>
              <IntegrationCardView card={card} onSetKey={(key) => setSecret({ key, is_set: false, masked: "" })} onTest={onTest} />
              {testResults[card.id] && (
                <div className={"mt-2 flex items-center gap-2 rounded-md border px-3 py-2 text-xs " + (testResults[card.id]!.ok ? "border-success/50 text-success" : "border-destructive/50 text-destructive")}>
                  {testResults[card.id]!.ok ? <CheckCircle2 className="h-3.5 w-3.5" /> : <XCircle className="h-3.5 w-3.5" />}
                  {testResults[card.id]!.message || (testResults[card.id]!.ok ? "Connection OK" : "Connection failed")}
                </div>
              )}
            </div>
          ))}
        </div>
      )}

      <Card className="mt-6">
        <CardHeader>
          <CardTitle className="text-base">Stored secrets</CardTitle>
          <p className="text-sm text-muted-foreground">Manage credentials used by the integrations above. Values are encrypted with the backend secret key and never shown.</p>
        </CardHeader>
        <CardContent>
          <ul className="grid gap-2 sm:grid-cols-2">
            {(data?.secrets || []).map((s) => (
              <li key={s.key}>
                <button
                  className="flex w-full items-center justify-between gap-2 rounded-md border px-3 py-2 text-left text-sm hover:bg-accent"
                  onClick={() => setSecret(s)}
                >
                  <span className="flex items-center gap-2 truncate">
                    <KeyRound className="h-3.5 w-3.5 shrink-0 text-muted-foreground" aria-hidden="true" />
                    <span className="truncate font-mono text-xs">{s.key}</span>
                  </span>
                  <Badge variant={s.is_set ? "success" : "secondary"}>{s.is_set ? "set" : "empty"}</Badge>
                </button>
              </li>
            ))}
          </ul>
        </CardContent>
      </Card>

      <Dialog open={!!secret} onOpenChange={(o) => !o && setSecret(null)}>
        <SecretManageDialog secret={secret} onDone={() => setSecret(null)} />
      </Dialog>
    </div>
  );
}
