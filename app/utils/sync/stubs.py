import importlib
import inspect
from pathlib import Path
from typing import Any

from pydantic import BaseModel
from rich import print

from .config import CodegenConfig, StubsData, TaskData, WorkflowData, header


def _unwrap_validator(v: Any) -> type[BaseModel] | None:
    """
    Hatchet stores validators as pydantic TypeAdapter instances.
    We want the underlying BaseModel class to generate models.py and stubs.
    """

    if v is None:
        return None

    # pydantic.TypeAdapter keeps the original python type on _type
    t = getattr(v, "_type", None) or v

    if inspect.isclass(t) and issubclass(t, BaseModel):
        if "EmptyModel" in t.__name__:
            return None
        return t

    return None


def iter_task_modules(tasks_package: str) -> list[str]:
    pkg = importlib.import_module(tasks_package)
    names: list[str] = []

    # Namespace packages (no __init__.py) don't work well with pkgutil.walk_packages.
    # Scan filesystem instead.
    for root in list(getattr(pkg, "__path__", []) or []):
        root_path = Path(str(root))
        for py in root_path.rglob("*.py"):
            if py.name == "__init__.py":
                continue
            rel = py.relative_to(root_path).with_suffix("")
            parts = ".".join(rel.parts)
            names.append(f"{tasks_package}.{parts}")

    return sorted(set(names))


def iter_workflows(tasks_package: str) -> list[Any]:
    """
    Import all task modules under a worker tasks package and return Hatchet workflow objects.

    Intentionally does NOT import workers.<name>.worker to avoid RPC calls in Hatchet Worker constructor.
    """

    workflows: dict[str, Any] = {}

    for module_name in iter_task_modules(tasks_package):
        try:
            module = importlib.import_module(module_name)
        except Exception as e:
            print(f"⚠️  Не удалось импортировать {module_name}: {e}")
            continue

        for _, obj in inspect.getmembers(module):
            if not (hasattr(obj, "name") and hasattr(obj, "tasks")):
                continue

            name = getattr(obj, "name", None)
            tasks = getattr(obj, "tasks", None)
            if isinstance(name, str) and isinstance(tasks, list) and tasks:
                workflows[name] = obj

    return list(workflows.values())


def get_stubs_data(tasks_package: str) -> StubsData:
    tasks: list[TaskData] = []
    workflows: list[WorkflowData] = []

    for wf in iter_workflows(tasks_package):
        for step in getattr(wf, "tasks", []) or []:
            step_name = getattr(step, "name", None)
            workflow = getattr(step, "workflow", None)
            workflow_name = getattr(workflow, "name", None)

            validators = getattr(step, "validators", None)
            workflow_input = getattr(validators, "workflow_input", None)
            step_output = getattr(validators, "step_output", None)

            if not isinstance(step_name, str):
                continue

            # "task" in our codebase is usually a 1-step workflow.
            if isinstance(workflow_name, str) and step_name == workflow_name:
                tasks.append(
                    TaskData(
                        name=step_name,
                        input_model=_unwrap_validator(workflow_input),
                        output_model=_unwrap_validator(step_output),
                    )
                )
            else:
                workflows.append(
                    WorkflowData(
                        name=str(workflow_name or step_name),
                        input_model=_unwrap_validator(workflow_input),
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
    gen: list[str] = []
    gen.append(header)
    gen.append("")
    gen.append("from . import models")
    gen.append(cfg.client_import)
    gen.append("")

    for t in stubs_data.tasks:
        args = [f'name=\"{t.name}\"']
        if t.input_model is not None:
            args.append(f"input_validator=models.{t.input_model.__name__}")
        if t.output_model is not None:
            args.append(f"output_validator=models.{t.output_model.__name__}")
        varname = t.name.replace("-", "_")
        gen.append(
            f"{varname} = hatchet.stubs.task(\n    {',\n    '.join(args)},\n)"
        )
        gen.append("")

    output_path = Path(cfg.output_dir).joinpath("tasks.py")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write("\n".join(gen))

    print(f"✅ {output_path}")


def generate_workflows(cfg: CodegenConfig, stubs_data: StubsData):
    if not stubs_data.workflows:
        return
    gen: list[str] = []
    gen.append(header)
    gen.append("")
    gen.append("from . import models")
    gen.append(cfg.client_import)
    gen.append("")

    for t in stubs_data.workflows:
        args = [f'name="{t.name}"']
        if t.input_model is not None:
            args.append(f"input_validator=models.{t.input_model.__name__}")
        varname = t.name.replace("-", "_")
        gen.append(f"{varname} = hatchet.stubs.workflow(\n    {',\n    '.join(args)},\n)")
        gen.append("")

    output_path = Path(cfg.output_dir).joinpath("workflows.py")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write("\n".join(gen))

    print(f"✅ {output_path}")
