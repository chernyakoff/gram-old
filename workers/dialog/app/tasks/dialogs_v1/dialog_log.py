from app.common.models import enums, orm
from app.utils.logger import Logger


def log_ai_terminal(logger: Logger, recipient: orm.Recipient, status: enums.DialogStatus):
    logger.info(
        f"[{recipient.username}] AI вернул терминальный статус: {status.value}"
    )


def log_ai_no_response(logger: Logger, recipient: orm.Recipient, attempt: int):
    logger.warning(
        f"[{recipient.username}] AI не вернул ответ (attempt {attempt})"
    )


def log_ai_timeout(logger: Logger, recipient: orm.Recipient, attempt: int):
    logger.warning(
        f"[{recipient.username}] OpenAI timeout (attempt {attempt})"
    )


def log_ai_critical(logger: Logger, recipient: orm.Recipient):
    logger.error(f"[{recipient.username}] Критическая ошибка AI")


def log_ai_timeout_final(logger: Logger, recipient: orm.Recipient):
    logger.error(f"[{recipient.username}] AI timeout")
