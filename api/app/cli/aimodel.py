from typing import Any, cast

from cyclopts import App
from openai import AsyncOpenAI
from rich import print

from app.config import config

app = App(name="aimodel", help="Generate OpenApi spec")


params = {
    "api_key": config.openai.api_key,
    "timeout": config.openai.timeout,
}
if config.openai.base_url:
    params["base_url"] = config.openai.base_url


client = AsyncOpenAI(**params)


@app.default
async def _(model: str):
    messages = [{"role": "user", "content": "Привет"}]
    try:
        raw_response = await client.responses.create(
            model=model,  # например "gpt-4.1" или "gpt-3.5-turbo"
            input=cast(Any, messages),
        )

        print(raw_response.output_text)  # completion.choices[0].message.content or ""
    except Exception as e:
        print(e)
