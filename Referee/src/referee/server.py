import os
import json
from typing import Optional, Dict, Any

from mcp.server.mcpserver import MCPServer

from starlette.applications import Starlette
from starlette.routing import Route, Mount
from starlette.staticfiles import StaticFiles
from starlette.responses import FileResponse, JSONResponse
from starlette.requests import Request

from referee.parser import parse_utterance
from referee.store import init_db, create_deal, append_event, get_deal_state
from vagueterms import detect_vague_terms, BLOCKING_FLAGS
from referee.verdict import compute_verdict
from referee.links import generate_upi_link, generate_whatsapp_share_link

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

    _, next_q, _ = detect_vague_terms(state, state.get("raw_utterance", ""))
    updates: Dict[str, Any] = {}
    answer_lower = answer.lower().strip()

    AFFIRMATIVE_ANSWERS = {"yes", "y", "yeah", "yep", "ok", "okay", "sure", "correct", "use default", "use defaults", "default"}

    if next_q:
        rule_id = next_q.rule_id
        is_affirmative = answer_lower in AFFIRMATIVE_ANSWERS

        if rule_id == "PARTY_PRONOUN":
            if not is_affirmative:
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
        elif rule_id == "AMOUNT_UNIT":
            if is_affirmative:
                updates["amount_confirmed"] = True
        elif rule_id in {"DEADLINE_RELATIVE", "DEADLINE_FUZZY", "DEADLINE_CONDITIONAL"}:
            if is_affirmative:
                updates["deadline_confirmed"] = True
            elif "upi" in answer_lower or "cash" in answer_lower:
                updates["deadline_confirmed"] = True
                updates["payment_mode"] = "upi" if "upi" in answer_lower else "cash"
        elif rule_id == "MODE_MISSING":
            if is_affirmative or "upi" in answer_lower:
                updates["payment_mode"] = "upi"
            elif "cash" in answer_lower:
                updates["payment_mode"] = "cash"
            elif "bank" in answer_lower:
                updates["payment_mode"] = "bank"
        elif rule_id == "PARTIAL_MISSING":
            if is_affirmative or "accept" in answer_lower:
                updates["partial_policy"] = "accept_partial"
            elif "all" in answer_lower or "no" in answer_lower:
                updates["partial_policy"] = "all_or_nothing"

    if updates:
        append_event(deal_id, "term_set", updates)

    updated_state = get_deal_state(deal_id) or {}
    remaining_flags, remaining_q, _ = detect_vague_terms(updated_state, updated_state.get("raw_utterance", ""))

    ready_to_lock = not any(f in BLOCKING_FLAGS for f in remaining_flags)
    next_question_str = remaining_q.prompt if remaining_q else None

    party = updated_state.get("counterparty") or "Counterparty"
    amount = (updated_state.get("principal_paise") or 0) / 100
    direction = updated_state.get("direction") or "agreed with"

    if not next_question_str and ready_to_lock:
        read_back = f"Deal updated: {direction} {party} ₹{amount:.0f}. All terms clear and ready to lock! Say 'lock it' to finalize."
    elif next_question_str:
        read_back = f"Updated. Next question: {next_question_str}"
    else:
        read_back = f"Updated terms with {party}."

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
        return {"error": "Confirmation required to lock deal", "summary": "Lock cancelled."}

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

    upi_link = generate_upi_link(amount_inr, note=f"Deal {deal_id}")
    wa_summary = f"{direction.upper()} ₹{amount_inr:.0f} with {party} (ID: {deal_id})."
    whatsapp_share_link = generate_whatsapp_share_link(wa_summary)
    summary = f"Deal {deal_id} locked successfully! Shared terms via WhatsApp or UPI."

    return {
        "deal_id": deal_id,
        "status": "LOCKED",
        "locked_terms": state,
        "upi_link": upi_link,
        "whatsapp_share_link": whatsapp_share_link,
        "summary": summary
    }

