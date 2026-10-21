from referee.store import init_db
from referee.server import propose_deal, answer_question, lock_deal

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