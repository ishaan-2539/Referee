from starlette.testclient import TestClient
from referee.server import app
from referee.store import init_db

def test_simulator_index_route():
    client = TestClient(app)
    response = client.get("/")
    assert response.status_code == 200
    assert "Referee — Alexa+ MCP Simulator" in response.text

def test_simulator_tool_api():
    init_db("test_tools.db")
    client = TestClient(app)
    response = client.post("/api/tool/propose_deal", json={"utterance": "I lent Aman 500"})
    assert response.status_code == 200
    data = response.json()
    assert "deal_id" in data
    assert data["slots"]["counterparty"] == "Aman"