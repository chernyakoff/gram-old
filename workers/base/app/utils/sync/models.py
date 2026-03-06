import ast
import copy
import inspect
import typing
from pathlib import Path

import astor
from pydantic import BaseModel
from rich import print

from .config import header


def get_validators(stubs_data) -> list[type]:
    initial = set()
    for t in stubs_data.tasks:
        initial.add(t.input_model)
        initial.add(t.output_model)
    for w in stubs_data.workflows:
        initial.add(w.input_model)

    all_models = set()
    for cls in initial:
        if cls is not None:
            all_models |= collect_dependencies(cls, seen=set())
    return list(all_models)


def collect_dependencies(cls: type, seen: set[type]) -> set[type]:
    """Рекурсивно собираем все Pydantic модели, которые нужны для cls"""
    if cls in seen:
        return set()
    seen.add(cls)

    deps = {cls}
    hints = typing.get_type_hints(cls, include_extras=True)

    for field_type in hints.values():
        origin = typing.get_origin(field_type)
        args = typing.get_args(field_type)

        # если поле — это другая Pydantic модель
        if inspect.isclass(field_type) and issubclass(field_type, BaseModel):
            deps |= collect_dependencies(field_type, seen)

        # если поле типа List[OtherModel], Optional[OtherModel], Dict[str, OtherModel], ...
        for arg in args:
            if inspect.isclass(arg) and issubclass(arg, BaseModel):
                deps |= collect_dependencies(arg, seen)

    return deps


def extract_names(node: ast.AST) -> set[str]:
    names = set()
    if isinstance(node, ast.Name):
        names.add(node.id)
    elif isinstance(node, ast.Attribute):
        names.add(node.attr)
    elif isinstance(node, ast.Subscript):
        names.update(extract_names(node.value))
        if node.slice is not None:
            names.update(extract_names(node.slice))
    elif isinstance(node, (ast.Tuple, ast.List)):
        for elt in node.elts:
            names.update(extract_names(elt))
    elif isinstance(node, ast.Constant):
        pass
    elif isinstance(node, ast.Call):
        names.update(extract_names(node.func))
        for arg in node.args:
            names.update(extract_names(arg))
    return names


def get_used_names(class_node: ast.ClassDef) -> set[str]:
    used = set()
    # базовые классы
    for base in class_node.bases:
        if isinstance(base, ast.Name):
            used.add(base.id)
        elif isinstance(base, ast.Attribute):
            used.add(base.attr)
    # тело класса
    for node in class_node.body:
        if isinstance(node, ast.AnnAssign) and node.annotation:
            used.update(extract_names(node.annotation))
        elif isinstance(node, ast.Assign) and isinstance(node.value, ast.Call):
            used.update(extract_names(node.value.func))
    return used


def filter_imports(import_nodes, used_names):
    filtered = []
    for node in import_nodes:
        if isinstance(node, ast.Import):
            names = [
                alias
                for alias in node.names
                if alias.asname in used_names or alias.name in used_names
            ]
            if names:
                new_node = copy.deepcopy(node)
                new_node.names = names
                filtered.append(new_node)
        elif isinstance(node, ast.ImportFrom):
            names = [
                alias
                for alias in node.names
                if alias.asname in used_names or alias.name in used_names
            ]
            if names:
                new_node = copy.deepcopy(node)
                new_node.names = names
                filtered.append(new_node)
    return filtered


def topo_sort_classes(classes: list[ast.ClassDef]) -> list[ast.ClassDef]:
    name_to_node = {cls.name: cls for cls in classes}
    deps = {cls.name: get_used_names(cls) & name_to_node.keys() for cls in classes}

    sorted_classes = []
    visited = {}

    def visit(name: str):
        if visited.get(name) == "perm":
            return
        if visited.get(name) == "temp":
            raise ValueError("Цикл в зависимостях классов!")
        visited[name] = "temp"
        for dep in deps[name]:
            visit(dep)
        visited[name] = "perm"
        sorted_classes.append(name_to_node[name])

    for name in name_to_node:
        if name not in visited:
            visit(name)

    return sorted_classes


def generate_models(cfg, stubs_data):
    validators = get_validators(stubs_data)
    # print("✅ Собраны модели:", [cls.__name__ for cls in validators])
    all_import_nodes = []
    all_class_nodes = []

    for cls in validators:
        file_path = inspect.getfile(cls)

        with open(file_path, "r", encoding="utf-8") as f:
            source = f.read()
        tree = ast.parse(source)

        # находим класс
        class_node = next(
            (
                n
                for n in tree.body
                if isinstance(n, ast.ClassDef) and n.name == cls.__name__
            ),
            None,
        )
        if class_node is None:
            raise ValueError(f"Class {cls.__name__} not found in {file_path}")
        all_class_nodes.append(class_node)

        # используемые имена
        used_names = get_used_names(class_node)

        # фильтруем импорты
        import_nodes = [
            n for n in tree.body if isinstance(n, (ast.Import, ast.ImportFrom))
        ]
        filtered_imports = filter_imports(import_nodes, used_names)
        all_import_nodes.extend(filtered_imports)

    # уникализируем импорты
    unique_imports = {ast.dump(node): node for node in all_import_nodes}.values()

    # формируем код
    imports_code = "\n".join(astor.to_source(node).strip() for node in unique_imports)
    sorted_classes = topo_sort_classes(all_class_nodes)
    classes_code = "\n\n".join(astor.to_source(node) for node in sorted_classes)
    final_code = header + "\n\n" + imports_code + "\n\n" + classes_code

    # пишем файл
    output_path = Path(cfg.output_dir).joinpath("models.py")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(final_code)

    print(f"✅ {output_path}")
