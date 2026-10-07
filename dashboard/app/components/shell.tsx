"use client";

import * as React from "react";
import { Suspense } from "react";
import { SideNav } from "@/app/components/sidebar";
import { TopBar } from "@/app/components/topbar";
import { Sheet, SheetContent } from "@/app/components/ui/sheet";

export function Shell({ children }: { children: React.ReactNode }) {
  const [mobileOpen, setMobileOpen] = React.useState(false);
  return (
    <div className="flex min-h-screen w-full">
      <aside className="hidden w-60 shrink-0 border-r bg-card md:block">
        <div className="flex h-14 items-center gap-2 border-b px-4">
          <div className="flex h-8 w-8 items-center justify-center rounded-md bg-primary font-black text-primary-foreground">
            LF
          </div>
          <span className="text-lg font-bold tracking-tight">LeadForge</span>
        </div>
        <div className="max-h-[calc(100vh-3.5rem)] overflow-y-auto">
          <SideNav />
        </div>
      </aside>
      <Sheet open={mobileOpen} onOpenChange={setMobileOpen}>
        <SheetContent side="left" className="w-64 p-0">
          <div className="flex h-14 items-center gap-2 border-b px-4">
            <div className="flex h-8 w-8 items-center justify-center rounded-md bg-primary font-black text-primary-foreground">
              LF
            </div>
            <span className="text-lg font-bold tracking-tight">LeadForge</span>
          </div>
          <SideNav />
        </SheetContent>
      </Sheet>
      <div className="flex min-w-0 flex-1 flex-col">
        <Suspense fallback={<div className="h-14" />}><TopBar onOpenSidebar={() => setMobileOpen(true)} /></Suspense>
        <main className="flex-1 p-4 md:p-6">{children}</main>
      </div>
    </div>
  );
}
