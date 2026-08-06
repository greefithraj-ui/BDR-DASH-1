import { Badge, EmptyState, LoadingSkeleton } from "../../components/design-system";
import { ApiErrorState } from "../../components/feedback/ApiErrorState";
import { describeApiError } from "../../lib/errors";
import { useReports } from "./useReports";
import { ReportDetailPanel } from "./components/ReportDetailPanel";
import { ReportHistoryPanel } from "./components/ReportHistoryPanel";
import { ReportPreviewPanel } from "./components/ReportPreviewPanel";
import { ReportTable } from "./components/ReportTable";
import { ReportsGrid } from "./components/ReportsGrid";
import { ReportsSummary } from "./components/ReportsSummary";
import { ReportsToolbar } from "./components/ReportsToolbar";
import "./reports.css";

export function ReportsPage() {
  const reports = useReports();

  if (reports.selected) {
    return (
      <ReportDetailPanel
        report={reports.selected}
        entries={reports.selected.history.map((run) => ({
          id: run.id,
          reportId: reports.selected!.id,
          date: run.date,
          reportTitle: reports.selected!.title,
          status: run.status,
          durationSeconds: run.durationSeconds,
          pages: run.pages
        }))}
        onBack={reports.closeDetail}
      />
    );
  }

  if (reports.isLoading) {
    return <LoadingSkeleton className="reports__loading" label="Loading reports" />;
  }

  if (reports.error) {
    return (
      <section className="reports" aria-labelledby="reports-title">
        <header className="reports__hero">
          <div>
            <p className="reports__eyebrow">Reports</p>
            <h1 id="reports-title">Reports</h1>
          </div>
        </header>
        <ApiErrorState
          message={describeApiError(reports.error)}
          onRetry={() => void reports.refresh()}
        />
      </section>
    );
  }

  return (
    <section className="reports" aria-labelledby="reports-title">
      <header className="reports__hero">
        <div>
          <p className="reports__eyebrow">Reports</p>
          <h1 id="reports-title">Reports</h1>
          <p className="reports__subtitle">
            Browse, preview, and track report schedules, execution history, and delivery for operations, quality, machine, and lifecycle reporting from live data.
          </p>
        </div>
        <button className="reports__button" type="button" onClick={() => void reports.refresh()}>
          Refresh
        </button>
        <Badge tone="info">Live Data</Badge>
      </header>

      <ReportsToolbar
        filters={reports.filters}
        options={reports.options}
        onFiltersChange={reports.updateFilters}
        onClearAll={reports.clearFilters}
      />

      <ReportsSummary kpis={reports.kpis} shownCount={reports.reports.length} activeFilterCount={reports.activeFilterCount} />

      <ReportsGrid
        kicker="Recent"
        title="Recent Reports"
        badgeLabel="Most recent first"
        reports={reports.recentReports}
        onSelect={reports.openDetail}
      />

      <ReportsGrid
        kicker="Automation"
        title="Scheduled Reports"
        badgeLabel={`${reports.scheduledReports.length} scheduled`}
        reports={reports.scheduledReports}
        onSelect={reports.openDetail}
      />

      <ReportHistoryPanel kicker="Execution" title="Execution History" entries={reports.historyEntries} />

      {reports.reports.length === 0 ? (
        <EmptyState label="No reports match the current filters" />
      ) : (
        <>
          <ReportTable reports={reports.reports} onSelect={reports.openDetail} />
          <ReportPreviewPanel report={reports.previewReport} />
        </>
      )}
    </section>
  );
}
