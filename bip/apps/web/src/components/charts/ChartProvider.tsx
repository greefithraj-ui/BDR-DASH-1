import { createContext, useContext, useMemo, type ReactNode } from "react";
import { useEffectiveTheme } from "../../hooks/useEffectiveTheme";
import { registerChartThemes, type ChartThemeName } from "./ChartTheme";

registerChartThemes();

type ChartContextValue = {
  theme: ChartThemeName;
};

const ChartContext = createContext<ChartContextValue>({ theme: "bip-light" });

type ChartProviderProps = {
  children: ReactNode;
};

export function ChartProvider({ children }: ChartProviderProps) {
  const effectiveTheme = useEffectiveTheme();

  const value = useMemo<ChartContextValue>(
    () => ({ theme: `bip-${effectiveTheme}` as ChartThemeName }),
    [effectiveTheme]
  );

  return <ChartContext.Provider value={value}>{children}</ChartContext.Provider>;
}

export function useChartTheme(): ChartContextValue {
  return useContext(ChartContext);
}
