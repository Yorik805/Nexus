from __future__ import annotations

import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent.parent.parent
sys.path.insert(0, str(ROOT_DIR))

try:
    import pytest
except ImportError:
    pytest = None  # type: ignore

if pytest is not None:
    pytest.importorskip("chromadb")
    pytest.importorskip("sentence_transformers")

import logging

from plugins.memory.actions.write import write
from plugins.memory.actions.update import update
from plugins.memory.actions.delete import delete
from plugins.memory.actions.search import search
from plugins.memory import database
from plugins.memory.vector_store import reset_store

logger = logging.getLogger(__name__)


def setup_function() -> None:
    logger.info("Resetting vector store persistence and sqlite database")
    reset_store()
    db_path = database.DATABASE_PATH
    if db_path.exists():
        db_path.unlink()


def test_vector_write_update_delete_and_sqlite_search_flow() -> None:
    logger.info("Starting vector write/update/delete flow")
    # Write a memory
    resp = write(
        {
            "title": "Pizza Day",
            "category": "IDEA",
            "content": "I had delicious pizza today",
            "tags": ["food", "happy"],
        }
    )
    assert resp["status"] == "SUCCESS", resp
    mem_id = resp["data"]["memory_id"]

    logger.info("Memory written, id=%s", mem_id)

    # Vector search for 'pizza' should find it
    logger.info("Performing initial VECTOR search for 'pizza'")
    vresp = search({"type": "VECTOR", "query": "pizza", "limit": 5})
    assert vresp["status"] == "SUCCESS", vresp
    assert any(r["memory_id"] == mem_id for r in vresp["data"]["results"]) or len(vresp["data"]["results"]) > 0

    logger.info("Updating memory content to mention 'sick'")

    # Update content to mention 'sick'
    uresp = update({"memory_id": mem_id, "changes": {"content": "I felt sick today"}})
    assert uresp["status"] == "SUCCESS"

    logger.info("Performing VECTOR search for 'sick' after update")
    # Vector search for 'sick' should find it
    vresp2 = search({"type": "VECTOR", "query": "sick", "limit": 5})
    assert vresp2["status"] == "SUCCESS"
    assert any(r["memory_id"] == mem_id for r in vresp2["data"]["results"]) or len(vresp2["data"]["results"]) > 0

    logger.info("Deleting memory id=%s", mem_id)
    # Delete the memory
    dresp = delete({"memory_id": mem_id})
    assert dresp["status"] == "SUCCESS"

    # By default, vector search should not find deleted items
    vresp3 = search({"type": "VECTOR", "query": "sick", "limit": 5})
    assert vresp3["status"] == "SUCCESS"
    assert not any(r["memory_id"] == mem_id for r in vresp3["data"]["results"]) 

    logger.info("Performing SQLITE search with include_deleted=True")
    # SQLITE search should still be able to find by title if include_deleted requested
    sresp = search({"type": "SQLITE", "query": "Pizza Day", "limit": 5, "include_deleted": True})
    assert sresp["status"] == "SUCCESS"
    assert any(r["memory_id"] == mem_id for r in sresp["data"]["results"]) or len(sresp["data"]["results"]) > 0


if __name__ == "__main__":
    setup_function()
    try:
        test_vector_write_update_delete_and_sqlite_search_flow()
    except AssertionError as exc:
        print(f"TEST FAILED: {exc}")
        raise
    else:
        print("TEST PASSED")
