import { createBrowserRouter } from "react-router-dom";
import { MainLayout } from "../../components/layout/MainLayout";
import { AdministrationPage } from "../../features/administration/AdministrationPage";
import { AnalyticsHubPage } from "../../features/analytics-hub/AnalyticsHubPage";
import { BatteryExplorerPage } from "../../features/battery-explorer/BatteryExplorerPage";
import { MachineExplorerPage } from "../../features/machine-explorer/MachineExplorerPage";
import { OperationsCenter } from "../../features/operations-center/OperationsCenter";
import { ReportsPage } from "../../features/reports/ReportsPage";
import { SettingsPage } from "../../features/settings/SettingsPage";
import { TimelinePage } from "../../features/timeline/TimelinePage";
import { NotFoundPage } from "../../pages/NotFoundPage";
import { PlaceholderPage } from "../../pages/PlaceholderPage";
import { appRoutes } from "./routes";

function getRouteElement(path: string, label: string) {
  if (path === "/" || path === "/ops") {
    return <OperationsCenter />;
  }


  if (path === "/analytics") {
    return <AnalyticsHubPage />;
  }

  if (path === "/battery-explorer") {
    return <BatteryExplorerPage />;
  }

  if (path === "/machine-explorer") {
    return <MachineExplorerPage />;
  }

  if (path === "/timeline") {
    return <TimelinePage />;
  }

  if (path === "/reports") {
    return <ReportsPage />;
  }

  if (path === "/administration") {
    return <AdministrationPage />;
  }

  if (path === "/settings") {
    return <SettingsPage />;
  }

  return <PlaceholderPage title={label} />;
}

export const router = createBrowserRouter([
  {
    element: <MainLayout />,
    children: [
      ...appRoutes.map((route) => ({
        path: route.path,
        element: getRouteElement(route.path, route.label)
      })),
      {
        path: "404",
        element: <NotFoundPage />
      },
      {
        path: "*",
        element: <NotFoundPage />
      }
    ]
  }
]);

