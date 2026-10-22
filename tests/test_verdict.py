from datetime import datetime, timedelta, timezone
from referee.verdict import compute_verdict

def test_verdict_settled():
    state = {
        "counterparty": "Aman",
        "direction": "lent",
        "principal_paise": 100000,
        "paid_paise": 100000
    }
    v = compute_verdict(state)
    assert v["status"] == "SETTLED"
    assert v["colour"] == "green"

def test_verdict_yellow_card():
    now = datetime.now(timezone.utc)
    deadline = (now - timedelta(days=3)).isoformat()
    state = {
        "counterparty": "Aman",
        "direction": "lent",
        "principal_paise": 100000,
        "paid_paise": 20000,
        "deadline_ts": deadline
    }
    v = compute_verdict(state, now=now)
    assert v["status"] == "OVERDUE"
    assert v["colour"] == "yellow"
    assert v["days_overdue"] == 3

def test_verdict_red_card():
    now = datetime.now(timezone.utc)
    deadline = (now - timedelta(days=10)).isoformat()
    state = {
        "counterparty": "Aman",
        "direction": "lent",
        "principal_paise": 100000,
        "paid_paise": 0,
        "deadline_ts": deadline
    }
    v = compute_verdict(state, now=now)
    assert v["status"] == "OVERDUE"
    assert v["colour"] == "red"
    assert v["days_overdue"] == 10