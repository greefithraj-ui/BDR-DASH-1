import { useMemo, useState } from "react";
import { getDefaultSettings, getSettingGroups } from "./settings.mock";
import type {
  AppearanceSettings,
  DataRefreshSettings,
  LocalizationSettings,
  SettingsGroupKey,
  SettingsKpi,
  SettingsState
} from "./settings.types";

function buildKpis(state: SettingsState): SettingsKpi[] {
  const themeLabel =
    state.appearance.theme === "bip-light" ? "Light" : state.appearance.theme === "bip-dark" ? "Dark" : "System";

  const notificationsOn = state.notifications.preferences.filter((item) => item.enabled).length;
  const notificationsTotal = state.notifications.preferences.length;

  const flagsOn = state.featureFlags.flags.filter((item) => item.enabled).length;
  const flagsTotal = state.featureFlags.flags.length;

  return [
    { id: "settings-kpi-theme", label: "Theme", value: themeLabel, delta: `Accent ${state.appearance.accentColor}`, deltaTone: "info" },
    { id: "settings-kpi-refresh", label: "Refresh Interval", value: state.dataRefresh.refreshInterval, delta: state.dataRefresh.autoRefresh ? "auto refresh on" : "auto refresh off", deltaTone: "success" },
    { id: "settings-kpi-notifications", label: "Notifications Enabled", value: `${notificationsOn} / ${notificationsTotal}`, delta: `${notificationsTotal - notificationsOn} disabled`, deltaTone: "success" },
    { id: "settings-kpi-flags", label: "Feature Flags Enabled", value: `${flagsOn} / ${flagsTotal}`, delta: `${flagsTotal - flagsOn} preview flags`, deltaTone: "warning" },
    { id: "settings-kpi-profile", label: "Profile Status", value: "Complete", delta: "100% verified", deltaTone: "success" }
  ];
}

export function getGroupSummary(key: SettingsGroupKey, state: SettingsState): string {
  switch (key) {
    case "appearance":
      return `${state.appearance.theme} · ${state.appearance.accentColor} · ${state.appearance.density}`;
    case "notifications": {
      const enabled = state.notifications.preferences.filter((item) => item.enabled).length;
      return `${enabled} of ${state.notifications.preferences.length} enabled`;
    }
    case "localization":
      return `${state.localization.language} · ${state.localization.dateFormat}`;
    case "dataRefresh":
      return `${state.dataRefresh.refreshInterval}${state.dataRefresh.autoRefresh ? " · auto" : ""}${state.dataRefresh.cacheEnabled ? " · cache" : ""}`;
    case "featureFlags": {
      const enabled = state.featureFlags.flags.filter((item) => item.enabled).length;
      return `${enabled} of ${state.featureFlags.flags.length} enabled`;
    }
    case "userPreferences": {
      const name = state.userPreferences.preferences.find((item) => item.id === "profile-name");
      const role = state.userPreferences.preferences.find((item) => item.id === "profile-role");
      return `${name?.value ?? ""} · ${role?.value ?? ""}`;
    }
  }
}

function groupChanged(key: SettingsGroupKey, current: SettingsState, defaults: SettingsState): boolean {
  return JSON.stringify(current[key]) !== JSON.stringify(defaults[key]);
}

function buildChangedGroups(state: SettingsState, defaults: SettingsState): Record<SettingsGroupKey, boolean> {
  return {
    appearance: groupChanged("appearance", state, defaults),
    notifications: groupChanged("notifications", state, defaults),
    localization: groupChanged("localization", state, defaults),
    dataRefresh: groupChanged("dataRefresh", state, defaults),
    featureFlags: groupChanged("featureFlags", state, defaults),
    userPreferences: groupChanged("userPreferences", state, defaults)
  };
}

export function useSettings() {
  const defaults = useMemo(() => getDefaultSettings(), []);
  const [state, setState] = useState<SettingsState>(() => getDefaultSettings());
  const [selectedGroup, setSelectedGroup] = useState<SettingsGroupKey | null>(null);

  const groups = useMemo(() => getSettingGroups(), []);
  const kpis = useMemo(() => buildKpis(state), [state]);

  const changedGroups = useMemo(() => buildChangedGroups(state, defaults), [state, defaults]);

  const changedCount = useMemo(
    () => groups.filter((group) => changedGroups[group.id]).length,
    [groups, changedGroups]
  );

  const updateAppearance = (patch: Partial<AppearanceSettings>) => {
    setState((current) => ({ ...current, appearance: { ...current.appearance, ...patch } }));
  };

  const updateLocalization = (patch: Partial<LocalizationSettings>) => {
    setState((current) => ({ ...current, localization: { ...current.localization, ...patch } }));
  };

  const updateDataRefresh = (patch: Partial<DataRefreshSettings>) => {
    setState((current) => ({ ...current, dataRefresh: { ...current.dataRefresh, ...patch } }));
  };

  const toggleNotification = (id: string) => {
    setState((current) => ({
      ...current,
      notifications: {
        preferences: current.notifications.preferences.map((item) =>
          item.id === id ? { ...item, enabled: !item.enabled } : item
        )
      }
    }));
  };

  const toggleFlag = (id: string) => {
    setState((current) => ({
      ...current,
      featureFlags: {
        flags: current.featureFlags.flags.map((item) => (item.id === id ? { ...item, enabled: !item.enabled } : item))
      }
    }));
  };

  const updatePreference = (id: string, value: string | boolean) => {
    setState((current) => ({
      ...current,
      userPreferences: {
        preferences: current.userPreferences.preferences.map((item) =>
          item.id === id ? { ...item, value } : item
        )
      }
    }));
  };

  const resetGroup = (key: SettingsGroupKey) => {
    setState((current) => ({ ...current, [key]: defaults[key] }));
  };

  const resetAll = () => {
    setState(defaults);
  };

  const openGroup = (key: SettingsGroupKey) => setSelectedGroup(key);
  const closeGroup = () => setSelectedGroup(null);

  const selectedMeta = selectedGroup ? (groups.find((group) => group.id === selectedGroup) ?? null) : null;

  return {
    state,
    kpis,
    groups,
    changedGroups,
    selectedGroup,
    selectedMeta,
    openGroup,
    closeGroup,
    updateAppearance,
    updateLocalization,
    updateDataRefresh,
    toggleNotification,
    toggleFlag,
    updatePreference,
    resetGroup,
    resetAll,
    changedCount
  };
}
