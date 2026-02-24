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


app = FastAPI(lifespan=lifespan)

cors_origins = config.auth.cors_origins or [config.web.url]

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
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
