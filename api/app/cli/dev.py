from cyclopts import App
from rich import print

from app.common.utils.s3 import AsyncS3Client

app = App(name="test", help="dev tests etc")

PROXIES = b"""
176.53.167.83:30042:sazanova-nadezda_ya_ru:6072b7fd12
45.134.29.254:30042:sazanova-nadezda_ya_ru:6072b7fd12
185.64.251.159:30042:sazanova-nadezda_ya_ru:6072b7fd12
84.54.8.245:30042:sazanova-nadezda_ya_ru:6072b7fd12
45.134.28.104:30042:sazanova-nadezda_ya_ru:6072b7fd12
176.53.164.101:30042:sazanova-nadezda_ya_ru:6072b7fd12
185.64.251.94:30042:sazanova-nadezda_ya_ru:6072b7fd12
85.31.50.7:30042:sazanova-nadezda_ya_ru:6072b7fd12
"""

ACCOUNTS_FILE = "accounts.zip"


@app.command
async def s3_url():
    async with AsyncS3Client() as s3:
        upload_url = await s3.presigned_put_url(
            "service/kukaryamba",
            meta={
                "customkey": "customvalue",
            },
        )

    print(upload_url)
