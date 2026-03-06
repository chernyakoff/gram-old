import subprocess
import sys

from watchfiles import run_process

GRACEFUL_TIMEOUT = 3  # секунд ждем shutdown, потом kill sdsd


def target():
    proc = subprocess.Popen([sys.executable, "-m", "app"])
    try:
        proc.wait()
    except KeyboardInterrupt:
        print("↪ KeyboardInterrupt: останавливаю uvicorn…")
        terminate(proc)


def terminate(proc: subprocess.Popen):
    """Попробовать завершить uvicorn аккуратно, а если не выйдет — убить."""
    if proc.poll() is None:  # процесс ещё жив
        proc.terminate()
        try:
            proc.wait(timeout=GRACEFUL_TIMEOUT)
        except subprocess.TimeoutExpired:
            print(
                f"⚠️  uvicorn не завершился за {GRACEFUL_TIMEOUT}s → принудительный kill"
            )
            proc.kill()


if __name__ == "__main__":
    print("👀 Watching for changes in ./app")
    run_process("./app", target=target)
