from app.common.models import enums, orm
from app.common.utils.prompt import (
    DEFAULT_SKIP_OPTIONS,
    ProjectSkipOptions,
    analyze_dialog_status,
    get_active_status,
)
from app.utils.logger import Logger


def build_history(messages: list[orm.Message]) -> list[dict]:
    history = []
    for msg in messages:
        if msg.sender == enums.MessageSender.SYSTEM:
            role = "assistant"
            content = f"[ВАЖНОЕ УТОЧНЕНИЕ] {msg.text}"
        elif msg.sender == enums.MessageSender.ACCOUNT:
            role = "assistant"
            content = msg.text
        else:
            role = "user"
            content = msg.text

        history.append({"role": role, "content": content})
    return history


class StatusResolver:
    """Определяет статус диалога."""

    def __init__(self, user: orm.User, logger: Logger):
        self.user = user
        self.logger = logger

    async def resolve_status(
        self,
        messages: list[orm.Message],
        project: orm.Project,
        current_status: enums.DialogStatus,
    ) -> enums.DialogStatus:
        history = build_history(messages)

        skip_options = (
            ProjectSkipOptions(**project.skip_options)
            if project.skip_options
            else DEFAULT_SKIP_OPTIONS
        )

        new_status = await analyze_dialog_status(
            self.user, history.copy(), current_status
        )
        if new_status:
            self.logger.info(f"AI установил статус: {new_status.value}")
            return get_active_status(new_status, skip_options)

        self.logger.warning("AI не вернул статус")
        return current_status
