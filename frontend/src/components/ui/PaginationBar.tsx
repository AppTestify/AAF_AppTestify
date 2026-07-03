const DEFAULT_PAGE_SIZES = [25, 50, 100] as const;

type PaginationBarProps = {
  offset: number;
  pageSize: number;
  /** Items returned on the current page. */
  itemCount: number;
  /** Total matching records when known; omit for open-ended lists. */
  totalCount?: number;
  onOffsetChange: (offset: number) => void;
  onPageSizeChange?: (pageSize: number) => void;
  pageSizeOptions?: readonly number[];
  className?: string;
};

function formatRange(offset: number, itemCount: number, totalCount?: number): string {
  if (itemCount === 0) {
    return totalCount != null ? `0 of ${totalCount}` : "0 results";
  }
  const start = offset + 1;
  const end = offset + itemCount;
  if (totalCount != null) {
    return `${start}–${Math.min(end, totalCount)} of ${totalCount}`;
  }
  return `${start}–${end}`;
}

export function PaginationBar({
  offset,
  pageSize,
  itemCount,
  totalCount,
  onOffsetChange,
  onPageSizeChange,
  pageSizeOptions = DEFAULT_PAGE_SIZES,
  className = "",
}: PaginationBarProps) {
  const atStart = offset === 0;
  const hasMore = itemCount >= pageSize;
  const atEnd = totalCount != null ? offset + itemCount >= totalCount : !hasMore;

  return (
    <div className={`pagination-bar ${className}`.trim()}>
      <span className="pagination-bar-range">{formatRange(offset, itemCount, totalCount)}</span>
      <div className="pagination-bar-controls">
        {onPageSizeChange ? (
          <label className="pagination-bar-size">
            <span>Per page</span>
            <select
              value={pageSize}
              onChange={(e) => {
                onPageSizeChange(Number(e.target.value));
                onOffsetChange(0);
              }}
            >
              {pageSizeOptions.map((size) => (
                <option key={size} value={size}>
                  {size}
                </option>
              ))}
            </select>
          </label>
        ) : null}
        <button
          type="button"
          className="btn btn-ghost btn-sm"
          disabled={atStart}
          onClick={() => onOffsetChange(Math.max(0, offset - pageSize))}
        >
          Prev
        </button>
        <button
          type="button"
          className="btn btn-ghost btn-sm"
          disabled={atEnd}
          onClick={() => onOffsetChange(offset + pageSize)}
        >
          Next
        </button>
      </div>
    </div>
  );
}
