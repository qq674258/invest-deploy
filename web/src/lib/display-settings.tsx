"use client";

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
} from "react";

export type KlineColorScheme = "cn" | "us";

const STORAGE_KEY = "invest-kline-colors";

export type KlineCandleStyle = {
  color: string;
  color0: string;
  borderColor: string;
  borderColor0: string;
};

const STYLES: Record<KlineColorScheme, KlineCandleStyle> = {
  cn: {
    color: "#ef4444",
    color0: "#22c55e",
    borderColor: "#ef4444",
    borderColor0: "#22c55e",
  },
  us: {
    color: "#22c55e",
    color0: "#ef4444",
    borderColor: "#22c55e",
    borderColor0: "#ef4444",
  },
};

type Ctx = {
  klineScheme: KlineColorScheme;
  setKlineScheme: (s: KlineColorScheme) => void;
  klineCandleStyle: KlineCandleStyle;
  toggleKlineScheme: () => void;
};

const DisplaySettingsContext = createContext<Ctx | null>(null);

export function DisplaySettingsProvider({ children }: { children: React.ReactNode }) {
  const [klineScheme, setKlineSchemeState] = useState<KlineColorScheme>("cn");

  useEffect(() => {
    try {
      const raw = localStorage.getItem(STORAGE_KEY);
      if (raw === "cn" || raw === "us") setKlineSchemeState(raw);
    } catch {
      /* ignore */
    }
  }, []);

  const setKlineScheme = useCallback((s: KlineColorScheme) => {
    setKlineSchemeState(s);
    try {
      localStorage.setItem(STORAGE_KEY, s);
    } catch {
      /* ignore */
    }
  }, []);

  const toggleKlineScheme = useCallback(() => {
    setKlineScheme(klineScheme === "cn" ? "us" : "cn");
  }, [klineScheme, setKlineScheme]);

  const value = useMemo(
    () => ({
      klineScheme,
      setKlineScheme,
      klineCandleStyle: STYLES[klineScheme],
      toggleKlineScheme,
    }),
    [klineScheme, setKlineScheme, toggleKlineScheme]
  );

  return (
    <DisplaySettingsContext.Provider value={value}>
      {children}
    </DisplaySettingsContext.Provider>
  );
}

export function useDisplaySettings() {
  const ctx = useContext(DisplaySettingsContext);
  if (!ctx) {
    throw new Error("useDisplaySettings must be used within DisplaySettingsProvider");
  }
  return ctx;
}

export function klineSchemeLabel(scheme: KlineColorScheme) {
  return scheme === "cn" ? "红涨绿跌（A股）" : "绿涨红跌（美股）";
}
