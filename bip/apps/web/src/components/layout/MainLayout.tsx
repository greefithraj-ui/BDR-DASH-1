import { Outlet } from "react-router-dom";
import { useCommandCenterShortcut } from "../../hooks/useCommandCenterShortcut";
import { CommandCenter } from "../command-center/CommandCenter";
import { FooterLayout } from "./FooterLayout";
import { HeaderLayout } from "./HeaderLayout";
import { SidebarLayout } from "./SidebarLayout";

export function MainLayout() {
  useCommandCenterShortcut();

  return (
    <div className="app-shell">
      <SidebarLayout />
      <div className="app-surface">
        <HeaderLayout />
        <main className="app-content">
          <Outlet />
        </main>
        <FooterLayout />
      </div>
      <CommandCenter />
    </div>
  );
}
