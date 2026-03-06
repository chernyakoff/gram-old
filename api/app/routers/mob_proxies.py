from fastapi import APIRouter, Depends, HTTPException

from app.common.models import orm
from app.dto.mob_proxy import MobProxyCreateIn, MobProxyOut, MobProxyUpdateIn
from app.routers.auth import get_current_user

router = APIRouter(prefix="/mob-proxies", tags=["mob-proxy"])


@router.post("/", response_model=MobProxyOut)
async def create_mob_proxy(data: MobProxyCreateIn, user=Depends(get_current_user)):
    instance = await orm.MobProxy.get_or_none(user_id=user.id)
    if instance:
        raise HTTPException(status_code=409, detail="mob proxy already exists")

    instance = await orm.MobProxy.create(
        user_id=user.id,
        **data.model_dump(),
    )
    return await MobProxyOut.from_tortoise_orm(instance)


@router.get("/", response_model=MobProxyOut | None)
async def get_mob_proxy(user=Depends(get_current_user)):
    instance = await orm.MobProxy.get_or_none(user_id=user.id)
    if not instance:
        return None
    return await MobProxyOut.from_tortoise_orm(instance)


@router.patch("/", response_model=MobProxyOut)
async def update_mob_proxy(data: MobProxyUpdateIn, user=Depends(get_current_user)):
    instance = await orm.MobProxy.get_or_none(user_id=user.id)
    if not instance:
        raise HTTPException(status_code=404, detail="not found")

    update_data = data.model_dump(exclude_unset=True)
    if update_data:
        for key, value in update_data.items():
            setattr(instance, key, value)
        await instance.save()

    return await MobProxyOut.from_tortoise_orm(instance)


@router.delete("/")
async def delete_mob_proxy(user=Depends(get_current_user)):
    deleted = await orm.MobProxy.filter(user_id=user.id).delete()
    if deleted == 0:
        raise HTTPException(status_code=404, detail="not found")
    return {"deleted": deleted}
