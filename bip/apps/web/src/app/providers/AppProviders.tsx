import type { ReactNode } from "react";
import { ChartProvider } from "../../components/charts/ChartProvider";
import { ErrorBoundary } from "../../components/feedback/ErrorBoundary";
import { NotificationProvider } from "./NotificationProvider";
import { QueryProvider } from "./QueryProvider";
import { StateProvider } from "./StateProvider";
import { ThemeProvider } from "./ThemeProvider";

type AppProvidersProps = {
  children: ReactNode;
};

export function AppProviders({ children }: AppProvidersProps) {
  return (
    <ErrorBoundary>
      <StateProvider>
        <QueryProvider>
          <ThemeProvider>
            <ChartProvider>
              <NotificationProvider>{children}</NotificationProvider>
            </ChartProvider>
          </ThemeProvider>
        </QueryProvider>
      </StateProvider>
    </ErrorBoundary>
  );
}
