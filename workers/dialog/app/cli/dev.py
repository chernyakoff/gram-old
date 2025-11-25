import httpx
from cyclopts import App
from rich import print

from app.config import config

app = App(name="dev", help="dev tests etc")


async def send_file_to_user(
    chat_id: int, filename: str, content: bytes, caption: str, bot_token: str
):
    url = f"https://api.telegram.org/bot{bot_token}/sendDocument"

    # Правильный формат для multipart/form-data в httpx:
    # "имя_поля": (имя_файла, контент_в_байтах, content_type)
    files = {
        "document": (filename, content, "text/plain"),
    }
    # Параметры, передаваемые как data, а не files
    data = {
        "chat_id": str(chat_id),
        "caption": caption,
    }

    async with httpx.AsyncClient() as client:
        # Используем параметр files для файла и data для остальных полей
        response = await client.post(url, data=data, files=files)
        # Добавим проверку ответа, чтобы понять, что происходит
        response.raise_for_status()  # Вызовет исключение при ошибке HTTP (4xx или 5xx)
        print(f"Telegram API response: {response.json()}")
        return response.json()


@app.command
async def test():
    user_id = 359107176
    caption = "test"
    filename = "test.txt"
    content = "aaaaaaa".encode()

    try:
        await send_file_to_user(
            user_id, filename, content, caption, config.api.bot.token.get_secret_value()
        )
        print("File sent successfully!")
    except httpx.HTTPStatusError as e:
        print(f"Failed to send file: {e.response.json()}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
