import { useEffect } from "react";
import { useCommandCenter } from "./useCommandCenter";

export function useCommandCenterShortcut() {
  const { isCommandCenterOpen, setCommandCenterOpen } = useCommandCenter();

  useEffect(() => {
    const handleKeyDown = (event: KeyboardEvent) => {
      if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === "k") {
        event.preventDefault();
        setCommandCenterOpen(!isCommandCenterOpen);
        return;
      }

      if (event.key === "Escape" && isCommandCenterOpen) {
        setCommandCenterOpen(false);
      }
    };

    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [isCommandCenterOpen, setCommandCenterOpen]);
}
