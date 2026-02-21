import json
import re
from decimal import ROUND_DOWN, Decimal
from functools import lru_cache
from types import SimpleNamespace
from typing import Any, Callable

import httpx
import tiktoken
from langchain_core.documents import Document
from langchain_text_splitters import (
    MarkdownHeaderTextSplitter,
    RecursiveCharacterTextSplitter,
)
from openrouter import OpenRouter
from openrouter.components import ChatGenerationTokenUsage
from openrouter.operations import (
    CreateKeysResponse,
    GetKeyResponse,
)

# import tiktoken  # type: ignore
from tortoise import Tortoise
from tortoise.exceptions import DoesNotExist
from tortoise.expressions import F
from tortoise.transactions import in_transaction

from config import config
from models.orm import AiModel, User
from utils.usd_rate import get_usd_rate

# enc = tiktoken.get_encoding("cl100k_base")
DEFAULT_MODEL = "openai/gpt-5.2-chat"
GENERATE_PROMPT_MODEL = "anthropic/claude-sonnet-4.5"
EMBED_MODEL = "openai/text-embedding-3-small"
NUMBERED_ITEM_RE = re.compile(
    r"(?m)^(?P<indent>[ \t]*)(?P<num>\d{1,4})(?P<delim>[.)])[ \t]+"
)
BULLET_ITEM_RE = re.compile(r"(?m)^(?P<indent>[ \t]*)(?:[-*+])[ \t]+")

_enc = None


def get_encoder():
    # Lazy init: prevents network/download during module import.
    global _enc
    if _enc is None:
        _enc = tiktoken.get_encoding("cl100k_base")
    return _enc


class AiError(Exception):
    pass


class InsufficientBalance(AiError):
    pass


class ModelNotFound(AiError):
    pass


class OpenRouterKeyError(AiError):
    pass


class OpenRouterResponseError(AiError):
    pass


@lru_cache(maxsize=1)
def _shared_openrouter_httpx_clients() -> tuple[httpx.Client, httpx.AsyncClient]:
    # Use explicit proxy settings rather than mutating process-wide env vars.
    proxy = getattr(config.openrouter, "proxy", None) or None
    kwargs: dict[str, Any] = {"follow_redirects": True}
    if proxy:
        kwargs["proxy"] = proxy
    return httpx.Client(**kwargs), httpx.AsyncClient(**kwargs)


def _openrouter(api_key: str) -> OpenRouter:
    client, async_client = _shared_openrouter_httpx_clients()
    return OpenRouter(api_key=api_key, client=client, async_client=async_client)


async def create_raw_response(
    user: User,
    messages: list,
    *,
    tools: list | None = None,
    max_tokens: int = 3000,
    timeout_min: int = 5,
):
    user = await add_openrouter_to_user(user)
    model = await get_ai_model(user.or_model)
    usd_rate = await get_usd_rate()

    await check_balance_before_request(user, model, max_tokens, usd_rate)

    try:
        async with _openrouter(api_key=user.or_api_key) as app:
            response = await app.chat.send_async(
                model=user.or_model,
                messages=messages,
                tools=tools,
                max_tokens=max_tokens,
                timeout_ms=timeout_min * 60 * 1000,
            )
    except Exception as e:
        raise OpenRouterResponseError(f"Ошибка запроса к OpenRouter: {e}") from e

    if not response or not response.choices:
        raise OpenRouterResponseError("Пустой ответ от AI")

    usage = response.usage
    if not usage:
        raise OpenRouterResponseError("Нет usage в ответе")

    await charge_user_for_usage(user, model, usage, usd_rate)

    return response.choices[0].message


