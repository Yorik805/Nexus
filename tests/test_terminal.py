"""Terminal plugin test suite."""

from __future__ import annotations

import sys
import tempfile
import time
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

from plugins.terminal import execute


def assert_success(response: dict) -> None:
    assert response["status"] == "SUCCESS", f"Expected SUCCESS, got {response}"


def assert_error(response: dict) -> None:
    assert response["status"] == "ERROR", f"Expected ERROR, got {response}"


def log(message: str) -> None:
    print(message, flush=True)


def make_temp_counter_script(temp_dir: str) -> str:
    script_path = Path(temp_dir) / "counter_script.py"
    script_path.write_text(
        """
import time
import sys
for i in range(1, 11):
    print(i)
    sys.stdout.flush()
    time.sleep(0.5)
"""
    )
    return str(script_path)


def test_foreground_execution() -> None:
    log("[STATIC] test_foreground_execution: verifying foreground command execution and cwd handling")
    command = [sys.executable, "-c", "import os; print('PWD=' + os.getcwd())"]
    with tempfile.TemporaryDirectory() as temp_dir:
        response = execute({
            "action": "EXECUTE",
            "data": {
                "command": command,
                "cwd": temp_dir,
                "dynamic": False,
            },
        })

        assert_success(response)
        data = response["data"]
        assert data["exit_code"] == 0
        assert "PWD=" in data["stdout"]
        assert Path(temp_dir).as_posix() in data["stdout"].replace("\\", "/")


def test_invalid_command() -> None:
    log("[STATIC] test_invalid_command: verifying invalid command handling")
    response = execute({
        "action": "EXECUTE",
        "data": {
            "command": "nonexistent-command-1234",
            "dynamic": False,
        },
    })
    assert_error(response)
    assert "Failed to launch" in response["message"]


def test_timeout() -> None:
    log("[STATIC] test_timeout: verifying foreground timeout handling")
    command = [sys.executable, "-c", "import time; time.sleep(5)"]
    response = execute({
        "action": "EXECUTE",
        "data": {
            "command": command,
            "dynamic": False,
            "timeout": 1,
        },
    })

    assert_error(response)
    assert "timed out" in response["message"].lower()


def test_dynamic_process_lifecycle() -> None:
    log("[DYNAMIC] test_dynamic_process_lifecycle: verifying dynamic process startup and completion")
    command = [sys.executable, "-c", "import time,sys; print('start'); sys.stdout.flush(); time.sleep(2); print('end');"]
    response = execute({
        "action": "EXECUTE",
        "data": {
            "command": command,
            "dynamic": True,
        },
    })

    assert_success(response)
    process_id = response["data"]["process_id"]
    assert response["data"]["status"] == "RUNNING"

    status_response = execute({
        "action": "STATUS",
        "data": {"process_id": process_id},
    })
    assert_success(status_response)
    assert status_response["data"]["status"] == "RUNNING"

    time.sleep(3)
    final_status = execute({
        "action": "STATUS",
        "data": {"process_id": process_id},
    })
    assert_success(final_status)
    assert final_status["data"]["status"] in {"COMPLETED", "FAILED"}
    assert "start" in final_status["data"]["stdout"]

def test_dynamic_process_update_properties() -> None:
    log("[DYNAMIC] test_dynamic_process_update_properties: verifying runtime property updates")
    with tempfile.TemporaryDirectory() as temp_dir:
        script_path = make_temp_counter_script(temp_dir)
        response = execute({
            "action": "EXECUTE",
            "data": {
                "command": [sys.executable, script_path],
                "cwd": temp_dir,
                "dynamic": True,
                "update_interval": 1000,
                "conversation_updates": True,
            },
        })

        assert_success(response)
        process_id = response["data"]["process_id"]

        update_response = execute({
            "action": "UPDATE",
            "data": {
                "process_id": process_id,
                "update_interval": 250,
                "conversation_updates": False,
                "metadata": {"phase": "updated"},
            },
        })

        assert_success(update_response)
        updated_process = update_response["data"]["process"]
        assert updated_process["update_interval"] == 250
        assert updated_process["conversation_updates"] is False
        assert updated_process["metadata"] == {"phase": "updated"}

        status_response = execute({
            "action": "STATUS",
            "data": {"process_id": process_id},
        })
        assert_success(status_response)
        assert status_response["data"]["update_interval"] == 250
        assert status_response["data"]["conversation_updates"] is False
        assert status_response["data"]["metadata"] == {"phase": "updated"}

        stop_response = execute({
            "action": "STOP",
            "data": {"process_id": process_id},
        })
        assert_success(stop_response)
        status = stop_response["data"].get("status")
        assert status in {"STOPPED", "COMPLETED", "FAILED", "TIMED_OUT"}, f"Unexpected status: {status}"


