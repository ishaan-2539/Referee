import os
import re
import json
from datetime import datetime, timedelta, time, timezone
from typing import Optional, Tuple, Dict, Any
from dateutil.relativedelta import relativedelta, FR, MO, TU, WE, TH, SA, SU
from referee.models import TermSheet, Direction, PaymentMode

IST = timezone(timedelta(hours=5, minutes=30))

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
    
    k_match = re.search(r"\b(\d+(?:\.\d+)?)\s*k\b", text_lower)
    if k_match:
        return int(float(k_match.group(1)) * 1000 * 100)
        
    l_match = re.search(r"\b(\d+(?:\.\d+)?)\s*l\b", text_lower)
    if l_match:
        return int(float(l_match.group(1)) * 100000 * 100)

    num_match = re.search(r"\b(?:rs\.?|inr|\₹)?\s*(\d{1,3}(?:,\d{3})*|\d+)\b", text_lower)
    if num_match:
        raw_num = num_match.group(1).replace(",", "")
        return int(raw_num) * 100

    return None

def parse_direction_and_party(text: str) -> Tuple[Optional[Direction], Optional[str]]:
    """Extracts lending/borrowing direction and counterparty name cleanly without swallowing amounts."""
    text_lower = text.lower()

    is_lent = bool(re.search(r"\b(?:lent|loaned|gave|paid)\b", text_lower)) or bool(re.search(r"\bowes?\s+me\b", text_lower))
    is_borrowed = bool(re.search(r"\b(?:borrowed|took|got)\b", text_lower)) or bool(re.search(r"\bi\s+owe\b", text_lower))

    direction = None
    if is_borrowed:
        direction = Direction.BORROWED
    elif is_lent:
        direction = Direction.LENT

    # Matches names like "Aman", "Aman Sharma", "Aman 2", "Aman (2)",
    # while preventing matching digits from formatted numbers like "1,500"
    name_pattern = r"([A-Za-z]+(?:\s+(?:\(\d+\)|\d\b(?![,\.\d])|[A-Za-z]+))*)"

    party = None

    if is_borrowed:
        m = re.search(r"\bi\s+owe\s+" + name_pattern, text, re.IGNORECASE)
        if m:
            party = m.group(1).strip()
        else:
            m2 = re.search(r"\b(?:from|borrowed\s+from|took\s+from|got\s+from)\s+" + name_pattern, text, re.IGNORECASE)
            if m2 and m2.group(1).lower() not in {"me", "a", "the", "some"}:
                party = m2.group(1).strip()

    elif is_lent:
        m = re.search(r"\b" + name_pattern + r"\s+owes?\s+me\b", text, re.IGNORECASE)
        if m:
            party = m.group(1).strip()
        else:
            m2 = re.search(r"\b(?:lent|loaned|gave|paid)\s+(?:to\s+)?" + name_pattern, text, re.IGNORECASE)
            if m2 and m2.group(1).lower() not in {"to", "me", "a", "the", "some"}:
                party = m2.group(1).strip()

    if party:
        party = re.sub(r"^(?:to|from|a|the)\s+", "", party, flags=re.IGNORECASE).strip().title()

    if not direction and re.search(r"\b(he|she|they|him|her)\b", text_lower):
        if "pay" in text_lower or "owes" in text_lower:
            direction = Direction.LENT
            party = "he"

    return direction, party

def parse_deadline(text: str, base_dt: Optional[datetime] = None) -> Optional[datetime]:
    """Parses relative weekday deadlines into absolute datetimes (11:59 PM IST)."""
    text_lower = text.lower()
    now = base_dt or datetime.now(IST)
    if now.tzinfo is None:
        now = now.replace(tzinfo=IST)

    if "tomorrow" in text_lower:
        target = now + timedelta(days=1)
        return datetime.combine(target.date(), time(23, 59), tzinfo=IST)

    for day_name, day_enum in WEEKDAYS.items():
        if day_name in text_lower:
            target = now + relativedelta(weekday=day_enum(+1))
            return datetime.combine(target.date(), time(23, 59), tzinfo=IST)

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

def parse_utterance_regex(utterance: str, base_dt: Optional[datetime] = None) -> TermSheet:
    """Regex + rule-based parser fallback."""
    direction, counterparty = parse_direction_and_party(utterance)

    # Strip out the counterparty name before parsing amount to prevent matching digits in names (e.g. 'Aman 2')
    text_for_amount = utterance
    if counterparty:
        text_for_amount = re.sub(re.escape(counterparty), "", utterance, flags=re.IGNORECASE)

    amount_paise = parse_amount_paise(text_for_amount)
    deadline_ts = parse_deadline(utterance, base_dt=base_dt)
    payment_mode = parse_payment_mode(utterance)

    return TermSheet(
        direction=direction,
        counterparty=counterparty,
        amount_paise=amount_paise,
        deadline_ts=deadline_ts,
        payment_mode=payment_mode
    )

def parse_utterance(utterance: str, base_dt: Optional[datetime] = None) -> TermSheet:
    return parse_utterance_regex(utterance, base_dt=base_dt)