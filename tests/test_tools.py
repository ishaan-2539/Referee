import os
import pytest
import referee.store as store_mod
from referee.store import init_db, verify_deal_integrity, get_deal_state
from referee.server import (
    propose_deal,
    answer_question,
    lock_deal,
    log_payment,
    get_verdict,
    get_ledger,
    amend_deal
)

TEST_DB = "test_tools.db"


@pytest.fixture(autouse=True)
def fresh_db():
    """Give every test its own empty database so deals never leak between tests."""
    old_path = store_mod.DEFAULT_DB_PATH
    store_mod.DEFAULT_DB_PATH = TEST_DB
    if os.path.exists(TEST_DB):
        os.remove(TEST_DB)
    init_db(TEST_DB)
    yield
    store_mod.DEFAULT_DB_PATH = old_path
    if os.path.exists(TEST_DB):
        os.remove(TEST_DB)


def test_full_deal_flow_and_hash_chain():
    # 1. Initial proposal
    p_res = propose_deal("I lent Aman 1500, he'll pay Friday")
    deal_id = p_res["deal_id"]
    assert deal_id is not None
    assert len(p_res["open_flags"]) > 0

    # 2. Answer mode question
    a_res = answer_question(deal_id, "UPI")
    assert a_res["ready_to_lock"] is True

    # 3. Lock deal
    l_res = lock_deal(deal_id, confirm=True)
    assert l_res["status"] == "LOCKED"

    # 4. Verify Cryptographic Event Chain Hash
    valid, msg = verify_deal_integrity(deal_id, db_path=TEST_DB)
    assert valid is True, f"Integrity check failed: {msg}"


def test_multi_turn_disambiguation_e2e_scenario():
    """Two Amans: party disambiguation, partial payment, integrity check and ledger query."""

    # --- Step A: Deal 1 with Aman #1 ---
    d1 = propose_deal("I lent Aman 1000 rupees")
    deal1_id = d1["deal_id"]
    answer_question(deal1_id, "UPI")
    l1 = lock_deal(deal1_id, confirm=True)
    assert l1["status"] == "LOCKED"

    # Deal 1 must keep the plain name "Aman" (not be renamed by the mode answer)
    state1 = get_deal_state(deal1_id, db_path=TEST_DB)
    assert state1 is not None
    assert state1["counterparty"] == "Aman"

    # --- Step B: Deal 2 with a different Aman ---
    d2 = propose_deal("I lent Aman 1500 rupees")
    deal2_id = d2["deal_id"]

    # Server asks whether this is the same Aman or a different person
    dis_res = answer_question(deal2_id, "its a different aman")
    assert "error" not in dis_res

    state2 = get_deal_state(deal2_id, db_path=TEST_DB)
    assert state2 is not None
    assert "Its" not in state2["counterparty"]
    assert state2["counterparty"] != "Aman"  # must not collide with deal 1

    # Complete and lock Deal 2
    answer_question(deal2_id, "UPI")
    l2 = lock_deal(deal2_id, confirm=True)
    assert l2["status"] == "LOCKED"

    # --- Step C: Log payment for the second Aman only ---
    target_party = state2["counterparty"]
    pay_res = log_payment(amount_inr=500.0, counterparty=target_party)
    assert "error" not in pay_res, pay_res
    assert pay_res["updated_balance_inr"] == 1000.0

    # --- Step D: Verify cryptographic integrity across both deals ---
    val1, _ = verify_deal_integrity(deal1_id, db_path=TEST_DB)
    val2, _ = verify_deal_integrity(deal2_id, db_path=TEST_DB)
    assert val1 is True
    assert val2 is True

    # --- Step E: Query ledger ---
    ledger = get_ledger()
    assert "deals" in ledger
    assert len(ledger["deals"]) >= 2