def test_dynamic_counter_and_mid_run_stop() -> None:
    log("[DYNAMIC] test_dynamic_counter_and_mid_run_stop: verifying live stdout capture and stop behavior")
    with tempfile.TemporaryDirectory() as temp_dir:
        script_path = make_temp_counter_script(temp_dir)
        response = execute({
            "action": "EXECUTE",
            "data": {
                "command": [sys.executable, script_path],
                "cwd": temp_dir,
                "dynamic": True,
                "update_interval": 500,
                "conversation_updates": True,
            },
        })

        assert_success(response)
        process_id = response["data"]["process_id"]
        assert response["data"]["status"] == "RUNNING"

        timeout = time.time() + 5
        stdout_seen = False
        while time.time() < timeout:
            status_response = execute({
                "action": "STATUS",
                "data": {"process_id": process_id},
            })
            assert_success(status_response)
            assert status_response["data"]["status"] in {"RUNNING", "COMPLETED", "FAILED"}
            assert status_response["data"]["continue_flag"] is True
            assert status_response["data"]["update_interval"] == 500
            assert status_response["data"]["conversation_updates"] is True

            if "1" in status_response["data"]["stdout"]:
                stdout_seen = True
                break

            if status_response["data"]["status"] != "RUNNING":
                break

            time.sleep(0.2)

        assert stdout_seen, f"Expected counter output in process stdout, got: {status_response['data']['stdout']}"

        stop_response = execute({
            "action": "STOP",
            "data": {"process_id": process_id},
        })
        assert_success(stop_response)
        status = stop_response["data"].get("status")
        assert status in {"STOPPED", "COMPLETED", "FAILED", "TIMED_OUT"}, f"Unexpected status: {status}"

        final_status = execute({
            "action": "STATUS",
            "data": {"process_id": process_id},
        })
        assert_success(final_status)
        final_status_value = final_status["data"]["status"]
        assert final_status_value in {"STOPPED", "COMPLETED", "FAILED", "TIMED_OUT"}, f"Unexpected final status: {final_status_value}"
        if final_status_value == "STOPPED":
            assert final_status["data"]["continue_flag"] is False
        assert final_status["data"]["finished_at"] is not None
        assert final_status["data"]["runtime"] is not None
        assert "1" in final_status["data"]["stdout"]


def test_stop_and_cleanup() -> None:
    log("[DYNAMIC] test_stop_and_cleanup: verifying stop and cleanup of a running process")
    command = [sys.executable, "-c", "import time; print('running'); time.sleep(10)"]
    response = execute({
        "action": "EXECUTE",
        "data": {
            "command": command,
            "dynamic": True,
        },
    })
    assert_success(response)
    process_id = response["data"]["process_id"]

    stop_response = execute({
        "action": "STOP",
        "data": {"process_id": process_id},
    })
    assert_success(stop_response)
    status = stop_response["data"]["status"]
    assert status in {"STOPPED", "COMPLETED", "FAILED", "TIMED_OUT"}, f"Unexpected status: {status}"

    cleanup_response = execute({
        "action": "CLEANUP",
        "data": {},
    })
    assert_success(cleanup_response)
    assert process_id in cleanup_response["data"]["removed_process_ids"]


def test_list_multiple_processes() -> None:
    log("[DYNAMIC] test_list_multiple_processes: verifying multiple concurrent process tracking")
    command_one = [sys.executable, "-c", "import time; print('p1'); time.sleep(2)"]
    command_two = [sys.executable, "-c", "import time; print('p2'); time.sleep(2)"]

    response_one = execute({
        "action": "EXECUTE",
        "data": {"command": command_one, "dynamic": True},
    })
    response_two = execute({
        "action": "EXECUTE",
        "data": {"command": command_two, "dynamic": True},
    })

    assert_success(response_one)
    assert_success(response_two)

    list_response = execute({"action": "LIST", "data": {}})
    assert_success(list_response)
    process_ids = {entry["process_id"] for entry in list_response["data"]["processes"]}

    assert response_one["data"]["process_id"] in process_ids
    assert response_two["data"]["process_id"] in process_ids

    execute({"action": "STOP", "data": {"process_id": response_one["data"]["process_id"]}})
    execute({"action": "STOP", "data": {"process_id": response_two["data"]["process_id"]}})


if __name__ == "__main__":
    log("=== STATIC TESTS ===")
    test_foreground_execution()
    test_invalid_command()
    test_timeout()
    log("=== STATIC TESTS COMPLETED ===")

    log("=== DYNAMIC TESTS ===")
    test_dynamic_process_lifecycle()
    test_dynamic_process_update_properties()
    test_dynamic_counter_and_mid_run_stop()
    test_stop_and_cleanup()
    test_list_multiple_processes()
    log("=== DYNAMIC TESTS COMPLETED ===")

    print("All terminal plugin tests passed.")
#hi