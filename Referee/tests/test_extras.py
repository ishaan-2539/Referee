import os
import tempfile
import referee.store as store_mod
from referee.store import init_db
from referee.server import propose_deal, answer_question, lock_deal, amend_deal, get_ledger
from referee.links import generate_upi_link, generate_whatsapp_share_link

def test_links_generation():
    upi = generate_upi_link(500.0, payee_vpa="test@upi")
    assert upi is not None
    assert "pa=test%40upi" in upi or "pa=test@upi" in upi
    assert "am=500.00" in upi

    wa = generate_whatsapp_share_link("LENT Rs 500 to Aman")
    assert "https://wa.me/" in wa

def test_amend_and_ledger_flow():
    db_fd, db_path = tempfile.mkstemp()
    os.close(db_fd)
    
    old_db = store_mod.DEFAULT_DB_PATH
    store_mod.DEFAULT_DB_PATH = db_path
    
    try:
        init_db()
        p_res = propose_deal("I lent Aman 1000")
        deal_id = p_res["deal_id"]
        answer_question(deal_id, "Aman")
        answer_question(deal_id, "UPI")
        lock_deal(deal_id, confirm=True)

        am_res = amend_deal(deal_id, field="amount_inr", new_value="1200")
        assert "deal_id" in am_res, f"amend_deal returned error: {am_res.get('error')}"
        assert am_res["deal_id"] == deal_id

        led_res = get_ledger(counterparty="Aman")
        assert led_res["net_balance_inr"] == 1200.0
    finally:
        store_mod.DEFAULT_DB_PATH = old_db
        if os.path.exists(db_path):
            os.unlink(db_path)