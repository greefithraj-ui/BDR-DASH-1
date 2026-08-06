import asyncpg
from fastapi import Depends

from app.config.settings import get_settings
from app.dependencies.database import get_db_connection
from app.repositories.administration import AdministrationRepository
from app.repositories.analytics import AnalyticsRepository
from app.repositories.health import HealthRepository
from app.repositories.machines import MachinesRepository
from app.repositories.metrics import MetricsRepository
from app.repositories.performance import PerformanceRepository
from app.repositories.prediction import PredictionRepository
from app.repositories.quality import QualityRepository
from app.repositories.rings import RingsRepository
from app.repositories.settings import SettingsRepository
from app.repositories.system import SystemRepository
from app.repositories.timeline import TimelineRepository
from app.services.administration import AdministrationService
from app.services.analytics import AnalyticsService
from app.services.health import HealthService
from app.services.machines import MachinesService
from app.services.metrics import MetricsService
from app.services.performance import PerformanceService
from app.services.prediction import PredictionService
from app.services.quality import QualityService
from app.services.rings import RingsService
from app.services.settings import SettingsService
from app.services.system import SystemService
from app.services.timeline import TimelineService
from app.services.report import ReportService
from app.report_generators import ReportGeneratorRegistry
from app.exporters import ExporterRegistry
from app.storage.report_store import ReportStore


async def get_health_service(
    conn: asyncpg.Connection = Depends(get_db_connection),
) -> HealthService:
    return HealthService(HealthRepository(conn), get_settings())


async def get_machines_service(
    conn: asyncpg.Connection = Depends(get_db_connection),
) -> MachinesService:
    return MachinesService(MachinesRepository(conn), get_settings())


async def get_rings_service(
    conn: asyncpg.Connection = Depends(get_db_connection),
) -> RingsService:
    return RingsService(RingsRepository(conn))


async def get_report_service(
    conn: asyncpg.Connection = Depends(get_db_connection),
) -> ReportService:
    """Report generation service wired to the read-only repositories and the
    filesystem report store (no database writes)."""
    settings = get_settings()
    return ReportService(
        metrics=MetricsRepository(conn),
        machines=MachinesRepository(conn),
        rings=RingsRepository(conn),
        timeline=TimelineRepository(conn),
        quality=QualityRepository(conn),
        analytics=AnalyticsRepository(conn),
        performance=PerformanceRepository(conn),
        health=HealthRepository(conn),
        settings=settings,
        store=ReportStore(settings.report_storage_dir),
        generators=ReportGeneratorRegistry.create_default_registry(),
        exporters=ExporterRegistry.create_default_registry(),
    )


async def get_analytics_service(
    conn: asyncpg.Connection = Depends(get_db_connection),
) -> AnalyticsService:
    return AnalyticsService(AnalyticsRepository(conn), get_settings())


async def get_timeline_service(
    conn: asyncpg.Connection = Depends(get_db_connection),
) -> TimelineService:
    return TimelineService(TimelineRepository(conn))


def get_prediction_service() -> PredictionService:
    return PredictionService(PredictionRepository())


async def get_quality_service(
    conn: asyncpg.Connection = Depends(get_db_connection),
) -> QualityService:
    return QualityService(QualityRepository(conn), get_settings())


async def get_performance_service(
    conn: asyncpg.Connection = Depends(get_db_connection),
) -> PerformanceService:
    return PerformanceService(PerformanceRepository(conn), get_settings())


async def get_administration_service(
    conn: asyncpg.Connection = Depends(get_db_connection),
) -> AdministrationService:
    return AdministrationService(AdministrationRepository(conn), get_settings())


def get_settings_service() -> SettingsService:
    return SettingsService(SettingsRepository(get_settings()))


def get_system_service() -> SystemService:
    return SystemService(SystemRepository(get_settings().api_version))


async def get_metrics_service(
    conn: asyncpg.Connection = Depends(get_db_connection),
) -> MetricsService:
    return MetricsService(MetricsRepository(conn), get_settings())
