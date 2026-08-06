import { Badge, Card } from "../../../components/design-system";
import type { ServiceEntry, ServiceStatus } from "../administration.types";

type ServiceStatusPanelProps = {
  services: ServiceEntry[];
};

const SERVICE_TONE: Record<ServiceStatus, "success" | "warning" | "danger"> = {
  Operational: "success",
  Degraded: "warning",
  Down: "danger"
};

export function ServiceStatusPanel({ services }: ServiceStatusPanelProps) {
  return (
    <Card>
      <div className="administration__section-header">
        <div>
          <p className="administration__kicker">Platform</p>
          <h2>Service Status</h2>
        </div>
        <Badge tone="info">{services.length} services</Badge>
      </div>
      <div className="administration__table-scroll">
        <table className="administration__table administration__table--compact">
          <thead>
            <tr>
              <th scope="col">Service</th>
              <th scope="col">Status</th>
              <th scope="col">Uptime</th>
              <th scope="col">Last Restart</th>
            </tr>
          </thead>
          <tbody>
            {services.map((service) => (
              <tr key={service.id}>
                <td className="administration__strong">{service.serviceName}</td>
                <td>
                  <Badge tone={SERVICE_TONE[service.status]}>{service.status}</Badge>
                </td>
                <td>{service.uptime}</td>
                <td>{service.lastRestart}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </Card>
  );
}
