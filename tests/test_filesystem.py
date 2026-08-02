#!/usr/bin/env python3
"""Comprehensive test suite for the Nexus File System Plugin.

Tests all 12 operations with various scenarios to ensure correctness
and compliance with the Plugin Standard.
"""

from __future__ import annotations

import json
import os
import shutil
import sys
import tempfile
from pathlib import Path

# Import the plugin
from plugins.filesystem import execute


def print_header(title: str) -> None:
    """Print a formatted test header."""
    print(f"\n{'=' * 60}")
    print(f"  {title}")
    print(f"{'=' * 60}")


def print_request(action: str, data: dict) -> None:
    """Print a formatted request."""
    print(f"\n→ Request: {action}")
    print(f"  {json.dumps(data, indent=2)}")


def print_response(response: dict) -> None:
    """Print a formatted response."""
    status = response.get("status", "UNKNOWN")
    message = response.get("message", "")
    print(f"\n← Response: {status}")
    print(f"  Message: {message}")
    if response.get("data"):
        print(f"  Data: {json.dumps(response.get('data', {}), indent=2)}")


def test_write(temp_dir: Path) -> bool:
    """Test WRITE operation."""
    print_header("Test: WRITE Operation")

    test_file = temp_dir / "test.txt"
    content = "Hello, File System Plugin!"

    request = {
        "action": "WRITE",
        "data": {
            "path": str(test_file),
            "content": content,
        }
    }

    print_request("WRITE", request["data"])
    response = execute(request)
    print_response(response)

    if response["status"] != "SUCCESS":
        print("❌ WRITE test failed: Expected SUCCESS")
        return False

    if not test_file.exists():
        print("❌ WRITE test failed: File was not created")
        return False

    if test_file.read_text() != content:
        print("❌ WRITE test failed: File content mismatch")
        return False

    print("✅ WRITE test passed")
    return True


def test_read(temp_dir: Path) -> bool:
    """Test READ operation."""
    print_header("Test: READ Operation")

    test_file = temp_dir / "test.txt"
    expected_content = test_file.read_text()

    request = {
        "action": "READ",
        "data": {
            "path": str(test_file)
        }
    }

    print_request("READ", request["data"])
    response = execute(request)
    print_response(response)

    if response["status"] != "SUCCESS":
        print("❌ READ test failed: Expected SUCCESS")
        return False

    if response["data"].get("content") != expected_content:
        print("❌ READ test failed: Content mismatch")
        return False

    print("✅ READ test passed")
    return True


def test_append(temp_dir: Path) -> bool:
    """Test APPEND operation."""
    print_header("Test: APPEND Operation")

    test_file = temp_dir / "test.txt"
    append_content = "\nAppended content"

    request = {
        "action": "APPEND",
        "data": {
            "path": str(test_file),
            "content": append_content
        }
    }

    print_request("APPEND", request["data"])
    response = execute(request)
    print_response(response)

    if response["status"] != "SUCCESS":
        print("❌ APPEND test failed: Expected SUCCESS")
        return False

    file_content = test_file.read_text()
    if not file_content.endswith(append_content):
        print("❌ APPEND test failed: Content not appended correctly")
        return False

    print("✅ APPEND test passed")
    return True


def test_mkdir(temp_dir: Path) -> bool:
    """Test MKDIR operation."""
    print_header("Test: MKDIR Operation")

    new_dir = temp_dir / "nested" / "directories" / "here"

    request = {
        "action": "MKDIR",
        "data": {
            "path": str(new_dir),
            "parents": True
        }
    }

    print_request("MKDIR", request["data"])
    response = execute(request)
    print_response(response)

    if response["status"] != "SUCCESS":
        print("❌ MKDIR test failed: Expected SUCCESS")
        return False

    if not new_dir.exists() or not new_dir.is_dir():
        print("❌ MKDIR test failed: Directory was not created")
        return False

    print("✅ MKDIR test passed")
    return True


def test_list(temp_dir: Path) -> bool:
    """Test LIST operation."""
    print_header("Test: LIST Operation")

    # Create some test files
    (temp_dir / "file1.txt").write_text("content1")
    (temp_dir / "file2.txt").write_text("content2")
    (temp_dir / "subdir").mkdir()

    request = {
        "action": "LIST",
        "data": {
            "path": str(temp_dir)
        }
    }

    print_request("LIST", request["data"])
    response = execute(request)
    print_response(response)

    if response["status"] != "SUCCESS":
        print("❌ LIST test failed: Expected SUCCESS")
        return False

    entries = response["data"].get("entries", [])
    if len(entries) < 3:  # At least file1, file2, subdir
        print(f"❌ LIST test failed: Expected at least 3 entries, got {len(entries)}")
        return False

    print("✅ LIST test passed")
    return True


