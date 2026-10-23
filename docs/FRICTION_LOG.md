# Friction Log: Referee (Amazon Developer Hackathon 2026)

**Project:** Referee, a voice-first MCP server (Streamable HTTP, spec 2025-11-25) for informal money deals
**Track:** Alexa+ (self-hosted MCP server, with a simulated Alexa+ web client)
**Tools covered:** MCP Python SDK (`mcp` 2.3.0), Starlette, MCP Inspector, plus two internal integration points (the simulator client and the `vagueterms` rules engine)

Each entry gives the task attempted, steps taken, expected vs. actual behaviour, severity, the workaround I used, and an actionable suggestion. Severity scale: **Blocker** (cannot proceed without a workaround), **Major** (significant time lost or broken behaviour), **Minor** (small annoyance).

## Summary

| ID | Area | Issue | Severity |
|---|---|---|---|
| FL-1 | MCP Python SDK | `FastMCP` renamed to `MCPServer` in v2.x | Blocker |
| FL-2 | Starlette + MCP | `Mount("/mcp")` issues a 307 redirect that breaks POST clients | Major |
| FL-3 | Starlette + MCP | Unhandled lifespan causes "Task group is not initialized" | Major |
| FL-4 | Simulator / tool routing | Active-deal state trapped users in clarification loops | Major |
| FL-5 | `vagueterms` / `answer_question` | "yes" / "sounds good" not accepted as default acceptance | Major |
| FL-6 | SQLite store + detector | Column and slot name mismatch kept `ready_to_lock` false | Major |
| FL-7 | Verdict engine / `log_payment` | Single-deal payments distorted multi-deal balances | Major |
| FL-8 | Simulator client | Deal context lost right after locking | Minor |
| FL-9 | MCP Inspector | Manual connect step and a Windows-incompatible default server | Minor |

---

## FL-1: `FastMCP` renamed to `MCPServer` in mcp v2.x

- **Tool / API / SDK:** `mcp` Python SDK
- **Task attempted:** Initialize the MCP server following the standard SDK v1 documentation.
- **Steps taken:**
  1. Installed `mcp[cli]` with pip.
  2. Wrote `from mcp.server.fastmcp import FastMCP`.
- **Expected:** `FastMCP` imports and instantiates cleanly.
- **Actual:** `ImportError` / `AttributeError`, because the class was renamed in the v2 Python SDK.
- **Severity:** Blocker
- **Workaround:** Changed the import to `from mcp.server.mcpserver import MCPServer`, and pinned `mcp[cli]==2.3.0` so the API cannot shift under the project.
- **Suggestion:** Keep a backward-compatible alias, or show a clear migration notice in the primary SDK docs and quickstart, since most tutorials still show the v1 import.

## FL-2: Starlette `Mount("/mcp")` issues an automatic 307 redirect

- **Tool / API / SDK:** Starlette with the MCP Streamable HTTP app
- **Task attempted:** Serve the MCP endpoint at `/mcp` and the simulator UI from the same Starlette server.
- **Steps taken:**
  1. Configured `Mount("/mcp", app=mcp_app)`.
  2. Sent JSON-RPC `POST /mcp` requests from MCP Inspector and the web client.
- **Expected:** The POST is handled directly by the MCP app.
- **Actual:** Starlette answered with a 307 redirect to `/mcp/`. Clients that do not re-send a POST body after a redirect failed with 404 and 500 errors.
- **Severity:** Major
- **Workaround:** Mounted the MCP app at the root (`Mount("/", app=mcp_app)`) next to explicit routes for the simulator, static files and the tool helper API.
- **Suggestion:** Document the recommended mounting pattern for Streamable HTTP inside Starlette/FastAPI, including the trailing-slash behaviour and the root-mount approach.

## FL-3: Unhandled lifespan causes "Task group is not initialized"

- **Tool / API / SDK:** Starlette and `mcp.streamable_http_app()`
- **Task attempted:** Serve the simulator's static assets alongside the Streamable HTTP MCP app in one process.
- **Steps taken:**
  1. Created `mcp_app = mcp.streamable_http_app()`.
  2. Mounted it inside a parent Starlette application.
  3. Started the client `initialize` handshake.
- **Expected:** The session manager's task group is ready when the first request arrives.
- **Actual:** The handshake failed with `500 Internal Server Error` and `RuntimeError: Task group is not initialized`. The parent app never ran the MCP app's lifespan.
- **Severity:** Major
- **Workaround:** Forwarded the child app's lifespan from the parent:

  ```python
  @asynccontextmanager
  async def lifespan(app: Starlette):
      async with mcp_app.router.lifespan_context(app):
          yield

  app = Starlette(routes=[...], lifespan=lifespan)
  ```

- **Suggestion:** Add an explicit "embedding in an existing Starlette/FastAPI app" example to the SDK tutorials, and consider raising a clearer error message that points to the lifespan requirement.

## FL-4: Rigid intent order trapped users in proposal loops

