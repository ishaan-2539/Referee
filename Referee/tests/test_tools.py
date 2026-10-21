from referee.store import init_db
from referee.server import propose_deal, answer_question, lock_deal
from referee.server import log_payment, get_verdict

def test_full_deal_flow():
    # Setup fresh DB
    init_db("test_tools.db")
    
    # 1. Propose deal
    p_res = propose_deal("I lent Aman 1500, he'll pay Friday")
    deal_id = p_res["deal_id"]
    assert deal_id is not None
    assert p_res["open_flags"]
    
    # 2. Answer question
    a_res = answer_question(deal_id, "UPI")
    assert a_res["ready_to_lock"] is True
    
    # 3. Lock deal
    l_res = lock_deal(deal_id, confirm=True)
    assert l_res["status"] == "LOCKED"
    assert "upi_link" in l_res

def test_log_payment_and_verdict_flow():
    init_db("test_tools.db")
    p_res = propose_deal("I lent Aman 1000 rupees")
    deal_id = p_res["deal_id"]
    
    # Answer required fields & lock
    answer_question(deal_id, "Aman")
    answer_question(deal_id, "UPI")
    lock_deal(deal_id, confirm=True)

    # Log payment of 400 INR
    pay_res = log_payment(amount_inr=400.0, deal_id=deal_id)
    assert pay_res["updated_balance_inr"] == 600.0

    # Retrieve verdict
    v_res = get_verdict(deal_id=deal_id)
    assert v_res["verdict_card"]["balance_paise"] == 60000
    assert "Aman" in v_res["summary"]