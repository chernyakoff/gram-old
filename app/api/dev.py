import subprocess
import sys

from watchfiles import run_process

GRACEFUL_TIMEOUT = 3  # seconds to wait before kill


def target():
    proc = subprocess.Popen([sys.executable, "-m", "api"])
    try:
        proc.wait()
    except KeyboardInterrupt:
        terminate(proc)


def terminate(proc: subprocess.Popen):
    if proc.poll() is None:
        proc.terminate()
        try:
            proc.wait(timeout=GRACEFUL_TIMEOUT)
        except subprocess.TimeoutExpired:
            proc.kill()


if __name__ == "__main__":
    # Watch whole repo-mounted /app tree.
    run_process(".", target=target)

