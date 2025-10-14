from .config import SyncConfig, get_config
from .models import generate_models
from .modules import copy_modules
from .stubs import generate_tasks, generate_workflows, get_stubs_data, get_worker


def codegen(cfg: SyncConfig):
    worker = get_worker(cfg.codegen.worker_module)
    if not worker:
        return
    data = get_stubs_data(worker)
    generate_tasks(cfg.codegen, data)
    generate_workflows(cfg.codegen, data)
    generate_models(cfg.codegen, data)


def run():
    cfg = get_config()
    copy_modules(cfg)
    # codegen(cfg)


__all__ = ["run"]
