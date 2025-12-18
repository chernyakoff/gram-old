import math
from typing import Optional

import httpx
from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from tortoise.transactions import in_transaction

from app.common.models import orm
from app.routers.auth import (
    get_current_user,
)

router = APIRouter(prefix="/settings", tags=["settings"])


class ProxyApiSettingsIn(BaseModel):
    api_key: str


class SettingsIn(BaseModel):
    proxy_api: ProxyApiSettingsIn


class ProxyApiSettingsOut(BaseModel):
    api_key: Optional[str] = None
    balance: Optional[int] = None
    error: Optional[str] = None


class SettingsOut(BaseModel):
    proxy_api: ProxyApiSettingsOut = Field(default_factory=ProxyApiSettingsOut)


# --- Функция проверки API ключа ---
async def get_proxyapi_balance(api_key: str) -> tuple[Optional[int], Optional[str]]:
    url = "https://api.proxyapi.ru/proxyapi/balance"
    headers = {"Authorization": f"Bearer {api_key}"}

    async with httpx.AsyncClient(timeout=10) as client:
        try:
            resp = await client.get(url, headers=headers)
            # не raise_for_status(), будем смотреть на статус сами
            data = resp.json()
        except httpx.HTTPError:
            return None, "Сервис недоступен"
        except ValueError:
            return None, "Некорректный ответ сервиса"

    # Если вернулся баланс
    if "balance" in data:
        bal = data["balance"]
        if isinstance(bal, (int, float)):
            return math.floor(bal), None
        return None, "Некорректный формат баланса"

    # Если вернулась ошибка
    if "detail" in data:
        msg = data["detail"]
        if "Invalid API Key" in msg:
            return None, "Невалидный API ключ"
        elif "You are not allowed" in msg:
            return None, "Включите доступ к балансу в настройках ключа"
        else:
            return None, msg

    # На всякий случай
    return None, "Неизвестная ошибка API"


# --- GET настройки ---
@router.get("/", response_model=SettingsOut)
async def get_settings(user=Depends(get_current_user)):
    data = await orm.Settings.fetch_all(user.id)
    settings = SettingsOut.model_validate(data)

    api_key = settings.proxy_api.api_key
    if api_key:
        balance, error = await get_proxyapi_balance(api_key)
        if error:
            settings.proxy_api.error = error
            settings.proxy_api.balance = None
        else:
            settings.proxy_api.balance = balance

    return settings


# --- POST / сохранение ---
@router.post("/", response_model=SettingsOut)
async def save_settings(data: SettingsIn, user=Depends(get_current_user)):
    payload = data.model_dump(exclude_unset=True)
    out = SettingsOut()  # объект для ответа

    # Проверяем proxy_api.api_key отдельно
    api_key = payload.get("proxy_api", {}).get("api_key")
    if api_key:
        balance, error = await get_proxyapi_balance(api_key)
        if error:
            out.proxy_api.error = error
            # Не сохраняем ключ, только остальные настройки
            payload["proxy_api"].pop("api_key", None)
        else:
            out.proxy_api.api_key = api_key
            out.proxy_api.balance = balance

    # Сохраняем все остальные настройки
    async with in_transaction():
        for section, values in payload.items():
            for name, value in values.items():
                await orm.Settings.update_or_create(
                    defaults={"value": str(value)},
                    user_id=user.id,
                    section=section,
                    name=name,
                )

    # Получаем актуальные настройки
    saved = await orm.Settings.fetch_all(user.id)
    saved_out = SettingsOut.model_validate(saved)

    # Подставляем валидный ключ и баланс, если есть
    if out.proxy_api.api_key and not out.proxy_api.error:
        saved_out.proxy_api.api_key = out.proxy_api.api_key
        saved_out.proxy_api.balance = out.proxy_api.balance

    # Подставляем ошибку, если ключ был невалидный
    if out.proxy_api.error:
        saved_out.proxy_api.error = out.proxy_api.error

    return saved_out
