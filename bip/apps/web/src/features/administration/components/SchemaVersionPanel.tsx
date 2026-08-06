import { Badge, Card } from "../../../components/design-system";
import { getSchemaTone } from "../administration.mock";
import type { SchemaVersion } from "../administration.types";

type SchemaVersionPanelProps = {
  schemas: SchemaVersion[];
};

export function SchemaVersionPanel({ schemas }: SchemaVersionPanelProps) {
  return (
    <Card>
      <div className="administration__section-header">
        <div>
          <p className="administration__kicker">Schema Registry</p>
          <h2>Schema Version</h2>
        </div>
        <Badge tone="info">{schemas.length} schemas</Badge>
      </div>
      <div className="administration__table-scroll">
        <table className="administration__table administration__table--compact">
          <thead>
            <tr>
              <th scope="col">Schema</th>
              <th scope="col">Version</th>
              <th scope="col">Status</th>
              <th scope="col">Tables</th>
              <th scope="col">Migrated</th>
            </tr>
          </thead>
          <tbody>
            {schemas.map((schema) => (
              <tr key={schema.id}>
                <td className="administration__strong">{schema.schemaName}</td>
                <td>v{schema.version}</td>
                <td>
                  <Badge tone={getSchemaTone(schema.status)}>{schema.status}</Badge>
                </td>
                <td>{schema.tables}</td>
                <td>{schema.migratedAt}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </Card>
  );
}
