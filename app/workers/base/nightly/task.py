from hatchet_sdk import Context, EmptyModel
from tortoise import Tortoise

from workers.base.client import hatchet
from models import orm
from utils import openrouter

# workflow запускается каждый день в 00:05
nightly = hatchet.workflow(name="nightly", on_crons=["3 0 * * *"])


@nightly.task()
async def task(input: EmptyModel, ctx: Context):
    await openrouter.upsert_models()

    # ----

    conn = Tortoise.get_connection("default")

    PROGREV = orm.Account.PROGREV
    # Генерируем CASE для PROGREV динамически
    case_lines = "\n".join(f"WHEN {i} THEN {v}" for i, v in enumerate(PROGREV))
    progrev_len = len(PROGREV)
    case_sql = f"""
    CASE ad.days_count
        {case_lines}
        ELSE a.out_daily_limit
    END
    """

    query = f"""
    WITH active_days AS (
        SELECT
            a.id AS account_id,
            COUNT(DISTINCT DATE(d.started_at)) AS days_count
        FROM accounts a
        LEFT JOIN dialogs d
            ON d.account_id = a.id
        GROUP BY a.id
    )
    UPDATE accounts AS a
    SET
        active_days_count = ad.days_count,
        daily_limit_left = CASE
            WHEN a.premium THEN {case_sql}
            WHEN ad.days_count < {progrev_len} THEN 1
            ELSE a.out_daily_limit
        END
    FROM active_days AS ad
    WHERE a.id = ad.account_id;
    """

    await conn.execute_query(query)

    ctx.log("Nightly: Updated active_days_count and daily_limit_left for all accounts")
