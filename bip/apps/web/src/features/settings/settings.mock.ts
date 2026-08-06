import type {
  AppearanceSettings,
  DataRefreshSettings,
  FeatureFlagsSettings,
  LocalizationSettings,
  NotificationSettings,
  SettingsGroupMeta,
  SettingsState,
  UserPreferencesSettings
} from "./settings.types";

const SETTINGS_GROUPS: SettingsGroupMeta[] = [
  { id: "appearance", label: "Appearance", description: "Theme, accent color, density, and animations." },
  { id: "notifications", label: "Notifications", description: "Alert channels and notification preferences." },
  { id: "localization", label: "Localization", description: "Language, time zone, and date format." },
  { id: "dataRefresh", label: "Data Refresh", description: "Dashboard refresh interval and caching." },
  { id: "featureFlags", label: "Feature Flags", description: "Preview features and capabilities." },
  { id: "userPreferences", label: "User Preferences", description: "Profile fields and personal defaults." }
];

export function getSettingGroups(): SettingsGroupMeta[] {
  return SETTINGS_GROUPS;
}

export function buildAppearance(): AppearanceSettings {
  return {
    theme: "bip-dark",
    accentColor: "navy",
    density: "Comfortable",
    animations: true
  };
}

export function buildNotifications(): NotificationSettings {
  return {
    preferences: [
      { id: "notify-machine-alerts", label: "Machine Alerts", description: "Alerts when a machine drops below its health threshold.", enabled: true, channel: "Push" },
      { id: "notify-quality", label: "Quality Thresholds", description: "Alerts when pass rate or yield crosses configured thresholds.", enabled: true, channel: "Email" },
      { id: "notify-reports", label: "Reports Ready", description: "Notification when a scheduled report finishes generating.", enabled: true, channel: "Email" },
      { id: "notify-collector", label: "Collector Offline", description: "Alerts when a collector stops sending heartbeats.", enabled: true, channel: "Push" },
      { id: "notify-digest", label: "Weekly Digest", description: "A weekly summary of fleet and quality highlights.", enabled: false, channel: "Email" },
      { id: "notify-product", label: "Product Announcements", description: "Updates about new platform features and releases.", enabled: false, channel: "In-app" }
    ]
  };
}

export function buildLocalization(): LocalizationSettings {
  return {
    language: "English",
    timeZone: "(GMT+01:00) Central European Time",
    dateFormat: "YYYY-MM-DD"
  };
}

export function buildDataRefresh(): DataRefreshSettings {
  return {
    refreshInterval: "30s",
    autoRefresh: true,
    cacheEnabled: true
  };
}

export function buildFeatureFlags(): FeatureFlagsSettings {
  return {
    flags: [
      { id: "flag-ai", label: "AI Assistant", description: "Expose the AI Intelligence Center conversation experience.", enabled: true, group: "Intelligence" },
      { id: "flag-predictive", label: "Predictive Maintenance", description: "Predictive maintenance recommendations on machine health.", enabled: true, group: "Intelligence" },
      { id: "flag-scheduling", label: "Reports Scheduling", description: "Schedule reports and delivery to recipients.", enabled: true, group: "Reports" },
      { id: "flag-dark", label: "Dark Mode", description: "Enable the dark theme option for all users.", enabled: true, group: "Appearance" },
      { id: "flag-chart-beta", label: "Beta Chart Library", description: "Preview the new chart container library.", enabled: false, group: "Analytics" },
      { id: "flag-export", label: "Export to Excel", description: "Allow exporting analytics tables to Excel.", enabled: false, group: "Reports" }
    ]
  };
}

export function buildUserPreferences(): UserPreferencesSettings {
  return {
    preferences: [
      { id: "profile-name", label: "Name", description: "Your display name across the platform.", value: "Jordan Reyes" },
      { id: "profile-role", label: "Role", description: "Your role used in audit logs and reports.", value: "Operations Manager" },
      { id: "profile-email", label: "Email", description: "Contact email for report and alert delivery.", value: "jordan@bip.local" },
      { id: "profile-dashboard", label: "Default Dashboard", description: "Landing view after sign-in.", value: "Executive", options: ["Executive", "Battery Intelligence", "Analytics", "Reports"] },
      { id: "profile-digest", label: "Weekly Digest", description: "Include you in the weekly digest distribution.", value: true },
      { id: "profile-time-format", label: "Time Format", description: "How timestamps are displayed.", value: "24-hour", options: ["12-hour", "24-hour"] }
    ]
  };
}

export function getDefaultSettings(): SettingsState {
  return {
    appearance: buildAppearance(),
    notifications: buildNotifications(),
    localization: buildLocalization(),
    dataRefresh: buildDataRefresh(),
    featureFlags: buildFeatureFlags(),
    userPreferences: buildUserPreferences()
  };
}
