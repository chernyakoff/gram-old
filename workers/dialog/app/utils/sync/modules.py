from .config import SyncConfig


def copy_modules(cfg: SyncConfig):
    for module in cfg.modules.modules:
        src_root = cfg.modules.src / module
        dest_root = cfg.modules.dest / module

        if not src_root.exists():
            print(f"⚠️  Пропускаю {src_root}, не существует")
            continue

        for src_file in src_root.rglob("*.py"):
            rel_path = src_file.relative_to(src_root)
            dest_file = dest_root / rel_path

            # Создаём директорию под файл
            dest_file.parent.mkdir(parents=True, exist_ok=True)

            # Читаем исходник
            with src_file.open("r", encoding="utf-8") as f:
                content = f.read()

            # Записываем с заголовком
            with dest_file.open("w", encoding="utf-8") as f:
                f.write(cfg.codegen.header + content)

            print(f"✅ Скопирован {src_file} → {dest_file}")
