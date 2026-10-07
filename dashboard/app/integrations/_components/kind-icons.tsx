"use client";
import { MapPin, Globe, Server, Mail, Phone, ShieldCheck, Sparkles, User, Gavel, Database, Bot, Building2 } from "lucide-react";

const map: Record<string, React.ComponentType<{ className?: string }>> = {
  source: MapPin, ai: Server, hosting: Globe, email: Mail, voice: Phone,
  dnc: ShieldCheck, identity: User,
};

export function KindIcon({ kind, className }: { kind: string; className?: string }) {
  const C = map[kind] || Bot;
  return <C className={className || "h-4 w-4"} aria-hidden="true" />;
}
