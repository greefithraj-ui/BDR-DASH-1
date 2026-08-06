import { useEffect, type ReactNode } from "react";
import { useEffectiveTheme } from "../../hooks/useEffectiveTheme";

type ThemeProviderProps = {
  children: ReactNode;
};

export function ThemeProvider({ children }: ThemeProviderProps) {
  const effectiveTheme = useEffectiveTheme();

  useEffect(() => {
    document.documentElement.dataset.theme = effectiveTheme;
  }, [effectiveTheme]);

  return <>{children}</>;
}
