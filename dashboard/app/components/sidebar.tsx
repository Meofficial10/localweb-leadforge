"use client";

import * as React from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  LayoutDashboard, Megaphone, Users, Send, Inbox, Phone, ShieldCheck, Plug, Settings,
} from "lucide-react";
import { cn } from "@/app/lib/utils";

const items = [
  { href: "/", label: "Overview", icon: LayoutDashboard },
  { href: "/campaigns", label: "Campaigns", icon: Megaphone },
  { href: "/leads", label: "Leads", icon: Users },
  { href: "/outreach", label: "Outreach Queue", icon: Send },
  { href: "/inbox", label: "Inbox", icon: Inbox },
  { href: "/calls", label: "Calls", icon: Phone },
  { href: "/compliance", label: "Compliance", icon: ShieldCheck },
  { href: "/integrations", label: "Integrations", icon: Plug },
  { href: "/settings", label: "Settings", icon: Settings },
];

export function SideNav() {
  const pathname = usePathname();
  return (
    <nav aria-label="Main navigation" className="space-y-1 p-3">
      {items.map((it) => {
        const Icon = it.icon;
        const active = pathname === it.href || (it.href !== "/" && pathname.startsWith(it.href));
        return (
          <Link
            key={it.href}
            href={it.href}
            aria-current={active ? "page" : undefined}
            className={cn(
              "flex items-center gap-3 rounded-md px-3 py-2 text-sm font-medium transition-colors",
              active
                ? "bg-accent text-accent-foreground"
                : "text-muted-foreground hover:bg-accent/60 hover:text-foreground"
            )}
          >
            <Icon className="h-4 w-4" aria-hidden="true" />
            <span>
              {it.label} <span className="sr-only">section</span>
            </span>
          </Link>
        );
      })}
    </nav>
  );
}
