import hashlib
import hmac

from cyclopts import App
from rich import print

from app.config import config

app = App(name="dev", help="dev tests etc")

TGDATA_PROBLEM = {
    "id": 6990122819,
    "first_name": "Алекс V",
    "last_name": "Громов",
    "username": "DoPNkb",
    "photo_url": "",
    "auth_date": 1760618549,
    "hash": "f0d1a2543e5b72e442765b8b7973a3a756c00aa446c54336e43348450a301b3f",
}
TGDATA_GOOD = {
    "id": 359107176,
    "first_name": "М",
    "last_name": "С",
    "username": "chernyakoff",
    "photo_url": "https://t.me/i/userpic/320/E5CF1DXAc92hvxFoNm0Z4y4Z4ycjpk6DqbKdvmjyVyw.jpg",
    "auth_date": 1760618840,
    "hash": "113c08f7bbe1d76232b0c815f50ed1342a58f424cc76161ce63804dc3dca8574",
}


def verify_telegram_login_data(data, bot_token):
    """
    Verifies the hash received from Telegram Login Widget.
    data: Dictionary containing user data (id, first_name, username, photo_url, hash, etc.)
    bot_token: Your Telegram bot's token.
    """
    if "hash" not in data:
        return False

    received_hash = data.pop("hash")

    # Sort parameters alphabetically by key
    sorted_keys = sorted(data.keys())
    data_check_string = "\n".join(
        [f"{key}={data[key]}" for key in sorted_keys if data[key] is not None]
    )

    secret_key = hashlib.sha256(bot_token.encode()).digest()
    calculated_hash = hmac.new(
        secret_key, data_check_string.encode(), hashlib.sha256
    ).hexdigest()

    return calculated_hash == received_hash


@app.command
async def qwerty():
    bad = verify_telegram_login_data(
        TGDATA_PROBLEM, config.api.bot.token.get_secret_value()
    )

    print(bad)
