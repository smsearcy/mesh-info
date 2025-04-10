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
        print(f"Starting {label}: {' '.join(prog_args)}")
        sub_processes[label] = subprocess.Popen(prog_args)

    try:
        while True:
            if any(proc.poll() is not None for proc in sub_processes.values()):
                # One of the processes is no longer running, so abort
                break
            time.sleep(2)
        print("\nDetected that a process ended, cleaning up")
        for label, process in sub_processes.items():
            if process.poll() is not None:
                print(f"Process {label} already finished")
                continue
            print(f"Terminating {label}")
            process.terminate()
    except KeyboardInterrupt:
        print("\nKeyboard interrupt detected, cleaning up")
        # The SIGINT will be automatically passed to the processes within the group
    finally:
        for label, process in sub_processes.items():
            try:
                process.wait(5)
            except subprocess.TimeoutExpired:
                print(f"Killing {label}")
                process.kill()


if __name__ == "__main__":
    sys.exit(main())
