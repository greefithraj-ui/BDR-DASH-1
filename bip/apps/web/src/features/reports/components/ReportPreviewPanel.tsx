import { Badge, Card } from "../../../components/design-system";
import type { Report } from "../reports.types";

type ReportPreviewPanelProps = {
  report: Report;
};

export function ReportPreviewPanel({ report }: ReportPreviewPanelProps) {
  return (
    <Card>
      <div className="reports__section-header">
        <div>
          <p className="reports__kicker">Preview</p>
          <h2>Report Preview</h2>
        </div>
        <Badge tone="info">{report.title}</Badge>
      </div>
      <div className="reports__preview-tables">
        {report.previewTables.map((table) => (
          <div key={table.id} className="reports__preview-table">
            <h3>{table.title}</h3>
            <div className="reports__table-scroll">
              <table className="reports__table reports__table--preview">
                <thead>
                  <tr>
                    {table.columns.map((column) => (
                      <th key={column.id} scope="col">
                        {column.label}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {table.rows.map((row) => (
                    <tr key={row.id}>
                      {row.values.map((value, index) => (
                        <td key={table.columns[index]?.id ?? index}>{value}</td>
                      ))}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        ))}
      </div>
    </Card>
  );
}
