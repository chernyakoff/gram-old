from decimal import Decimal

from pydantic import BaseModel
from tortoise_serializer import ContextType, Serializer

from app.common.models.orm import AiModel


class AiModelOut(Serializer):
    id: str
    name: str
    description: str
    prompt_price: Decimal
    completion_price: Decimal

    @classmethod
    async def resolve_prompt_price(
        cls, instance: AiModel, context: ContextType
    ) -> Decimal:
        return instance.prompt_price * context["usd_rate"] * Decimal("1.1")

    @classmethod
    async def resolve_completion_price(
        cls, instance: AiModel, context: ContextType
    ) -> Decimal:
        return instance.completion_price * context["usd_rate"] * Decimal("1.1")


class AiModelIn(BaseModel):
    id: str
