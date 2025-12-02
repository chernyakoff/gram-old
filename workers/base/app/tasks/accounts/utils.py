import tempfile
import zipfile
from io import BytesIO

from aiopath import AsyncPath

from app.common.utils.account import AccountFile


async def unzip_tmpfile(tmpfile: str) -> AsyncPath:
    tmp_dir = AsyncPath(tempfile.mkdtemp())  # временная папка

    zip_path = AsyncPath(tmpfile)
    if not await zip_path.exists():
        raise ValueError("tmpfile не найден")

    data = await zip_path.read_bytes()

    zip_bytes = BytesIO(data)
    with zipfile.ZipFile(zip_bytes) as zf:
        for member in zf.infolist():
            member_path = tmp_dir / member.filename
            if member.is_dir():
                await member_path.mkdir(parents=True, exist_ok=True)
            else:
                await (member_path.parent).mkdir(parents=True, exist_ok=True)
                file_data = zf.read(member)
                await member_path.write_bytes(file_data)

    return tmp_dir


async def get_account_files(tmp_dir: AsyncPath) -> list[AccountFile]:
    files = [f async for f in tmp_dir.glob("*")]
    json_files = {f.stem: f for f in files if f.suffix == ".json"}
    session_files = {f.stem: f for f in files if f.suffix == ".session"}
    result = []
    for name in json_files:
        if name in session_files:
            result.append(
                AccountFile(session=session_files[name], json=json_files[name])
            )

    return result
