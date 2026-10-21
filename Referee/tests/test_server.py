from referee.server import ping

def test_ping():
    """Verify that the ping tool returns 'pong'."""
    assert ping() == "pong"