from fastapi import FastAPI
from contextlib import asynccontextmanager

from app.routes.photoscan import router as photoscan_router
from app.routes.bucket_loader import router as bucket_loader_router
from app.routes.units import router as units_router

# Регаем все три модели метаданных в общеем реестре
# from app.db_models.prisoners_etalons import PrisonerEtalon
# from app.db_models.attendance_sessions import AttendanceSession
# from app.db_models.attendance_logs import AttendanceLog

from app.core.cv_engine import init_cv_engine, close_cv_engine
from app.core.config import settings
from app.dependencies.minio import get_minio_client
from app.core.database import init_db


@asynccontextmanager
async def global_lifespan(app: FastAPI):
    await init_cv_engine()
    await init_db()
    minio_client = get_minio_client()
    await minio_client.init_buckets(
        [settings.BUILDINGS_BUCKET, settings.INFERENCE_BUCKET]
    )
    
    yield

    await close_cv_engine()


app = FastAPI(lifespan=global_lifespan)


app.include_router(photoscan_router)
app.include_router(bucket_loader_router)
app.include_router(units_router)