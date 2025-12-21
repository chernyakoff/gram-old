from fastapi import APIRouter, Depends, HTTPException

from app.common.models import orm
from app.common.utils.openrouter import DEFAULT_MODEL
from app.common.utils.usd_rate import get_usd_rate
from app.dto.ai_models import AiModelIn, AiModelOut
from app.routers.auth import get_current_user

router = APIRouter(prefix="/ai-models", tags=["ai-models"])


@router.get("/", response_model=list[AiModelOut])
async def get_ai_models(user=Depends(get_current_user)):
    usd_rate = await get_usd_rate()
    return await AiModelOut.from_queryset(
        orm.AiModel.all(), context={"usd_rate": usd_rate}
    )


@router.get("/selected", response_model=AiModelOut)
async def get_selected_model(user=Depends(get_current_user)):
    if user.or_model is not None:
        model = await orm.AiModel.get_or_none(id=user.or_model)
    else:
        model = await orm.AiModel.get_or_none(id=DEFAULT_MODEL)

    if not model:
        raise HTTPException(status_code=404, detail="Ai model not found")

    usd_rate = await get_usd_rate()
    return await AiModelOut.from_tortoise_orm(model, context={"usd_rate": usd_rate})


@router.post("/", response_model=AiModelOut)
async def save_ai_model(selection: AiModelIn, user=Depends(get_current_user)):
    """Выбрать AI модель"""
    model = await orm.AiModel.get_or_none(id=selection.id)
    if not model:
        raise HTTPException(status_code=404, detail="Model not found")

    user.or_model = selection.id
    await user.save(update_fields=["or_model"])

    usd_rate = await get_usd_rate()
    return await AiModelOut.from_tortoise_orm(model, context={"usd_rate": usd_rate})
