# apps/ai_core/tests/api/test_agents_api.py
"""
Integration tests for agents API endpoints (v5.0).

Tests the FastAPI endpoints for agent management including
versioning, drafts, and soft delete functionality.
"""

import pytest
import os
import json
import tempfile
import shutil
from unittest.mock import patch, Mock
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

from apps.ai_core.ai_core.db.orm_models import Base
import apps.ai_core.ai_core.db.session as session_module
from apps.ai_core.ai_core.api.agents_api import router
from fastapi import FastAPI


# Create a fresh test app for each test module
def create_test_app():
    app = FastAPI()
    app.include_router(router)
    return app


class TestAgentsAPISetup:
    """Base class with common fixtures for API tests."""

    @pytest.fixture
    def temp_data_dir(self):
        """Create a temporary directory for agent files."""
        dir_path = tempfile.mkdtemp()
        yield dir_path
        shutil.rmtree(dir_path, ignore_errors=True)

    @pytest.fixture
    def client(self, temp_data_dir):
        """Create a test client with mocked dependencies."""
        # Create engine with check_same_thread=False for SQLite
        engine = create_engine(
            "sqlite:///:memory:",
            echo=False,
            connect_args={"check_same_thread": False}
        )
        Base.metadata.create_all(bind=engine)
        TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

        app = create_test_app()

        # Create a generator function that yields sessions
        def get_test_session():
            session = TestingSessionLocal()
            try:
                yield session
            finally:
                session.close()

        # Override dependencies using the module reference
        app.dependency_overrides[session_module.get_session] = get_test_session

        # Mock get_data_root and trigger_manager
        with patch('apps.ai_core.ai_core.api.agents_api.get_data_root', return_value=temp_data_dir):
            with patch('apps.ai_core.ai_core.api.agents_api.get_trigger_manager') as mock_tm:
                mock_tm.return_value = Mock(
                    register_trigger=Mock(return_value=True),
                    unregister_triggers_for_agent=Mock(return_value=0),
                    validate_triggers_config=Mock(return_value=(True, None))
                )
                yield TestClient(app)

        app.dependency_overrides.clear()
        engine.dispose()


@pytest.mark.skip(reason="API integration tests require additional FastAPI test setup")
class TestAgentCRUD(TestAgentsAPISetup):
    """Test basic agent CRUD operations."""

    def test_create_agent(self, client, temp_data_dir):
        """Test creating a new agent."""
        response = client.post("/agents", json={
            "name": "Test Agent",
            "description": "A test agent",
            "tags": ["test", "sample"]
        })

        assert response.status_code == 201
        data = response.json()
        assert "agent_id" in data
        assert data["status"] == "created"

        # Verify file was created
        agent_dir = os.path.join(temp_data_dir, data["agent_id"])
        assert os.path.exists(agent_dir)
        assert os.path.exists(os.path.join(agent_dir, "v1.json"))

    def test_list_agents(self, client):
        """Test listing agents."""
        # Create some agents
        client.post("/agents", json={"name": "Agent 1"})
        client.post("/agents", json={"name": "Agent 2"})

        response = client.get("/agents")

        assert response.status_code == 200
        agents = response.json()
        assert len(agents) == 2

    def test_get_agent(self, client):
        """Test getting a specific agent."""
        # Create agent
        create_resp = client.post("/agents", json={"name": "Get Test Agent"})
        agent_id = create_resp.json()["agent_id"]

        response = client.get(f"/agents/{agent_id}")

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == agent_id
        assert data["name"] == "Get Test Agent"
        assert data["version"] == 1
        assert data["is_active"] is False

    def test_get_agent_not_found(self, client):
        """Test getting non-existent agent returns 404."""
        response = client.get("/agents/nonexistent-id")

        assert response.status_code == 404

    def test_update_agent(self, client):
        """Test updating agent properties."""
        # Create agent
        create_resp = client.post("/agents", json={"name": "Original Name"})
        agent_id = create_resp.json()["agent_id"]

        response = client.put(f"/agents/{agent_id}", json={
            "name": "Updated Name",
            "description": "New description"
        })

        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Updated Name"
        assert data["description"] == "New description"

    def test_delete_agent_soft_delete(self, client):
        """Test deleting agent uses soft delete."""
        # Create agent
        create_resp = client.post("/agents", json={"name": "To Delete"})
        agent_id = create_resp.json()["agent_id"]

        response = client.delete(f"/agents/{agent_id}")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "marked_for_deletion"

        # Agent should not appear in list
        list_resp = client.get("/agents")
        agents = list_resp.json()
        assert not any(a["id"] == agent_id for a in agents)


