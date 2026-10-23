from datetime import datetime
from referee.parser import parse_utterance, parse_utterance_regex
from referee.models import Direction

def test_parse_simple_lending():
    utterance = "I lent Aman 1,500, he'll pay Friday"
    base_date = datetime(2026, 10, 21) # Wednesday
    
    sheet = parse_utterance_regex(utterance, base_dt=base_date)
    
    assert sheet.direction == Direction.LENT
    assert sheet.counterparty == "Aman"
    assert sheet.amount_paise == 150000  # Rs 1,500 in paise
    assert sheet.deadline_ts is not None
    assert sheet.deadline_ts.strftime("%Y-%m-%d") == "2026-10-23"  # Friday

def test_parse_utterance_fallback():
    # Verify the rule-based parser works
    sheet = parse_utterance("I borrowed 500 from Rohan")
    assert sheet.direction == Direction.BORROWED
    assert sheet.counterparty == "Rohan"
    assert sheet.amount_paise == 50000