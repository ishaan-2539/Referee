import os
import re
import json
from datetime import datetime, timedelta, time
from typing import Optional, Tuple, Dict, Any
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
    """Extracts lending/borrowing direction and counterparty name."""
    text_lower = text.lower()

    is_lent = bool(re.search(r"\b(?:lent|loaned|gave|paid)\b", text_lower))
    is_borrowed = bool(re.search(r"\b(?:borrowed|took|got)\b", text_lower))

    from_match = re.search(r"\bfrom\s+([A-Za-z]+)", text, re.IGNORECASE)
    to_match = re.search(r"\bto\s+([A-Za-z]+)", text, re.IGNORECASE)

    party = None
    direction = None

    if is_borrowed:
        direction = Direction.BORROWED
        if from_match and from_match.group(1).lower() not in {"me", "a", "the", "some"}:
            party = from_match.group(1).capitalize()
        else:
            m = re.search(r"\b(?:borrowed|took|got)\s+(?:from\s+)?([A-Za-z]+)", text, re.IGNORECASE)
            if m and m.group(1).lower() not in {"from", "me", "a", "the", "some"}:
                party = m.group(1).capitalize()

    elif is_lent:
        direction = Direction.LENT
        if to_match and to_match.group(1).lower() not in {"me", "a", "the", "some"}:
            party = to_match.group(1).capitalize()
        else:
            m = re.search(r"\b(?:lent|loaned|gave|paid)\s+(?:to\s+)?([A-Za-z]+)", text, re.IGNORECASE)
            if m and m.group(1).lower() not in {"to", "me", "a", "the", "some"}:
                party = m.group(1).capitalize()

    if not direction and re.search(r"\b(he|she|they|him|her)\b", text_lower):
        if "pay" in text_lower or "owes" in text_lower:
            direction = Direction.LENT
            party = "he"

    return direction, party

def parse_deadline(text: str, base_dt: Optional[datetime] = None) -> Optional[datetime]:
    """Parses relative weekday deadlines into absolute datetimes (11:59 PM IST)."""
    text_lower = text.lower()
    now = base_dt or datetime.now()

    if "tomorrow" in text_lower:
        target = now + timedelta(days=1)
        return datetime.combine(target.date(), time(23, 59))

    for day_name, day_enum in WEEKDAYS.items():
        if day_name in text_lower:
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

def parse_utterance_regex(utterance: str, base_dt: Optional[datetime] = None) -> TermSheet:
    """Regex + rule-based parser fallback."""
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

def parse_utterance_bedrock(utterance: str, base_dt: Optional[datetime] = None) -> Optional[TermSheet]:
    """Parses utterance using Amazon Bedrock (Amazon Nova models). Returns None on failure."""
    try:
        import boto3
        region = os.getenv("AWS_REGION", "us-east-1")
        model_id = os.getenv("BEDROCK_MODEL_ID", "amazon.nova-lite-v1:0")
        client = boto3.client("bedrock-runtime", region_name=region)

        prompt = f"""Extract term sheet slots from this informal money handshake utterance: "{utterance}"
Return ONLY a valid JSON object with the following fields:
- "direction": "lent" or "borrowed" or null
- "counterparty": string name or pronoun or null
- "amount_inr": float or null
- "deadline_relative": relative string description or null
- "payment_mode": "cash", "upi", "bank", or null
Do not include any extra text or markdown formatting.
"""

        body = json.dumps({
            "messages": [{"role": "user", "content": [{"text": prompt}]}],
            "inferenceConfig": {"temperature": 0.0, "maxTokens": 200}
        })

        response = client.invoke_model(
            modelId=model_id,
            contentType="application/json",
            accept="application/json",
            body=body
        )
        
        resp_body = json.loads(response["body"].read().decode("utf-8"))
        content_text = resp_body["output"]["message"]["content"][0]["text"].strip()
        
        # Clean JSON markdown backticks if present
        if content_text.startswith("```"):
            content_text = re.sub(r"^```(?:json)?\n?|\n?```$", "", content_text, flags=re.MULTILINE).strip()

        data = json.loads(content_text)

        dir_val = Direction(data.get("direction")) if data.get("direction") in {"lent", "borrowed"} else None
        amt_val = int(float(data["amount_inr"]) * 100) if data.get("amount_inr") is not None else None
        mode_val = PaymentMode(data.get("payment_mode")) if data.get("payment_mode") in {"cash", "upi", "bank"} else None
        
        deadline_val = None
        if data.get("deadline_relative"):
            deadline_val = parse_deadline(data["deadline_relative"], base_dt=base_dt)

        return TermSheet(
            direction=dir_val or parse_direction_and_party(utterance)[0],
            counterparty=data.get("counterparty") or parse_direction_and_party(utterance)[1],
            amount_paise=amt_val or parse_amount_paise(utterance),
            deadline_ts=deadline_val or parse_deadline(utterance, base_dt=base_dt),
            payment_mode=mode_val or parse_payment_mode(utterance)
        )
    except Exception:
        return None

def parse_utterance(utterance: str, base_dt: Optional[datetime] = None) -> TermSheet:
    """Primary parser entry point. Tries Amazon Bedrock first, falling back to deterministic regex."""
    if os.getenv("ENABLE_BEDROCK", "false").lower() in {"true", "1"}:
        parsed = parse_utterance_bedrock(utterance, base_dt=base_dt)
        if parsed is not None:
            return parsed

    return parse_utterance_regex(utterance, base_dt=base_dt)