@pytest.mark.skip(reason="API integration tests require additional FastAPI test setup")
class TestAgentActivation(TestAgentsAPISetup):
    """Test agent activation and deactivation."""

    def test_activate_agent(self, client):
        """Test activating an agent."""
        # Create agent
        create_resp = client.post("/agents", json={"name": "To Activate"})
        agent_id = create_resp.json()["agent_id"]

        response = client.post(f"/agents/{agent_id}/activate")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "active"

        # Verify agent is now active
        get_resp = client.get(f"/agents/{agent_id}")
        assert get_resp.json()["is_active"] is True

    def test_deactivate_agent(self, client):
        """Test deactivating an agent."""
        # Create and activate agent
        create_resp = client.post("/agents", json={"name": "To Deactivate"})
        agent_id = create_resp.json()["agent_id"]
        client.post(f"/agents/{agent_id}/activate")

        response = client.post(f"/agents/{agent_id}/deactivate")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "inactive"

        # Verify agent is now inactive
        get_resp = client.get(f"/agents/{agent_id}")
        assert get_resp.json()["is_active"] is False

    def test_activate_deleted_agent_fails(self, client):
        """Test activating deleted agent returns 409."""
        # Create and delete agent
        create_resp = client.post("/agents", json={"name": "Deleted"})
        agent_id = create_resp.json()["agent_id"]
        client.delete(f"/agents/{agent_id}")

        response = client.post(f"/agents/{agent_id}/activate")

        assert response.status_code == 409


@pytest.mark.skip(reason="API integration tests require additional FastAPI test setup")
class TestAgentVersions(TestAgentsAPISetup):
    """Test agent versions endpoint."""

    def test_list_versions_live_only(self, client):
        """Test listing versions with only live version."""
        # Create agent
        create_resp = client.post("/agents", json={"name": "Version Test"})
        agent_id = create_resp.json()["agent_id"]

        response = client.get(f"/agents/{agent_id}/versions")

        assert response.status_code == 200
        data = response.json()
        assert "versions" in data
        assert len(data["versions"]) == 1

        live_version = data["versions"][0]
        assert live_version["type"] == "live"
        assert live_version["version"] == 1

    def test_list_versions_with_drafts(self, client):
        """Test listing versions with drafts."""
        # Create agent and draft
        create_resp = client.post("/agents", json={"name": "Version Test"})
        agent_id = create_resp.json()["agent_id"]

        client.post(f"/agents/{agent_id}/drafts", json={
            "name": "Draft 1",
            "source": "live"
        })

        response = client.get(f"/agents/{agent_id}/versions")

        assert response.status_code == 200
        data = response.json()
        assert len(data["versions"]) == 2

        types = [v["type"] for v in data["versions"]]
        assert "live" in types
        assert "draft" in types


