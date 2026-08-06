import { create } from "zustand";

type LayoutState = {
  isSidebarCollapsed: boolean;
  isCommandCenterOpen: boolean;
  setSidebarCollapsed: (isSidebarCollapsed: boolean) => void;
  setCommandCenterOpen: (isCommandCenterOpen: boolean) => void;
};

export const useLayoutStore = create<LayoutState>((set) => ({
  isSidebarCollapsed: false,
  isCommandCenterOpen: false,
  setSidebarCollapsed: (isSidebarCollapsed) => set({ isSidebarCollapsed }),
  setCommandCenterOpen: (isCommandCenterOpen) => set({ isCommandCenterOpen })
}));
