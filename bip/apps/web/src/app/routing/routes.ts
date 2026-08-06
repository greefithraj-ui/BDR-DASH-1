export type AppRoute = {
  path: string;
  label: string;
};

export const appRoutes: AppRoute[] = [
  { path: "/", label: "Operations Command Center" },
  { path: "/ops", label: "Operations" },
  { path: "/battery-explorer", label: "Ring Explorer" },
  { path: "/machine-explorer", label: "Machine Explorer" },
  { path: "/timeline", label: "Timeline" },
  { path: "/analytics", label: "Analytics" },
  { path: "/reports", label: "Reports" },
  { path: "/administration", label: "Administration" },
  { path: "/settings", label: "Settings" }
];