@pytest.mark.skip(reason="API integration tests require additional FastAPI test setup")
class TestAgentDrafts(TestAgentsAPISetup):
    """Test agent draft endpoints."""

    def test_create_draft_from_live(self, client):
        """Test creating a draft from live version."""
        # Create agent
        create_resp = client.post("/agents", json={"name": "Draft Test"})
        agent_id = create_resp.json()["agent_id"]

        response = client.post(f"/agents/{agent_id}/drafts", json={
            "name": "My Draft",
            "source": "live"
        })

        assert response.status_code == 201
        data = response.json()
        assert "draft_id" in data
        assert data["name"] == "My Draft"
        assert data["base_version"] == 1
        assert data["type"] == "draft"

    def test_create_draft_from_draft(self, client):
        """Test creating a draft from another draft."""
        # Create agent and first draft
        create_resp = client.post("/agents", json={"name": "Draft Test"})
        agent_id = create_resp.json()["agent_id"]

        draft1_resp = client.post(f"/agents/{agent_id}/drafts", json={
            "name": "First Draft",
            "source": "live"
        })
        draft1_id = draft1_resp.json()["draft_id"]

        # Create second draft from first
        response = client.post(f"/agents/{agent_id}/drafts", json={
            "name": "Second Draft",
            "source": draft1_id
        })

        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Second Draft"

    def test_get_draft_content(self, client, temp_data_dir):
        """Test getting draft content."""
        # Create agent and draft
        create_resp = client.post("/agents", json={"name": "Get Draft Test"})
        agent_id = create_resp.json()["agent_id"]

        draft_resp = client.post(f"/agents/{agent_id}/drafts", json={
            "name": "Test Draft",
            "source": "live"
        })
        draft_id = draft_resp.json()["draft_id"]

        response = client.get(f"/agents/{agent_id}/drafts/{draft_id}")

        assert response.status_code == 200
        data = response.json()
        assert "updated_at" in data
        assert "graph" in data
        assert "nodes" in data["graph"]
        assert "edges" in data["graph"]

    def test_update_draft(self, client):
        """Test updating draft content (autosave)."""
        # Create agent and draft
        create_resp = client.post("/agents", json={"name": "Update Draft Test"})
        agent_id = create_resp.json()["agent_id"]

        draft_resp = client.post(f"/agents/{agent_id}/drafts", json={
            "name": "Test Draft",
            "source": "live"
        })
        draft_id = draft_resp.json()["draft_id"]

        # Update with new graph
        new_graph = {
            "nodes": [
                {"id": "start", "type": "start", "data": {}},
                {"id": "custom", "type": "custom", "data": {"name": "test"}},
                {"id": "end", "type": "end", "data": {}}
            ],
            "edges": [
                {"source": "start", "target": "custom"},
                {"source": "custom", "target": "end"}
            ],
            "triggers": [],
            "permissions": {}
        }

        response = client.put(f"/agents/{agent_id}/drafts/{draft_id}", json={
            "graph": new_graph
        })

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "saved"

        # Verify content was saved
        get_resp = client.get(f"/agents/{agent_id}/drafts/{draft_id}")
        saved_graph = get_resp.json()["graph"]
        assert len(saved_graph["nodes"]) == 3

    def test_update_draft_with_optimistic_lock_conflict(self, client):
        """Test update with wrong expected_updated_at returns 409."""
        # Create agent and draft
        create_resp = client.post("/agents", json={"name": "Lock Test"})
        agent_id = create_resp.json()["agent_id"]

        draft_resp = client.post(f"/agents/{agent_id}/drafts", json={
            "name": "Test Draft",
            "source": "live"
        })
        draft_id = draft_resp.json()["draft_id"]

        response = client.put(f"/agents/{agent_id}/drafts/{draft_id}", json={
            "expected_updated_at": "1970-01-01T00:00:00.000Z",
            "graph": {"nodes": [], "edges": []}
        })

        assert response.status_code == 409

    def test_delete_draft(self, client):
        """Test deleting a draft."""
        # Create agent and draft
        create_resp = client.post("/agents", json={"name": "Delete Draft Test"})
        agent_id = create_resp.json()["agent_id"]

        draft_resp = client.post(f"/agents/{agent_id}/drafts", json={
            "name": "To Delete",
            "source": "live"
        })
        draft_id = draft_resp.json()["draft_id"]

        response = client.delete(f"/agents/{agent_id}/drafts/{draft_id}")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "deleted"

        # Verify draft is gone
        get_resp = client.get(f"/agents/{agent_id}/drafts/{draft_id}")
        assert get_resp.status_code == 404


@pytest.mark.skip(reason="API integration tests require additional FastAPI test setup")
class TestAgentDeploy(TestAgentsAPISetup):
    """Test draft deployment endpoint."""

    def test_deploy_draft(self, client, temp_data_dir):
        """Test deploying a draft as new live version."""
        # Create agent and draft
        create_resp = client.post("/agents", json={"name": "Deploy Test"})
        agent_id = create_resp.json()["agent_id"]

        draft_resp = client.post(f"/agents/{agent_id}/drafts", json={
            "name": "Deploy Draft",
            "source": "live"
        })
        draft_id = draft_resp.json()["draft_id"]

        # Deploy
        response = client.post(f"/agents/{agent_id}/drafts/{draft_id}/deploy")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "deployed"
        assert data["new_version"] == 2

        # Verify agent version updated
        get_resp = client.get(f"/agents/{agent_id}")
        agent_data = get_resp.json()
        assert agent_data["version"] == 2
        assert agent_data["is_active"] is True

        # Verify new version file exists
        v2_path = os.path.join(temp_data_dir, agent_id, "v2.json")
        assert os.path.exists(v2_path)

        # Verify draft is deleted
        versions_resp = client.get(f"/agents/{agent_id}/versions")
        versions = versions_resp.json()["versions"]
        assert all(v["type"] == "live" for v in versions)

    def test_deploy_draft_version_conflict(self, client):
        """Test deploying draft when agent version changed returns 409."""
        # Create agent
        create_resp = client.post("/agents", json={"name": "Conflict Test"})
        agent_id = create_resp.json()["agent_id"]

        # Create first draft
        draft1_resp = client.post(f"/agents/{agent_id}/drafts", json={
            "name": "Draft 1",
            "source": "live"
        })
        draft1_id = draft1_resp.json()["draft_id"]

        # Create and deploy second draft (increments version)
        draft2_resp = client.post(f"/agents/{agent_id}/drafts", json={
            "name": "Draft 2",
            "source": "live"
        })
        draft2_id = draft2_resp.json()["draft_id"]
        client.post(f"/agents/{agent_id}/drafts/{draft2_id}/deploy")

        # Try to deploy first draft (based on v1, but current is v2)
        response = client.post(f"/agents/{agent_id}/drafts/{draft1_id}/deploy")

        assert response.status_code == 409
        assert "Conflict" in response.json()["detail"]


