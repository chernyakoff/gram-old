import importlib
import inspect
from pathlib import Path
from typing import Any

from hatchet_sdk import Worker
from rich import print

from .config import CodegenConfig, StubsData, TaskData, WorkflowData, header


def get_worker(worker_module: str) -> Worker | None:
    try:
        module = importlib.import_module(worker_module)
        for _, obj in inspect.getmembers(module):
            if isinstance(obj, Worker):
                return obj
    except ImportError as e:
        print(f"Не удалось импортировать {worker_module}: {e}")
        return None
    except Exception as e:
        print(f"Ошибка при поиске Worker: {e}")
        return None
    return None


def get_validator(v: type[Any] | None) -> type[Any] | None:
    return v if "EmptyModel" not in str(v) else None


def get_stubs_data(worker: Worker) -> StubsData:
    tasks = []
    workflows = []
    for _, task in worker.action_registry.items():
        if task.name == task.workflow.name:
            tasks.append(
                TaskData(
                    name=task.name,
                    input_model=get_validator(task.validators.workflow_input),  # type: ignore
                    output_model=get_validator(task.validators.step_output),  # type: ignore
                )
            )
        else:
            workflows.append(
                WorkflowData(
                    name=task.workflow.name,
                    input_model=get_validator(task.validators.workflow_input),
                )
            )

    return StubsData(tasks, workflows)


def get_validators(stubs_data: StubsData) -> list[type[Any]]:
    classes = set()
    for t in stubs_data.tasks:
        classes.add(t.input_model)
        classes.add(t.output_model)
    for w in stubs_data.workflows:
        classes.add(w.input_model)
    return [c for c in classes if c is not None]


def generate_tasks(cfg: CodegenConfig, stubs_data: StubsData):
    if not stubs_data.tasks:
        return
    gen = []
    gen.append(header)
    gen.append("")
    gen.append("from . import models")
    gen.append(cfg.client_import)
    gen.append("")

    for t in stubs_data.tasks:
        args = [f'name="{t.name}"']
        if t.input_model is not None:
            args.append(f"input_validator=models.{t.input_model.__name__}")
        if t.output_model is not None:
            args.append(f"output_validator=models.{t.output_model.__name__}")
        varname = t.name.replace("-", "_")
        gen.append(
            f"{varname} = {cfg.client_name}.stubs.task(\n    {',\n    '.join(args)},\n)"
        )
        gen.append("")

    output_path = Path(f"{cfg.output_dir}").joinpath("tasks.py")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write("\n".join(gen))

    print(f"✅ {output_path}")


def generate_workflows(cfg: CodegenConfig, stubs_data: StubsData):
    if not stubs_data.workflows:
        return
    gen = []
    gen.append(header)

    gen.append("from . import models")
    gen.append(cfg.client_import)
    gen.append("")
    for t in stubs_data.workflows:
        args = [f'name="{t.name}"']
        if t.input_model is not None:
            args.append(f"input_validator=models.{t.input_model.__name__}")
        varname = t.name.replace("-", "_")
        gen.append(
            f"{varname} = {cfg.client_name}.stubs.workflow(\n"
            f"  {',\n    '.join(args)},\n"
            f")"
        )
        gen.append("")

    output_path = Path(f"{cfg.output_dir}").joinpath("workflows.py")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write("\n".join(gen))

    print(f"✅ {output_path}")