def test_exists(temp_dir: Path) -> bool:
    """Test EXISTS operation."""
    print_header("Test: EXISTS Operation")

    test_file = temp_dir / "test.txt"

    # Check file exists
    request = {
        "action": "EXISTS",
        "data": {
            "path": str(test_file)
        }
    }

    print_request("EXISTS (file)", request["data"])
    response = execute(request)
    print_response(response)

    if response["status"] != "SUCCESS":
        print("❌ EXISTS test failed (file): Expected SUCCESS")
        return False

    if not response["data"].get("exists"):
        print("❌ EXISTS test failed (file): Should exist")
        return False

    if response["data"].get("type") != "file":
        print("❌ EXISTS test failed (file): Should be file type")
        return False

    # Check directory exists
    request = {
        "action": "EXISTS",
        "data": {
            "path": str(temp_dir)
        }
    }

    print_request("EXISTS (directory)", request["data"])
    response = execute(request)
    print_response(response)

    if response["data"].get("type") != "directory":
        print("❌ EXISTS test failed (directory): Should be directory type")
        return False

    # Check non-existent path
    request = {
        "action": "EXISTS",
        "data": {
            "path": str(temp_dir / "nonexistent.txt")
        }
    }

    print_request("EXISTS (non-existent)", request["data"])
    response = execute(request)
    print_response(response)

    if response["data"].get("exists"):
        print("❌ EXISTS test failed (non-existent): Should not exist")
        return False

    print("✅ EXISTS test passed")
    return True


def test_metadata(temp_dir: Path) -> bool:
    """Test METADATA operation."""
    print_header("Test: METADATA Operation")

    test_file = temp_dir / "test.txt"

    request = {
        "action": "METADATA",
        "data": {
            "path": str(test_file)
        }
    }

    print_request("METADATA", request["data"])
    response = execute(request)
    print_response(response)

    if response["status"] != "SUCCESS":
        print("❌ METADATA test failed: Expected SUCCESS")
        return False

    metadata = response["data"].get("metadata", {})
    if not metadata.get("size"):
        print("❌ METADATA test failed: Missing size information")
        return False

    if metadata.get("type") != "file":
        print("❌ METADATA test failed: Should be file type")
        return False

    print("✅ METADATA test passed")
    return True


def test_search(temp_dir: Path) -> bool:
    """Test SEARCH operation."""
    print_header("Test: SEARCH Operation")

    # Create test files
    (temp_dir / "document1.txt").write_text("content")
    (temp_dir / "document2.txt").write_text("content")
    (temp_dir / "image.png").write_text("binary")

    request = {
        "action": "SEARCH",
        "data": {
            "path": str(temp_dir),
            "pattern": "*.txt"
        }
    }

    print_request("SEARCH", request["data"])
    response = execute(request)
    print_response(response)

    if response["status"] != "SUCCESS":
        print("❌ SEARCH test failed: Expected SUCCESS")
        return False

    results = response["data"].get("results", [])
    if len(results) < 2:
        print(f"❌ SEARCH test failed: Expected at least 2 results, got {len(results)}")
        return False

    print("✅ SEARCH test passed")
    return True


def test_copy(temp_dir: Path) -> bool:
    """Test COPY operation."""
    print_header("Test: COPY Operation")

    source_file = temp_dir / "source.txt"
    source_file.write_text("source content")
    dest_file = temp_dir / "destination.txt"

    request = {
        "action": "COPY",
        "data": {
            "source": str(source_file),
            "destination": str(dest_file)
        }
    }

    print_request("COPY", request["data"])
    response = execute(request)
    print_response(response)

    if response["status"] != "SUCCESS":
        print("❌ COPY test failed: Expected SUCCESS")
        return False

    if not dest_file.exists():
        print("❌ COPY test failed: Destination file not created")
        return False

    if dest_file.read_text() != source_file.read_text():
        print("❌ COPY test failed: Content mismatch")
        return False

    print("✅ COPY test passed")
    return True


