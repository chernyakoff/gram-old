from hatchet_sdk import ClientConfig, ClientTLSConfig, Hatchet

from config import config

params = {
    "token": config.hatchet.token,
    "tls_config": ClientTLSConfig(strategy="none"),
}
if "localhost" not in config.hatchet.host_port:
    params["host_port"] = config.hatchet.host_port

hatchet = Hatchet(config=ClientConfig(**params))
