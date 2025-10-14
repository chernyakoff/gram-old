from hatchet_sdk import ClientConfig, ClientTLSConfig, Hatchet

# from app.common.utils.logger import logger
from app.config import config

hatchet = Hatchet(
    config=ClientConfig(
        # logger=logger,
        host_port=config.hatchet.host_port,
        token=config.hatchet.token,
        tls_config=ClientTLSConfig(strategy="none"),
    )
)
