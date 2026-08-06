export type SettingStatusTone = "neutral" | "success" | "warning" | "danger" | "info";

export type ThemeName = "bip-light" | "bip-dark" | "system";

export type AccentColor = "navy" | "cyan" | "green" | "amber" | "violet";

export type Density = "Comfortable" | "Compact";

export type LanguageName = "English" | "Deutsch" | "Français" | "Español" | "日本語";

export type TimeZoneName =
  | "(GMT+01:00) Central European Time"
  | "(GMT+00:00) UTC"
  | "(GMT-05:00) Eastern Time"
  | "(GMT-08:00) Pacific Time";

export type DateFormatName = "YYYY-MM-DD" | "DD/MM/YYYY" | "MM/DD/YYYY" | "DD.MM.YYYY";

export type RefreshIntervalValue = "Off" | "15s" | "30s" | "1m" | "5m" | "15m";

export type NotificationChannel = "Email" | "Push" | "In-app";

export type NotificationPreference = {
  id: string;
  label: string;
  description: string;
  enabled: boolean;
  channel: NotificationChannel;
};

export type FeatureFlag = {
  id: string;
  label: string;
  description: string;
  enabled: boolean;
  group: string;
};

export type UserPreference = {
  id: string;
  label: string;
  description: string;
  value: string | boolean;
  options?: string[];
};

export type AppearanceSettings = {
  theme: ThemeName;
  accentColor: AccentColor;
  density: Density;
  animations: boolean;
};

export type NotificationSettings = {
  preferences: NotificationPreference[];
};

export type LocalizationSettings = {
  language: LanguageName;
  timeZone: TimeZoneName;
  dateFormat: DateFormatName;
};

export type DataRefreshSettings = {
  refreshInterval: RefreshIntervalValue;
  autoRefresh: boolean;
  cacheEnabled: boolean;
};

export type FeatureFlagsSettings = {
  flags: FeatureFlag[];
};

export type UserPreferencesSettings = {
  preferences: UserPreference[];
};

export type SettingsState = {
  appearance: AppearanceSettings;
  notifications: NotificationSettings;
  localization: LocalizationSettings;
  dataRefresh: DataRefreshSettings;
  featureFlags: FeatureFlagsSettings;
  userPreferences: UserPreferencesSettings;
};

export type SettingsGroupKey = keyof SettingsState;

export type SettingsGroupMeta = {
  id: SettingsGroupKey;
  label: string;
  description: string;
};

export type SettingsKpi = {
  id: string;
  label: string;
  value: string;
  delta: string;
  deltaTone: SettingStatusTone;
};
