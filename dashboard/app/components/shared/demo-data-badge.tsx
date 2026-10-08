import * as React from "react";
import { AlertTriangle } from "lucide-react";
import { Badge } from "@/app/components/ui/badge";

/** Unmissable "DEMO DATA" marker for seeded/mock/mock data. */
export function DemoDataBadge({ label = "DEMO DATA" }: { label?: string }) {
  return (
    <Badge variant="destructive" className="gap-1 border-2 px-2 py-0.5 text-[11px] font-bold tracking-wide" title="This is demo/sample data, not real subscriber data.">
      <AlertTriangle className="h-3 w-3" aria-hidden="true" />
      {label}
    </Badge>
  );
}
