import sqlite3
import json
import uuid
import hashlib
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List, Tuple

DEFAULT_DB_PATH = "referee.db"

# event payload key -> deals table column (whitelist, so the dynamic SQL below is safe)
TERM_TO_COLUMN = {
    "direction": "direction",
    "counterparty": "counterparty",
    "currency": "currency",
    "payment_mode": "mode",
    "mode": "mode",
    "partial_policy": "partial_policy",
    "amount_paise": "principal_paise",
    "principal_paise": "principal_paise",
    "deadline_ts": "deadline_ts",
    "purpose": "purpose",
}


def get_connection(db_path: Optional[str] = None) -> sqlite3.Connection:
    if db_path is None:
        db_path = DEFAULT_DB_PATH
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def init_db(db_path: Optional[str] = None) -> None:
    """Initializes the SQLite database with deals and deal_events tables."""
    if db_path is None:
        db_path = DEFAULT_DB_PATH
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
                prev_hash TEXT,
                hash TEXT NOT NULL,
                FOREIGN KEY(deal_id) REFERENCES deals(id)
            )
        """)

        # Migration check for existing DB instances without hash columns
        cursor = conn.cursor()
        cursor.execute("PRAGMA table_info(deal_events)")
        columns = [column[1] for column in cursor.fetchall()]
        if "prev_hash" not in columns:
            cursor.execute("ALTER TABLE deal_events ADD COLUMN prev_hash TEXT")
        if "hash" not in columns:
            cursor.execute("ALTER TABLE deal_events ADD COLUMN hash TEXT DEFAULT ''")
    conn.close()


def compute_event_hash(prev_hash: str, event_type: str, payload_json: str, ts: str) -> str:
    """Computes a SHA-256 digest over event components for tamper-evidence."""
    raw = f"{prev_hash}{event_type}{payload_json}{ts}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def create_deal(
    raw_utterance: str,
    slots: Dict[str, Any],
    db_path: Optional[str] = None
) -> str:
    """Creates a new deal record and appends an initial 'created' event with cryptographic hash genesis."""
    if db_path is None:
        db_path = DEFAULT_DB_PATH
    deal_id = str(uuid.uuid4())[:8]
    now_iso = datetime.now(timezone.utc).isoformat()
    payload_json = json.dumps(slots, sort_keys=True)

    # Genesis event prev_hash is derived from the deal_id itself
    prev_hash = f"GENESIS_{deal_id}"
    event_hash = compute_event_hash(prev_hash, "created", payload_json, now_iso)

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
            INSERT INTO deal_events (id, deal_id, type, payload_json, ts, prev_hash, hash)
            VALUES (?, ?, 'created', ?, ?, ?, ?)
        """, (event_id, deal_id, payload_json, now_iso, prev_hash, event_hash))

    conn.close()
    return deal_id


def append_event(
    deal_id: str,
    event_type: str,
    payload: Dict[str, Any],
    db_path: Optional[str] = None
) -> str:
    """Appends an event to the tamper-evident append-only event log."""
    if db_path is None:
        db_path = DEFAULT_DB_PATH
    event_id = str(uuid.uuid4())
    now_iso = datetime.now(timezone.utc).isoformat()
    payload_json = json.dumps(payload, sort_keys=True)

    conn = get_connection(db_path)
    with conn:
        cursor = conn.cursor()
        cursor.execute("SELECT hash FROM deal_events WHERE deal_id = ? ORDER BY ts DESC, rowid DESC LIMIT 1", (deal_id,))
        row = cursor.fetchone()
        prev_hash = row["hash"] if row else f"GENESIS_{deal_id}"

        event_hash = compute_event_hash(prev_hash, event_type, payload_json, now_iso)

        conn.execute("""
            INSERT INTO deal_events (id, deal_id, type, payload_json, ts, prev_hash, hash)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (event_id, deal_id, event_type, payload_json, now_iso, prev_hash, event_hash))

        # Keep the deals lookup columns in sync with the event log.
        # The event log stays the source of truth; this is a read-model cache so that
        # SQL lookups by counterparty (log_payment, get_verdict, get_ledger) see renames.
        if event_type in ("term_set", "amended"):
            if event_type == "term_set":
                items = list(payload.items())
            else:
                items = [(payload.get("field"), payload.get("new_value"))]

            column_updates: Dict[str, Any] = {}
            for key, value in items:
                col = TERM_TO_COLUMN.get(key) if isinstance(key, str) else None
                if col:
                    column_updates[col] = value

            if column_updates:
                set_clause = ", ".join(f"{col} = ?" for col in column_updates)
                conn.execute(
                    f"UPDATE deals SET {set_clause} WHERE id = ?",
                    (*column_updates.values(), deal_id),
                )

        if event_type == "locked":
            conn.execute("UPDATE deals SET status = 'LOCKED', locked_at = ? WHERE id = ?", (now_iso, deal_id))

    conn.close()
    return event_id


def verify_deal_integrity(deal_id: str, db_path: Optional[str] = None) -> Tuple[bool, str]:
    """Verifies that no events in the deal's ledger chain have been modified or reordered."""
    if db_path is None:
        db_path = DEFAULT_DB_PATH
    conn = get_connection(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT id, type, payload_json, ts, prev_hash, hash FROM deal_events WHERE deal_id = ? ORDER BY ts ASC, rowid ASC", (deal_id,))
    rows = cursor.fetchall()
    conn.close()

    if not rows:
        return False, "No events found for deal"

    expected_prev = f"GENESIS_{deal_id}"
    for idx, row in enumerate(rows):
        if row["prev_hash"] != expected_prev:
            return False, f"Broken chain link at index {idx}: prev_hash mismatch."

        recomputed = compute_event_hash(row["prev_hash"], row["type"], row["payload_json"], row["ts"])
        if recomputed != row["hash"]:
            return False, f"Tampered event at index {idx}: hash mismatch."

        expected_prev = row["hash"]

    return True, "Ledger integrity verified: SHA-256 chain intact."


def get_deal_events(deal_id: str, db_path: Optional[str] = None) -> List[Dict[str, Any]]:
    """Fetches all events for a deal ordered by timestamp."""
    if db_path is None:
        db_path = DEFAULT_DB_PATH
    conn = get_connection(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT id, type, payload_json, ts, prev_hash, hash FROM deal_events WHERE deal_id = ? ORDER BY ts ASC, rowid ASC", (deal_id,))
    rows = cursor.fetchall()
    conn.close()

    events = []
    for row in rows:
        events.append({
            "id": row["id"],
            "type": row["type"],
            "payload": json.loads(row["payload_json"]),
            "ts": row["ts"],
            "prev_hash": row["prev_hash"],
            "hash": row["hash"]
        })
    return events


def get_deal_state(deal_id: str, db_path: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """Derives current deal state by folding its event history."""
    if db_path is None:
        db_path = DEFAULT_DB_PATH

    conn = get_connection(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM deals WHERE id = ?", (deal_id,))
    deal_row = cursor.fetchone()
    conn.close()

    if not deal_row:
        return None

    state = dict(deal_row)
    events = get_deal_events(deal_id, db_path)

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
            field = payload.get("field")
            if field:
                new_val = payload.get("new_value")
                state[field] = new_val
                if field == "principal_paise":
                    state["amount_paise"] = new_val
                elif field == "payment_mode":
                    state["mode"] = new_val

    principal = state.get("principal_paise") or 0
    balance = principal - paid_paise

    state["paid_paise"] = paid_paise
    state["balance_paise"] = max(balance, 0)
    state["payments"] = payments
    state["amendments"] = amendments

    return state