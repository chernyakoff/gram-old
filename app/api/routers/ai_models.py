from fastapi import APIRouter, Depends

from models import orm
from utils.usd_rate import get_usd_rate
from api.dto.ai_models import AiModelOut
from api.routers.auth import get_current_user

router = APIRouter(prefix="/ai-models", tags=["ai-models"])


@router.get("/", response_model=list[AiModelOut])
async def get_ai_models(user=Depends(get_current_user)):
    usd_rate = await get_usd_rate()

    return await AiModelOut.from_queryset(
        orm.AiModel.filter(visible=True)
        .exclude(id__startswith="google")
        .order_by("completion_price")
        .all(),
        context={"usd_rate": usd_rate},
    )
