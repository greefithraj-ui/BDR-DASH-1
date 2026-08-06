from typing import Annotated

from fastapi import APIRouter, Depends

from app.dependencies.services import get_prediction_service
from app.models.domain import PredictionModel
from app.schemas.common import SuccessEnvelope
from app.schemas.filters import FilterParams
from app.schemas.pagination import PageQuery, PaginatedResponse
from app.services.prediction import PredictionService

router = APIRouter(prefix="/prediction", tags=["prediction"])


@router.get("/models", response_model=SuccessEnvelope[PaginatedResponse[PredictionModel]], summary="List prediction models")
async def list_models(
    filters: Annotated[FilterParams, Depends()],
    page: Annotated[PageQuery, Depends()],
    service: PredictionService = Depends(get_prediction_service),
) -> SuccessEnvelope[PaginatedResponse[PredictionModel]]:
    return await service.list_models(filters, page)


@router.get("/models/{model_id}", response_model=SuccessEnvelope[PredictionModel], summary="Get one prediction model")
async def get_model(
    model_id: str,
    service: PredictionService = Depends(get_prediction_service),
) -> SuccessEnvelope[PredictionModel]:
    return await service.get_by_id(model_id)
