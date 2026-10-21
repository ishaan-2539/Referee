import os
import referee.store as store_mod
from referee.store import init_db
from referee.server import propose_deal, answer_question, lock_deal, log_payment, get_verdict

def setup_module(module):
    store_mod.DEFAULT_DB_PATH = "test_tools.db"
    init_db("test_tools.db")

def test_full_deal_flow():
    p_res = propose_deal("I lent Aman 1500, he'll pay Friday")
    deal_id = p_res["deal_id"]
    assert deal_id is not None
    assert p_res["open_flags"]
    
    a_res = answer_question(deal_id, "UPI")
    assert a_res["ready_to_lock"] is True
    
    l_res = lock_deal(deal_id, confirm=True)
    assert l_res["status"] == "LOCKED"

def test_log_payment_and_verdict_flow():
    p_res = propose_deal("I lent Aman 1000 rupees")
    deal_id = p_res["deal_id"]
    
    answer_question(deal_id, "Aman")
    answer_question(deal_id, "UPI")
    lock_deal(deal_id, confirm=True)

    pay_res = log_payment(amount_inr=400.0, deal_id=deal_id)
    assert pay_res["updated_balance_inr"] == 600.0

    v_res = get_verdict(deal_id=deal_id)
    assert v_res["verdict_card"]["balance_paise"] == 60000