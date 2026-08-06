import { Badge, Button } from "../../../components/design-system";

type OperationsHeaderProps = {
  isSystemHealthy: boolean;
  activeRingsCount: number;
  pendingRemovalCount: number;
  onRefresh: () => void;
};

export function OperationsHeader({
  isSystemHealthy,
  activeRingsCount,
  pendingRemovalCount,
  onRefresh
}: OperationsHeaderProps) {
  return (
    <header className="ops-header">
      <div className="ops-header__title-group">
        <h1 className="ops-header__title">OPERATIONS COMMAND CENTER</h1>
        <p className="ops-header__subtitle">
          Real-time battery ring lifecycle tracking, floor queues, and urgent action items.
        </p>
      </div>

      <div className="ops-header__status-bar">
        <div className="ops-header__badge-group">
          <Badge tone={isSystemHealthy ? "success" : "danger"}>
            SYSTEM HEALTH: {isSystemHealthy ? "🟢 ALL MACHINES ONLINE" : "🔴 DEGRADED"}
          </Badge>

          <Badge tone="info">ACTIVE RINGS: {activeRingsCount}</Badge>

          <Badge tone={pendingRemovalCount > 0 ? "warning" : "success"}>
            PENDING REMOVAL: {pendingRemovalCount} {pendingRemovalCount > 0 ? "⚠️" : ""}
          </Badge>
        </div>

        <div className="ops-header__actions">
          <span className="ops-header__live-indicator">
            <span className="ops-header__pulse-dot" /> Auto-Sync Active
          </span>
          <Button type="button" onClick={onRefresh}>
            Refresh Floor Data
          </Button>
        </div>
      </div>
    </header>
  );
}
