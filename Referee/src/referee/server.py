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

AFFIRMATIVE_ANSWERS = {
    "yes", "y", "yeah", "yep", "yup", "ok", "okay", "sure", "correct", 
    "use default", "use defaults", "default", "sounds good", "go ahead", 
    "cool", "that works", "do it", "fine", "perfect", "sure thing"
}

@mcp.tool()
def ping() -> str:
    """A simple hello-world ping tool to verify MCP connectivity."""
    return "pong"

@mcp.tool()
def propose_deal(utterance: str) -> Dict[str, Any]:
    """Tool 1: Parses an initial handshake utterance, checks for existing counterparty names, and detects vague terms."""
    try:
        term_sheet = parse_utterance(utterance)
        slots = term_sheet.to_dict()

        counterparty = slots.get("counterparty")
        matching_parties = []

        # Check database for existing counterparties with the same name
        if counterparty:
            import referee.store as store_mod
            conn = store_mod.get_connection(store_mod.DEFAULT_DB_PATH)
            cursor = conn.cursor()
            cursor.execute("SELECT DISTINCT counterparty FROM deals WHERE LOWER(counterparty) = LOWER(?)", (counterparty.strip(),))
            rows = cursor.fetchall()
            conn.close()
            if rows:
                matching_parties = [r["counterparty"] for r in rows]

        deal_id = create_deal(utterance, slots)
        open_flags, next_q, defaults_applied = detect_vague_terms(slots, utterance, matching_counterparties=matching_parties)

        next_question_str = next_q.prompt if next_q else None
        party = slots.get("counterparty") or "your friend"
        amount_inr = (slots.get("amount_paise") or 0) / 100

        if next_question_str:
            summary = f"Got it! I've noted the agreement. {next_question_str}"
        else:
            summary = f"Got it! I've recorded the deal with {party} for ₹{amount_inr:.0f}. All terms look clear and ready to lock!"

        return {
            "deal_id": deal_id,
            "slots": slots,
            "open_flags": open_flags,
            "next_question": next_question_str,
            "defaults_applied": defaults_applied,
            "summary": summary
        }
    except Exception as e:
        return {"error": str(e), "summary": "I couldn't process that agreement. Could you say it again?"}

@mcp.tool()
def answer_question(deal_id: str, answer: str) -> Dict[str, Any]:
    """Tool 2: Takes an answer to a clarifying question, resolves party disambiguation, and updates deal slots."""
    try:
        state = get_deal_state(deal_id)
        if not state:
            return {"error": f"Deal {deal_id} not found", "summary": "I couldn't find an active deal to update."}

        counterparty = state.get("counterparty")
        matching_parties = []
        if counterparty:
            import referee.store as store_mod
            conn = store_mod.get_connection(store_mod.DEFAULT_DB_PATH)
            cursor = conn.cursor()
            cursor.execute("SELECT DISTINCT counterparty FROM deals WHERE LOWER(counterparty) = LOWER(?)", (counterparty.strip(),))
            rows = cursor.fetchall()
            conn.close()
            if rows:
                matching_parties = [r["counterparty"] for r in rows]

        _, next_q, _ = detect_vague_terms(state, state.get("raw_utterance", ""), matching_counterparties=matching_parties)
        updates: Dict[str, Any] = {}
        answer_lower = answer.lower().strip()

        if next_q:
            rule_id = next_q.rule_id
            is_affirmative = answer_lower in AFFIRMATIVE_ANSWERS

            if rule_id == "PARTY_AMBIGUOUS":
                if is_affirmative or "same" in answer_lower:
                    updates["party_confirmed"] = True
                else:
                    # User provided a new distinguishing name (e.g., "Aman Sharma" or "Different Aman")
                    new_name = answer.strip().title()
                    updates["counterparty"] = new_name
                    updates["party_confirmed"] = True
            elif rule_id == "PARTY_PRONOUN":
                if not is_affirmative:
                    updates["counterparty"] = answer.strip().title()
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
        
        # Re-check remaining flags
        updated_party = updated_state.get("counterparty")
        matching_updated = []
        if updated_party:
            import referee.store as store_mod
            conn = store_mod.get_connection(store_mod.DEFAULT_DB_PATH)
            cursor = conn.cursor()
            cursor.execute("SELECT DISTINCT counterparty FROM deals WHERE LOWER(counterparty) = LOWER(?)", (updated_party.strip(),))
            rows = cursor.fetchall()
            conn.close()
            if rows:
                matching_updated = [r["counterparty"] for r in rows]

        remaining_flags, remaining_q, _ = detect_vague_terms(updated_state, updated_state.get("raw_utterance", ""), matching_counterparties=matching_updated)

        ready_to_lock = not any(f in BLOCKING_FLAGS for f in remaining_flags)
        next_question_str = remaining_q.prompt if remaining_q else None

        party = updated_state.get("counterparty") or "your counterparty"
        amount = (updated_state.get("principal_paise") or 0) / 100
        direction = updated_state.get("direction") or "agreed with"

        if not next_question_str and ready_to_lock:
            read_back = f"Updated! Terms set: {direction} {party} ₹{amount:.0f}. Everything looks clear and ready. Say 'lock it' to finalize!"
        elif next_question_str:
            read_back = f"Got it. {next_question_str}"
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
    except Exception as e:
        return {"error": str(e), "summary": "Failed to update terms."}
    
