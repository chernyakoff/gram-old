from tortoise import BaseDBAsyncClient


async def upgrade(db: BaseDBAsyncClient) -> str:
    return '''
        CREATE TABLE IF NOT EXISTS mob_proxies (
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    id SERIAL NOT NULL PRIMARY KEY,
    host VARCHAR(64) NOT NULL,
    port INT NOT NULL,
    username VARCHAR(255) NOT NULL,
    password VARCHAR(255) NOT NULL,
    change_url TEXT NOT NULL,
    active BOOL NOT NULL DEFAULT True,
    country VARCHAR(2) NOT NULL,
    locked_until TIMESTAMPTZ,
    lock_session VARCHAR(36),
    failures INT NOT NULL DEFAULT 0,
    user_id BIGINT NOT NULL REFERENCES users (id) ON DELETE CASCADE,
    CONSTRAINT uid_mob_proxies_host_05a39c UNIQUE (host, port, username, password)
);'''


async def downgrade(db: BaseDBAsyncClient) -> str:
    return '''
        DROP TABLE IF EXISTS mob_proxies;'''
