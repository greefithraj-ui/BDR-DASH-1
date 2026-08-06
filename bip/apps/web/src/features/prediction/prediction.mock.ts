import type { PredictionModel, PredictionKpi } from "./prediction.types";

export function getMockModels(): PredictionModel[] {
  return [
    { id: "m1", name: "Predictive Maintenance", description: "Predicts machine failure 24h in advance.", status: "Ready", version: "2.1.0", accuracy: 0.94, lastTrained: "2026-07-20", nextTraining: "2026-08-20", coverage: 0.85, datasetSize: "1.2 TB", healthScore: 95, owner: "Fleet Team" },
    { id: "m2", name: "Remaining Useful Life", description: "Estimates remaining life of components.", status: "Ready", version: "1.5.0", accuracy: 0.89, lastTrained: "2026-07-15", nextTraining: "2026-08-15", coverage: 0.78, datasetSize: "500 GB", healthScore: 92, owner: "Data Science" },
    { id: "m3", name: "Failure Probability", description: "Probability of failure within next hour.", status: "Training", version: "3.0.0-beta", accuracy: 0.0, lastTrained: "2026-08-01", nextTraining: "2026-08-05", coverage: 0.92, datasetSize: "2.5 TB", healthScore: 88, owner: "Reliability" },
    { id: "m4", name: "Machine Health Forecast", description: "General health outlook for the next week.", status: "Prototype", version: "0.1.0", accuracy: 0.75, lastTrained: "2026-07-30", nextTraining: "2026-08-30", coverage: 0.60, datasetSize: "100 GB", healthScore: 75, owner: "R&D" },
    { id: "m5", name: "Product Reliability", description: "Reliability score of output products.", status: "Planned", version: "0.0.1", accuracy: 0.0, lastTrained: "N/A", nextTraining: "2026-09-01", coverage: 0.0, datasetSize: "0 GB", healthScore: 0, owner: "Quality" },
    { id: "m6", name: "Capacity Degradation", description: "Tracks degradation of machine capacity.", status: "Ready", version: "1.2.4", accuracy: 0.91, lastTrained: "2026-07-10", nextTraining: "2026-08-10", coverage: 0.88, datasetSize: "800 GB", healthScore: 94, owner: "Operations" }
  ];
}

export function getMockKpis(): PredictionKpi[] {
  return [
    { id: "kpi-models", label: "Models", value: "6", helper: "Across 4 teams" },
    { id: "kpi-ready", label: "Ready Models", value: "3", helper: "Deployable" },
    { id: "kpi-training", label: "Training Models", value: "1", helper: "In progress" },
    { id: "kpi-coverage", label: "Coverage", value: "74%", helper: "Fleet-wide" },
    { id: "kpi-accuracy", label: "Average Accuracy", value: "88%", helper: "Across ready models" }
  ];
}
