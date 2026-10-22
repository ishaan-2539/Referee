from datetime import datetime, timedelta, timezone
from typing import Dict, Any, Optional

IST = timezone(timedelta(hours=5, minutes=30))
def compute_verdict(state: Dict[str, Any], now: Optional[datetime] = None) -> Dict[str, Any]:
    if now is None:
        now = datetime.now(IST)
    elif now.tzinfo is None:
        now = now.replace(tzinfo=IST)

    principal_paise = state.get("principal_paise") or state.get("amount_paise") or 0
    paid_paise = state.get("paid_paise") or 0
    balance_paise = max(principal_paise - paid_paise, 0)

    counterparty = state.get("counterparty") or "Counterparty"
    direction = state.get("direction") or "lent"
    partial_policy = state.get("partial_policy") or "accept_partial"

    deadline_ts_str = state.get("deadline_ts")
    deadline_dt = None
    if deadline_ts_str:
        try:
            deadline_dt = datetime.fromisoformat(deadline_ts_str)
            if deadline_dt.tzinfo is None:
                deadline_dt = deadline_dt.replace(tzinfo=IST)
        except ValueError:
            pass

    if balance_paise == 0 and principal_paise > 0:
        status = "SETTLED"
        colour = "green"
        days_overdue = 0
    elif deadline_dt and now > deadline_dt and balance_paise > 0:
        status = "OVERDUE"
        time_diff = now - deadline_dt
        days_overdue = max(time_diff.days, 1)

        if 1 <= days_overdue <= 7:
            colour = "yellow"
        else:
            colour = "red"
    else:
        days_overdue = 0
        if paid_paise > 0 and partial_policy != "all_or_nothing":
            status = "PARTIALLY_PAID"
        else:
            status = "OPEN"
        colour = "neutral"

    balance_inr = balance_paise / 100
    if status == "SETTLED":
        one_liner = f"Verdict: Deal with {counterparty} is fully SETTLED. Green card."
    elif status == "OVERDUE":
        verb = "owes you" if direction == "lent" else "you owe"
        card_str = "Yellow card" if colour == "yellow" else "Red card"
        one_liner = f"Verdict: {counterparty} {verb} ₹{balance_inr:.0f}. Deadline passed {days_overdue} day(s) ago. {card_str}."
    else:
        verb = "owes you" if direction == "lent" else "you owe"
        one_liner = f"Verdict: {counterparty} {verb} ₹{balance_inr:.0f}. Status: {status}."

    return {
        "status": status,
        "colour": colour,
        "days_overdue": days_overdue,
        "balance_paise": balance_paise,
        "paid_paise": paid_paise,
        "principal_paise": principal_paise,
        "counterparty": counterparty,
        "one_liner": one_liner
    }