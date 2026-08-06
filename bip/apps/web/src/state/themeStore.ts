import { create } from "zustand";

export type ThemeMode = "light" | "dark" | "auto";

const STORAGE_KEY = "bip.theme";

const cycleOrder: ThemeMode[] = ["light", "dark", "auto"];

function readStoredMode(): ThemeMode {
  if (typeof window === "undefined") {
    return "auto";
  }

  const stored = window.localStorage.getItem(STORAGE_KEY);
  if (stored === "light" || stored === "dark" || stored === "auto") {
    return stored;
  }

  return "auto";
}

type ThemeState = {
  mode: ThemeMode;
  setMode: (mode: ThemeMode) => void;
  cycleMode: () => void;
};

export const useThemeStore = create<ThemeState>((set) => ({
  mode: readStoredMode(),
  setMode: (mode) => {
    if (typeof window !== "undefined") {
      window.localStorage.setItem(STORAGE_KEY, mode);
    }
    set({ mode });
  },
  cycleMode: () =>
    set((state) => {
      const next = cycleOrder[(cycleOrder.indexOf(state.mode) + 1) % cycleOrder.length];
      if (typeof window !== "undefined") {
        window.localStorage.setItem(STORAGE_KEY, next);
      }
      return { mode: next };
    })
}));
