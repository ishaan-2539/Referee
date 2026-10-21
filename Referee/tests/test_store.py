import os
import tempfile
import pytest
from referee.store import init_db, create_deal, append_event, get_deal_state

@pytest.fixture
def test_db():
    db_fd, db_path = tempfile.mkstemp()
    init_db(db_path)
    yield db_path
    os.close(db_fd)
    os.unlink(db_path)

def test_create_and_fold_deal(test_db):
    slots = {
        "direction": "lent",
        "counterparty": "Aman",
        "amount_paise": 100000,
        "payment_mode": "upi"
    }
    deal_id = create_deal("I lent Aman 1000", slots, db_path=test_db)
    
    # Verify initial creation
    state = get_deal_state(deal_id, db_path=test_db)
    assert state is not None
    assert state["counterparty"] == "Aman"
    assert state["balance_paise"] == 100000

    # Lock deal
    append_event(deal_id, "locked", {"locked_by": "user"}, db_path=test_db)
    
    # Log a payment of 400 INR (40000 paise)
    append_event(deal_id, "payment", {"amount_paise": 40000}, db_path=test_db)
    
    # Fold state again and check balance calculation
    updated_state = get_deal_state(deal_id, db_path=test_db)
    assert updated_state is not None
    assert updated_state["paid_paise"] == 40000
    assert updated_state["balance_paise"] == 60000