@mcp.tool()
def lock_deal(deal_id: str, confirm: bool = True) -> Dict[str, Any]:
    """Tool 3: Freezes terms and locks the deal. Returns UPI and WhatsApp sharing links."""
    try:
        if not confirm:
            return {"error": "Confirmation required to lock deal", "summary": "No problem, deal left unlocked."}

        state = get_deal_state(deal_id)
        if not state:
            return {"error": f"Deal {deal_id} not found", "summary": "Error: Deal not found."}

        open_flags, _, _ = detect_vague_terms(state, state.get("raw_utterance", ""))
        blocking_present = [f for f in open_flags if f in BLOCKING_FLAGS]

        if blocking_present:
            return {
                "error": f"Cannot lock deal with unresolved blocking flags: {blocking_present}",
                "summary": "We still need a few details before locking this deal."
            }

        append_event(deal_id, "locked", {"locked": True})

        amount_inr = (state.get("principal_paise") or 0) / 100
        party = state.get("counterparty", "friend")
        direction = state.get("direction", "lent")

        upi_link = generate_upi_link(amount_inr, note=f"Deal with {party}")
        wa_summary = f"{direction.upper()} ₹{amount_inr:.0f} with {party}."
        whatsapp_share_link = generate_whatsapp_share_link(wa_summary)
        summary = f"Locked! I've finalized the agreement with {party} for ₹{amount_inr:.0f}. You can share the WhatsApp confirmation link or use the UPI link when paying."

        return {
            "deal_id": deal_id,
            "status": "LOCKED",
            "locked_terms": state,
            "upi_link": upi_link,
            "whatsapp_share_link": whatsapp_share_link,
            "summary": summary
        }
    except Exception as e:
        return {"error": str(e), "summary": "Failed to lock deal."}

