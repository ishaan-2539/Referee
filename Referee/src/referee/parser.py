import re
from datetime import datetime, timedelta, time
from typing import Optional, Tuple
from dateutil.relativedelta import relativedelta, FR, MO, TU, WE, TH, SA, SU
from referee.models import TermSheet, Direction, PaymentMode

WEEKDAYS = {
    "monday": MO,
    "tuesday": TU,
    "wednesday": WE,
    "thursday": TH,
    "friday": FR,
    "saturday": SA,
    "sunday": SU
}

def parse_amount_paise(text: str) -> Optional[int]:
    """Extracts amount and converts Rupees to integer Paise."""
    text_lower = text.lower()
    
    # Check shorthand amounts like 1.5k, 2l
    k_match = re.search(r"\b(\d+(?:\.\d+)?)\s*k\b", text_lower)
    if k_match:
        return int(float(k_match.group(1)) * 1000 * 100)
        
    l_match = re.search(r"\b(\d+(?:\.\d+)?)\s*l\b", text_lower)
    if l_match:
        return int(float(l_match.group(1)) * 100000 * 100)

    # Match standard numeric formats like 1,500 or 1500
    num_match = re.search(r"\b(?:rs\.?|inr|\₹)?\s*(\d{1,3}(?:,\d{3})*|\d+)\b", text_lower)
    if num_match:
        raw_num = num_match.group(1).replace(",", "")
        return int(raw_num) * 100

    return None

def parse_direction_and_party(text: str) -> Tuple[Optional[Direction], Optional[str]]:
    """Extracts lending/borrowing direction and counterparty name."""
    text_lower = text.lower()
    
    # Patterns for lending
    lent_match = re.search(r"\b(?:lent|loaned|gave|paid)\s+(?:to\s+)?([A-Z][a-z]+|[a-z]+)", text, re.IGNORECASE)
    if lent_match:
        party = lent_match.group(1)
        if party.lower() not in {"to", "me", "a", "the", "some"}:
            return Direction.LENT, party.capitalize()
        return Direction.LENT, None

    # Patterns for borrowing
    borrowed_match = re.search(r"\b(?:borrowed|took|got)\s+(?:from\s+)?([A-Z][a-z]+|[a-z]+)", text, re.IGNORECASE)
    if borrowed_match:
        party = borrowed_match.group(1)
        if party.lower() not in {"from", "me", "a", "the", "some"}:
            return Direction.BORROWED, party.capitalize()
        return Direction.BORROWED, None

    # Pronoun fallback
    if re.search(r"\b(he|she|they|him|her)\b", text_lower):
        if "pay" in text_lower or "owes" in text_lower:
            return Direction.LENT, "he"

    return None, None

def parse_deadline(text: str, base_dt: Optional[datetime] = None) -> Optional[datetime]:
    """Parses relative weekday deadlines into absolute timezone-naive datetimes (11:59 PM)."""
    text_lower = text.lower()
    now = base_dt or datetime.now()

    if "tomorrow" in text_lower:
        target = now + timedelta(days=1)
        return datetime.combine(target.date(), time(23, 59))

    for day_name, day_enum in WEEKDAYS.items():
        if day_name in text_lower:
            # Advance to the next occurrence of the given weekday
            target = now + relativedelta(weekday=day_enum(+1))
            return datetime.combine(target.date(), time(23, 59))

    return None

def parse_payment_mode(text: str) -> Optional[PaymentMode]:
    """Detects specified payment mode."""
    text_lower = text.lower()
    if "upi" in text_lower or "gpay" in text_lower or "phonepe" in text_lower:
        return PaymentMode.UPI
    if "cash" in text_lower:
        return PaymentMode.CASH
    if "bank" in text_lower or "transfer" in text_lower:
        return PaymentMode.BANK
    return None

def parse_utterance(utterance: str, base_dt: Optional[datetime] = None) -> TermSheet:
    """Combines parsing rules into a filled TermSheet."""
    direction, counterparty = parse_direction_and_party(utterance)
    amount_paise = parse_amount_paise(utterance)
    deadline_ts = parse_deadline(utterance, base_dt=base_dt)
    payment_mode = parse_payment_mode(utterance)

    return TermSheet(
        direction=direction,
        counterparty=counterparty,
        amount_paise=amount_paise,
        deadline_ts=deadline_ts,
        payment_mode=payment_mode
    )