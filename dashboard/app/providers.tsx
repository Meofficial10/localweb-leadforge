"use client";

import * as React from "react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { ThemeProvider } from "next-themes";

const makeClient = () =>
  new QueryClient({
    defaultOptions: {
      queries: { retry: 1, staleTime: 15_000, refetchOnWindowFocus: false },
    },
  });

export function Providers({ children }: { children: React.ReactNode }) {
  const [client] = React.useState(makeClient);
  return (
    <QueryClientProvider client={client}>{children}</QueryClientProvider>
  );
}
