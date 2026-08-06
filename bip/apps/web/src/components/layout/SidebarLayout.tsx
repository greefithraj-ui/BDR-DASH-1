import { NavLink } from "react-router-dom";

const primaryNavItems = [
  { label: "🏠 Operations", to: "/ops" },
  { label: "🔍 Search", to: "#search" },
  { label: "🔋 Rings", to: "/battery-explorer" },
  { label: "🏭 Machines", to: "/machine-explorer" },
  { label: "📜 Timeline", to: "/timeline" },
  { label: "📈 Analytics", to: "/analytics" },
  { label: "📄 Reports", to: "/reports" }
];

export function SidebarLayout() {
  const handleNavClick = (to: string) => {
    if (to === "#search") {
      const searchEl = document.getElementById("search");
      if (searchEl) {
        searchEl.scrollIntoView({ behavior: "smooth" });
        const input = searchEl.querySelector("input");
        if (input) input.focus();
      }
    }
  };

  return (
    <aside className="sidebar-shell" aria-label="Primary navigation">
      <NavLink to="/ops" className="platform-mark">
        <span className="platform-mark__symbol">BIP</span>
        <span>Battery Intelligence Platform</span>
      </NavLink>
      <nav className="sidebar-nav">
        <section className="sidebar-section">
          <h2>Command Center</h2>
          {primaryNavItems.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              onClick={() => handleNavClick(item.to)}
              className={({ isActive }) =>
                `sidebar-link${isActive && item.to !== "#search" ? " sidebar-link--active" : ""}`
              }
            >
              {item.label}
            </NavLink>
          ))}
        </section>
      </nav>
    </aside>
  );
}


