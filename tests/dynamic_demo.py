"""Demo harness for the Terminal Plugin dynamic features.

Run from the repository root:

python3 tests/dynamic_demo.py

This script will:
- start `tests/dynamic_counter.py` in dynamic mode
- poll `STATUS` periodically and print updates
- send an `UPDATE` to change properties mid-run
- stop the process and show final status
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

from plugins.terminal import execute
import os


def log(msg: str) -> None:
    print(msg, flush=True)


def main() -> None:
    script = str(Path(__file__).parent / "dynamic_counter.py")
    log(f"Starting dynamic counter: {script}")

    response = execute({
        "action": "EXECUTE",
        "data": {
            "command": [sys.executable, script],
            "cwd": str(Path(__file__).parent),
            "dynamic": True,
            "update_interval": 1000,
            "conversation_updates": False,
        },
    })

    if response.get("status") != "SUCCESS":
        log(f"Failed to start process: {response}")
        return

    pid = response["data"]["process_id"]
    log(f"Started process_id={pid}")

    # Poll and print a few status updates
    for _ in range(5):
        time.sleep(1)
        status = execute({"action": "STATUS", "data": {"process_id": pid}})
        log(f"STATUS: {status}")

    # Update properties mid-run
    log("Sending UPDATE: set update_interval=250, conversation_updates=True, metadata.phase=demo")
    upd = execute({
        "action": "UPDATE",
        "data": {
            "process_id": pid,
            "update_interval": 250,
            "conversation_updates": True,
            "metadata": {"phase": "demo"},
        },
    })
    log(f"UPDATE response: {upd}")

    # Poll a few more times
    for _ in range(5):
        time.sleep(1)
        status = execute({"action": "STATUS", "data": {"process_id": pid}})
        log(f"STATUS: {status}")

    # Stop the process
    log("Stopping process")
    stop = execute({"action": "STOP", "data": {"process_id": pid}})
    log(f"STOP response: {stop}")

    final = execute({"action": "STATUS", "data": {"process_id": pid}})
    log(f"FINAL STATUS: {final}")


if __name__ == "__main__":
    main()
