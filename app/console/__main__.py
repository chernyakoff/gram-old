from config import init_db
from utils.cyclopts import run_app

if __name__ == "__main__":
    run_app(
        path="console:app",
        on_startup=init_db,
        usage="Usage: ./task cli [COMMAND] [OPTION]",
    )
