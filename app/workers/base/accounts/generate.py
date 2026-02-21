import asyncio
import re
from datetime import timedelta
from typing import Literal

from hatchet_sdk import Context
from pydantic import BaseModel
from tortoise.transactions import in_transaction

from models import orm
from utils.account import AccountUtil
from utils.logger import StreamLogger
from utils import openrouter
from utils.proxy_pool import ProxyPool
from workers.base.accounts.exceptions import SessionExpiredError
from workers.base.accounts.update import update_profile, update_username
from workers.base.client import hatchet

USERNAME_RE = re.compile(r"^[a-zA-Z0-9_]+$")


class AccountsGenerateIn(BaseModel):
    ids: list[int]
    gender: Literal["any", "male", "female"] = "any"
    generate_names: bool = True
    generate_usernames: bool = True


class AccountUpdate(BaseModel):
    id: int
    name: str | None = None
    username: str | None = None


SYSTEM_PROMPT = """
Ты генерируешь данные профилей Telegram.
Верни результат СТРОГО в формате TSV с разделителем "|", без markdown, без пояснений.
Разрешены только строки данных, первая строка — заголовок.

Формат:
id|name|username

Правила:
1) Количество строк результата = количеству входных id.
2) Пол:
- male: русские мужские имена.
- female: русские женские имена.
- any: смешивай мужские и женские естественно.
3) Поле name всегда в формате "Имя Фамилия" (два слова кириллицей), если это возможно.
4) Если генерируешь username:
- только латиница, цифры, "_"
- длина 5..32
- без "@"
- уникален в пределах ответа
- не начинается с "_"
- не заканчивается на "_"
- не содержит "__"
- желательна фонетическая/смысловая связь с name (транслит, сокращение, вариации).
5) Никаких символов "|" внутри полей.
6) Пустое значение = пустая строка между разделителями (например: 15||ivan_fox).
""".strip()


def _account_name(account: orm.Account) -> str:
    first = (account.first_name or "").strip()
    last = (account.last_name or "").strip()
    return " ".join(part for part in (first, last) if part)


def _prepare_rows(accounts: list[orm.Account]) -> str:
    lines = ["id|name|username"]
    for account in accounts:
        name = _account_name(account).replace("|", " ")
        username = (account.username or "").strip().replace("|", "")
        if username.startswith("@"):
            username = username[1:]
        lines.append(f"{account.id}|{name}|{username}")
    return "\n".join(lines)


def _strip_code_fences(text: str) -> str:
    stripped = text.strip()
    if stripped.startswith("```") and stripped.endswith("```"):
        parts = stripped.split("\n")
        if len(parts) >= 3:
            return "\n".join(parts[1:-1]).strip()
    return stripped


def _normalize_username(value: str | None) -> str | None:
    if not value:
        return None
    username = value.strip()
    if username.startswith("@"):
        username = username[1:]
    if not username:
        return None
    return username


def _is_valid_username(value: str | None) -> bool:
    if not value:
        return False
    if len(value) < 5 or len(value) > 32:
        return False
    if value.startswith("_") or value.endswith("_"):
        return False
    if "__" in value:
        return False
    if not USERNAME_RE.fullmatch(value):
        return False
    return True


def _parse_updates(
    raw: str, accounts: list[orm.Account], input: AccountsGenerateIn
) -> list[AccountUpdate]:
    existing_by_id = {
        account.id: AccountUpdate(
            id=account.id,
            name=_account_name(account) or None,
            username=account.username,
        )
        for account in accounts
    }
    requested_ids = [account.id for account in accounts]
    result: dict[int, AccountUpdate] = {}
    lines = [line.strip() for line in _strip_code_fences(raw).splitlines() if line.strip()]
    if not lines:
        return [existing_by_id[account_id] for account_id in requested_ids]

    data_lines = lines[1:] if lines[0].lower() == "id|name|username" else lines
    for line in data_lines:
        if line.count("|") != 2:
            continue
        id_raw, name_raw, username_raw = line.split("|", 2)
        try:
            account_id = int(id_raw.strip())
        except ValueError:
            continue
        if account_id not in existing_by_id:
            continue

        base = existing_by_id[account_id]
        name = name_raw.strip() or None
        username = _normalize_username(username_raw.strip() or None)
        if username and not _is_valid_username(username):
            username = None

        # Mode rules:
        # both=true  -> regenerate both.
        # names only -> regenerate name; keep username if exists, otherwise generate username.
        # usernames only -> regenerate username; keep name if exists, otherwise generate name.
        # both=false -> return empty update.
        if input.generate_names and input.generate_usernames:
            final_name = name or base.name
            final_username = username or base.username
        elif input.generate_names and not input.generate_usernames:
            final_name = name or base.name
            final_username = base.username or username
        elif not input.generate_names and input.generate_usernames:
            final_name = base.name or name
            final_username = username or base.username
        else:
            final_name = None
            final_username = None

        result[account_id] = AccountUpdate(
            id=account_id,
            name=final_name,
            username=final_username,
        )

    # Fill missing rows with fallback data.
    for account_id in requested_ids:
        if account_id in result:
            continue
        base = existing_by_id[account_id]
        if input.generate_names and input.generate_usernames:
            fallback_name = base.name
            fallback_username = base.username
        elif input.generate_names and not input.generate_usernames:
            fallback_name = base.name
            fallback_username = base.username
        elif not input.generate_names and input.generate_usernames:
            fallback_name = base.name
            fallback_username = base.username
        else:
            fallback_name = None
            fallback_username = None
        result[account_id] = AccountUpdate(
            id=account_id,
            name=fallback_name,
            username=fallback_username,
        )

    return [result[account_id] for account_id in requested_ids]


