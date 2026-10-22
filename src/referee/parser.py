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
        
    l_match = re.search(r"\b(\d+(?:\.\d+)?)\s*(?:lakh|lac|l)\b", text_lower)
    if l_match:
        return int(float(l_match.group(1)) * 100000 * 100)

    num_match = re.search(r"\b(?:rs\.?|inr|\₹)?\s*(\d{1,3}(?:,\d{3})*|\d+)(?:\.(\d{1,2}))?\b", text_lower)
    if num_match:
        raw_num = num_match.group(1).replace(",", "")
        paise_str = num_match.group(2)
        if paise_str:
            paise_str = paise_str.ljust(2, '0')
            return int(raw_num) * 100 + int(paise_str)
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

    party = None

    if is_borrowed:
        m = re.search(r"\bi\s+owe\s+(.+)", text, re.IGNORECASE)
        if not m:
            m = re.search(r"\b(?:from|borrowed\s+from|took\s+from|got\s+from)\s+(.+)", text, re.IGNORECASE)
    elif is_lent:
        m = re.search(r"\b(.+?)\s+owes?\s+me\b", text, re.IGNORECASE)
        if not m:
            m = re.search(r"\b(?:lent|loaned|gave|paid)\s+(?:to\s+)?(.+)", text, re.IGNORECASE)
    else:
        m = None

    if m:
        raw_tail = m.group(1).strip()
        tokens = raw_tail.split()
        name_tokens = []
        for i, tok in enumerate(tokens):
            tok_clean = re.sub(r"[^\w\(\)]", "", tok)
            tok_lower = tok_clean.lower()

            if i == 0 and tok_lower in {"to", "from", "a", "the", "me", "some"}:
                continue

            if tok_lower in {"lakh", "lac", "l", "k", "thousand", "crore", "rs", "inr", "rupees", "rupee", "for", "on", "about", "around", "by", "via", "cash", "upi", "bank"}:
                break

            if re.match(r"^(?:\₹|rs\.?)?\d", tok_lower):
                if re.match(r"^\(\d+\)$", tok_lower) or (i > 0 and re.match(r"^\d{1,2}$", tok_lower)):
                    if i + 1 < len(tokens) and tokens[i+1].lower() in {"lakh", "lac", "l", "k", "thousand", "crore", "rupees", "rs", "inr"}:
                        break
                    name_tokens.append(tok)
                else:
                    break
            elif tok_clean.isalpha():
                name_tokens.append(tok_clean)
            else:
                break

        if name_tokens:
            party = " ".join(name_tokens).strip().title()

    if not party and not direction and re.search(r"\b(he|she|they|him|her)\b", text_lower):
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