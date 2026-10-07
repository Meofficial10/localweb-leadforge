import * as React from "react";
import { cn } from "@/app/lib/utils";

export function EmptyState({ icon, title, description, action, className }: {
  icon?: React.ReactNode;
  title: string;
  description?: string;
  action?: React.ReactNode;
  className?: string;
}) {
  return (
    <div
      className={cn(
        "flex flex-col items-center justify-center gap-3 rounded-lg border border-dashed py-16 text-center",
        className
      )}
    >
      {icon ? (
        <div className="flex h-12 w-12 items-center justify-center rounded-full bg-muted text-muted-foreground" aria-hidden="true">
          {icon}
        </div>
      ) : null}
      <div>
        <h3 className="text-sm font-semibold">{title}</h3>
        {description ? <p className="mx-auto mt-1 max-w-sm text-sm text-muted-foreground">{description}</p> : null}
      </div>
      {action ? <div>{action}</div> : null}
    </div>
  );
}
