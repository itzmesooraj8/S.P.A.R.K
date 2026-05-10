import sys
import asyncio
import pytest
from unittest.mock import MagicMock

# Create a proper mock for APIRouter that doesn't replace the functions it decorates
class MockAPIRouter:
    def __init__(self, *args, **kwargs): pass
    def get(self, *args, **kwargs): return lambda x: x
    def post(self, *args, **kwargs): return lambda x: x
    def put(self, *args, **kwargs): return lambda x: x
    def delete(self, *args, **kwargs): return lambda x: x

class MockHTTPException(Exception):
    def __init__(self, status_code, detail=None, headers=None):
        self.status_code = status_code
        self.detail = detail
        self.headers = headers

# Mocking FastAPI and Pydantic before importing the module
fastapi_mock = MagicMock()
fastapi_mock.APIRouter = MockAPIRouter
fastapi_mock.HTTPException = MockHTTPException
sys.modules['fastapi'] = fastapi_mock

pydantic_mock = MagicMock()
sys.modules['pydantic'] = pydantic_mock

import api.routes.projects as projects_module

def run_async(coro):
    return asyncio.run(coro)

def test_switch_project_success():
    # Reset focus
    projects_module._CURRENT_FOCUS = "Original"

    result = run_async(projects_module.switch_project("NewProject"))

    assert result == {
        "status": "ok",
        "current_focus": "NewProject",
    }
    assert projects_module._CURRENT_FOCUS == "NewProject"

def test_switch_project_empty_id():
    with pytest.raises(MockHTTPException) as excinfo:
        run_async(projects_module.switch_project("  "))

    assert excinfo.value.status_code == 400
    assert excinfo.value.detail == "project_id required"

def test_list_projects():
    projects_module._CURRENT_FOCUS = "HUD Frontend"

    result = run_async(projects_module.list_projects())

    assert result["current_focus"] == "HUD Frontend"
    assert "active_projects" in result

def test_switch_and_list_persistence():
    run_async(projects_module.switch_project("PersistenceTest"))
    result = run_async(projects_module.list_projects())
    assert result["current_focus"] == "PersistenceTest"
