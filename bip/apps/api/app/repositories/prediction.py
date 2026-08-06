from app.models.domain import PredictionModel
from app.repositories.base import InMemoryListRepository

PREDICTION_ROWS = (
    PredictionModel(
        id="PRD-01",
        name="Predictive Maintenance",
        status="Ready",
        version="2.1.0",
        accuracy=0.94,
        coverage=0.85,
        owner="Fleet Team",
    ),
    PredictionModel(
        id="PRD-02",
        name="Remaining Useful Life",
        status="Ready",
        version="1.5.0",
        accuracy=0.89,
        coverage=0.78,
        owner="Data Science",
    ),
    PredictionModel(
        id="PRD-03",
        name="Failure Probability",
        status="Training",
        version="3.0.0-beta",
        accuracy=0.0,
        coverage=0.92,
        owner="Reliability",
    ),
    PredictionModel(
        id="PRD-04",
        name="Machine Health Forecast",
        status="Prototype",
        version="0.1.0",
        accuracy=0.75,
        coverage=0.60,
        owner="R&D",
    ),
    PredictionModel(
        id="PRD-05",
        name="Product Reliability",
        status="Planned",
        version="0.0.1",
        accuracy=0.0,
        coverage=0.0,
        owner="Quality",
    ),
    PredictionModel(
        id="PRD-06",
        name="Capacity Degradation",
        status="Ready",
        version="1.2.4",
        accuracy=0.91,
        coverage=0.88,
        owner="Operations",
    ),
)


class PredictionRepository(InMemoryListRepository[PredictionModel]):
    def __init__(self) -> None:
        super().__init__(PREDICTION_ROWS)
