import { Badge, EmptyState, MetricCard } from "../../components/design-system";
import { useAdministration } from "./useAdministration";
import { AdministrationDetailPanel } from "./components/AdministrationDetailPanel";
import { AdministrationToolbar } from "./components/AdministrationToolbar";
import { AuditLogPanel } from "./components/AuditLogPanel";
import { CollectorStatusPanel } from "./components/CollectorStatusPanel";
import { DatabaseStatusPanel } from "./components/DatabaseStatusPanel";
import { MachineRegistryPanel } from "./components/MachineRegistryPanel";
import { SchemaVersionPanel } from "./components/SchemaVersionPanel";
import { ServiceStatusPanel } from "./components/ServiceStatusPanel";
import { SystemHealthPanel } from "./components/SystemHealthPanel";
import "./administration.css";

export function AdministrationPage() {
  const administration = useAdministration();

  if (administration.selected) {
    return (
      <AdministrationDetailPanel
        machine={administration.selected}
        points={administration.machineTimeline}
        auditEntries={administration.machineAuditEntries}
        onBack={administration.closeDetail}
      />
    );
  }

  return (
    <section className="administration" aria-labelledby="administration-title">
      <header className="administration__hero">
        <div>
          <p className="administration__eyebrow">Administration</p>
          <h1 id="administration-title">Administration Center</h1>
          <p className="administration__subtitle">
            System health, collector status, machine registry, schema versions, audit log, and platform information using mock data.
          </p>
        </div>
        <div className="administration__hero-badges">
          <Badge tone="info">Mock Data</Badge>
          <Badge tone="neutral">8 machines registered</Badge>
        </div>
      </header>

      <AdministrationToolbar
        filters={administration.filters}
        options={administration.options}
        onFiltersChange={administration.updateFilters}
        onClearAll={administration.clearFilters}
      />

      <div className="administration__kpi-row">
        {administration.kpis.map((kpi) => (
          <MetricCard key={kpi.id} label={kpi.label} value={kpi.value} helper={kpi.delta} tone={kpi.deltaTone} />
        ))}
      </div>

      <div className="administration__summary-row">
        <p>
          {administration.machines.length} machines shown
          {administration.activeFilterCount > 0 ? ` · ${administration.activeFilterCount} active filter${administration.activeFilterCount === 1 ? "" : "s"}` : ""}
        </p>
      </div>

      <SystemHealthPanel metrics={administration.healthMetrics} />

      <div className="administration__pair-grid">
        <ServiceStatusPanel services={administration.services} />
        <DatabaseStatusPanel databases={administration.databases} />
      </div>

      <div className="administration__pair-grid">
        <CollectorStatusPanel collectors={administration.collectors} />
        <SchemaVersionPanel schemas={administration.schemas} />
      </div>

      {administration.machines.length === 0 ? (
        <EmptyState label="No machines match the current filters" />
      ) : (
        <MachineRegistryPanel machines={administration.machines} onSelect={administration.openDetail} />
      )}

      <AuditLogPanel entries={administration.auditEntries} />

      <section className="administration__platform" aria-label="Platform information">
        <div className="administration__section-header">
          <div>
            <p className="administration__kicker">Platform</p>
            <h2>Platform Information</h2>
          </div>
          <Badge tone="info">{administration.platform.environment}</Badge>
        </div>
        <dl className="administration__platform-grid">
          <div>
            <dt>Platform</dt>
            <dd>{administration.platform.platformName}</dd>
          </div>
          <div>
            <dt>Version</dt>
            <dd>{administration.platform.version}</dd>
          </div>
          <div>
            <dt>Environment</dt>
            <dd>{administration.platform.environment}</dd>
          </div>
          <div>
            <dt>Deployed</dt>
            <dd>{administration.platform.deployDate}</dd>
          </div>
          <div>
            <dt>Build</dt>
            <dd>{administration.platform.build}</dd>
          </div>
          <div>
            <dt>Nodes</dt>
            <dd>{administration.platform.nodes}</dd>
          </div>
          <div>
            <dt>Storage</dt>
            <dd>
              {administration.platform.storageUsed} of {administration.platform.storageTotal}
            </dd>
          </div>
          <div>
            <dt>Region</dt>
            <dd>{administration.platform.region}</dd>
          </div>
        </dl>
      </section>
    </section>
  );
}
