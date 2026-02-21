from pathlib import Path

from rich import print

from .config import CodegenConfig, SyncConfig
from .models import generate_models
from .stubs import generate_tasks, generate_workflows, get_stubs_data

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def discover_workers(workers_dir: Path) -> list[str]:
    if not workers_dir.exists():
        return []
    names: list[str] = []
    for p in sorted(workers_dir.iterdir()):
        if not p.is_dir():
            continue
        if p.name.startswith(".") or p.name == "__pycache__":
            continue
        if (p / "worker.py").is_file() or (p / "task").is_dir() or (p / "tasks").is_dir():
            names.append(p.name)
    return names


def resolve_tasks_package(workers_dir: Path, worker: str) -> str:
    worker_dir = workers_dir / worker
    if (worker_dir / "tasks").is_dir():
        return f"workers.{worker}.tasks"
    if (worker_dir / "task").is_dir():
        return f"workers.{worker}.task"
    return f"workers.{worker}"


def codegen_one(sync_cfg: SyncConfig, workers_dir: Path, worker: str):
    tasks_package = resolve_tasks_package(workers_dir, worker)
    output_dir = sync_cfg.output_root / worker

    cfg = CodegenConfig(
        worker=worker,
        tasks_package=tasks_package,
        output_dir=output_dir,
        client_import=sync_cfg.client_import,
    )

    data = get_stubs_data(tasks_package)
    generate_tasks(cfg, data)
    generate_workflows(cfg, data)
    generate_models(cfg, data)


def run():
    sync_cfg = SyncConfig.load(PROJECT_ROOT / "pyproject.toml")
    workers_dir = (PROJECT_ROOT / sync_cfg.workers_dir).resolve()
    sync_cfg.output_root = (PROJECT_ROOT / sync_cfg.output_root).resolve()

    workers = discover_workers(workers_dir)
    if sync_cfg.include is not None:
        workers = [w for w in workers if w in set(sync_cfg.include)]
    if sync_cfg.exclude:
        workers = [w for w in workers if w not in set(sync_cfg.exclude)]

    if not workers:
        print(f"⚠️  No workers discovered in {workers_dir}")
        return

    for w in workers:
        print(f"🔧 codegen: {w}")
        codegen_one(sync_cfg, workers_dir, w)


__all__ = ["run"]
