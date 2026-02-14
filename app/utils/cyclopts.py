from cyclopts import App


def create_app(name: str, help: str = "cli command") -> App:
    return App(name=name, help=help)


def run_app(
    path: str,
    on_startup=None,
    usage: str = "Usage: python -m console [COMMAND] [OPTION]",
) -> App:
    """
    Project-local CLI bootstrap.

    Mirrors the old behavior from `console/__main__.py`:
    - create a root `cyclopts.App` (with custom usage)
    - load and register sub-apps from `path` (e.g. "console:app")
    - run optional startup hook (sync or async) before dispatching commands
    - start cyclopts meta command parsing via `app.meta()`
    """
    import asyncio
    import inspect

    from utils import vars

    app = App(usage=usage)

    for subapp in vars.load(path, App):
        app.command(subapp)

    @app.meta.default
    def _meta_default(*tokens: str):
        if on_startup is not None:
            result = on_startup()
            if inspect.isawaitable(result):
                asyncio.run(result)  # type: ignore
        app(tokens)

    app.meta()
    return app
