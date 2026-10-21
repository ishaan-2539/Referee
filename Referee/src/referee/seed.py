"""
Seed Data Script for Referee Demo.
Populates referee.db with realistic handshake deals for demonstration purposes.
Clearly labeled: DEMO SEED DATA
"""

import os
from datetime import datetime, timedelta, timezone
from referee.store import init_db, create_deal, append_event

def seed_database(db_path: str = "referee.db"):
    """Populates database with sample deals in various states (OPEN, OVERDUE, SETTLED)."""
    # Re-initialize DB
    init_db(db_path)
    now = datetime.now(timezone.utc)

    print("🌱 Seeding Referee database with sample demo deals...")

    # --- Deal 1: Rahul (Yellow Card - Overdue by 3 days) ---
    d1_slots = {
        "direction": "lent",
        "counterparty": "Rahul",
        "amount_paise": 200000, # ₹2,000
        "currency": "INR",
        "deadline_ts": (now - timedelta(days=3)).isoformat(),
        "payment_mode": "upi",
        "partial_policy": "accept_partial"
    }
    deal1_id = create_deal("I lent Rahul 2000 rupees, due 3 days ago", d1_slots, db_path=db_path)
    append_event(deal1_id, "locked", {"locked": True}, db_path=db_path)
    append_event(deal1_id, "payment", {"amount_paise": 50000, "mode": "upi"}, db_path=db_path) # ₹500 paid, ₹1500 remaining

    # --- Deal 2: Priya (Red Card - Overdue by 10 days) ---
    d2_slots = {
        "direction": "lent",
        "counterparty": "Priya",
        "amount_paise": 500000, # ₹5,000
        "currency": "INR",
        "deadline_ts": (now - timedelta(days=10)).isoformat(),
        "payment_mode": "bank",
        "partial_policy": "accept_partial"
    }
    deal2_id = create_deal("I lent Priya 5000 for concert tickets", d2_slots, db_path=db_path)
    append_event(deal2_id, "locked", {"locked": True}, db_path=db_path)

    # --- Deal 3: Rohan (Settled Deal - Green Card) ---
    d3_slots = {
        "direction": "lent",
        "counterparty": "Rohan",
        "amount_paise": 100000, # ₹1,000
        "currency": "INR",
        "deadline_ts": (now - timedelta(days=1)).isoformat(),
        "payment_mode": "cash",
        "partial_policy": "accept_partial"
    }
    deal3_id = create_deal("I lent Rohan 1000 cash", d3_slots, db_path=db_path)
    append_event(deal3_id, "locked", {"locked": True}, db_path=db_path)
    append_event(deal3_id, "payment", {"amount_paise": 100000, "mode": "cash"}, db_path=db_path)

    print(f"✅ Seeding complete! Populated 3 sample deals:\n - Rahul (₹1,500 due, Yellow Card)\n - Priya (₹5,000 due, Red Card)\n - Rohan (Fully SETTLED, Green Card)")

if __name__ == "__main__":
    seed_database()