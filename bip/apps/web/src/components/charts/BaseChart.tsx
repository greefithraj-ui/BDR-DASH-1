import * as echarts from "echarts/core";
import type { EChartsCoreOption } from "echarts/core";
import { useEffect, useRef } from "react";
import { useChartTheme } from "./ChartProvider";

export type BaseChartProps = {
  option: EChartsCoreOption;
  className?: string;
  loading?: boolean;
};

export function BaseChart({ className, loading = false, option }: BaseChartProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<echarts.ECharts | null>(null);
  const { theme } = useChartTheme();

  const optionRef = useRef(option);
  optionRef.current = option;

  const loadingRef = useRef(loading);
  loadingRef.current = loading;

  useEffect(() => {
    const container = containerRef.current;
    if (!container) {
      return;
    }

    const chart = echarts.init(container, theme);
    chartRef.current = chart;
    chart.setOption(optionRef.current, { notMerge: true });

    if (loadingRef.current) {
      chart.showLoading("default", { text: "Loading…", color: "#12355b" });
    }

    return () => {
      chart.dispose();
      chartRef.current = null;
    };
  }, [theme]);

  useEffect(() => {
    chartRef.current?.setOption(option, { notMerge: true });
  }, [option]);

  useEffect(() => {
    if (loading) {
      chartRef.current?.showLoading("default", { text: "Loading…", color: "#12355b" });
    } else {
      chartRef.current?.hideLoading();
    }
  }, [loading]);

  useEffect(() => {
    const container = containerRef.current;
    if (!container) {
      return;
    }

    const observer = new ResizeObserver(() => chartRef.current?.resize());
    observer.observe(container);

    return () => observer.disconnect();
  }, []);

  return <div ref={containerRef} className={className} />;
}