@mcp.tool()
def log_payment(amount_inr: float, deal_id: Optional[str] = None, counterparty: Optional[str] = None, mode: Optional[str] = None) -> Dict[str, Any]:
    """Tool 4: Logs a payment against a deal by deal_id or counterparty name."""
    target_deal_id = deal_id
    if not target_deal_id and counterparty:
        import referee.store as store_mod
        conn = store_mod.get_connection(store_mod.DEFAULT_DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM deals WHERE LOWER(counterparty) = LOWER(?) ORDER BY created_at DESC LIMIT 1", (counterparty.strip(),))
        row = cursor.fetchone()
        conn.close()
        if row:
            target_deal_id = row["id"]

    if not target_deal_id:
        return {"error": "Deal not found", "summary": "Could not find an active deal to record payment."}

    amount_paise = int(amount_inr * 100)
    event_id = append_event(target_deal_id, "payment", {"amount_paise": amount_paise, "mode": mode or "upi"})
    state = get_deal_state(target_deal_id) or {}
    verdict = compute_verdict(state)

    party = state.get("counterparty") or "counterparty"
    bal_inr = verdict["balance_paise"] / 100
    summary = f"Logged payment of ₹{amount_inr:.0f} for deal {target_deal_id}. Remaining balance with {party}: ₹{bal_inr:.0f} ({verdict['status']})."

    return {
        "event_id": event_id,
        "deal_id": target_deal_id,
        "amount_logged_inr": amount_inr,
        "updated_balance_inr": bal_inr,
        "status": verdict["status"],
        "summary": summary
    }

@mcp.tool()
def get_verdict(deal_id: Optional[str] = None, counterparty: Optional[str] = None) -> Dict[str, Any]:
    """Tool 5: Returns the deterministic verdict card payload and summary for a deal."""
    target_deal_id = deal_id
    if not target_deal_id and counterparty:
        import referee.store as store_mod
        conn = store_mod.get_connection(store_mod.DEFAULT_DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM deals WHERE LOWER(counterparty) = LOWER(?) ORDER BY created_at DESC LIMIT 1", (counterparty.strip(),))
        row = cursor.fetchone()
        conn.close()
        if row:
            target_deal_id = row["id"]

    if not target_deal_id:
        return {"error": "Deal not found", "summary": "No deal matching that query was found."}

    state = get_deal_state(target_deal_id)
    if not state:
        return {"error": f"Deal {target_deal_id} not found", "summary": f"Error: Deal {target_deal_id} not found."}

    verdict = compute_verdict(state)

    return {
        "deal_id": target_deal_id,
        "verdict_card": verdict,
        "summary": verdict["one_liner"]
    }

@mcp.tool()
def amend_deal(deal_id: str, field: str, new_value: str, reason: Optional[str] = None) -> Dict[str, Any]:
    """Tool 6: Appends an 'amended' event modifying a deal term."""
    state = get_deal_state(deal_id)
    if not state:
        return {"error": f"Deal {deal_id} not found", "summary": f"Error: Deal {deal_id} not found."}

    original_val = state.get(field)
    parsed_value: Any = new_value
    if field == "amount_inr":
        field = "principal_paise"
        parsed_value = int(float(new_value) * 100)

    amendment_payload = {
        "field": field,
        "old_value": original_val,
        "new_value": parsed_value,
        "reason": reason or "User requested amendment"
    }

    event_id = append_event(deal_id, "amended", amendment_payload)
    updated_state = get_deal_state(deal_id) or {}
    summary = f"Deal {deal_id} amended: updated {field} to {new_value}."

    return {
        "event_id": event_id,
        "deal_id": deal_id,
        "amendment": amendment_payload,
        "updated_terms": updated_state,
        "summary": summary
    }

@mcp.tool()
def get_ledger(counterparty: Optional[str] = None) -> Dict[str, Any]:
    """Tool 7: Summarizes net balances across all recorded deals."""
    import referee.store as store_mod
    conn = store_mod.get_connection(store_mod.DEFAULT_DB_PATH)
    cursor = conn.cursor()

    if counterparty:
        cursor.execute("SELECT id FROM deals WHERE LOWER(counterparty) = LOWER(?)", (counterparty.strip(),))
    else:
        cursor.execute("SELECT id FROM deals")

    rows = cursor.fetchall()
    conn.close()

    deals_summary = []
    total_net_paise = 0

    for row in rows:
        d_id = row["id"]
        st = get_deal_state(d_id)
        if st:
            verdict = compute_verdict(st)
            direction = st.get("direction", "lent")
            bal = verdict["balance_paise"]
            if direction == "lent":
                total_net_paise += bal
            else:
                total_net_paise -= bal

            deals_summary.append({
                "deal_id": d_id,
                "counterparty": st.get("counterparty"),
                "direction": direction,
                "balance_inr": bal / 100,
                "status": verdict["status"],
                "colour": verdict["colour"]
            })

    net_inr = total_net_paise / 100
    summary = f"Ledger summary: {len(deals_summary)} deal(s) tracked. Net balance across all deals: ₹{net_inr:.0f}."

    return {
        "net_balance_inr": net_inr,
        "deals": deals_summary,
        "summary": summary
    }

TOOLS_MAP = {
    "propose_deal": propose_deal,
    "answer_question": answer_question,
    "lock_deal": lock_deal,
    "log_payment": log_payment,
    "get_verdict": get_verdict,
    "amend_deal": amend_deal,
    "get_ledger": get_ledger
}

async def handle_simulator_tool_call(request: Request) -> JSONResponse:
    tool_name = request.path_params.get("tool_name")
    if tool_name not in TOOLS_MAP:
        return JSONResponse({"error": f"Unknown tool {tool_name}"}, status_code=404)

    body = await request.json()
    func = TOOLS_MAP[tool_name]
    res = func(**body)
    return JSONResponse(res)

async def serve_index(request: Request) -> FileResponse:
    sim_dir = os.path.join(os.path.dirname(__file__), "simulator")
    return FileResponse(os.path.join(sim_dir, "index.html"))

sim_dir_path = os.path.join(os.path.dirname(__file__), "simulator")
mcp_http_app = mcp.streamable_http_app()

async def mcp_dispatch(scope, receive, send):
    if scope["type"] in ("http", "websocket"):
        path = scope.get("path", "")
        if path in ("/mcp", "/mcp/"):
            scope_copy = dict(scope)
            scope_copy["path"] = "/"
            scope_copy["raw_path"] = b"/"
            await mcp_http_app(scope_copy, receive, send)
            return
        elif path.startswith("/mcp/"):
            subpath = path[4:]
            scope_copy = dict(scope)
            scope_copy["path"] = subpath
            scope_copy["raw_path"] = subpath.encode("utf-8")
            await mcp_http_app(scope_copy, receive, send)
            return
    await mcp_http_app(scope, receive, send)

from contextlib import asynccontextmanager

# Build the MCP Streamable HTTP app instance
mcp_app = mcp.streamable_http_app()

# Lifespan manager to initialize MCP's background session task group on server boot
@asynccontextmanager
async def lifespan(app: Starlette):
    async with mcp_app.router.lifespan_context(app):
        yield

# Outer Starlette application
app = Starlette(
    routes=[
        Route("/", endpoint=serve_index),
        Route("/api/tool/{tool_name}", endpoint=handle_simulator_tool_call, methods=["POST"]),
        Mount("/simulator", StaticFiles(directory=sim_dir_path)),
        Mount("/", app=mcp_app),
    ],
    lifespan=lifespan
)