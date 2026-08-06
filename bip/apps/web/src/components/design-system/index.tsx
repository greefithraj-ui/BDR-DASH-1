import type { ReactNode } from "react";
import { cn } from "../../lib/cn";

type ShellComponentProps = {
  children?: ReactNode;
  className?: string;
  label?: string;
};

type ButtonProps = ShellComponentProps & {
  type?: "button" | "submit" | "reset";
  onClick?: () => void;
};

type BadgeProps = ShellComponentProps & {
  tone?: "neutral" | "success" | "warning" | "danger" | "info";
};

type MetricCardProps = {
  className?: string;
  label: string;
  value: string;
  helper?: string;
  tone?: "neutral" | "success" | "warning" | "danger" | "info";
};

function createShellComponent(name: string, defaultClassName: string) {
  return function ShellComponent({ children, className, label }: ShellComponentProps) {
    return (
      <div className={cn(defaultClassName, className)} data-component={name}>
        {children ?? label ?? name}
      </div>
    );
  };
}

export function Button({ children, className, label, onClick, type = "button" }: ButtonProps) {
  return (
    <button className={cn("ds-button", className)} data-component="Button" type={type} onClick={onClick}>
      {children ?? label ?? "Button"}
    </button>
  );
}


export function Card({ children, className, label }: ShellComponentProps) {
  return (
    <section className={cn("ds-card", className)} data-component="Card">
      {children ?? label ?? "Card"}
    </section>
  );
}

export function MetricCard({ className, helper, label, tone = "neutral", value }: MetricCardProps) {
  return (
    <Card className={cn("ds-metric-card", className)} data-tone={tone}>
      <div className="ds-metric-card__label">{label}</div>
      <div className="ds-metric-card__value">{value}</div>
      {helper ? <div className="ds-metric-card__helper">{helper}</div> : null}
    </Card>
  );
}

export const Dialog = createShellComponent("Dialog", "ds-shell-component");
export const Drawer = createShellComponent("Drawer", "ds-shell-component");

export function Badge({ children, className, label, tone = "neutral" }: BadgeProps) {
  return (
    <span className={cn("ds-badge", `ds-badge--${tone}`, className)} data-component="Badge">
      {children ?? label ?? "Badge"}
    </span>
  );
}

export const Avatar = createShellComponent("Avatar", "ds-avatar");
export const Tabs = createShellComponent("Tabs", "ds-shell-component");
export const Table = createShellComponent("Table", "ds-shell-component");

export function EmptyState({ children, className, label }: ShellComponentProps) {
  return (
    <div className={cn("ds-empty-state", className)} data-component="EmptyState">
      {children ?? label ?? "Coming Soon"}
    </div>
  );
}

export function LoadingSkeleton({ className, label }: ShellComponentProps) {
  return (
    <div className={cn("ds-loading-skeleton", className)} data-component="LoadingSkeleton">
      {label ? <span>{label}</span> : null}
    </div>
  );
}

export { ChartContainer } from "../charts/ChartContainer";

export const Filters = createShellComponent("Filters", "ds-shell-component");
export const SearchInput = createShellComponent("SearchInput", "ds-shell-component");
