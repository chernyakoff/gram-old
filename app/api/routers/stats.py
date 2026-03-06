from fastapi import APIRouter, Depends

from models.orm import DialogStatus  # ваш enum из проекта
from models.orm import Dialog
from api.dto.stats import StatsIn, StatsOut
from api.routers.auth import get_current_user

router = APIRouter(prefix="/stats", tags=["Stats"])


@router.post("/", response_model=StatsOut)
async def get_stats(payload: StatsIn, user=Depends(get_current_user)):
    date_from, date_to = payload.date_from, payload.date_to
    filters = payload.to_filter_q(user_id=user.id)

    rows = await Dialog.filter(filters).values("status", "started_at")

    days_count = (date_to - date_from).days + 1
    init = [0] * days_count
    engage = [0] * days_count
    offer = [0] * days_count
    closing = [0] * days_count
    complete = [0] * days_count
    negative = [0] * days_count
    operator = [0] * days_count
    manual = [0] * days_count

    status_map = {
        DialogStatus.INIT.value: init,
        DialogStatus.ENGAGE.value: engage,
        DialogStatus.OFFER.value: offer,
        DialogStatus.CLOSING.value: closing,
        DialogStatus.COMPLETE.value: complete,
        DialogStatus.NEGATIVE.value: negative,
        DialogStatus.OPERATOR.value: operator,
        DialogStatus.MANUAL.value: manual,
    }

    for r in rows:
        started_at = r.get("started_at")
        status = r.get("status")
        if not started_at or status not in status_map:
            continue
        idx = (started_at.date() - date_from).days
        if 0 <= idx < days_count:
            status_map[status][idx] += 1

    return StatsOut(
        init=init,
        engage=engage,
        offer=offer,
        closing=closing,
        complete=complete,
        negative=negative,
        operator=operator,
        manual=manual,
    )
