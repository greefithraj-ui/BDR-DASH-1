import { useEffect, useState } from "react";
import { useThemeStore } from "../state/themeStore";

export type EffectiveTheme = "light" | "dark";

export function useEffectiveTheme(): EffectiveTheme {
  const mode = useThemeStore((state) => state.mode);

  const [systemPrefersDark, setSystemPrefersDark] = useState<boolean>(
    () =>
      typeof window !== "undefined" &&
      window.matchMedia("(prefers-color-scheme: dark)").matches
  );

  useEffect(() => {
    if (typeof window === "undefined") {
      return;
    }

    const media = window.matchMedia("(prefers-color-scheme: dark)");
    const onChange = (event: MediaQueryListEvent) => setSystemPrefersDark(event.matches);

    media.addEventListener("change", onChange);
    return () => media.removeEventListener("change", onChange);
  }, []);

  if (mode === "auto") {
    return systemPrefersDark ? "dark" : "light";
  }

  return mode;
}
