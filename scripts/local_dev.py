"""Script to manage running collector and web service for local development."""

import subprocess
import sys
import time

_PROGRAMS = {
    "collector": [sys.executable, "-m", "meshinfo", "collector"],
    "web": [
        sys.executable,
        "-m",
        "gunicorn",
        "--workers=1",
        "--reload",
        "meshinfo.web:create_app()",
    ],
}


def main():
    sub_processes = {}

    for label, prog_args in _PROGRAMS.items():
        print(f"Starting {label}: {prog_args}")
        sub_processes[label] = subprocess.Popen(prog_args)

    try:
        while True:
            # TODO: check to see if sub-processes exited on their own?
            time.sleep(5)
    except KeyboardInterrupt:
        print("\nCanceling processes...")
        for label, process in sub_processes.items():
            if process.poll() is not None:
                print(f"Process {label} already finished")
                continue
            print(f"Terminating {label}")
            process.terminate()
            try:
                process.wait(5)
            except subprocess.TimeoutExpired:
                print(f"Killing {label}")
                process.kill()


if __name__ == "__main__":
    sys.exit(main())
