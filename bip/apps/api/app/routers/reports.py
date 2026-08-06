from datetime import datetime
from typing import Annotated, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse

from app.dependencies.services import get_report_service
from app.models.report import ExportFormat, ReportDocument, ReportFilters, ReportType
from app.schemas.common import SuccessEnvelope
from app.schemas.filters import FilterParams
from app.schemas.pagination import PageQuery, PaginatedResponse
from app.services.report import ReportService
from app.models.domain import ReportSummary

router = APIRouter(prefix="/reports", tags=["reports"])

_REPORT_TYPES = {report_type.value: report_type for report_type in ReportType}


@router.get("", response_model=SuccessEnvelope[PaginatedResponse[ReportSummary]], summary="List reports")
async def list_reports(
    filters: Annotated[FilterParams, Depends()],
    page: Annotated[PageQuery, Depends()],
    service: ReportService = Depends(get_report_service),
) -> SuccessEnvelope[PaginatedResponse[ReportSummary]]:
    """List generated reports with optional filtering."""
    report_filters = ReportFilters.from_filter_params(filters)
    reports = await service.list_reports(report_filters)

    page_obj = page or PageQuery(page=1, page_size=20)
    start = (page_obj.page - 1) * page_obj.page_size
    end = start + page_obj.page_size

    return SuccessEnvelope.ok(
        PaginatedResponse(items=reports[start:end], total=len(reports),
                          page=page_obj.page, page_size=page_obj.page_size)
    )


@router.get("/{report_id}", response_model=SuccessEnvelope[ReportDocument], summary="Get report document")
async def get_report(
    report_id: str,
    service: ReportService = Depends(get_report_service),
) -> SuccessEnvelope[ReportDocument]:
    """Get a generated report document."""
    document = await service.get_report_document(report_id)
    if document is None:
        raise HTTPException(status_code=404, detail="Report document not found")
    return SuccessEnvelope.ok(document)


@router.post("/generate", response_model=SuccessEnvelope[ReportDocument], summary="Generate report")
async def generate_report(
    report_type: str = Query(..., description="Report type"),
    date_from: Optional[str] = Query(None, description="Start date"),
    date_to: Optional[str] = Query(None, description="End date"),
    machines: Optional[List[str]] = Query(None, description="Machine IDs"),
    rings: Optional[List[str]] = Query(None, description="Ring IDs"),
    products: Optional[List[str]] = Query(None, description="Product filters"),
    quality_statuses: Optional[List[str]] = Query(None, description="Quality status filters"),
    timeline_events: Optional[List[str]] = Query(None, description="Timeline event type filters"),
    service: ReportService = Depends(get_report_service),
) -> SuccessEnvelope[ReportDocument]:
    """Generate a new report."""
    if report_type not in _REPORT_TYPES:
        raise HTTPException(status_code=400, detail=f"Invalid report type: {report_type}")

    try:
        from_date = datetime.fromisoformat(date_from) if date_from else None
        to_date = datetime.fromisoformat(date_to) if date_to else None
    except ValueError:
        raise HTTPException(status_code=400, detail="date_from and date_to must be ISO-8601 timestamps")

    filters = ReportFilters(
        date_from=from_date,
        date_to=to_date,
        machines=machines or [],
        rings=rings or [],
        products=products or [],
        quality_statuses=quality_statuses or [],
        timeline_events=timeline_events or [],
        report_type=_REPORT_TYPES[report_type],
    )

    document = await service.generate_report(filters.report_type, filters, "user")
    return SuccessEnvelope.ok(document)


@router.get("/download/{report_id}", summary="Download report")
async def download_report(
    report_id: str,
    format: str = Query("csv", description="Export format"),
    service: ReportService = Depends(get_report_service),
) -> StreamingResponse:
    """Download a report in the specified format."""
    try:
        format_enum = ExportFormat(format.lower())
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid export format: {format}")

    file_data = await service.download_report(report_id, format_enum, "user")

    if format_enum == ExportFormat.CSV:
        media_type = "text/csv; charset=utf-8"
    else:
        media_type = format_enum.media_type
    filename = f"report_{report_id}.{format_enum.value}"

    return StreamingResponse(
        iter([file_data]),
        media_type=media_type,
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )