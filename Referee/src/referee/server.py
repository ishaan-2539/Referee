import json
from typing import Optional, Dict, Any
from mcp.server.mcpserver import MCPServer
from referee.parser import parse_utterance
from referee.store import init_db, create_deal, append_event, get_deal_state, DEFAULT_DB_PATH
from vagueterms import detect_vague_terms, BLOCKING_FLAGS

# Initialize SQLite database schema
init_db()

mcp = MCPServer("Referee", dependencies=["mcp"])

@mcp.tool()
def ping() -> str:
    """A simple hello-world ping tool to verify MCP connectivity."""
    return "pong"


@mcp.tool()
def propose_deal(utterance: str) -> Dict[str, Any]:
    """Tool 1: Parses an initial handshake utterance, stores the proposal, detects vague terms, and returns open flags with the next question."""
    term_sheet = parse_utterance(utterance)
    slots = term_sheet.to_dict()

    deal_id = create_deal(utterance, slots)
    open_flags, next_q, defaults_applied = detect_vague_terms(slots, utterance)

    next_question_str = next_q.prompt if next_q else None

    # Construct speakable summary
    if next_question_str:
        summary = f"Recorded deal {deal_id}. {next_question_str}"
    else:
        summary = f"Recorded deal {deal_id}. All terms clear. Ready to lock."

    return {
        "deal_id": deal_id,
        "slots": slots,
        "open_flags": open_flags,
        "next_question": next_question_str,
        "defaults_applied": defaults_applied,
        "summary": summary
    }


@mcp.tool()
def answer_question(deal_id: str, answer: str) -> Dict[str, Any]:
    """Tool 2: Takes an answer to a clarifying question, updates deal slots, and returns remaining flags or ready_to_lock status."""
    state = get_deal_state(deal_id)
    if not state:
        return {"error": f"Deal {deal_id} not found", "summary": f"Error: Deal {deal_id} not found."}

    current_flags, next_q, _ = detect_vague_terms(state, state.get("raw_utterance", ""))

    updates: Dict[str, Any] = {}
    answer_lower = answer.lower()

    if next_q:
        rule_id = next_q.rule_id

        if answer_lower in {"use default", "use defaults", "default"}:
            if rule_id == "DIRECTION_UNCLEAR":
                updates["direction"] = "lent"
            elif rule_id in {"MODE_MISSING", "DEADLINE_RELATIVE"}:
                updates["payment_mode"] = "upi"
            elif rule_id == "PARTIAL_MISSING":
                updates["partial_policy"] = "accept_partial"
        else:
            if rule_id == "PARTY_PRONOUN":
                updates["counterparty"] = answer.strip()
            elif rule_id == "DIRECTION_UNCLEAR":
                if "borrow" in answer_lower or "i owe" in answer_lower:
                    updates["direction"] = "borrowed"
                else:
                    updates["direction"] = "lent"
            elif rule_id == "AMOUNT_FUZZY":
                try:
                    num = int("".join(filter(str.isdigit, answer)))
                    updates["amount_paise"] = num * 100
                    updates["principal_paise"] = num * 100
                except ValueError:
                    pass
            elif rule_id in {"MODE_MISSING", "DEADLINE_RELATIVE", "DEADLINE_FUZZY"}:
                if "cash" in answer_lower:
                    updates["payment_mode"] = "cash"
                elif "bank" in answer_lower:
                    updates["payment_mode"] = "bank"
                elif "upi" in answer_lower:
                    updates["payment_mode"] = "upi"

    if updates:
        append_event(deal_id, "term_set", updates)

    updated_state = get_deal_state(deal_id) or {}
    remaining_flags, remaining_q, defaults_applied = detect_vague_terms(updated_state, updated_state.get("raw_utterance", ""))

    ready_to_lock = not any(f in BLOCKING_FLAGS for f in remaining_flags)
    next_question_str = remaining_q.prompt if remaining_q else None

    party = updated_state.get("counterparty") or "Counterparty"
    amount = (updated_state.get("principal_paise") or 0) / 100
    direction = updated_state.get("direction") or "agreed with"

    if ready_to_lock and not next_question_str:
        read_back = f"Deal updated: {direction} {party} ₹{amount:.0f}. Ready to lock!"
    else:
        read_back = f"Updated. Next question: {next_question_str}"

    return {
        "deal_id": deal_id,
        "updated_slots": updated_state,
        "remaining_flags": remaining_flags,
        "next_question": next_question_str,
        "ready_to_lock": ready_to_lock,
        "read_back": read_back,
        "summary": read_back
    }


@mcp.tool()
def lock_deal(deal_id: str, confirm: bool = True) -> Dict[str, Any]:
    """Tool 3: Freezes terms and locks the deal. Returns UPI and WhatsApp sharing links."""
    if not confirm:
        return {"error": "Confirmation required to lock deal", "summary": "Lock cancelled. Confirmation was not provided."}

    state = get_deal_state(deal_id)
    if not state:
        return {"error": f"Deal {deal_id} not found", "summary": f"Error: Deal {deal_id} not found."}

    open_flags, _, _ = detect_vague_terms(state, state.get("raw_utterance", ""))
    blocking_present = [f for f in open_flags if f in BLOCKING_FLAGS]

    if blocking_present:
        return {
            "error": f"Cannot lock deal with unresolved blocking flags: {blocking_present}",
            "summary": f"Cannot lock deal yet. Unresolved flags: {', '.join(blocking_present)}"
        }

    append_event(deal_id, "locked", {"locked": True})

    amount_inr = (state.get("principal_paise") or 0) / 100
    party = state.get("counterparty", "friend")
    direction = state.get("direction", "lent")

    # Stubbed links (full link generator added in P2.4)
    upi_link = f"upi://pay?pa=payee@upi&pn=Referee&am={amount_inr:.2f}&cu=INR"
    wa_text = f"Referee Deal Locked: {direction.upper()} ₹{amount_inr:.0f} with {party}."
    whatsapp_share_link = f"https://wa.me/?text={wa_text.replace(' ', '%20')}"

    summary = f"Deal {deal_id} locked successfully! Shared terms via WhatsApp or UPI."

    return {
        "deal_id": deal_id,
        "status": "LOCKED",
        "locked_terms": state,
        "upi_link": upi_link,
        "whatsapp_share_link": whatsapp_share_link,
        "summary": summary
    }


if __name__ == "__main__":
    mcp.run()