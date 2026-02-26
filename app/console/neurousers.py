from rich import print

from models import orm
from utils.cyclopts import create_app
from utils.neurousers_api import (
    CreateUserRequest,
    InternalUsernamesRequest,
    NeuroUsersClient,
)

app = create_app("neurousers", "sync neurogram users to neurousers")


@app.command
async def sync_users(*, limit: int = 0, offset: int = 0, dry_run: bool = False):
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
            print(f"[dim]DRY-RUN[/dim] id={user.id}")
        return

    async with NeuroUsersClient() as client:
        for user in users:
            try:
                result = await client.create_or_update_user(
                    CreateUserRequest(
                        id=user.id,
                        username=user.username,
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


@app.command
async def sync_usernames(
    *,
    limit: int = 0,
    offset: int = 0,
    only_missing: bool = False,
    batch_size: int = 500,
    dry_run: bool = False,
):
    """Sync username from neurousers API to local neurogram users table."""
    if batch_size <= 0:
        raise ValueError("batch_size must be > 0")

    print("[cyan]Source[/cyan]: neurousers internal API")
    print("[cyan]Target[/cyan]: local gram users table")

    qs = orm.User.all().order_by("id")
    if only_missing:
        qs = qs.filter(username__isnull=True)
    if offset > 0:
        qs = qs.offset(offset)
    if limit > 0:
        qs = qs.limit(limit)

    local_users = await qs
    if not local_users:
        print("[yellow]No local users to sync[/yellow]")
        return

    local_by_id = {u.id: u for u in local_users}
    local_ids = list(local_by_id.keys())

    matched = 0
    updated = 0
    skipped = 0

    async with NeuroUsersClient() as client:
        for i in range(0, len(local_ids), batch_size):
            batch_ids = local_ids[i : i + batch_size]
            response = await client.internal_get_usernames(
                InternalUsernamesRequest(user_ids=batch_ids)
            )

            for item in response.items:
                if item.username is None:
                    continue

                local_user = local_by_id.get(item.user_id)
                if local_user is None:
                    continue

                matched += 1
                if local_user.username == item.username:
                    skipped += 1
                    continue

                if dry_run:
                    print(
                        f"[dim]DRY-RUN[/dim] id={item.user_id} username: {local_user.username!r} -> {item.username!r}"
                    )
                    updated += 1
                    continue

                local_user.username = item.username
                await local_user.save(update_fields=["username"])
                updated += 1

    total = len(local_users)
    missing_in_source = total - matched
    print(
        "[green]Done[/green] "
        f"total_local={total} matched={matched} updated={updated} "
        f"unchanged={skipped} missing_in_source={missing_in_source}"
    )