@mcp.tool()
def log_payment(amount_inr: float, deal_id: Optional[str] = None, counterparty: Optional[str] = None, mode: Optional[str] = None) -> Dict[str, Any]:
    """Tool 4: Logs a payment using a FIFO waterfall across active deals for a counterparty."""
    try:
        import referee.store as store_mod
        conn = store_mod.get_connection(store_mod.DEFAULT_DB_PATH)
        cursor = conn.cursor()

        target_deals = []

        if deal_id:
            cursor.execute("SELECT id FROM deals WHERE id = ?", (deal_id,))
            rows = cursor.fetchall()
            target_deals = [r["id"] for r in rows]
        elif counterparty:
            cursor.execute("""
                SELECT id FROM deals 
                WHERE LOWER(counterparty) = LOWER(?) AND status != 'SETTLED'
                ORDER BY created_at ASC
            """, (counterparty.strip(),))
            rows = cursor.fetchall()
            target_deals = [r["id"] for r in rows]

            if not target_deals:
                cursor.execute("""
                    SELECT id FROM deals 
                    WHERE LOWER(counterparty) = LOWER(?)
                    ORDER BY created_at DESC LIMIT 1
                """, (counterparty.strip(),))
                row = cursor.fetchone()
                if row:
                    target_deals = [row["id"]]

        conn.close()

        if not target_deals:
            return {"error": "Deal not found", "summary": f"I couldn't find an active deal for {counterparty or 'that query'} to record that payment."}

        remaining_paise_to_apply = int(amount_inr * 100)
        events_logged = []
        last_deal_id = target_deals[0]

        for d_id in target_deals:
            if remaining_paise_to_apply <= 0:
                break
            
            last_deal_id = d_id
            st = get_deal_state(d_id, db_path=store_mod.DEFAULT_DB_PATH) or {}
            v = compute_verdict(st)
            deal_balance = v["balance_paise"]

            if deal_balance <= 0 and len(target_deals) > 1:
                continue

            paise_for_this_deal = min(remaining_paise_to_apply, deal_balance) if deal_balance > 0 else remaining_paise_to_apply
            if paise_for_this_deal > 0:
                ev_id = append_event(d_id, "payment", {"amount_paise": paise_for_this_deal, "mode": mode or "upi"}, db_path=store_mod.DEFAULT_DB_PATH)
                events_logged.append(ev_id)
                remaining_paise_to_apply -= paise_for_this_deal

        # Retrieve specific target deal balance and counterparty name
        last_st = get_deal_state(last_deal_id, db_path=store_mod.DEFAULT_DB_PATH) or {}
        last_verdict = compute_verdict(last_st)
        deal_bal_inr = last_verdict["balance_paise"] / 100
        party_name = counterparty or last_st.get("counterparty") or "counterparty"

        ledger_res = get_ledger(counterparty=party_name)
        overall_net_inr = ledger_res.get("net_balance_inr", 0)

        if overall_net_inr == 0:
            summary = f"Logged payment of ₹{amount_inr:.0f} from {party_name}. All deals with {party_name} are now fully SETTLED! Green card."
        elif overall_net_inr > 0:
            summary = f"Logged payment of ₹{amount_inr:.0f} from {party_name}. Overall remaining total owed across all active deals with {party_name} is now ₹{overall_net_inr:.0f}."
        else:
            summary = f"Logged payment of ₹{amount_inr:.0f} from {party_name}. Net total balance with {party_name}: You owe ₹{abs(overall_net_inr):.0f}."

        return {
            "events_logged": events_logged,
            "deal_id": last_deal_id,
            "amount_logged_inr": amount_inr,
            "updated_balance_inr": deal_bal_inr,
            "overall_net_balance_inr": overall_net_inr,
            "status": last_verdict["status"],
            "summary": summary
        }
    except Exception as e:
        return {"error": str(e), "summary": "Failed to log payment."}

@mcp.tool()
def get_verdict(deal_id: Optional[str] = None, counterparty: Optional[str] = None) -> Dict[str, Any]:
    """Tool 5: Returns the deterministic verdict card payload and summary for a deal or counterparty."""
    try:
        party = counterparty
        target_deal_id = deal_id

        if party:
            import referee.store as store_mod
            conn = store_mod.get_connection(store_mod.DEFAULT_DB_PATH)
            cursor = conn.cursor()
            cursor.execute("SELECT id FROM deals WHERE LOWER(counterparty) = LOWER(?) ORDER BY created_at DESC LIMIT 1", (party.strip(),))
            row = cursor.fetchone()
            conn.close()
            if row:
                target_deal_id = row["id"]

        if not target_deal_id:
            return {"error": "Deal not found", "summary": f"No active record found for {party or 'that query'}."}

        state = get_deal_state(target_deal_id)
        if not state:
            return {"error": f"Deal {target_deal_id} not found", "summary": "Error: Deal record not found."}

        verdict = compute_verdict(state)

        # If counterparty was queried, append overall context if multiple deals exist
        if party:
            ledger_info = get_ledger(counterparty=party)
            net_bal = ledger_info.get("net_balance_inr", 0)
            party_name = state.get("counterparty") or party
            if net_bal > 0:
                summary = f"Verdict for {party_name}: Outstanding balance across active deals is ₹{net_bal:.0f} ({verdict['status']})."
            elif net_bal == 0:
                summary = f"Verdict for {party_name}: Fully SETTLED. Green card."
            else:
                summary = f"Verdict for {party_name}: You owe {party_name} ₹{abs(net_bal):.0f} in total."
        else:
            summary = verdict["one_liner"]

        return {
            "deal_id": target_deal_id,
            "verdict_card": verdict,
            "summary": summary
        }
    except Exception as e:
        return {"error": str(e), "summary": "Failed to compute verdict."}

