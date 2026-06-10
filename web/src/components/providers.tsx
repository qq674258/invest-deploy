"use client";

import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { useState } from "react";
import { CACHE_STALE_MS } from "@/lib/cache-config";
import { DisplaySettingsProvider } from "@/lib/display-settings";

export function Providers({ children }: { children: React.ReactNode }) {
  const [client] = useState(
    () =>
      new QueryClient({
        defaultOptions: {
          queries: {
            staleTime: CACHE_STALE_MS,
            gcTime: CACHE_STALE_MS * 5,
            retry: 1,
          },
        },
      })
  );
  return (
    <QueryClientProvider client={client}>
      <DisplaySettingsProvider>{children}</DisplaySettingsProvider>
    </QueryClientProvider>
  );
}
