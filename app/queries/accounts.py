from tortoise.transactions import in_transaction

from models import orm


async def set_main_photo(account_id: int) -> None:
    """
    Ensure exactly one main photo exists (the latest by id), or none if no photos.
    """
    async with in_transaction():
        await orm.AccountPhoto.filter(account_id=account_id).update(main=False)
        max_photo = (
            await orm.AccountPhoto.filter(account_id=account_id).order_by("-id").first()
        )
        if max_photo:
            max_photo.main = True
            await max_photo.save()

