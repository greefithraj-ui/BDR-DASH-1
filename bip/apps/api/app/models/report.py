from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field

from app.models.domain import (
    AnalyticsSummary,
    Machine,
    MetricSummary,
    PerformanceSummary,
    QualitySummary,
    ReportSummary,
    Ring,
    TimelineEvent,
)
from app.models.health import HealthResponse


class ReportType(str, Enum):
    EXECUTIVE_SUMMARY = "Executive Summary"
    MACHINE_PERFORMANCE = "Machine Performance"
    BATTERY_SUMMARY = "Battery Summary"
    BATTERY_LIFECYCLE = "Battery Lifecycle"
    QUALITY_SUMMARY = "Quality Summary"
    ANALYTICS_SUMMARY = "Analytics Summary"
    TIMELINE_REPORT = "Timeline Report"
    OPERATIONS_SUMMARY = "Operations Summary"
    SYSTEM_HEALTH = "System Health"
    COLLECTOR_STATUS = "Collector Status"


class ExportFormat(str, Enum):
    CSV = "csv"
    XLSX = "xlsx"
    PDF = "pdf"

    @property
    def media_type(self) -> str:
        mapping = {
            ExportFormat.CSV: "text/csv; charset=utf-8",
            ExportFormat.XLSX: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            ExportFormat.PDF: "application/pdf",
        }
        return mapping[self]


class TimeRange(BaseModel):
    model_config = ConfigDict(frozen=True)

    start: datetime
    end: datetime
    timezone: str = "UTC"


class ReportFilters(BaseModel):
    model_config = ConfigDict(frozen=True)

    date_from: Optional[datetime] = None
    date_to: Optional[datetime] = None
    machines: List[str] = Field(default_factory=list)
    rings: List[str] = Field(default_factory=list)
    products: List[str] = Field(default_factory=list)
    quality_statuses: List[str] = Field(default_factory=list)
    timeline_events: List[str] = Field(default_factory=list)
    report_type: Optional[ReportType] = None

    @classmethod
    def from_filter_params(cls, params: Any) -> "ReportFilters":
        """Build report filters from a standard FilterParams query object."""
        return cls(
            date_from=getattr(params, "date_from", None),
            date_to=getattr(params, "date_to", None),
        )

    def summary(self) -> str:
        """Human-readable description of the filters used for a report run."""
        parts: List[str] = []
        if self.date_from:
            parts.append(f"from {self.date_from.isoformat()}")
        if self.date_to:
            parts.append(f"to {self.date_to.isoformat()}")
        if self.machines:
            parts.append(f"machines: {', '.join(sorted(self.machines))}")
        if self.rings:
            parts.append(f"rings: {', '.join(sorted(self.rings))}")
        if self.products:
            parts.append(f"products: {', '.join(sorted(self.products))}")
        if self.quality_statuses:
            parts.append(f"quality: {', '.join(sorted(self.quality_statuses))}")
        if self.timeline_events:
            parts.append(f"events: {', '.join(sorted(self.timeline_events))}")
        return "No filters" if not parts else ", ".join(parts)


class ReportSectionType(str, Enum):
    SUMMARY = "summary"
    TABLE = "table"
    CHART = "chart"
    METRICS = "metrics"


class ReportSection(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: str
    type: ReportSectionType
    title: str
    data: Dict[str, Any]
    config: Dict[str, Any] = Field(default_factory=dict)


class ReportMetadata(BaseModel):
    model_config = ConfigDict(frozen=True)

    generated_by: str
    version: str = "1.0"
    template_version: str = "Phase 20"


class ReportDocument(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: str
    title: str
    report_type: ReportType
    generated_at: datetime
    time_range: TimeRange
    filters: ReportFilters
    sections: List[ReportSection]
    metadata: ReportMetadata

    def to_summary(self) -> ReportSummary:
        return ReportSummary(
            id=self.id,
            title=self.title,
            kind=self.report_type.value,
            status="Ready",
            generated_at=self.generated_at,
        )


class ReportGenerationContext(BaseModel):
    """Live data snapshot handed to report generators.

    Built once by :class:`ReportService` from the existing repositories and
    shared by every generator so that a single report run issues each query at
    most once (no N+1, no duplicate queries).
    """

    model_config = ConfigDict(frozen=True)

    metrics: List[MetricSummary] = Field(default_factory=list)
    machines: List[Machine] = Field(default_factory=list)
    rings: List[Ring] = Field(default_factory=list)
    timeline_events: List[TimelineEvent] = Field(default_factory=list)
    quality_data: List[QualitySummary] = Field(default_factory=list)
    performance_data: List[PerformanceSummary] = Field(default_factory=list)
    analytics_data: List[AnalyticsSummary] = Field(default_factory=list)
    reports: List[ReportSummary] = Field(default_factory=list)
    health: Optional[HealthResponse] = None
    filters: ReportFilters = Field(default_factory=ReportFilters)