async def create_response_with_tools(
    user: User,
    history: list,
    tools: list,
    tool_handlers: dict[str, Callable],
    max_tokens: int = 3000,
    tool_events: list[dict[str, Any]] | None = None,
) -> str:
    message = await create_raw_response(
        user=user,
        messages=history,
        tools=tools,
        max_tokens=max_tokens,
    )

    for _ in range(5):  # защита от зацикливания
        history.append(
            {
                "role": "assistant",
                "content": message.content,
                "tool_calls": message.tool_calls,
            }
        )
        if not message.tool_calls:
            content = message.content
            if content is None:
                return ""
            return str(content)

        for call in message.tool_calls:
            if call.TYPE != "function":
                continue

            tool_name = call.function.name
            args = json.loads(call.function.arguments or "{}")

            handler = tool_handlers.get(tool_name)
            if not handler:
                raise RuntimeError(f"Нет handler-а для tool {tool_name}")

            try:
                result = await handler(**args)
            except Exception as e:
                # Do not fail the whole LLM request on tool errors. Return an error
                # payload so the model can self-correct (e.g. re-call get_slots).
                result = {"status": "error", "tool": tool_name, "message": str(e)}

            if tool_events is not None:
                tool_events.append(
                    {
                        "tool": tool_name,
                        "arguments": args,
                        "result": result,
                    }
                )

            history.append(
                {
                    "role": "tool",
                    "tool_call_id": call.id,
                    "content": json.dumps(result),
                }
            )

        message = await create_raw_response(
            user=user,
            messages=history,
            tools=tools,
            max_tokens=max_tokens,
        )

    raise RuntimeError("LLM tool loop exceeded limit")


async def create_response(
    user: User, input: Any, max_tokens: int = 3000, timeout_min: int = 5
) -> str:
    # атомарно добавляем ключ/модель
    user = await add_openrouter_to_user(user)

    model = await get_ai_model(user.or_model)  # type: ignore
    usd_rate = await get_usd_rate()

    await check_balance_before_request(user, model, max_tokens, usd_rate)

    try:
        async with _openrouter(api_key=user.or_api_key) as app:  # type: ignore
            response = await app.chat.send_async(
                model=user.or_model,
                messages=input,
                max_tokens=max_tokens,
                timeout_ms=timeout_min * 60 * 1000,
            )
    except Exception as e:
        raise OpenRouterResponseError(f"Ошибка запроса к OpenRouter: {e}") from e

    if not response or not response.choices:
        raise OpenRouterResponseError("Пустой ответ от AI")

    message = response.choices[0].message
    content = message.content
    usage = response.usage

    if not usage:
        raise OpenRouterResponseError("Нет usage в ответе")

    # атомарное списание баланса
    await charge_user_for_usage(user, model, usage, usd_rate)

    return str(content)


async def generate_prompt(user: User, metaprompt: str, timeout_min: int = 10) -> str:
    user = await add_openrouter_to_user(user)

    model = await get_ai_model(GENERATE_PROMPT_MODEL)
    usd_rate = await get_usd_rate()

    estimated_tokens = 20000
    await check_balance_before_request(user, model, estimated_tokens, usd_rate)

    try:
        async with _openrouter(api_key=user.or_api_key) as app:
            response = await app.chat.send_async(
                model=model.id,
                messages=[{"role": "user", "content": metaprompt}],
                timeout_ms=timeout_min * 60 * 1000,
            )
    except Exception as e:
        raise OpenRouterResponseError(f"Ошибка запроса к OpenRouter: {e}") from e

    if not response or not response.choices:
        raise OpenRouterResponseError("Пустой ответ от AI")

    message = response.choices[0].message
    content = message.content
    usage = response.usage

    if usage:
        await charge_user_for_usage(user, model, usage, usd_rate)

    return str(content)


def _split_by_list_items(
    text: str,
    *,
    item_re: re.Pattern[str],
    max_items_per_chunk: int,
    min_tokens: int,
    max_tokens: int,
    tiktoken_len,
) -> list[str]:
    starts = [m.start() for m in item_re.finditer(text)]
    if len(starts) < 2:
        t = text.strip()
        return [t] if t else []

    blocks: list[str] = []
    preface = text[: starts[0]].strip()
    if preface:
        blocks.append(preface)

    items: list[str] = []
    for i, s in enumerate(starts):
        e = starts[i + 1] if i + 1 < len(starts) else len(text)
        item = text[s:e].strip()
        if item:
            items.append(item)

    packed: list[str] = []
    cur_parts: list[str] = []
    cur_tokens = 0
    cur_items = 0

    def flush():
        nonlocal cur_parts, cur_tokens, cur_items
        if cur_parts:
            packed.append("\n\n".join(cur_parts).strip())
        cur_parts = []
        cur_tokens = 0
        cur_items = 0

    for item in items:
        item_tokens = tiktoken_len(item)
        if item_tokens > max_tokens:
            flush()
            packed.append(item)
            continue

        next_tokens = cur_tokens + (2 if cur_parts else 0) + item_tokens
        should_flush = (
            (cur_parts and next_tokens > max_tokens)
            or (cur_items >= max_items_per_chunk)
            or (cur_parts and cur_tokens >= min_tokens)
        )
        if should_flush:
            flush()

        cur_parts.append(item)
        cur_tokens = cur_tokens + (2 if len(cur_parts) > 1 else 0) + item_tokens
        cur_items += 1

    flush()
    blocks.extend([b for b in packed if b])
    return blocks


