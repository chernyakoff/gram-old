from hatchet_sdk import ClientConfig, ClientTLSConfig, Hatchet

from app.config import config

hatchet = Hatchet(
    config=ClientConfig(
        # logger=logger,
        token=config.hatchet.token,
        tls_config=ClientTLSConfig(strategy="none"),
    )
)
