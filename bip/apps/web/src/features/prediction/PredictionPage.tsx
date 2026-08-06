import { Badge, Card, MetricCard } from "../../components/design-system";
import { usePrediction } from "./usePrediction";
import "./prediction.css";

export function PredictionPage() {
  const { kpis, filteredModels, selectedModel, setSelectedModelId } = usePrediction();

  if (selectedModel) {
    return (
        <div className="prediction">
            <header className="prediction__hero">
                <button type="button" className="prediction__back" onClick={() => setSelectedModelId(null)}>← Back to List</button>
                <h1>{selectedModel.name}</h1>
                <Badge tone="info">{selectedModel.status}</Badge>
            </header>
            <Card>
                <div className="prediction__detail-grid">
                    <p><strong>Description:</strong> {selectedModel.description}</p>
                    <p><strong>Version:</strong> {selectedModel.version}</p>
                    <p><strong>Owner:</strong> {selectedModel.owner}</p>
                    <p><strong>Accuracy:</strong> {(selectedModel.accuracy * 100).toFixed(0)}%</p>
                </div>
            </Card>
        </div>
    );
  }

  return (
    <section className="prediction">
      <header className="prediction__hero">
        <div>
          <p className="prediction__eyebrow">Prediction Center</p>
          <h1>Prediction Models</h1>
        </div>
        <Badge tone="neutral">Mock Data</Badge>
      </header>

      <div className="prediction__kpi-row">
        {kpis.map((kpi) => (
          <MetricCard key={kpi.id} label={kpi.label} value={kpi.value} helper={kpi.helper} />
        ))}
      </div>

      <div className="prediction__model-list">
        {filteredModels.map((model) => (
          <Card key={model.id} className="prediction__model-card">
            <h3>{model.name}</h3>
            <p>{model.description}</p>
            <Badge tone={model.status === "Ready" ? "success" : "neutral"}>{model.status}</Badge>
            <button type="button" onClick={() => setSelectedModelId(model.id)}>View Details</button>
          </Card>
        ))}
      </div>
    </section>
  );
}