def chunk_markdown(
    text: str,
    min_tokens: int = 200,
    max_tokens: int = 700,
    overlap: int = 120,
) -> list[str]:
    text = text.replace("\r\n", "\n").strip()
    text = re.sub(r"\n{3,}", "\n\n", text)
    if not text:
        return []

    def tiktoken_len(s: str) -> int:
        return len(get_encoder().encode(s))

    header_splitter = MarkdownHeaderTextSplitter(
        headers_to_split_on=[
            ("#", "h1"),
            ("##", "h2"),
            ("###", "h3"),
            ("####", "h4"),
            ("#####", "h5"),
            ("######", "h6"),
        ],
        strip_headers=False,
        return_each_line=False,
    )
    recursive_splitter = RecursiveCharacterTextSplitter(
        chunk_size=max_tokens,
        chunk_overlap=overlap,
        length_function=tiktoken_len,
        separators=[
            "\n\n",
            "\n",
            ". ",
            "! ",
            "? ",
            "; ",
            ": ",
            ", ",
            " ",
            "",
        ],
    )

    header_docs = header_splitter.split_text(text)
    header_blocks: list[str] = []
    for d in header_docs:
        if isinstance(d, Document):
            block = d.page_content.strip()
        else:
            block = str(d).strip()
        if block:
            header_blocks.append(block)
    if not header_blocks:
        header_blocks = [text]

    blocks: list[str] = []
    for b in header_blocks:
        list_blocks = _split_by_list_items(
            b,
            item_re=NUMBERED_ITEM_RE,
            max_items_per_chunk=4,
            min_tokens=min_tokens,
            max_tokens=max_tokens,
            tiktoken_len=tiktoken_len,
        )
        if len(list_blocks) == 1:
            list_blocks = _split_by_list_items(
                b,
                item_re=BULLET_ITEM_RE,
                max_items_per_chunk=6,
                min_tokens=min_tokens,
                max_tokens=max_tokens,
                tiktoken_len=tiktoken_len,
            )
        blocks.extend(list_blocks)

    raw_chunks: list[str] = []
    for b in blocks:
        if tiktoken_len(b) <= max_tokens:
            raw_chunks.append(b)
        else:
            raw_chunks.extend(recursive_splitter.split_text(b))

    return [
        c.strip()
        for c in raw_chunks
        if len(c.strip()) > 30 and re.search(r"[A-Za-zА-Яа-я0-9]", c)
    ]


async def embed_chunks(
    user: User, chunks: list[str], batch_size=32
) -> list[list[float]]:
    user = await add_openrouter_to_user(user)
    model = await get_ai_model(EMBED_MODEL)
    usd_rate = await get_usd_rate()

    embeddings: list[list[float]] = []
    async with _openrouter(api_key=user.or_api_key) as app:
        for i in range(0, len(chunks), batch_size):
            batch = chunks[i : i + batch_size]

            tokens_estimate = sum(len(get_encoder().encode(c)) for c in batch)
            estimated_cost_usd = (
                model.prompt_price * Decimal(tokens_estimate)
            ) * Decimal("1.1")
            estimated_cost_rub = estimated_cost_usd * usd_rate
            estimated_cost_cents = int(estimated_cost_rub * 100)
            if user.balance < estimated_cost_cents:
                needed_rub = Decimal(estimated_cost_cents) / Decimal(100)
                user_rub = Decimal(user.balance) / Decimal(100)
                raise InsufficientBalance(
                    f"Недостаточно средств. Нужно ~{needed_rub:.2f} ₽, есть {user_rub:.2f} ₽"
                )

            response = await app.embeddings.generate_async(
                model=model.id,
                input=batch,
                encoding_format="float",
            )

            if not response or not response.data:  # type: ignore
                raise OpenRouterResponseError("Пустой ответ от embeddings")

            await charge_user_for_embedding_usage(
                user,
                model,
                response.usage,  # type: ignore
                usd_rate,
            )

            embeddings.extend([e.embedding for e in response.data])  # type: ignore

    return embeddings


