import subprocess
import sys
import time
from pathlib import Path

DIST_CORE = Path().parent / "dist" / "core"


def file_system(*args: object):
    return subprocess.run(
        [sys.executable, "scripts/pyboard.py", "--device", "/dev/cu.usbmodem0000000000001", "-f", *args]
    )


def main():
    subprocess.run(["rshell", "rm", "/flash", "-r"])

    time.sleep(5)

    for folder in ("", "utils"):
        file_system("mkdir", folder)

    for file in sorted(DIST_CORE.rglob("*.py")):
        file_system(
            "cp",
            file,
            f":{file.name}",
        )


if __name__ == "__main__":
    main()
