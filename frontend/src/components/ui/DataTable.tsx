import type { ReactNode } from "react";
import { EmptyState } from "./EmptyState";

export type DataTableColumn<T> = {
  key: string;
  header: ReactNode;
  render: (row: T) => ReactNode;
  className?: string;
};

type DataTableProps<T> = {
  columns: DataTableColumn<T>[];
  rows: T[];
  rowKey: (row: T) => string | number;
  loading?: boolean;
  emptyMessage?: string;
  emptyAction?: ReactNode;
  onRowClick?: (row: T) => void;
  selectedRowKey?: string | number | null;
  className?: string;
};

export function DataTable<T>({
  columns,
  rows,
  rowKey,
  loading = false,
  emptyMessage = "No records found.",
  emptyAction,
  onRowClick,
  selectedRowKey = null,
  className = "",
}: DataTableProps<T>) {
  const skeletonRows = 5;

  return (
    <div className={`table-wrap ${loading ? "table-wrap--loading" : ""} ${className}`.trim()} aria-busy={loading || undefined}>
      <table className="data-table">
        <thead>
          <tr>
            {columns.map((col) => (
              <th key={col.key} className={col.className}>
                {col.header}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {loading
            ? Array.from({ length: skeletonRows }, (_, i) => (
                <tr key={`skeleton-${i}`} className="table-skeleton-row" aria-hidden="true">
                  {columns.map((col) => (
                    <td key={col.key}>
                      <span className="table-cell-skeleton" />
                    </td>
                  ))}
                </tr>
              ))
            : rows.map((row) => {
                const key = rowKey(row);
                const selected = selectedRowKey != null && selectedRowKey === key;
                return (
                  <tr
                    key={key}
                    className={selected ? "row-selected" : undefined}
                    onClick={onRowClick ? () => onRowClick(row) : undefined}
                  >
                    {columns.map((col) => (
                      <td key={col.key} className={col.className}>
                        {col.render(row)}
                      </td>
                    ))}
                  </tr>
                );
              })}
          {!loading && rows.length === 0 ? (
            <tr>
              <td colSpan={columns.length} className="table-empty">
                {emptyAction ? (
                  <EmptyState action={emptyAction}>{emptyMessage}</EmptyState>
                ) : (
                  emptyMessage
                )}
              </td>
            </tr>
          ) : null}
        </tbody>
      </table>
    </div>
  );
}
