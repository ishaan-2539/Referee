import os
import pytest
from starlette.testclient import TestClient
import referee.store as store_mod
from referee.store import init_db
from referee.server import app

TEST_DB = "test_simulator_temp.db"


@pytest.fixture(autouse=True)
def fresh_db():
    old_path = store_mod.DEFAULT_DB_PATH
    store_mod.DEFAULT_DB_PATH = TEST_DB
    if os.path.exists(TEST_DB):
        os.remove(TEST_DB)
    init_db(TEST_DB)
    yield
    store_mod.DEFAULT_DB_PATH = old_path
    if os.path.exists(TEST_DB):
        os.remove(TEST_DB)


def test_simulator_index_route():
    client = TestClient(app)
    response = client.get("/")
    assert response.status_code == 200
    assert "Referee — Alexa+ MCP Simulator" in response.text


def test_simulator_tool_api():
    client = TestClient(app)
    response = client.post("/api/tool/propose_deal", json={"utterance": "I lent Aman 500"})
    assert response.status_code == 200
    data = response.json()
    assert "deal_id" in data
    assert data["slots"]["counterparty"] == "Aman"