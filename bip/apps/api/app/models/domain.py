from datetime import datetime

from pydantic import BaseModel, ConfigDict


class Machine(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: str
    name: str
    status: str
    connection: str
    health_score: float
    firmware: str
    last_seen: datetime


class Ring(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: str
    name: str
    status: str
    capacity_mwh: float
    installed_at: datetime


class ReportSummary(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: str
    title: str
    kind: str
    status: str
    generated_at: datetime


class TimelineEvent(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: str
    timestamp: datetime
    type: str
    machine_id: str
    message: str


class PredictionModel(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: str
    name: str
    status: str
    version: str
    accuracy: float
    coverage: float
    owner: str


class QualitySummary(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: str
    metric: str
    value: float
    target: float
    status: str


class PerformanceSummary(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: str
    metric: str
    value: float
    unit: str
    status: str


class AnalyticsSummary(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: str
    key: str
    label: str
    value: float
    unit: str


class AdministrationOverview(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: str
    platform: str
    version: str
    environment: str
    uptime_seconds: int


class SettingsEntry(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: str
    key: str
    label: str
    value: str


class SystemInfo(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: str
    hostname: str
    python_version: str
    framework: str
    version: str


class MetricSummary(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: str
    name: str
    value: float
    unit: str
    status: str
