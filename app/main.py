from fastapi import FastAPI
from contextlib import asynccontextmanager

from app.routes.photoscan import router as photoscan_router
from app.routes.bucket_loader import router as bucket_loader_router

# Регаем все три модели метаданных в общеем реестре
from app.db_models.prisoners_etalons import PrisonerEtalon
from app.db_models.attendance_sessions import AttendanceSession
from app.db_models.attendance_logs import AttendanceLog

from app.core.cv_engine import init_cv_engine, close_cv_engine


@asynccontextmanager
async def global_lifespan(app: FastAPI):
    await init_cv_engine()
    
    yield

    await close_cv_engine()


app = FastAPI(lifespan=global_lifespan)


app.include_router(photoscan_router)
app.include_router(bucket_loader_router)