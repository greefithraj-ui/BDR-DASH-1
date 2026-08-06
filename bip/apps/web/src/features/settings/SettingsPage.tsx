import { Badge, Card, EmptyState, MetricCard } from "../../components/design-system";
import { getGroupSummary, useSettings } from "./useSettings";
import { AppearanceSettingsPanel } from "./components/AppearanceSettingsPanel";
import { DataRefreshPanel } from "./components/DataRefreshPanel";
import { FeatureFlagsPanel } from "./components/FeatureFlagsPanel";
import { LanguagePanel } from "./components/LanguagePanel";
import { NotificationSettingsPanel } from "./components/NotificationSettingsPanel";
import { SettingsDetailPanel } from "./components/SettingsDetailPanel";
import { SettingsSummaryPanel, type SettingsSummaryRow } from "./components/SettingsSummaryPanel";
import { TimeZonePanel } from "./components/TimeZonePanel";
import { UserPreferencesPanel } from "./components/UserPreferencesPanel";
import "./settings.css";

export function SettingsPage() {
  const settings = useSettings();

  const rows: SettingsSummaryRow[] = settings.groups.map((group) => ({
    id: group.id,
    label: group.label,
    description: group.description,
    summary: getGroupSummary(group.id, settings.state),
    changed: settings.changedCount > 0
  }));

  const renderDetail = () => {
    if (!settings.selectedMeta) {
      return <EmptyState label="Select a section from the left to edit its settings" />;
    }

    const meta = settings.selectedMeta;
    const groupChanged = settings.changedGroups[meta.id];

    return (
      <SettingsDetailPanel
        meta={meta}
        changed={groupChanged}
        onBack={settings.closeGroup}
        onReset={() => settings.resetGroup(meta.id)}
      >
        {meta.id === "appearance" && (
          <AppearanceSettingsPanel appearance={settings.state.appearance} onChange={settings.updateAppearance} />
        )}
        {meta.id === "notifications" && (
          <NotificationSettingsPanel
            preferences={settings.state.notifications.preferences}
            onToggle={settings.toggleNotification}
          />
        )}
        {meta.id === "localization" && (
          <div className="settings__stack">
            <LanguagePanel
              language={settings.state.localization.language}
              dateFormat={settings.state.localization.dateFormat}
              onChangeLanguage={(language) => settings.updateLocalization({ language })}
              onChangeDateFormat={(dateFormat) => settings.updateLocalization({ dateFormat })}
            />
            <TimeZonePanel
              timeZone={settings.state.localization.timeZone}
              onChange={(timeZone) => settings.updateLocalization({ timeZone })}
            />
          </div>
        )}
        {meta.id === "dataRefresh" && (
          <DataRefreshPanel settings={settings.state.dataRefresh} onChange={settings.updateDataRefresh} />
        )}
        {meta.id === "featureFlags" && (
          <FeatureFlagsPanel flags={settings.state.featureFlags.flags} onToggle={settings.toggleFlag} />
        )}
        {meta.id === "userPreferences" && (
          <UserPreferencesPanel
            preferences={settings.state.userPreferences.preferences}
            onUpdate={settings.updatePreference}
          />
        )}
      </SettingsDetailPanel>
    );
  };

  return (
    <section className="settings" aria-labelledby="settings-title">
      <header className="settings__hero">
        <div>
          <p className="settings__eyebrow">Settings</p>
          <h1 id="settings-title">Settings Center</h1>
          <p className="settings__subtitle">
            Appearance, notifications, localization, data refresh, feature flags, and user preferences using mock data.
          </p>
        </div>
        <div className="settings__hero-badges">
          <Badge tone="info">Mock Data</Badge>
          <Badge tone="neutral">{settings.changedCount} sections modified</Badge>
        </div>
      </header>

      <div className="settings__kpi-row">
        {settings.kpis.map((kpi) => (
          <MetricCard key={kpi.id} label={kpi.label} value={kpi.value} helper={kpi.delta} tone={kpi.deltaTone} />
        ))}
      </div>

      <div className="settings__content">
        <SettingsSummaryPanel rows={rows} selectedGroup={settings.selectedGroup} onSelect={settings.openGroup} />
        {renderDetail()}
      </div>

      <Card>
        <div className="settings__reset-bar">
          <div className="settings__reset-copy">
            <span className="settings__reset-label">Reset all settings</span>
            <span className="settings__reset-hint">
              Restores every section to its default mock values. Changes are local to this session and never persisted.
            </span>
          </div>
          <button className="settings__button settings__button--secondary" type="button" onClick={settings.resetAll}>
            Reset all
          </button>
        </div>
      </Card>
    </section>
  );
}
