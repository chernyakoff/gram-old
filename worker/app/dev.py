import subprocess
import sys

from watchfiles import run_process


def target():
    try:
        subprocess.run([sys.executable, "-m", "app"])
    except KeyboardInterrupt:
        print("↪ Подпроцесс остановлен вручную")


if __name__ == "__main__":
    run_process("./app", target=target)
