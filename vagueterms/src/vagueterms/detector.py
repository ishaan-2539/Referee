import re
from dataclasses import dataclass
from typing import List, Optional, Dict, Any, Tuple

# Rule ID constants
DEADLINE_RELATIVE = "DEADLINE_RELATIVE"
DEADLINE_FUZZY = "DEADLINE_FUZZY"
DEADLINE_CONDITIONAL = "DEADLINE_CONDITIONAL"
AMOUNT_FUZZY = "AMOUNT_FUZZY"
AMOUNT_UNIT = "AMOUNT_UNIT"
PARTY_PRONOUN = "PARTY_PRONOUN"
PARTY_AMBIGUOUS = "PARTY_AMBIGUOUS"
DIRECTION_UNCLEAR = "DIRECTION_UNCLEAR"
MODE_MISSING = "MODE_MISSING"
PARTIAL_MISSING = "PARTIAL_MISSING"

# Blocking flags that prevent locking a deal
BLOCKING_FLAGS = {DIRECTION_UNCLEAR, PARTY_PRONOUN, AMOUNT_FUZZY}

# Priority order for asking clarifying questions
PRIORITY_ORDER = [
    DIRECTION_UNCLEAR,
    PARTY_PRONOUN,
    PARTY_AMBIGUOUS,
    AMOUNT_FUZZY,
    AMOUNT_UNIT,
    DEADLINE_RELATIVE,
    DEADLINE_FUZZY,
    DEADLINE_CONDITIONAL,
    MODE_MISSING,
    PARTIAL_MISSING,
]

PRONOUNS = {"he", "she", "they", "them", "him", "her", "guys", "group", "someone", "friend"}

@dataclass
class Question:
    rule_id: str
    prompt: str
    proposed_default: Any

def detect_vague_terms(
    slots: Dict[str, Any],
    raw_utterance: str,
    matching_counterparties: Optional[List[str]] = None
) -> Tuple[List[str], Optional[Question], List[str]]:
    """
    Pure-function detector for vague handshake terms.
    Returns:
        open_flags: List of rule IDs triggered
        next_question: The highest priority question (or None if no flags)
        defaults_applied: List of defaulted slot descriptions if capped
    """
    flags = []
    utterance_lower = raw_utterance.lower()

    # Rule 1: DIRECTION_UNCLEAR
    if not slots.get("direction"):
        flags.append(DIRECTION_UNCLEAR)

    # Rule 2: PARTY_PRONOUN
    counterparty = slots.get("counterparty")
    if not counterparty or counterparty.lower() in PRONOUNS:
        flags.append(PARTY_PRONOUN)

    # Rule 3: PARTY_AMBIGUOUS
    if matching_counterparties and len(matching_counterparties) > 1:
        flags.append(PARTY_AMBIGUOUS)

    # Rule 4: AMOUNT_FUZZY
    if re.search(r"\b(around|about|approx|approximately|~|some|a few)\b", utterance_lower) or not slots.get("amount_paise"):
        flags.append(AMOUNT_FUZZY)

    # Rule 5: AMOUNT_UNIT
    if not slots.get("amount_confirmed") and re.search(r"\b(\d+k|\d+l|half)\b", utterance_lower):
        flags.append(AMOUNT_UNIT)

    # Rule 6: DEADLINE_RELATIVE
    if not slots.get("deadline_confirmed") and re.search(r"\b(monday|tuesday|wednesday|thursday|friday|saturday|sunday|next week|tomorrow|later)\b", utterance_lower):
        flags.append(DEADLINE_RELATIVE)

    # Rule 7: DEADLINE_FUZZY
    if not slots.get("deadline_confirmed") and re.search(r"\b(end of month|by evening|in a few days|soon)\b", utterance_lower):
        flags.append(DEADLINE_FUZZY)

    # Rule 8: DEADLINE_CONDITIONAL
    if not slots.get("deadline_confirmed") and re.search(r"\b(when he gets paid|when i need it|once he can|whenever)\b", utterance_lower):
        flags.append(DEADLINE_CONDITIONAL)

    # Rule 9: MODE_MISSING
    if not slots.get("payment_mode"):
        flags.append(MODE_MISSING)

    # Rule 10: PARTIAL_MISSING
    if not slots.get("partial_policy"):
        flags.append(PARTIAL_MISSING)

    # Questions mapping
    questions_map = {
        DIRECTION_UNCLEAR: Question(DIRECTION_UNCLEAR, "Does the other person owe you, or do you owe them?", "lent"),
        PARTY_PRONOUN: Question(PARTY_PRONOUN, "Who exactly? Give me a full name.", None),
        PARTY_AMBIGUOUS: Question(PARTY_AMBIGUOUS, f"Which person did you mean? ({', '.join(matching_counterparties or [])})", matching_counterparties[0] if matching_counterparties else None),
        AMOUNT_FUZZY: Question(AMOUNT_FUZZY, "Exactly how much was agreed in total?", None),
        AMOUNT_UNIT: Question(AMOUNT_UNIT, "Can you confirm the exact total amount in Rupees?", slots.get("amount_paise")),
        DEADLINE_RELATIVE: Question(DEADLINE_RELATIVE, "Is Friday 11:59 PM IST acceptable as the exact deadline?", "Friday 11:59 PM IST"),
        DEADLINE_FUZZY: Question(DEADLINE_FUZZY, "Should we set the deadline to the end of this month at 11:59 PM IST?", "End of Month 11:59 PM IST"),
        DEADLINE_CONDITIONAL: Question(DEADLINE_CONDITIONAL, "What specific date should it be due if that event hasn't happened?", "In 14 days"),
        MODE_MISSING: Question(MODE_MISSING, "How will this be paid: cash, UPI, or bank transfer?", "UPI"),
        PARTIAL_MISSING: Question(PARTIAL_MISSING, "If a partial payment is made, does that count towards reducing the balance with the deadline unchanged?", "accept_partial"),
    }

    # Pick the highest priority question
    next_q = None
    for rule in PRIORITY_ORDER:
        if rule in flags:
            next_q = questions_map.get(rule)
            break

    return flags, next_q, []