def test_rename(temp_dir: Path) -> bool:
    """Test RENAME operation."""
    print_header("Test: RENAME Operation")

    original_file = temp_dir / "original.txt"
    original_file.write_text("content")
    new_name = "renamed.txt"

    request = {
        "action": "RENAME",
        "data": {
            "path": str(original_file),
            "new_name": new_name
        }
    }

    print_request("RENAME", request["data"])
    response = execute(request)
    print_response(response)

    if response["status"] != "SUCCESS":
        print("❌ RENAME test failed: Expected SUCCESS")
        return False

    new_file = temp_dir / new_name
    if not new_file.exists():
        print("❌ RENAME test failed: New file not created")
        return False

    if original_file.exists():
        print("❌ RENAME test failed: Original file still exists")
        return False

    print("✅ RENAME test passed")
    return True


def test_move(temp_dir: Path) -> bool:
    """Test MOVE operation."""
    print_header("Test: MOVE Operation")

    # Create subdirectories
    (temp_dir / "source_dir").mkdir()
    (temp_dir / "dest_dir").mkdir()

    source_file = temp_dir / "source_dir" / "file.txt"
    source_file.write_text("content")
    dest_file = temp_dir / "dest_dir" / "file.txt"

    request = {
        "action": "MOVE",
        "data": {
            "source": str(source_file),
            "destination": str(dest_file)
        }
    }

    print_request("MOVE", request["data"])
    response = execute(request)
    print_response(response)

    if response["status"] != "SUCCESS":
        print("❌ MOVE test failed: Expected SUCCESS")
        return False

    if not dest_file.exists():
        print("❌ MOVE test failed: Destination file not created")
        return False

    if source_file.exists():
        print("❌ MOVE test failed: Source file still exists")
        return False

    print("✅ MOVE test passed")
    return True


def test_delete(temp_dir: Path) -> bool:
    """Test DELETE operation."""
    print_header("Test: DELETE Operation")

    # Test file deletion
    file_to_delete = temp_dir / "delete_me.txt"
    file_to_delete.write_text("content")

    request = {
        "action": "DELETE",
        "data": {
            "path": str(file_to_delete)
        }
    }

    print_request("DELETE (file)", request["data"])
    response = execute(request)
    print_response(response)

    if response["status"] != "SUCCESS":
        print("❌ DELETE test failed: Expected SUCCESS")
        return False

    if file_to_delete.exists():
        print("❌ DELETE test failed: File still exists")
        return False

    # Test directory deletion with recursive
    dir_to_delete = temp_dir / "delete_dir"
    dir_to_delete.mkdir()
    (dir_to_delete / "file.txt").write_text("content")

    request = {
        "action": "DELETE",
        "data": {
            "path": str(dir_to_delete),
            "recursive": True
        }
    }

    print_request("DELETE (directory, recursive)", request["data"])
    response = execute(request)
    print_response(response)

    if response["status"] != "SUCCESS":
        print("❌ DELETE test failed: Expected SUCCESS")
        return False

    if dir_to_delete.exists():
        print("❌ DELETE test failed: Directory still exists")
        return False

    print("✅ DELETE test passed")
    return True


def run_all_tests() -> bool:
    """Run all tests."""
    print("\n" + "=" * 60)
    print("  Nexus File System Plugin - Comprehensive Test Suite")
    print("=" * 60)

    # Create temporary directory for testing
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)

        tests = [
            ("WRITE", lambda: test_write(temp_path)),
            ("READ", lambda: test_read(temp_path)),
            ("APPEND", lambda: test_append(temp_path)),
            ("MKDIR", lambda: test_mkdir(temp_path)),
            ("LIST", lambda: test_list(temp_path)),
            ("EXISTS", lambda: test_exists(temp_path)),
            ("METADATA", lambda: test_metadata(temp_path)),
            ("SEARCH", lambda: test_search(temp_path)),
            ("COPY", lambda: test_copy(temp_path)),
            ("RENAME", lambda: test_rename(temp_path)),
            ("MOVE", lambda: test_move(temp_path)),
            ("DELETE", lambda: test_delete(temp_path)),
        ]

        passed = 0
        failed = 0

        for name, test_func in tests:
            try:
                if test_func():
                    passed += 1
                else:
                    failed += 1
            except Exception as e:
                print(f"\n❌ {name} test crashed: {str(e)}")
                import traceback
                traceback.print_exc()
                failed += 1

        # Final summary
        print("\n" + "=" * 60)
        print("  Test Summary")
        print("=" * 60)
        print(f"Total tests: {len(tests)}")
        print(f"✅ Passed: {passed}")
        print(f"❌ Failed: {failed}")
        print("=" * 60 + "\n")

        return failed == 0


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