async def retrieve_chunks(
    user: User, question: str, top_k: int = 5, project_id: int | None = None
) -> list[str]:
    user = await add_openrouter_to_user(user)
    model = await get_ai_model(EMBED_MODEL)
    usd_rate = await get_usd_rate()

    # Fast, conservative estimate to prevent outbound requests when balance is clearly insufficient.
    estimated_tokens = max(1, len(question) // 3)
    estimated_cost_usd = (model.prompt_price * Decimal(estimated_tokens)) * Decimal(
        "1.1"
    )
    estimated_cost_rub = estimated_cost_usd * usd_rate
    estimated_cost_cents = int(estimated_cost_rub * 100)
    if user.balance < estimated_cost_cents:
        needed_rub = Decimal(estimated_cost_cents) / Decimal(100)
        user_rub = Decimal(user.balance) / Decimal(100)
        raise InsufficientBalance(
            f"Недостаточно средств. Нужно ~{needed_rub:.2f} ₽, есть {user_rub:.2f} ₽"
        )

    try:
        async with _openrouter(api_key=user.or_api_key) as app:
            response = await app.embeddings.generate_async(
                model=EMBED_MODEL,
                input=[question],
                encoding_format="float",
            )
    except Exception as e:
        raise OpenRouterResponseError(f"Ошибка запроса к OpenRouter: {e}") from e

    data = getattr(response, "data", None)
    if not response or not data:
        raise OpenRouterResponseError("Пустой ответ от embeddings")

    usage = getattr(response, "usage", None) or SimpleNamespace(
        prompt_tokens=estimated_tokens
    )
    await charge_user_for_embedding_usage(user, model, usage, usd_rate)

    query_embedding = data[0].embedding

    query_vector = "[" + ",".join(f"{x:.8f}" for x in query_embedding) + "]"

    top_k = max(1, int(top_k))
    params: list[object] = [query_vector]
    where_clause = ""
    if project_id is not None:
        where_clause = "WHERE project_id = $2"
        params.append(int(project_id))

    rows = await Tortoise.get_connection("default").execute_query_dict(
        f"""
        SELECT content, metadata
        FROM knowledge_chunks
        {where_clause}
        ORDER BY embedding <=> $1::vector
        LIMIT {top_k}
    """,
        params,
    )

    return [r["content"] for r in rows]


# ----------------- ПОТОКОБЕЗОПАСНЫЕ ВСПОМОГАТЕЛЬНЫЕ -----------------


async def add_openrouter_to_user(user: User) -> User:
    """
    Потокобезопасное добавление модели и API ключа OpenRouter.
    Используем транзакцию и select_for_update.
    """
    # Fast path: most callers already have these fields on the in-memory user.
    # Keep the DB/lock path only for the "needs provisioning" case.
    if getattr(user, "or_model", None) and getattr(user, "or_api_key", None):
        return user

    async with in_transaction() as conn:
        try:
            # блокируем пользователя для обновления
            db_user = (
                await User.filter(id=user.id).using_db(conn).select_for_update().get()
            )
        except DoesNotExist:
            raise ValueError(f"Пользователь с id={user.id} не найден")

        changed = False

        if not db_user.or_model:
            db_user.or_model = DEFAULT_MODEL
            changed = True

        if not db_user.or_api_key:
            try:
                key = await create_key(db_user.display_name)
            except Exception as e:
                raise OpenRouterKeyError("Не удалось создать API ключ") from e

            db_user.or_api_key = key.key
            db_user.or_api_hash = key.data.hash
            changed = True

        if changed:
            await db_user.save(update_fields=["or_model", "or_api_key", "or_api_hash"])

        return db_user


async def charge_user_for_usage(
    user: User,
    model: AiModel,
    usage: ChatGenerationTokenUsage,
    usd_rate: Decimal,
):
    prompt_cost = model.prompt_price * Decimal(usage.prompt_tokens or 0)
    completion_cost = model.completion_price * Decimal(usage.completion_tokens or 0)

    total_usd = (prompt_cost + completion_cost) * Decimal("1.1")
    total_rub = total_usd * usd_rate
    total_cents = int(total_rub * 100)

    if total_cents <= 0:
        return

    updated = await User.filter(id=user.id, balance__gte=total_cents).update(
        balance=F("balance") - total_cents
    )
    if not updated:
        raise InsufficientBalance("Недостаточно средств для списания")


async def charge_user_for_embedding_usage(
    user: User,
    model: AiModel,
    usage,
    usd_rate: Decimal,
):
    if usage is None:
        return

    prompt_tokens = usage.prompt_tokens or 0

    if prompt_tokens <= 0:
        return

    # embeddings тарифицируются ТОЛЬКО по prompt_tokens
    prompt_cost = model.prompt_price * Decimal(prompt_tokens)

    total_usd = prompt_cost * Decimal("1.1")
    total_rub = total_usd * usd_rate
    total_cents = int(total_rub * 100)

    if total_cents <= 0:
        return

    updated = await User.filter(
        id=user.id,
        balance__gte=total_cents,
    ).update(balance=F("balance") - total_cents)

    if not updated:
        raise InsufficientBalance("Недостаточно средств для списания")


async def check_balance_before_request(
    user: User, model: AiModel, max_tokens: int, usd_rate: Decimal
):
    estimated_cost_usd = (model.completion_price * Decimal(max_tokens)) * Decimal("1.1")
    estimated_cost_rub = estimated_cost_usd * usd_rate
    estimated_cost_cents = int(estimated_cost_rub * 100)

    if user.balance < estimated_cost_cents:
        needed_rub = Decimal(estimated_cost_cents) / Decimal(100)
        user_rub = Decimal(user.balance) / Decimal(100)
        raise InsufficientBalance(
            f"Недостаточно средств. Нужно ~{needed_rub:.2f} ₽, есть {user_rub:.2f} ₽"
        )


async def get_ai_model(or_model: str) -> AiModel:
    model = await AiModel.get_or_none(id=or_model)
    if not model:
        raise ModelNotFound(f"Модель {or_model} не найдена")
    return model


async def create_key(name: str) -> CreateKeysResponse:
    async with _openrouter(api_key=config.openrouter.manager_api_key) as app:
        key = await app.api_keys.create_async(name=name)
    return key


async def get_key(hash: str) -> GetKeyResponse:
    async with _openrouter(api_key=config.openrouter.manager_api_key) as app:
        key = await app.api_keys.get_async(hash=hash)
    return key


async def upsert_models():
    async def _upsert_models(response):
        for model in response.data:
            if model.id not in model_ids:
                continue
            await AiModel.update_or_create(
                id=model.id,
                defaults={
                    "name": model.name,
                    # "description": model.description,
                    "prompt_price": Decimal(model.pricing.prompt),
                    "completion_price": Decimal(model.pricing.completion),
                },
            )

    model_ids = await AiModel.all().values_list("id", flat=True)
    async with _openrouter(api_key=config.openrouter.manager_api_key) as app:
        response = await app.models.list_async()
        await _upsert_models(response)
        response = app.embeddings.list_models()
        await _upsert_models(response)


async def get_balance() -> Decimal:
    usd_rate = await get_usd_rate()
    async with _openrouter(api_key=config.openrouter.manager_api_key) as open_router:
        response = await open_router.credits.get_credits_async()

        balance_usd = Decimal(str(response.data.total_credits)) - Decimal(
            str(response.data.total_usage)
        )
        balance_rub = balance_usd * usd_rate
        return balance_rub.quantize(
            Decimal("0.00"),
            rounding=ROUND_DOWN,
        )
