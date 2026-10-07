"use client";

import * as React from "react";
import { useQuery } from "@tanstack/react-query";
import { useSearchParams, useRouter, usePathname } from "next/navigation";
import { Menu } from "lucide-react";
import { campaignsApi, systemApi } from "@/app/lib/api";
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from "@/app/components/ui/select";
import { GlobalSearch } from "@/app/components/global-search";
import { ThemeToggle } from "@/app/components/theme-toggle";
import { KillSwitch } from "@/app/components/kill-switch";
import { ModeBadge } from "@/app/components/mode-badge";
import { Button } from "@/app/components/ui/button";

export function TopBar({ onOpenSidebar }: { onOpenSidebar?: () => void }) {
  const { data: campaigns } = useQuery({ queryKey: ["campaigns"], queryFn: campaignsApi.list });
  const { data: status } = useQuery({ queryKey: ["system-status"], queryFn: systemApi.status });
  const paused = status?.paused ?? false;

  const searchParams = useSearchParams();
  const router = useRouter();
  const pathname = usePathname();
  const campaignId = searchParams.get("campaign") || "";

  const onCampaignChange = (v: string) => {
    const p = new URLSearchParams(searchParams.toString());
    if (v) p.set("campaign", v);
    else p.delete("campaign");
    router.push(pathname + "?" + p.toString());
  };

  return (
    <header className="sticky top-0 z-30 flex h-14 items-center gap-3 border-b bg-card/95 px-4 backdrop-blur">
      <Button variant="ghost" size="icon" className="md:hidden" onClick={onOpenSidebar} aria-label="Open menu">
        <Menu className="h-5 w-5" />
      </Button>
      <div className="w-44 flex-none">
        <Select value={campaignId} onValueChange={onCampaignChange}>
          <SelectTrigger aria-label="Campaign switcher">
            <SelectValue placeholder="All campaigns" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="">All campaigns</SelectItem>
            {(campaigns ?? []).map((c) => (
              <SelectItem key={c.id} value={c.id}>
                {c.name}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>
      <GlobalSearch />
      <div className="ml-auto flex items-center gap-2">
        <ModeBadge campaignId={campaignId || null} />
        <KillSwitch enabled={paused} />
        <ThemeToggle />
      </div>
    </header>
  );
}
