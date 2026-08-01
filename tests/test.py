from plugins.memory.execute import execute


def run_write_test() -> dict:
    request = {
        "action": "WRITE",
        "data": {
            "title": "Final End-to-End Test Memory",
            "category": "PROJECT",
            "content": "This memory is created as part of the final end-to-end test.",
            "tags": ["final", "integration", "nexus"],
        },
    }
    return execute(request)


def run_search_test(query: str, include_deleted: bool = False) -> dict:
    request = {
        "action": "SEARCH",
        "data": {
            "query": query,
            "category": None,
            "tags": None,
            "limit": 10,
            "include_deleted": include_deleted,
        },
    }
    return execute(request)


def run_get_test(memory_id: str, include_deleted: bool = False) -> dict:
    request = {
        "action": "GET",
        "data": {
            "memory_id": memory_id,
            "include_deleted": include_deleted,
        },
    }
    return execute(request)


def run_update_test(memory_id: str) -> dict:
    request = {
        "action": "UPDATE",
        "data": {
            "memory_id": memory_id,
            "changes": {
                "title": "Final End-to-End Test Memory (Updated)",
                "content": "The content has been updated for the final end-to-end test.",
                "tags": ["final", "integration", "updated"],
                "category": "PROJECT",
            },
        },
    }
    return execute(request)


def run_delete_test(memory_id: str) -> dict:
    request = {
        "action": "DELETE",
        "data": {
            "memory_id": memory_id,
        },
    }
    return execute(request)


def run_list_test(category: str | None = None, include_deleted: bool = False, limit: int = 10) -> dict:
    request = {
        "action": "LIST",
        "data": {
            "category": category,
            "limit": limit,
            "include_deleted": include_deleted,
        },
    }
    return execute(request)


if __name__ == "__main__":
    print("Running final big test for Nexus Memory Plugin...\n")

    print("1) WRITE")
    write_result = run_write_test()
    print(write_result)

    if write_result.get("status") != "SUCCESS":
        raise SystemExit("WRITE failed; aborting final test.")

    memory_id = write_result["data"]["memory_id"]

    print("\n2) SEARCH")
    search_result = run_search_test("Final End-to-End Test")
    print(search_result)

    print("\n3) GET")
    get_result = run_get_test(memory_id)
    print(get_result)

    print("\n4) UPDATE")
    update_result = run_update_test(memory_id)
    print(update_result)

    print("\n5) GET after UPDATE")
    get_after_update_result = run_get_test(memory_id)
    print(get_after_update_result)

    print("\n6) DELETE")
    delete_result = run_delete_test(memory_id)
    print(delete_result)

    print("\n7) GET deleted memory without include_deleted")
    get_deleted_result = run_get_test(memory_id)
    print(get_deleted_result)

    print("\n8) GET deleted memory with include_deleted")
    get_deleted_with_flag_result = run_get_test(memory_id, include_deleted=True)
    print(get_deleted_with_flag_result)

    print("\n9) LIST")
    list_result = run_list_test("PROJECT", include_deleted=True, limit=20)
    print(list_result)

    print("\n10) SEARCH including deleted")
    search_deleted_result = run_search_test("Final End-to-End Test", include_deleted=True)
    print(search_deleted_result)

    print("\nFinal big test complete.")
