import { BATTERY_EXPLORER_PAGE_SIZE } from "../useBatteryExplorer";

type ExplorerPaginationProps = {
  page: number;
  pageCount: number;
  total: number;
  onPageChange: (page: number) => void;
};

export function ExplorerPagination({ page, pageCount, total, onPageChange }: ExplorerPaginationProps) {
  if (total === 0) {
    return null;
  }

  const from = (page - 1) * BATTERY_EXPLORER_PAGE_SIZE + 1;
  const to = Math.min(page * BATTERY_EXPLORER_PAGE_SIZE, total);

  return (
    <nav className="battery-explorer__pagination" aria-label="Pagination">
      <p className="battery-explorer__pagination-summary">
        Showing {from}–{to} of {total}
      </p>
      <div className="battery-explorer__pagination-controls">
        <button
          className="battery-explorer__button"
          type="button"
          disabled={page <= 1}
          onClick={() => onPageChange(page - 1)}
        >
          Previous
        </button>
        {Array.from({ length: pageCount }, (_, index) => index + 1).map((pageNumber) => (
          <button
            key={pageNumber}
            className={pageNumber === page ? "battery-explorer__button battery-explorer__button--active" : "battery-explorer__button"}
            type="button"
            aria-current={pageNumber === page ? "page" : undefined}
            onClick={() => onPageChange(pageNumber)}
          >
            {pageNumber}
          </button>
        ))}
        <button
          className="battery-explorer__button"
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
