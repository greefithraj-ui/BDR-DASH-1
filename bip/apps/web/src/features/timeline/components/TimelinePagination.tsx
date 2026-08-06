import { TIMELINE_PAGE_SIZE } from "../useTimeline";

type TimelinePaginationProps = {
  page: number;
  pageCount: number;
  groupCount: number;
  onPageChange: (page: number) => void;
};

export function TimelinePagination({ page, pageCount, groupCount, onPageChange }: TimelinePaginationProps) {
  if (groupCount === 0) {
    return null;
  }

  const from = (page - 1) * TIMELINE_PAGE_SIZE + 1;
  const to = Math.min(page * TIMELINE_PAGE_SIZE, groupCount);

  return (
    <nav className="timeline__pagination" aria-label="Pagination">
      <p className="timeline__pagination-summary">
        Showing groups {from}–{to} of {groupCount}
      </p>
      <div className="timeline__pagination-controls">
        <button
          className="timeline__button timeline__button--soft"
          type="button"
          disabled={page <= 1}
          onClick={() => onPageChange(page - 1)}
        >
          Previous
        </button>
        {Array.from({ length: pageCount }, (_, index) => index + 1).map((pageNumber) => (
          <button
            key={pageNumber}
            className={pageNumber === page ? "timeline__button timeline__button--active" : "timeline__button timeline__button--soft"}
            type="button"
            aria-current={pageNumber === page ? "page" : undefined}
            onClick={() => onPageChange(pageNumber)}
          >
            {pageNumber}
          </button>
        ))}
        <button
          className="timeline__button timeline__button--soft"
          type="button"
          disabled={page >= pageCount}
          onClick={() => onPageChange(page + 1)}
        >
          Next
        </button>
      </div>
    </nav>
  );
}
