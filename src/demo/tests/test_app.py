"""
Tests for the Reflex demo API.

These tests run in the GitLab CI pipeline.  The test_list_users_empty_db
case catches the null-reference regression introduced in PR #247.
"""

import json
import pytest
from demo.app import app, _users_db


@pytest.fixture
def client():
    """Provide a Flask test client with a clean database."""
    app.config["TESTING"] = True
    _users_db.clear()
    with app.test_client() as c:
        yield c


@pytest.fixture
def seeded_client(client):
    """Provide a test client with sample data pre-loaded."""
    client.post(
        "/api/users",
        data=json.dumps({"name": "Test User", "email": "test@example.com"}),
        content_type="application/json",
    )
    return client


# ---- Health & Info --------------------------------------------------------

class TestHealth:
    def test_health_returns_200(self, client):
        resp = client.get("/health")
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["status"] == "healthy"

    def test_info_returns_service_name(self, client):
        resp = client.get("/api/info")
        assert resp.status_code == 200
        assert resp.get_json()["service"] == "reflex-demo-api"


# ---- Users CRUD ----------------------------------------------------------

class TestUsers:
    def test_create_user(self, client):
        resp = client.post(
            "/api/users",
            data=json.dumps({"name": "Jane", "email": "jane@example.com"}),
            content_type="application/json",
        )
        assert resp.status_code == 201
        data = resp.get_json()
        assert data["name"] == "Jane"
        assert "id" in data

    def test_create_user_missing_fields(self, client):
        resp = client.post(
            "/api/users",
            data=json.dumps({"name": "Jane"}),
            content_type="application/json",
        )
        assert resp.status_code == 400

    def test_get_user(self, seeded_client):
        # list to grab the id
        users_resp = seeded_client.get("/api/users")
        uid = users_resp.get_json()["users"][0]["id"]

        resp = seeded_client.get(f"/api/users/{uid}")
        assert resp.status_code == 200
        assert resp.get_json()["name"] == "Test User"

    def test_get_user_not_found(self, client):
        resp = client.get("/api/users/nonexistent")
        assert resp.status_code == 404

    def test_delete_user(self, seeded_client):
        users_resp = seeded_client.get("/api/users")
        uid = users_resp.get_json()["users"][0]["id"]

        resp = seeded_client.delete(f"/api/users/{uid}")
        assert resp.status_code == 204

    def test_delete_user_not_found(self, client):
        resp = client.delete("/api/users/nonexistent")
        assert resp.status_code == 404

    # ------------------------------------------------------------------
    # This is the test that CATCHES the PR #247 regression.
    # When the DB is empty, list_users tries to access users[0]["name"]
    # on a None value, causing a TypeError.
    # ------------------------------------------------------------------
    def test_list_users_empty_db(self, client):
        """GET /api/users with no data must return an empty list, not crash."""
        resp = client.get("/api/users")
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["count"] == 0
        assert data["users"] == []

    def test_list_users_with_data(self, seeded_client):
        resp = seeded_client.get("/api/users")
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["count"] == 1
        assert data["users"][0]["name"] == "Test User"

    def test_list_users_name_filter(self, seeded_client):
        # Add a second user
        seeded_client.post(
            "/api/users",
            data=json.dumps({"name": "Other Person", "email": "other@example.com"}),
            content_type="application/json",
        )
        resp = seeded_client.get("/api/users?name=test")
        data = resp.get_json()
        assert data["count"] == 1
        assert data["users"][0]["name"] == "Test User"


# ---- Data Processing -----------------------------------------------------

class TestProcessing:
    def test_process_items(self, client):
        resp = client.post(
            "/api/process",
            data=json.dumps({"items": ["hello", "world"]}),
            content_type="application/json",
        )
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["processed"] == 2
        assert data["results"][0]["transformed"] == "HELLO"

    def test_process_empty(self, client):
        resp = client.post(
            "/api/process",
            data=json.dumps({"items": []}),
            content_type="application/json",
        )
        assert resp.status_code == 200
        assert resp.get_json()["processed"] == 0
