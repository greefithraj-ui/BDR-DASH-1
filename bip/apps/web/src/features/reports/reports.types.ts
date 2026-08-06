export type ReportTone = "neutral" | "success" | "warning" | "danger" | "info";

export type ReportStatus = "Scheduled" | "Ready" | "Draft" | "Failed" | "Paused";

export type ReportFrequency = "Daily" | "Weekly" | "Monthly" | "On Demand" | "Shift";

export type ReportCategory = "Operations" | "Executive" | "Machine" | "Quality" | "Lifecycle" | "Failure" | "Intelligence" | "Product";

export type ReportRunStatus = "Success" | "Failed" | "Running";

export type ReportRun = {
  id: string;
  date: string;
  status: ReportRunStatus;
  durationSeconds: number;
  pages: number;
};

export type ReportPreviewColumn = {
  id: string;
  label: string;
};

export type ReportPreviewRow = {
  id: string;
  values: string[];
};

export type ReportPreviewTable = {
  id: string;
  title: string;
  columns: ReportPreviewColumn[];
  rows: ReportPreviewRow[];
};

export type Report = {
  id: string;
  title: string;
  description: string;
  category: ReportCategory;
  owner: string;
  createdDate: string;
  lastRun: string;
  nextScheduledRun: string;
  status: ReportStatus;
  statusTone: ReportTone;
  frequency: ReportFrequency;
  estimatedDurationSeconds: number;
  pages: number;
  schedule: {
    time: string;
    days: string;
    recipients: string[];
  };
  previewTables: ReportPreviewTable[];
  history: ReportRun[];
};

export type ReportHistoryEntry = {
  id: string;
  reportId: string;
  reportTitle: string;
  date: string;
  status: ReportRunStatus;
  durationSeconds: number;
  pages: number;
};

export type ReportsFilters = {
  search: string;
  category: string;
  status: string;
  owner: string;
  frequency: string;
  dateFrom: string;
  dateTo: string;
};

export type ReportsOptions = {
  categories: string[];
  statuses: string[];
  owners: string[];
  frequencies: string[];
};

export type ReportsKpi = {
  id: string;
  label: string;
  value: string;
  delta: string;
  deltaTone: ReportTone;
};