- **Tool / API / SDK:** Simulator client (`app.js`) and MCP tool routing
- **Task attempted:** Let users cancel, or ask a general ledger question, while a deal proposal is being drafted.
- **Steps taken:**
  1. Started a deal with `propose_deal`.
  2. Typed "cancel", "nevermind" or "Who owes me what?" before finishing it.
- **Expected:** The draft is cleared, or the ledger query runs.
- **Actual:** The client checked the active `currentDealId` first and sent every message to `answer_question`, so the user stayed stuck in the clarifying-question loop.
- **Severity:** Major
- **Workaround:** Reordered client-side intent classification: chit-chat, cancellation, then explicit ledger and verdict queries are evaluated before falling back to answering the active deal's question.
- **Suggestion:** Agent SDKs and Alexa+ guidance should recommend turn-level intent routing, so context-switching commands override an active slot-filling flow.

## FL-5: Conversational "yes" not accepted as default acceptance

- **Tool / API / SDK:** `vagueterms` and the `answer_question` tool
- **Task attempted:** Confirm a proposed default (a deadline or payment mode) with a normal spoken affirmation.
- **Steps taken:**
  1. `propose_deal` asked a clarifying question with a suggested default.
  2. Replied "yes", "sounds good" or "cool".
- **Expected:** The default is accepted and the flag clears.
- **Actual:** The reply was matched against specific slot values, so affirmations counted as unknown input and the same question was asked again.
- **Severity:** Major
- **Workaround:** Added an explicit `AFFIRMATIVE_ANSWERS` set in `server.py` that maps conversational agreement to accepting the question's default.
- **Suggestion:** Voice-agent guidance and rule-engine patterns should standardize default-acceptance phrases, since spoken confirmation rarely repeats the exact value.

## FL-6: Slot and column name mismatch broke `ready_to_lock`

- **Tool / API / SDK:** SQLite store (`store.py`) and the `vagueterms` detector
- **Task attempted:** Fold `term_set` events into the deal state and then check `ready_to_lock`.
- **Steps taken:**
  1. Answered questions to fill in amount and payment mode.
  2. Checked `ready_to_lock` from the detector.
- **Expected:** `ready_to_lock` becomes true once required terms are filled.
- **Actual:** The database stored `principal_paise` and `mode`, but the detector read `amount_paise` and `payment_mode`, so the flags never cleared.
- **Severity:** Major
- **Workaround:** Added a `TERM_TO_COLUMN` whitelist mapping in `store.py` and normalized both key names when building state in `get_deal_state`.
- **Suggestion:** Define one shared data model (for example Pydantic) between the event-sourced store and the rules engine so the two cannot drift apart.

## FL-7: Single-deal payment logging distorted multi-deal balances

- **Tool / API / SDK:** Verdict engine (`verdict.py`) and the `log_payment` tool
- **Task attempted:** Log a lump-sum payment for a counterparty with more than one active deal.
- **Steps taken:**
  1. Created two separate deals with the same counterparty.
  2. Logged "Aman paid 500".
- **Expected:** The person's overall outstanding balance updates correctly.
- **Actual:** The payment landed on a single deal, so per-deal and total balances disagreed across queries.
- **Severity:** Major
- **Workaround:** Rewrote `log_payment` as a FIFO waterfall that applies a payment to the oldest open deals first, and rejects overpayments with an explicit error.
- **Suggestion:** Financial agent guides should include a ledger-level payment allocation pattern for multi-obligation counterparties.

## FL-8: Active deal context lost right after locking

- **Tool / API / SDK:** Simulator client (`app.js`) and session state
- **Task attempted:** Ask follow-ups immediately after locking a deal.
- **Steps taken:**
  1. Said "lock it".
  2. Immediately said "Aman paid 500" or "Did Aman pay?" without repeating context.
- **Expected:** The most recently locked deal or counterparty is understood.
- **Actual:** `currentDealId` was cleared on lock, so follow-up tools had no target.
- **Severity:** Minor
- **Workaround:** Kept `lastLockedDealId` and `lastCounterparty` in the client and used them as fallbacks.
- **Suggestion:** MCP client libraries and Alexa+ guidance should describe session-level context handling for multi-turn conversations.

## FL-9: MCP Inspector needs a manual connect step and ships a Windows-incompatible default

- **Tool / API / SDK:** MCP Inspector
- **Task attempted:** Connect Inspector to the local server and negotiate protocol 2025-11-25.
- **Steps taken:**
  1. Launched the Inspector on Windows.
  2. Tried the default demo server, then my own `http://localhost:8000/mcp`.
- **Expected:** One-step connection, and a default server that works on every OS.
- **Actual:** The connection had to be toggled manually before negotiation would start, and the default filesystem server failed on Windows because the `/tmp` directory does not exist.
- **Severity:** Minor
- **Workaround:** Selected the Streamable HTTP transport, entered the server URL explicitly and clicked Connect.
- **Suggestion:** Use a cross-platform default path, and make the connect state and transport choice more visible in the UI.
