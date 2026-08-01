from plugins.memory.execute import execute


def run_write_test() -> dict:
    request = {
        "action": "WRITE",
        "data": {
            "title": "My First Memory",
            "category": "PROJECT",
            "content": "This is a test memory entry for the Nexus memory plugin.",
            "tags": ["test", "demo", "nexus"],
        },
    }
    return execute(request)


def run_search_test(query: str) -> dict:
    request = {
        "action": "SEARCH",
        "data": {
            "query": query,
            "category": "PROJECT",
            "tags": ["demo"],
            "limit": 5,
        },
    }
    return execute(request)


if __name__ == "__main__":
    print("Running WRITE test...")
    write_result = run_write_test()
    print(write_result)

    if write_result.get("status") == "SUCCESS":
        print("\nRunning SEARCH test...")
        search_result = run_search_test("memory")
        print(search_result)
    else:
        print("\nSkipping SEARCH test because WRITE failed.")