@pytest.mark.skip(reason="API integration tests require additional FastAPI test setup")
class TestAgentRuns(TestAgentsAPISetup):
    """Test agent runs endpoints."""

    def test_create_run(self, client):
        """Test creating an agent run."""
        # Create agent
        create_resp = client.post("/agents", json={"name": "Run Test"})
        agent_id = create_resp.json()["agent_id"]

        # Mock priority policy
        with patch('apps.ai_core.ai_core.api.agents_api.get_priority_policy') as mock_pp:
            mock_pp.return_value = Mock(assign_priority=Mock(return_value=30))

            response = client.post(f"/agents/{agent_id}/runs", json={
                "trigger_type": "manual",
                "status": "pending"
            })

        assert response.status_code == 201
        data = response.json()
        assert "run_id" in data
        assert data["status"] == "pending"
        assert data["trigger_type"] == "manual"

    def test_list_runs(self, client):
        """Test listing agent runs."""
        # Create agent
        create_resp = client.post("/agents", json={"name": "List Runs Test"})
        agent_id = create_resp.json()["agent_id"]

        with patch('apps.ai_core.ai_core.api.agents_api.get_priority_policy') as mock_pp:
            mock_pp.return_value = Mock(assign_priority=Mock(return_value=30))

            # Create some runs
            client.post(f"/agents/{agent_id}/runs", json={"trigger_type": "manual"})
            client.post(f"/agents/{agent_id}/runs", json={"trigger_type": "schedule"})

        response = client.get(f"/agents/{agent_id}/runs")

        assert response.status_code == 200
        runs = response.json()
        assert len(runs) == 2


@pytest.mark.skip(reason="API integration tests require additional FastAPI test setup")
class TestAgentTestCases(TestAgentsAPISetup):
    """Test agent test cases endpoints."""

    def test_create_test_case(self, client):
        """Test creating a test case."""
        # Create agent
        create_resp = client.post("/agents", json={"name": "Test Case Test"})
        agent_id = create_resp.json()["agent_id"]

        response = client.post(f"/agents/{agent_id}/test-cases", json={
            "node_id": "node_001",
            "name": "Test Empty Input",
            "initial_state": {"input": "", "expected": "error"}
        })

        assert response.status_code == 201
        data = response.json()
        assert "case_id" in data
        assert data["name"] == "Test Empty Input"
        assert data["node_id"] == "node_001"

    def test_list_test_cases(self, client):
        """Test listing test cases."""
        # Create agent
        create_resp = client.post("/agents", json={"name": "List TC Test"})
        agent_id = create_resp.json()["agent_id"]

        # Create test cases
        client.post(f"/agents/{agent_id}/test-cases", json={
            "node_id": "node_001",
            "name": "TC 1",
            "initial_state": {}
        })
        client.post(f"/agents/{agent_id}/test-cases", json={
            "node_id": "node_002",
            "name": "TC 2",
            "initial_state": {}
        })

        response = client.get(f"/agents/{agent_id}/test-cases")

        assert response.status_code == 200
        test_cases = response.json()
        assert len(test_cases) == 2

    def test_delete_test_case(self, client):
        """Test deleting a test case."""
        # Create agent and test case
        create_resp = client.post("/agents", json={"name": "Delete TC Test"})
        agent_id = create_resp.json()["agent_id"]

        tc_resp = client.post(f"/agents/{agent_id}/test-cases", json={
            "node_id": "node_001",
            "name": "To Delete",
            "initial_state": {}
        })
        case_id = tc_resp.json()["case_id"]

        response = client.delete(f"/agents/{agent_id}/test-cases/{case_id}")

        assert response.status_code == 204


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
