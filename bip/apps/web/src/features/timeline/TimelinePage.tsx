import { Badge, EmptyState, LoadingSkeleton } from "../../components/design-system";
import { ApiErrorState } from "../../components/feedback/ApiErrorState";
import { describeApiError } from "../../lib/errors";
import { TimelineDetailPanel } from "./components/TimelineDetailPanel";
import { TimelineGroupSection } from "./components/TimelineGroupSection";
import { TimelinePagination } from "./components/TimelinePagination";
import { TimelineToolbar } from "./components/TimelineToolbar";
import { useTimeline } from "./useTimeline";
import "./timeline.css";

export function TimelinePage() {
  const timeline = useTimeline();

  if (timeline.selected) {
    return <TimelineDetailPanel event={timeline.selected} onBack={timeline.closeDetail} />;
  }

  if (timeline.isLoading) {
    return <LoadingSkeleton className="timeline__loading" label="Loading timeline" />;
  }

  if (timeline.error) {
    return <ApiErrorState message={describeApiError(timeline.error)} onRetry={() => void timeline.refresh()} />;
  }

  return (
    <section className="timeline" aria-labelledby="timeline-title">
      <header className="timeline__hero">
        <div>
          <p className="timeline__eyebrow">Timeline</p>
          <h1 id="timeline-title">Timeline</h1>
          <p className="timeline__subtitle">
            Chronological battery and machine events grouped by date, machine, or battery from live collector data.
          </p>
        </div>
        <button className="timeline__button" type="button" onClick={() => void timeline.refresh()}>
          Refresh
        </button>
        <Badge tone="info">Live Data</Badge>
      </header>

      <TimelineToolbar
        filters={timeline.filters}
        options={timeline.options}
        groupBy={timeline.groupBy}
        sort={timeline.sort}
        onFiltersChange={timeline.updateFilters}
        onClearAll={timeline.clearFilters}
        onGroupByChange={timeline.changeGroupBy}
        onToggleSort={timeline.toggleSort}
      />

      <div className="timeline__summary-row">
        <p>
          {timeline.filteredCount} events in {timeline.groupCount} groups
          {timeline.activeFilterCount > 0 ? ` · ${timeline.activeFilterCount} active filter${timeline.activeFilterCount === 1 ? "" : "s"}` : ""}
        </p>
        <p className="timeline__summary-sort">Grouped by {timeline.groupBy}</p>
      </div>

      {timeline.pageGroups.length === 0 ? (
        <EmptyState label="No events match the current filters" />
      ) : (
        <div className="timeline__groups">
          {timeline.pageGroups.map((group) => (
            <TimelineGroupSection key={group.key} group={group} onSelect={timeline.openDetail} />
          ))}
        </div>
      )}

      <TimelinePagination
        page={timeline.page}
        pageCount={timeline.pageCount}
        groupCount={timeline.groupCount}
        onPageChange={timeline.changePage}
      />
    </section>
  );
}