import re
from typing import Any, cast

from fastapi import APIRouter, Depends, HTTPException

from app.common.models import orm
from app.common.models.enums import DialogStatus
from app.common.utils import openrouter
from app.common.utils.functions import (
    generate_message,
    normalize_dashes,
    randomize_message,
)
from app.common.utils.prompt import (
    DEFAULT_SKIP_OPTIONS,
    build_prompt_v2,
    get_active_status,
    get_ooc_status,
    get_status_addon,
    get_status_info,
    strip_ooc_status,
)
from app.dto.chat import ChatIn, ChatOut, Message, MessageRole
from app.dto.project import ProjectSkipOptions
from app.routers.auth import get_current_user

router = APIRouter(prefix="/chat", tags=["chat"])

ANALYZE_PROMPT = """
определи статус диалога и верни только статус

Универсальные статусы определяются по смыслу сообщения пользователя и активному модулю промпта.

INIT - установка базового контакта.

ENGAGE - понять ситуацию/задачи/цели/боли пользователя.

OFFER - предложить решение/продукта услуги.

CLOSING - согласовать следующий шаг и необходимые детали.

COMPLETE - корректно завершить диалог.

**NEGATIVE - если видишь, что человек резок к нам, строгий подтвержденный отказ, то извиниться за контакт, а после вернуть этот статус перед следующим ответом.

**OPERATOR - если видишь раздражение от ИИ или в запросе человека он говорит что ему не нравится общаться с ИИ, а также когда прямо заявляют что ИИ бесит, уведомить, что сделаешь перевод на человека или выполни цель (ссылка на группу, передача оператору), верни этот статус после этого перед следующим ответом.
"""


async def analyze_dialog_status(
    user: orm.User, messages: list[Message]
) -> DialogStatus | None:
    history = [{"role": m.role.value, "content": m.text} for m in messages]
    history.append({"role": "user", "content": ANALYZE_PROMPT})
    response = await openrouter.create_response(user, messages)
    match = re.search(
        r"(init|engage|offer|closing|complete|negative|operator)",
        response.strip(),
        re.IGNORECASE,
    )
    if match:
        return DialogStatus(response.strip())


@router.post("/", response_model=ChatOut)
async def chat(chat: ChatIn, user=Depends(get_current_user)):
    project = await orm.Project.filter(
        id=chat.project_id, user_id=user.id
    ).get_or_none()

    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    skip_options = (
        ProjectSkipOptions(**project.skip_options)
        if project.skip_options
        else DEFAULT_SKIP_OPTIONS
    )

    if skip_options != DEFAULT_SKIP_OPTIONS and chat.messages:
        new_status = await analyze_dialog_status(user, chat.messages)
        print("found status", new_status)
        if not new_status:
            raise HTTPException(
                status_code=404, detail="Не могу определить статус диалога"
            )
        chat.status = get_active_status(new_status, skip_options)

    STATUS_INFO = ""  # get_status_info(chat.status, skip_options)

    if not chat.messages and project.first_message:
        first_message = generate_message(project.first_message)
        first_message = randomize_message(first_message)
        return ChatOut(text=first_message, status=chat.status)
    else:
        STATUS_ADDON = await get_status_addon()
        for msg in reversed(chat.messages):
            if msg.role == MessageRole.user:
                msg.text = f"{msg.text}\n{STATUS_ADDON}\n{STATUS_INFO}"
                if chat.status == DialogStatus.CLOSING:
                    msg.text += "\nВАЖНО, если ты попрощался, а тебе продолжают писать, то отвечай одним словом COMPLETE и больше ничего не пиши"

                break

    orm_prompt = await orm.Prompt.get(project_id=project.id)

    # prompt = build_prompt(orm_prompt.to_dict(), chat.status)
    prompt = build_prompt_v2(orm_prompt.to_dict(), chat.status)

    messages = [{"role": "system", "content": prompt}]
    messages.extend([{"role": m.role.value, "content": m.text} for m in chat.messages])

    try:
        response = await openrouter.create_response(user, messages)
    except Exception as e:
        return ChatOut(text=str(e), status=chat.status)

    if not response:
        return ChatOut(text="AI не вернул ответ", status=chat.status)

    add_status_alert = False
    status = get_ooc_status(response)
    if not status:
        add_status_alert = True
        status = chat.status

    response = strip_ooc_status(response)
    response = normalize_dashes(response)

    if add_status_alert:
        response += "\n\nВНИМАНИЕ!! AI НЕ ВЕРНУЛ СТАТУС"
    return ChatOut(text=response, status=status)
