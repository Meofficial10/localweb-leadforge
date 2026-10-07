"use client";

import * as React from "react";
import { useQuery } from "@tanstack/react-query";
import { Search } from "lucide-react";
import { campaignsApi, leadsApi } from "@/app/lib/api";
import { Button } from "@/app/components/ui/button";
import {
  Dialog, DialogContent, DialogTrigger,
} from "@/app/components/ui/dialog";
import { Input } from "@/app/components/ui/input";

export function GlobalSearch() {
  const [open, setOpen] = React.useState(false);
  const [q, setQ] = React.useState("");
  const camp = useQuery({ queryKey: ["campaigns"], queryFn: campaignsApi.list, enabled: open });
  const leads = useQuery({
    queryKey: ["leads", "search", q],
    queryFn: () => leadsApi.list({ search: q || "", limit: "20" }),
    enabled: open,
  });

  React.useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "k") {
        e.preventDefault();
        setOpen((v) => !v);
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []);

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        <Button variant="outline" size="sm" className="w-56 justify-start text-muted-foreground">
          <Search className="h-4 w-4" />
          <span>Search…</span>
          <kbd className="ml-auto rounded bg-muted px-1.5 text-[10px]">Ctrl K</kbd>
        </Button>
      </DialogTrigger>
      <DialogContent className="max-w-md">
        <Input
          autoFocus
          placeholder="Search leads or campaigns…"
          value={q}
          onChange={(e) => setQ(e.target.value)}
          aria-label="Search"
        />
        <div className="max-h-72 space-y-2 overflow-auto pt-2">
          <p className="text-xs font-semibold text-muted-foreground">Campaigns</p>
          {(camp.data ?? []).slice(0, 5).map((c) => (
            <a
              key={c.id}
              href={"/campaigns?focus=" + c.id}
              className="block rounded-md px-2 py-1.5 text-sm hover:bg-accent"
            >
              {c.name} <span className="text-muted-foreground">({c.city})</span>
            </a>
          ))}
          <p className="text-xs font-semibold text-muted-foreground">Leads</p>
          {(leads.data ? (leads.data as any).items ?? (leads.data as any) : []).slice(0, 8).map((l: any) => (
            <a
              key={l.id}
              href={"/leads?focus=" + l.id}
              className="flex items-center justify-between rounded-md px-2 py-1.5 text-sm hover:bg-accent"
            >
              <span>{l.name}</span>
              <span className="text-xs text-muted-foreground">{l.status}</span>
            </a>
          ))}
          {!leads.data && <p className="text-sm text-muted-foreground">No matches</p>}
        </div>
      </DialogContent>
    </Dialog>
  );
}
