import asyncio
from contextlib import asynccontextmanager

from fastapi import APIRouter, FastAPI, status
from fastapi.middleware.cors import CORSMiddleware

from utils import vars
from config import config, init_db, shutdown_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield
    await shutdown_db()


def _is_local_dev_env() -> bool:
    url = (config.api.url or "").lower()
    host = (config.api.host or "").lower()
    return "localhost" in url or "127.0.0.1" in url or host in {"localhost", "127.0.0.1"}


openapi_url = "/openapi.json" if _is_local_dev_env() else None
docs_url = "/docs" if _is_local_dev_env() else None
redoc_url = "/redoc" if _is_local_dev_env() else None

app = FastAPI(
    lifespan=lifespan,
    docs_url=docs_url,
    redoc_url=redoc_url,
    openapi_url=openapi_url,
)


app.add_middleware(
    CORSMiddleware,
    allow_origins=[config.web.url],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

for router in vars.load("api.routers:router", APIRouter):
    app.include_router(router)


@app.get("/", status_code=status.HTTP_200_OK)
def health_check():
    return {"status": "ok"}


@app.get("/slow")
async def ping():
    await asyncio.sleep(15)  # имитируем долгую обработку
    return {"ok": True}
