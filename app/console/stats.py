import json

from rich import print

from models import orm
from models.orm import DialogStatus
from utils.cyclopts import create_app
from utils.notify import send_file_to_user

app = create_app("stats", "send system stats as json")


def _normalize_username(username: str) -> str:
    return username.lstrip("@").strip()


async def _build_stats() -> dict:
    users_total = await orm.User.all().count()
    projects_total = await orm.Project.all().count()
    dialogs_total = await orm.Dialog.all().count()

    dialogs_by_status: dict[str, int] = {}
    for status in DialogStatus:
        dialogs_by_status[status.value] = await orm.Dialog.filter(status=status).count()

    return {
        "users_total": users_total,
        "projects_total": projects_total,
        "dialogs_total": dialogs_total,
        "dialogs_by_status": dialogs_by_status,
    }


@app.default
async def _(username: str):
    username = _normalize_username(username)
    user = await orm.User.get_or_none(username=username)
    if not user:
        raise ValueError(f"user not found: {username}")

    stats = await _build_stats()
    content = json.dumps(stats, ensure_ascii=False, indent=2).encode("utf-8")
    filename = "stats.json"
    caption = f"System stats for {user.display_name}"

    await send_file_to_user(user.id, filename, content, caption)
    print(f"Sent {filename} to {user.display_name}")
