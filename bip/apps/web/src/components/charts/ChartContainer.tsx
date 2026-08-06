import type { EChartsCoreOption } from "echarts/core";
import { useMemo, type ReactNode } from "react";
import { cn } from "../../lib/cn";
import { BaseChart } from "./BaseChart";
import { useChartTheme } from "./ChartProvider";
import "./charts.css";

type ChartContainerProps = {
  children?: ReactNode;
  className?: string;
  description?: string;
  height?: string;
  option?: EChartsCoreOption;
  title?: string;
};

function getCssColor(variable: string, fallback: string): string {
  if (typeof window === "undefined") {
    return fallback;
  }

  return getComputedStyle(document.documentElement).getPropertyValue(variable).trim() || fallback;
}

export function ChartContainer({
  children,
  className,
  description,
  height = "240px",
  option,
  title
}: ChartContainerProps) {
  const { theme } = useChartTheme();

  const placeholderOption = useMemo<EChartsCoreOption>(
    () => ({
      graphic: {
        elements: [
          {
            type: "text",
            left: "center",
            top: "middle",
            style: {
              text: "Chart placeholder",
              fontSize: 14,
              fill: getCssColor("--text-muted", theme === "bip-dark" ? "#c3cad6" : "#687386")
            }
          }
        ]
      }
    }),
    [theme]
  );

  return (
    <section className={cn("ds-chart-container", className)} data-component="ChartContainer">
      {title || description ? (
        <header className="ds-chart-container__header">
          {title ? <h3>{title}</h3> : null}
          {description ? <p>{description}</p> : null}
        </header>
      ) : null}
      <div className="ds-chart-container__body" style={{ height }}>
        {children ?? <BaseChart option={option ?? placeholderOption} />}
      </div>
    </section>
  );
}
