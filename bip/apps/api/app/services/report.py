from typing import Any, List, Optional

from app.config.settings import Settings
from app.core.exceptions import ResourceNotFoundError
from app.exporters import ExportOptions, ExporterRegistry
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
from app.models.report import (
    ExportFormat,
    ReportDocument,
    ReportFilters,
    ReportGenerationContext,
    ReportType,
)
from app.report_generators import ReportGeneratorRegistry
from app.repositories.analytics import AnalyticsRepository
from app.repositories.health import HealthRepository
from app.repositories.machines import MachinesRepository
from app.repositories.metrics import MetricsRepository
from app.repositories.performance import PerformanceRepository
from app.repositories.quality import QualityRepository
from app.repositories.rings import RingsRepository
from app.repositories.timeline import TimelineRepository
from app.storage.report_store import ReportStore
from app.utils.time import utc_now

_CONTEXT_LIMIT = 1000


class ReportService:
    """Report generation and management over the read-only platform data.

    The service owns the orchestration flow:
    ``ReportService -> Repository (SQL) -> ReportGenerationContext -> Generator``.

    Generators never touch SQL and the service never calls back into the API;
    the context is a single in-memory snapshot fetched through the existing
    read-only repositories. Generated documents are cached in a filesystem
    :class:`ReportStore`; the database is never written to.
    """

    def __init__(
        self,
        metrics: MetricsRepository,
        machines: MachinesRepository,
        rings: RingsRepository,
        timeline: TimelineRepository,
        quality: QualityRepository,
        analytics: AnalyticsRepository,
        performance: PerformanceRepository,
        health: HealthRepository,
        settings: Settings,
        store: ReportStore,
        generators: ReportGeneratorRegistry,
        exporters: ExporterRegistry,
    ) -> None:
        self._metrics = metrics
        self._machines = machines
        self._rings = rings
        self._timeline = timeline
        self._quality = quality
        self._analytics = analytics
        self._performance = performance
        self._health = health
        self._settings = settings
        self._store = store
        self._generators = generators
        self._exporters = exporters

    async def generate_report(
        self, report_type: ReportType, filters: ReportFilters, generated_by: str
    ) -> ReportDocument:
        """Generate a report document from a live data snapshot and store it."""
        generator = self._generators.get_generator(report_type)
        context = await self._build_context(filters)
        document = await generator.generate(context, generated_by)
        self._store.save(document)
        return document

    async def get_report_document(self, report_id: str) -> Optional[ReportDocument]:
        """Retrieve a stored report document (or ``None``)."""
        return self._store.get(report_id)

    async def get_report(self, report_id: str) -> Optional[ReportSummary]:
        """Retrieve a stored report summary (or ``None``)."""
        return self._store.get_summary(report_id)

    async def download_report(
        self, report_id: str, format: ExportFormat, generated_by: str
    ) -> bytes:
        """Export a stored report to the requested format as bytes."""
        document = self._store.get(report_id)
        if document is None:
            raise ResourceNotFoundError("report", report_id)
        exporter = self._exporters.get_exporter(format)
        options = ExportOptions(
            filename=f"report_{report_id}",
            include_charts=True,
            include_metadata=True,
        )
        return await exporter.export(document, options)

    async def list_reports(self, filters: ReportFilters) -> List[ReportSummary]:
        """List stored report summaries, narrowed by the filter time range."""
        return self._store.list_summaries(
            date_from=filters.date_from,
            date_to=filters.date_to,
        )

    # ------------------------------------------------------------------
    # Context assembly (Repository -> domain models, one snapshot per run)
    # ------------------------------------------------------------------

    async def _build_context(self, filters: ReportFilters) -> ReportGenerationContext:
        freshness_window = self._settings.freshness_window_seconds

        metrics = [
            MetricSummary(**row)
            for row in await self._metrics.metrics(freshness_window)
        ]
        machines = await self._fetch_machines(filters, freshness_window)
        rings = [
            self._to_ring(row)
            for row in (
                await self._rings.list_rings(
                    search=None,
                    status=None,
                    sort_by="ring_id",
                    sort_dir="asc",
                    date_from=filters.date_from,
                    date_to=filters.date_to,
                    limit=_CONTEXT_LIMIT,
                    offset=0,
                )
            )[0]
        ]
        timeline_events = [
            TimelineEvent(**row)
            for row in (
                await self._timeline.list_events(
                    search=None,
                    status=None,
                    sort_by="timestamp",
                    sort_dir="desc",
                    date_from=filters.date_from,
                    date_to=filters.date_to,
                    limit=_CONTEXT_LIMIT,
                    offset=0,
                )
            )[0]
        ]
        quality_data = [
            QualitySummary(**row)
            for row in await self._quality.summary(freshness_window)
        ]
        performance_data = [
            PerformanceSummary(**row)
            for row in await self._performance.summary(freshness_window)
        ]
        analytics_data = [
            AnalyticsSummary(**row)
            for row in await self._analytics.summary(freshness_window)
        ]
        health = await self._build_health()
        reports = self._store.list_summaries()

        return ReportGenerationContext(
            metrics=metrics,
            machines=machines,
            rings=rings,
            timeline_events=timeline_events,
            quality_data=quality_data,
            performance_data=performance_data,
            analytics_data=analytics_data,
            reports=reports,
            health=health,
            filters=filters,
        )

    async def _fetch_machines(
        self, filters: ReportFilters, freshness_window: int
    ) -> List[Machine]:
        rows, _ = await self._machines.list_machines(
            freshness_window=freshness_window,
            search=None,
            status=None,
            sort_by="machine_name",
            sort_dir="asc",
            date_from=filters.date_from,
            date_to=filters.date_to,
            limit=_CONTEXT_LIMIT,
            offset=0,
        )
        stats = {row["machine_name"]: row for row in await self._machines.fleet_stats()}
        machines: List[Machine] = []
        for row in rows:
            stat = stats.get(row["machine_name"], {})
            is_online = bool(row["is_online"])
            failed = int(stat.get("failed_count") or 0)
            slot_count = int(stat.get("slot_count") or 0)
            if not is_online:
                status = "Offline"
            elif failed > 0:
                status = "Warning"
            else:
                status = "Healthy"
            machines.append(
                Machine(
                    id=row["machine_name"],
                    name=row["machine_name"],
                    status=status,
                    connection="Online" if is_online else "Offline",
                    health_score=self._health_score(is_online, failed, slot_count),
                    firmware=stat.get("dominant_firmware") or "",
                    last_seen=row["last_seen_at"],
                )
            )
        return machines

    async def _build_health(self) -> HealthResponse:
        snapshot = await self._health.get_health_data()
        return HealthResponse(
            status="ok",
            version=self._settings.api_version,
            service=snapshot["service"],
            timestamp=utc_now(),
            environment=self._settings.environment,
        )

    @staticmethod
    def _to_ring(row: dict[str, Any]) -> Ring:
        return Ring(
            id=row["ring_id"],
            name=row["ring_name"] or row["ring_id"],
            status=row["status"],
            capacity_mwh=float(row["slot_count"]),
            installed_at=row["installed_at"],
        )

    @staticmethod
    def _health_score(is_online: bool, failed: int, slot_count: int) -> float:
        score = 100.0 if is_online else 40.0
        score -= failed * 4.0
        return max(0.0, min(100.0, round(score, 1)))
