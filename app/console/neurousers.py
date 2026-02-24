from rich import print

from models import orm
from utils.cyclopts import create_app
from utils.neurousers_api import CreateUserRequest, NeuroUsersClient

app = create_app("neurousers", "sync neurogram users to neurousers")


@app.command
async def sync_users(limit: int = 0, offset: int = 0, dry_run: bool = False):
    qs = orm.User.all().order_by("id")
    if offset > 0:
        qs = qs.offset(offset)
    if limit > 0:
        qs = qs.limit(limit)

    users = await qs
    total = len(users)
    if total == 0:
        print("[yellow]No users to sync[/yellow]")
        return

    print(f"[cyan]Syncing {total} users to neurousers...[/cyan]")
    created = 0
    updated = 0
    failed = 0

    if dry_run:
        for user in users:
            print(f"[dim]DRY-RUN[/dim] id={user.id} username={user.username}")
        return

    async with NeuroUsersClient() as client:
        for user in users:
            try:
                result = await client.create_or_update_user(
                    CreateUserRequest(
                        id=user.id,
                        username=user.username,
                        first_name=user.first_name,
                        last_name=user.last_name,
                        photo_url=user.photo_url,
                        role=int(user.role),
                        license_end_date=user.license_end_date,
                        balance=user.balance,
                        ref_code=user.ref_code,
                        or_api_key=user.or_api_key,
                        or_api_hash=user.or_api_hash,
                        or_model=user.or_model,
                    )
                )
            except Exception as exc:
                failed += 1
                print(f"[red]FAILED[/red] id={user.id}: {exc}")
                continue

            if result.status == "created":
                created += 1
            else:
                updated += 1

    print(
        f"[green]Done[/green] total={total} created={created} updated={updated} failed={failed}"
    )
