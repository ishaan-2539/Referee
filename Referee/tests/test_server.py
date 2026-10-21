from referee.server import ping, mcp

def test_ping():
    """Verify that the ping tool returns 'pong'."""
    assert ping() == "pong"

def test_server_name():
    """Verify MCP server instance name."""
    assert mcp.name == "Referee"