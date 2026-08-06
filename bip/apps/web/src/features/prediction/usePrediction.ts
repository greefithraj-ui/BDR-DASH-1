import { useMemo, useState } from "react";
import { getMockKpis, getMockModels } from "./prediction.mock";
import type { PredictionFilters } from "./prediction.types";

export function usePrediction() {
  const models = useMemo(() => getMockModels(), []);
  const kpis = useMemo(() => getMockKpis(), []);
  const [filters, setFilters] = useState<PredictionFilters>({ search: "", status: "All", owner: "All" });
  const [selectedModelId, setSelectedModelId] = useState<string | null>(null);

  const filteredModels = useMemo(() => {
    return models.filter((model) => {
      const matchesSearch =
        model.name.toLowerCase().includes(filters.search.toLowerCase()) ||
        model.description.toLowerCase().includes(filters.search.toLowerCase());
      const matchesStatus = filters.status === "All" || model.status === filters.status;
      const matchesOwner = filters.owner === "All" || model.owner === filters.owner;
      return matchesSearch && matchesStatus && matchesOwner;
    });
  }, [models, filters]);

  const selectedModel = useMemo(() => {
    return selectedModelId ? models.find((m) => m.id === selectedModelId) || null : null;
  }, [models, selectedModelId]);

  const updateFilters = (patch: Partial<PredictionFilters>) => {
    setFilters((prev) => ({ ...prev, ...patch }));
  };

  const clearFilters = () => {
    setFilters({ search: "", status: "All", owner: "All" });
  };

  return {
    models,
    kpis,
    filteredModels,
    filters,
    selectedModel,
    updateFilters,
    clearFilters,
    setSelectedModelId,
  };
}
