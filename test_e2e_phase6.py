"""
Phase 6: End-to-End Testing and Verification
Tests all CRUD operations for tasks and briefings
"""
import asyncio
import json
import httpx
import time
import sys

BASE_URL = "http://localhost:8000"
HEADERS = {"Content-Type": "application/json"}

test_results = {
    "backend_health": False,
    "tasks": {},
    "briefings": {},
    "websocket": False,
    "persistence": False,
}

async def test_backend_health():
    """Test if backend is running."""
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(f"{BASE_URL}/api/health")
            if response.status_code == 200:
                print("[PASS] Backend health check")
                return True
    except Exception as e:
        print(f"[FAIL] Backend health check: {e}")
    return False

async def test_task_create():
    """Test task creation."""
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            payload = {
                "title": "Test Task 1",
                "description": "Testing task creation",
                "priority": 2,
                "tags": ["test", "e2e"],
            }
            response = await client.post(
                f"{BASE_URL}/api/personal/tasks",
                json=payload,
                headers=HEADERS
            )
            if response.status_code == 201:
                data = response.json()
                if "id" in data and data["title"] == "Test Task 1":
                    print(f"[PASS] Task creation - ID: {data['id']}")
                    test_results["tasks"]["created_id"] = data["id"]
                    return True
    except Exception as e:
        print(f"[FAIL] Task creation: {e}")
    return False

async def test_task_list():
    """Test task listing."""
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(
                f"{BASE_URL}/api/personal/tasks?limit=10&offset=0",
                headers=HEADERS
            )
            if response.status_code == 200:
                data = response.json()
                if "tasks" in data and "total" in data:
                    print(f"[PASS] Task listing - Found {len(data['tasks'])} tasks")
                    return True
    except Exception as e:
        print(f"[FAIL] Task listing: {e}")
    return False

async def test_task_get():
    """Test get specific task."""
    task_id = test_results["tasks"].get("created_id")
    if not task_id:
        print("[SKIP] Task get - no task ID")
        return False
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(
                f"{BASE_URL}/api/personal/tasks/{task_id}",
                headers=HEADERS
            )
            if response.status_code == 200:
                data = response.json()
                if data["id"] == task_id:
                    print(f"[PASS] Task get - {data['title']}")
                    return True
    except Exception as e:
        print(f"[FAIL] Task get: {e}")
    return False

async def test_task_update():
    """Test task update."""
    task_id = test_results["tasks"].get("created_id")
    if not task_id:
        print("[SKIP] Task update - no task ID")
        return False
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            payload = {"status": "IN_PROGRESS", "priority": 3}
            response = await client.put(
                f"{BASE_URL}/api/personal/tasks/{task_id}",
                json=payload,
                headers=HEADERS
            )
            if response.status_code == 200:
                data = response.json()
                if data["status"] == "IN_PROGRESS":
                    print("[PASS] Task update - status changed")
                    return True
    except Exception as e:
        print(f"[FAIL] Task update: {e}")
    return False

async def test_task_complete():
    """Test mark task complete."""
    task_id = test_results["tasks"].get("created_id")
    if not task_id:
        print("[SKIP] Task complete - no task ID")
        return False
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                f"{BASE_URL}/api/personal/tasks/{task_id}/complete",
                json={},
                headers=HEADERS
            )
            if response.status_code == 200:
                data = response.json()
                if data["status"] == "COMPLETED":
                    print("[PASS] Task complete - status is COMPLETED")
                    return True
    except Exception as e:
        print(f"[FAIL] Task complete: {e}")
    return False

async def test_briefing_create():
    """Test briefing creation."""
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            payload = {
                "content_text": "Morning briefing for test",
                "title": "Test Briefing",
                "mood": "OPTIMISTIC",
                "tags": ["test"],
            }
            response = await client.post(
                f"{BASE_URL}/api/personal/briefings",
                json=payload,
                headers=HEADERS
            )
            if response.status_code == 201:
                data = response.json()
                if "id" in data and data["title"] == "Test Briefing":
                    print(f"[PASS] Briefing creation - ID: {data['id']}")
                    test_results["briefings"]["created_id"] = data["id"]
                    return True
    except Exception as e:
        print(f"[FAIL] Briefing creation: {e}")
    return False

async def test_briefing_list():
    """Test briefing listing."""
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(
                f"{BASE_URL}/api/personal/briefings?limit=10&offset=0",
                headers=HEADERS
            )
            if response.status_code == 200:
                data = response.json()
                if "briefings" in data and "total" in data:
                    print(f"[PASS] Briefing listing - Found {len(data['briefings'])} briefings")
                    return True
    except Exception as e:
        print(f"[FAIL] Briefing listing: {e}")
    return False

async def test_briefing_latest():
    """Test get latest briefing."""
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(
                f"{BASE_URL}/api/personal/briefings/latest",
                headers=HEADERS
            )
            if response.status_code == 200:
                data = response.json()
                print(f"[PASS] Latest briefing - {data.get('title', 'No title')}")
                return True
    except Exception as e:
        # 404 is expected if no briefing exists yet
        if "404" not in str(e):
            print(f"[FAIL] Latest briefing: {e}")
        else:
            print("[PASS] Latest briefing - returns 404 when none exists (expected)")
            return True
    return False

async def run_tests():
    """Run all E2E tests."""
    print("=" * 70)
    print("Phase 6: End-to-End Testing and Verification")
    print("=" * 70)
    print()

    # Check if backend is running
    if not await test_backend_health():
        print("\nBackend is not running - start it with:")
        print("  cd spark_core && python -X utf8 main.py")
        return

    print()
    print("Tasks Tests:")
    print("-" * 70)
    await test_task_create()
    await test_task_list()
    await test_task_get()
    await test_task_update()
    await test_task_complete()

    print()
    print("Briefings Tests:")
    print("-" * 70)
    await test_briefing_create()
    await test_briefing_list()
    await test_briefing_latest()

    print()
    print("=" * 70)
    print("Test Summary")
    print("=" * 70)
    print("Start backend in one terminal:")
    print("  cd spark_core && python -X utf8 main.py")
    print()
    print("Then run this test again")
    print("=" * 70)

if __name__ == "__main__":
    asyncio.run(run_tests())
