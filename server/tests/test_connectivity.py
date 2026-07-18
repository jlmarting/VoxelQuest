"""Tests de WebSocket y MCP."""

import pytest
from httpx import AsyncClient
from starlette.testclient import TestClient

from server.main import app


@pytest.fixture
def client():
    return TestClient(app)


class TestHealth:
    def test_health(self, client):
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json()["status"] == "ok"


class TestMcp:
    def test_initialize(self, client):
        response = client.post("/mcp", json={"jsonrpc": "2.0", "id": 1, "method": "initialize"})
        assert response.status_code == 200
        data = response.json()
        assert "protocolVersion" in data["content"][0]["text"]

    def test_tools_list(self, client):
        response = client.post("/mcp", json={"jsonrpc": "2.0", "id": 1, "method": "tools/list"})
        assert response.status_code == 200
        data = response.json()
        import json

        result = json.loads(data["content"][0]["text"])
        assert len(result["tools"]) > 0

    def test_get_block(self, client):
        response = client.post(
            "/mcp",
            json={
                "jsonrpc": "2.0",
                "id": 1,
                "method": "tools/call",
                "params": {"name": "get_block", "arguments": {"x": 0, "y": 0, "z": 0}},
            },
        )
        assert response.status_code == 200

    def test_place_and_break_block(self, client):
        import json

        client.post(
            "/mcp",
            json={
                "jsonrpc": "2.0",
                "id": 1,
                "method": "tools/call",
                "params": {"name": "place_block", "arguments": {"x": 10, "y": 25, "z": 10, "type": 1}},
            },
        )
        response = client.post(
            "/mcp",
            json={
                "jsonrpc": "2.0",
                "id": 1,
                "method": "tools/call",
                "params": {"name": "get_block", "arguments": {"x": 10, "y": 25, "z": 10}},
            },
        )
        data = response.json()
        result = json.loads(data["content"][0]["text"])
        assert result["type"] == 1


class TestWebSocket:
    def test_websocket_welcome(self, client):
        with client.websocket_connect("/ws") as ws:
            data = ws.receive_json()
            assert data["type"] == "welcome"
            assert data["player_id"] == 1

    def test_websocket_input(self, client):
        with client.websocket_connect("/ws") as ws:
            ws.receive_json()  # welcome
            ws.send_json({"type": "input", "player_id": 1, "move": {"x": 0, "z": -1}, "look": {"x": 0, "y": 0}})
            # No hay respuesta inmediata, pero no debe fallar

    def test_websocket_ping(self, client):
        with client.websocket_connect("/ws") as ws:
            ws.receive_json()  # welcome
            ws.send_json({"type": "ping", "client_time": 0})
            data = ws.receive_json()
            assert data["type"] == "pong"
