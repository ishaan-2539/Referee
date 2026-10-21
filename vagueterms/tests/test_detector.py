from vagueterms.detector import detect_vague_terms, DIRECTION_UNCLEAR, PARTY_PRONOUN, AMOUNT_FUZZY

def test_direction_and_pronoun_flagged():
    slots = {"counterparty": "he", "amount_paise": 150000}
    flags, next_q, _ = detect_vague_terms(slots, "he owes me 1500 around Friday")
    
    assert DIRECTION_UNCLEAR in flags
    assert PARTY_PRONOUN in flags
    assert next_q is not None
    assert next_q.rule_id == DIRECTION_UNCLEAR  # Highest priority

def test_blocking_flags():
    slots = {"direction": "lent", "counterparty": "Aman", "amount_paise": None}
    flags, next_q, _ = detect_vague_terms(slots, "I lent Aman about 1500")
    
    assert AMOUNT_FUZZY in flags
    assert next_q is not None
    assert next_q.rule_id == AMOUNT_FUZZY