def _split_name(full_name: str | None) -> tuple[str, str]:
    if not full_name:
        return "", ""
    parts = [p for p in full_name.strip().split() if p]
    if not parts:
        return "", ""
    first_name = parts[0][:64]
    last_name = " ".join(parts[1:])[:64] if len(parts) > 1 else ""
    return first_name, last_name


async def _generate(
    accounts: list[orm.Account], input: AccountsGenerateIn, logger: StreamLogger
) -> list[AccountUpdate]:
    if not accounts:
        return []

    if not input.generate_names and not input.generate_usernames:
        return [AccountUpdate(id=account.id) for account in accounts]

    user = await orm.User.get(id=accounts[0].user_id)
    rows = _prepare_rows(accounts)
    mode_rules = """
Режим генерации:
1) generate_names=true и generate_usernames=true:
- перегенерируй И name, И username для каждой строки, даже если уже заполнены.
2) generate_names=true и generate_usernames=false:
- перегенерируй name для каждой строки, даже если уже заполнен;
- username используй как опору для созвучия;
- если username пустой, сгенерируй username тоже.
3) generate_names=false и generate_usernames=true:
- перегенерируй username для каждой строки, даже если уже заполнен;
- name используй как опору для созвучия;
- если name пустой, сгенерируй name тоже.
4) generate_names=false и generate_usernames=false:
- оставь name и username пустыми.
""".strip()
    user_prompt = f"""
Сгенерируй/обнови данные аккаунтов по правилам режима.

Параметры:
gender={input.gender}
generate_names={str(input.generate_names).lower()}
generate_usernames={str(input.generate_usernames).lower()}

{mode_rules}

Входные данные (TSV):
{rows}

Где:
- name во входе уже дан как full name: first_name + " " + last_name; соблюдай этот формат в ответе.
- в ответе верни строку для каждого id.
- порядок строк сохранить.
""".strip()
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_prompt},
    ]
    await logger.tech(
        "TODO_REMOVE_DEBUG accounts_generate llm messages",
        payload={
            "marker": "TODO_REMOVE_DEBUG",
            "messages": messages,
        },
    )

    try:
        raw = await openrouter.create_response(user, messages, max_tokens=4000, timeout_min=5)
        await logger.tech(
            "TODO_REMOVE_DEBUG accounts_generate llm response",
            payload={
                "marker": "TODO_REMOVE_DEBUG",
                "raw_response": raw,
            },
        )
    except Exception as e:
        await logger.error(f"ошибка генерации имен/username: {e}")
        return [
            AccountUpdate(
                id=account.id,
                name=_account_name(account) or None,
                username=account.username,
            )
            for account in accounts
        ]

    updates = _parse_updates(raw, accounts, input)
    await logger.info(f"сгенерировано профилей: {len(updates)}")
    return updates


async def _update(
    orm_account: orm.Account,
    generated: AccountUpdate,
    pool: ProxyPool,
    logger: StreamLogger,
):

    proxy = await pool.verify_proxy(orm_account)

    if not proxy:
        await logger.from_proxy_pool(pool)
        return

    orm_account.busy = True
    async with in_transaction() as conn:
        await orm_account.save(using_db=conn, update_fields=["busy", "updated_at"])

    account = AccountUtil.from_orm(orm_account)

    client = account.create_client(proxy)

    try:
        await client.connect()

        if not await client.is_user_authorized():
            raise SessionExpiredError(account.phone)

        if generated.username is not None:
            desired_username = generated.username
            current_username = orm_account.username
            if _normalize_username(desired_username) != _normalize_username(current_username):
                await update_username(client, desired_username, orm_account, logger)
            else:
                await logger.info("username без изменений")

        if generated.name is not None:
            first_name, last_name = _split_name(generated.name)
            profile_update: dict[str, str] = {}
            if (orm_account.first_name or "") != first_name:
                profile_update["first_name"] = first_name
            if (orm_account.last_name or "") != last_name:
                profile_update["last_name"] = last_name
            if profile_update:
                await update_profile(client, profile_update, orm_account, logger)
            else:
                await logger.info("name без изменений")
    except SessionExpiredError:
        await logger.error(f"{account.phone} вылет из сессии")
        orm_account.status = orm.AccountStatus.EXITED

    except Exception as e:
        orm_account.status = orm.AccountStatus.BANNED
        orm_account.busy = False
        await orm_account.save()
        await logger.error(f"{account.phone} забанен {e}")
    finally:
        await client.disconnect()  # type: ignore
        orm_account.busy = False
        await orm_account.save()


@hatchet.task(
    name="accounts-generate",
    input_validator=AccountsGenerateIn,
    execution_timeout=timedelta(minutes=60),
    schedule_timeout=timedelta(minutes=60),
)
async def accounts_generate(input: AccountsGenerateIn, ctx: Context):
    await asyncio.sleep(2)  # эмуляция задержки
    logger = StreamLogger(ctx)
    accounts = (
        await orm.Account.filter(id__in=input.ids).prefetch_related("proxy").all()
    )
    if not accounts:
        await logger.error("аккаунты не найдены")
        return

    user_id = accounts[0].user_id
    pool = ProxyPool(user_id)

    generated = await _generate(accounts, input, logger)
    generated_by_id = {item.id: item for item in generated}

    tasks = [
        _update(account, generated_by_id.get(account.id, AccountUpdate(id=account.id)), pool, logger)
        for account in accounts
    ]
    await asyncio.gather(*tasks)
