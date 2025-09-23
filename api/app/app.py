from contextlib import asynccontextmanager

from fastapi import APIRouter, FastAPI, status
from fastapi.middleware.cors import CORSMiddleware

from app.common.utils import vars
from app.config import config, init_db, shutdown_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield
    await shutdown_db()


app = FastAPI(lifespan=lifespan)


app.add_middleware(
    CORSMiddleware,
    allow_origins=[config.web.url],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

for router in vars.load("app.routers:router", APIRouter):
    app.include_router(router)


@app.get("/", status_code=status.HTTP_200_OK)
def health_check():
    return {"status": "ok"}