@mcp.tool()
def amend_deal(deal_id: str, field: str, new_value: str, reason: Optional[str] = None) -> Dict[str, Any]:
    """Tool 6: Appends an 'amended' event modifying a deal term."""
    try:
        state = get_deal_state(deal_id)
        if not state:
            return {"error": f"Deal {deal_id} not found", "summary": "Error: Deal record not found."}

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
        party = updated_state.get("counterparty") or "deal"
        summary = f"Amended! Updated {field} for {party} to {new_value}."

        return {
            "event_id": event_id,
            "deal_id": deal_id,
            "amendment": amendment_payload,
            "updated_terms": updated_state,
            "summary": summary
        }
    except Exception as e:
        return {"error": str(e), "summary": "Failed to amend deal."}

@mcp.tool()
def get_ledger(counterparty: Optional[str] = None) -> Dict[str, Any]:
    """Tool 7: Summarizes net balances across all recorded deals with an itemized person breakdown."""
    try:
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
        party_balances = {}

        for row in rows:
            d_id = row["id"]
            st = get_deal_state(d_id)
            if st:
                verdict = compute_verdict(st)
                party = st.get("counterparty") or "Unknown"
                direction = st.get("direction", "lent")
                bal = verdict["balance_paise"]
                status = verdict["status"]

                if status == "SETTLED" and not counterparty:
                    continue

                net_p = bal if direction == "lent" else -bal

                if party not in party_balances:
                    party_balances[party] = {"net_paise": 0, "status": status, "colour": verdict["colour"]}
                
                party_balances[party]["net_paise"] += net_p
                if verdict["colour"] in ("yellow", "red"):
                    party_balances[party]["status"] = status
                    party_balances[party]["colour"] = verdict["colour"]

                deals_summary.append({
                    "deal_id": d_id,
                    "counterparty": party,
                    "direction": direction,
                    "balance_inr": bal / 100,
                    "status": status,
                    "colour": verdict["colour"]
                })

        if not party_balances:
            return {
                "net_balance_inr": 0,
                "deals": [],
                "summary": "Your ledger is completely clear! No active or overdue balances found."
            }

        total_net_paise = sum(p["net_paise"] for p in party_balances.values())
        lines = ["Here is your current ledger breakdown:"]

        for name, info in party_balances.items():
            amount = info["net_paise"] / 100
            if amount > 0:
                lines.append(f"• {name} owes you ₹{amount:.0f} ({info['status']})")
            elif amount < 0:
                lines.append(f"• You owe {name} ₹{abs(amount):.0f} ({info['status']})")
            else:
                lines.append(f"• {name}: Fully settled")

        total_inr = total_net_paise / 100
        if total_inr > 0:
            lines.append(f"\nNet total: ₹{total_inr:.0f} owed to you across active deals.")
        elif total_inr < 0:
            lines.append(f"\nNet total: You owe ₹{abs(total_inr):.0f} in total.")
        else:
            lines.append(f"\nNet total balance: ₹0.")

        summary_text = "\n".join(lines)

        return {
            "net_balance_inr": total_inr,
            "deals": deals_summary,
            "summary": summary_text
        }
    except Exception as e:
        return {"error": str(e), "summary": "Failed to retrieve ledger."}

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
mcp_app = mcp.streamable_http_app()

from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: Starlette):
    async with mcp_app.router.lifespan_context(app):
        yield

app = Starlette(
    routes=[
        Route("/", endpoint=serve_index),
        Route("/api/tool/{tool_name}", endpoint=handle_simulator_tool_call, methods=["POST"]),
        Mount("/simulator", StaticFiles(directory=sim_dir_path)),
        Mount("/", app=mcp_app),
    ],
    lifespan=lifespan
)