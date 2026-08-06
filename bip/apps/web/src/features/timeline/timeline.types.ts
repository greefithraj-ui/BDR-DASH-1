export type TimelineTone = "neutral" | "success" | "warning" | "danger" | "info";

export type TimelineEventType =
  | "Observed"
  | "Tracking"
  | "Pending Removal"
  | "Finalized"
  | "Passed"
  | "Failed"
  | "Replacement"
  | "Machine Offline"
  | "Machine Online"
  | "Firmware Changed";

export type TimelineGroupBy = "date" | "machine" | "battery";

export type TimelineMetadataItem = {
  label: string;
  value: string;
};

export type TimelineEvent = {
  id: string;
  timestamp: string;
  date: string;
  type: TimelineEventType;
  batterySerialNumber: string;
  machineId: string;
  slot: string;
  reason: string;
  previousState?: string;
  currentState?: string;
  metadata: TimelineMetadataItem[];
  tone: TimelineTone;
};

export type TimelineFilters = {
  search: string;
  machine: string;
  battery: string;
  eventType: string;
  dateFrom: string;
  dateTo: string;
};

export type TimelineOptions = {
  machines: string[];
  batteries: string[];
  eventTypes: TimelineEventType[];
};

export type TimelineSort = {
  direction: "asc" | "desc";
};

export type TimelineGroup = {
  key: string;
  label: string;
  events: TimelineEvent[];
};
