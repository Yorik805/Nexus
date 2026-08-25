#!/usr/bin/env python3
"""Official Nexus runtime startup entry point."""

from __future__ import annotations

import signal
import time

from runtime import NexusRuntime


def main() -> None:
    runtime = NexusRuntime()

    def _handle_shutdown(signum: int, _frame: object) -> None:
        print(f"Received signal {signum}; shutting down Nexus runtime.")
        runtime.stop()

    signal.signal(signal.SIGINT, _handle_shutdown)
    signal.signal(signal.SIGTERM, _handle_shutdown)

    runtime.start()

    try:
        while runtime.is_running:
            time.sleep(0.25)
    except KeyboardInterrupt:
        print("Keyboard interrupt received.")
    finally:
        runtime.stop()
        print("Nexus Runtime shutdown complete.")


if __name__ == "__main__":
    main()
