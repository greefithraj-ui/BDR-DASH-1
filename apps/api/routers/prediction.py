from fastapi import APIRouter, Depends
from apps.api.models.response import SuccessResponse
from apps.api.dependencies.providers import get_db_session
from apps.api.services.prediction import PredictionService
from apps.api.repositories.prediction import PredictionRepository
import asyncpg

router = APIRouter(tags=["Prediction"])

@router.get("/prediction", response_model=SuccessResponse[list])
async def get_prediction(db: asyncpg.Connection = Depends(get_db_session)):
    repo = PredictionRepository(db)
    service = PredictionService(repo)
    data = await service.get_data()
    return SuccessResponse(data=data)
