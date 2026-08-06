import { NavLink } from "react-router-dom";
import { useCommandCenter } from "../../hooks/useCommandCenter";
import { useThemeStore } from "../../state/themeStore";

export function HeaderLayout() {
  const mode = useThemeStore((state) => state.mode);
  const cycleMode = useThemeStore((state) => state.cycleMode);
  const { setCommandCenterOpen } = useCommandCenter();

  return (
    <header className="header-shell">
      <div className="header-group">
        <div className="logo-placeholder">BIP Command Center</div>
      </div>
      <div className="header-actions">
        <button
          className="shell-button"
          type="button"
          onClick={() => setCommandCenterOpen(true)}
          title="Global Search (Ctrl+K)"
        >
          🔍 Search (CTRL+K)
        </button>
        <button className="shell-button" type="button" onClick={cycleMode} title="Cycle theme">
          Theme: {mode}
        </button>
        <NavLink to="/administration" className="shell-button" title="Administration">
          Admin
        </NavLink>
        <NavLink to="/settings" className="shell-button" title="Settings">
          Settings
        </NavLink>
      </div>
    </header>
  );
}

