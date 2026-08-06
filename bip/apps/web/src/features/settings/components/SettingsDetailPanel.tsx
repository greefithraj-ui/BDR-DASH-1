import type { ReactNode } from "react";
import { Badge, Card } from "../../../components/design-system";
import type { SettingsGroupMeta } from "../settings.types";

type SettingsDetailPanelProps = {
  meta: SettingsGroupMeta;
  changed: boolean;
  children: ReactNode;
  onBack: () => void;
  onReset: () => void;
};

export function SettingsDetailPanel({ meta, changed, children, onBack, onReset }: SettingsDetailPanelProps) {
  return (
    <Card>
      <div className="settings-detail__header">
        <div>
          <p className="settings__kicker">Editing</p>
          <h2>{meta.label}</h2>
          <p className="settings-detail__desc">{meta.description}</p>
        </div>
        {changed ? <Badge tone="warning">Unsaved changes</Badge> : <Badge tone="success">Using defaults</Badge>}
      </div>
      <div className="settings-detail__body">{children}</div>
      <div className="settings-detail__actions">
        <button className="settings__button" type="button" onClick={onBack}>
          Back to settings
        </button>
        <button className="settings__button settings__button--secondary" type="button" onClick={onReset}>
          Reset section
        </button>
      </div>
    </Card>
  );
}
