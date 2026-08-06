export type PredictionStatus = "Planned" | "Prototype" | "Training" | "Ready";

export type PredictionModel = {
  id: string;
  name: string;
  description: string;
  status: PredictionStatus;
  version: string;
  accuracy: number;
  lastTrained: string;
  nextTraining: string;
  coverage: number;
  datasetSize: string;
  healthScore: number;
  owner: string;
};

export type PredictionKpi = {
  id: string;
  label: string;
  value: string;
  helper: string;
};

export type PredictionFilters = {
  search: string;
  status: PredictionStatus | "All";
  owner: string;
};

export type PredictionState = {
  models: PredictionModel[];
  kpis: PredictionKpi[];
};
