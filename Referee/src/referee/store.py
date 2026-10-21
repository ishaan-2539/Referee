import sqlite3
import json
import uuid
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List

DEFAULT_DB_PATH = "referee.db"

def get_connection(db_path: str = DEFAULT_DB_PATH) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn

def init_db(db_path: str = DEFAULT_DB_PATH) -> None:
    """Initializes the SQLite database with deals and deal_events tables."""
    conn = get_connection(db_path)
    with conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS deals (
                id TEXT PRIMARY KEY,
                direction TEXT,
                counterparty TEXT,
                currency TEXT DEFAULT 'INR',
                mode TEXT,
                partial_policy TEXT DEFAULT 'accept_partial',
                principal_paise INTEGER,
                deadline_ts TEXT,
                status TEXT DEFAULT 'PROPOSED',
                purpose TEXT,
                raw_utterance TEXT,
                created_at TEXT,
                locked_at TEXT
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS deal_events (
                id TEXT PRIMARY KEY,
                deal_id TEXT NOT NULL,
                type TEXT NOT NULL,
                payload_json TEXT NOT NULL,
                ts TEXT NOT NULL,
                FOREIGN KEY(deal_id) REFERENCES deals(id)
            )
        """)
    conn.close()

def create_deal(
    raw_utterance: str,
    slots: Dict[str, Any],
    db_path: str = DEFAULT_DB_PATH
) -> str:
    """Creates a new deal record and appends a 'created' event."""
    deal_id = str(uuid.uuid4())[:8]
    now_iso = datetime.now(timezone.utc).isoformat()
    
    conn = get_connection(db_path)
    with conn:
        conn.execute("""
            INSERT INTO deals (id, direction, counterparty, currency, mode, partial_policy, principal_paise, deadline_ts, status, purpose, raw_utterance, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'PROPOSED', ?, ?, ?)
        """, (
            deal_id,
            slots.get("direction"),
            slots.get("counterparty"),
            slots.get("currency", "INR"),
            slots.get("payment_mode"),
            slots.get("partial_policy", "accept_partial"),
            slots.get("amount_paise"),
            slots.get("deadline_ts"),
            slots.get("purpose"),
            raw_utterance,
            now_iso
        ))
        
        event_id = str(uuid.uuid4())
        conn.execute("""
            INSERT INTO deal_events (id, deal_id, type, payload_json, ts)
            VALUES (?, ?, 'created', ?, ?)
        """, (event_id, deal_id, json.dumps(slots), now_iso))
        
    conn.close()
    return deal_id

def append_event(
    deal_id: str,
    event_type: str,
    payload: Dict[str, Any],
    db_path: str = DEFAULT_DB_PATH
) -> str:
    """Appends an event to the append-only event log."""
    event_id = str(uuid.uuid4())
    now_iso = datetime.now(timezone.utc).isoformat()
    
    conn = get_connection(db_path)
    with conn:
        conn.execute("""
            INSERT INTO deal_events (id, deal_id, type, payload_json, ts)
            VALUES (?, ?, ?, ?, ?)
        """, (event_id, deal_id, event_type, json.dumps(payload), now_iso))
        
        if event_type == "locked":
            conn.execute("UPDATE deals SET status = 'LOCKED', locked_at = ? WHERE id = ?", (now_iso, deal_id))
            
    conn.close()
    return event_id

def get_deal_events(deal_id: str, db_path: str = DEFAULT_DB_PATH) -> List[Dict[str, Any]]:
    """Fetches all events for a deal ordered by timestamp."""
    conn = get_connection(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT id, type, payload_json, ts FROM deal_events WHERE deal_id = ? ORDER BY ts ASC", (deal_id,))
    rows = cursor.fetchall()
    conn.close()
    
    events = []
    for row in rows:
        events.append({
            "id": row["id"],
            "type": row["type"],
            "payload": json.loads(row["payload_json"]),
            "ts": row["ts"]
        })
    return events

def get_deal_state(deal_id: str, db_path: str = DEFAULT_DB_PATH) -> Optional[Dict[str, Any]]:
    """Derives current deal state by folding its event history."""
    conn = get_connection(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM deals WHERE id = ?", (deal_id,))
    deal_row = cursor.fetchone()
    conn.close()

    if not deal_row:
        return None

    state = dict(deal_row)
    events = get_deal_events(deal_id, db_path)
    
    # Map DB column names to detector slot names
    state["amount_paise"] = state.get("principal_paise")
    state["payment_mode"] = state.get("mode")

    paid_paise = 0
    payments = []
    amendments = []

    for ev in events:
        ev_type = ev["type"]
        payload = ev["payload"]
        
        if ev_type == "term_set":
            for k, v in payload.items():
                state[k] = v
                if k == "payment_mode":
                    state["mode"] = v
                if k == "amount_paise":
                    state["principal_paise"] = v
        elif ev_type == "payment":
            amount = payload.get("amount_paise", 0)
            paid_paise += amount
            payments.append(payload)
        elif ev_type == "amended":
            amendments.append(payload)
            for k, v in payload.items():
                if k in state:
                    state[k] = v

    principal = state.get("principal_paise") or 0
    balance = principal - paid_paise

    state["paid_paise"] = paid_paise
    state["balance_paise"] = max(balance, 0)
    state["payments"] = payments
    state["amendments"] = amendments
    
    return state