import { useLayoutStore } from "../state/layoutStore";

export function useCommandCenter() {
  const isCommandCenterOpen = useLayoutStore((state) => state.isCommandCenterOpen);
  const setCommandCenterOpen = useLayoutStore((state) => state.setCommandCenterOpen);

  return {
    isCommandCenterOpen,
    setCommandCenterOpen
  };
}
