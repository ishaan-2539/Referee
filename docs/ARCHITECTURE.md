# Referee: Architecture

Referee is a self-hosted [Model Context Protocol](https://modelcontextprotocol.io) (MCP) server that turns vague, spoken money deals into exact, trackable terms. This document explains how the pieces fit together and why they are built the way they are.

## Overview

```
 Browser simulator (chat + mic)            Alexa+ (real device: not used, see README)
  = MCP client, keyword intent rules
          │
          │  JSON-RPC over Streamable HTTP (MCP spec 2025-11-25)
          ▼
 ┌───────────────────────────────────────────────────────────────┐
 │  Referee server  (Starlette app + MCP Python SDK)             │
 │                                                               │
 │   /mcp          real MCP endpoint (7 tools + ping)            │
 │   /api/tool/*   plain REST wrapper over the same functions    │
 │   /             static simulator (index.html, app.js)         │
 └──────┬──────────────────────┬──────────────────────┬──────────┘
        │                      │                      │
        ▼                      ▼                      ▼
 ┌─────────────┐      ┌────────────────┐     ┌─────────────────┐
 │   Parser    │      │   Detector     │     │  Event store    │
 │ regex +     │ ───► │  (vagueterms)  │     │  SQLite,        │
 │ dateutil    │ slots│  pure rules    │     │  append-only,   │
 └─────────────┘      └────────────────┘     │  hash-chained   │
                                             └────────┬────────┘
                                                      │ fold events
                                                      ▼
                                             ┌─────────────────┐
                                             │ Verdict engine  │
                                             │ pure function   │
                                             └─────────────────┘
```

## Core principles

1. **The parser fills slots; the rules decide.** Turning a sentence into a term sheet is a fuzzy job. Deciding whether a term is vague, and who owes what, is not. The second part is plain, unit-tested Python with no network calls. Parsing is currently rule-based (regex + `dateutil`). Model-based parsing is on the roadmap and would sit behind the same parser interface, so it could only ever fill slots, never decide a verdict.
2. **Append-only history.** A deal's state is never overwritten. Every action adds an event, and the current state is derived by folding the events in order.
3. **Deterministic core.** The detector and the verdict engine are pure functions. The same input always gives the same output, which makes them easy to test and easy to trust.
4. **Money is integers.** Amounts are stored as integer paise, never floats. Datetimes are timezone-aware and default to `Asia/Kolkata`.
5. **Honest scope.** Referee records what the user says was agreed and paid. It does not verify payments or create enforceable contracts.

## Components

| Component | File | Responsibility |
|---|---|---|
| Server | `src/referee/server.py` | Defines the MCP tools, builds the Starlette app, mounts `/mcp`, the REST helper and the simulator |
| Parser | `src/referee/parser.py` | Turns an utterance into a `TermSheet` using regex and `dateutil` |
| Models | `src/referee/models.py` | The `TermSheet` and its enums (direction, payment mode) |
| Detector | `vagueterms` (separate package) | Flags vague slots, ranks them, and picks the next clarifying question |
| Store | `src/referee/store.py` | SQLite event log, hash chain, and folding events into deal state |
| Verdict engine | `src/referee/verdict.py` | Computes paid amount, balance, status, days overdue and card colour |
| Links | `src/referee/links.py` | Builds the UPI `upi://pay` link and the WhatsApp `wa.me` share link |
| Seed data | `src/referee/seed.py` | Fictional demo deals (`python -m referee.seed`) |
| Simulator | `src/referee/simulator/` | Browser chat and mic UI that acts as an MCP client and shows raw JSON-RPC traffic |

## Request flow: from sentence to verdict

1. **Propose.** `propose_deal("I lent Aman 1,500, he'll pay Friday")` runs the parser, which fills a term sheet. The detector then flags what is vague (here: `DEADLINE_RELATIVE`, `MODE_MISSING`, `PARTIAL_MISSING`) and returns the highest-priority question with a proposed default.
2. **Clarify.** `answer_question` applies the answer, re-runs the detector, and returns either the next question or `ready_to_lock: true` with a read-back of the terms.
3. **Lock.** `lock_deal(confirm=True)` is refused while a blocking flag is open. Otherwise it appends a `locked` event that freezes the terms, and returns a UPI link and a WhatsApp share link.
4. **Track.** `log_payment` appends `payment` events. `amend_deal` appends `amended` events and never edits the original.
5. **Judge.** `get_verdict` folds the events into current state and passes it to the verdict engine. `get_ledger` does the same across all deals, per person.

### Question priority and blocking flags

The detector asks in this order: direction, counterparty, amount, deadline, mode, partial-payment rule. It asks one question per turn and attaches a default so that a one-word answer finishes it.

A deal cannot be locked while any of these is open: `DIRECTION_UNCLEAR`, `PARTY_PRONOUN`, `PARTY_AMBIGUOUS`, `AMOUNT_FUZZY`.

## Data model

Two SQLite tables:

```
deals(id, direction, counterparty, currency, mode, partial_policy,
      principal_paise, deadline_ts, status, purpose, raw_utterance,
      created_at, locked_at)

deal_events(id, deal_id, type, payload_json, ts, hash)
  type: created | term_set | locked | payment | amended
```

- Terms at lock time are frozen inside the `locked` event.
- An amendment is a new `amended` event. The original terms stay in the log, so the full history of moved goalposts is always visible.
- Balance and status are **derived** by folding events. They are not stored as separate fields that could drift out of sync.

### Tamper evidence

Each event stores `sha256(prev_hash + type + payload + timestamp)`, and `verify_deal_integrity` re-checks the chain. Editing or deleting a past event breaks the chain, so it is **detectable**. This is tamper-evident, not tamper-proof: someone with write access to the database file could rewrite the entire chain consistently.

## Verdict logic

Inputs are the current terms (original plus amendments), the payments, and the current time.

| Field | Rule |
|---|---|
| `paid_paise` | Sum of payments |
| `balance_paise` | Principal minus paid |
| Status | `OPEN`, `PARTIALLY_PAID`, `SETTLED`, or `OVERDUE` (derived when now is past the deadline and balance is above zero) |
| `days_overdue` | Whole days past the current deadline |
| Card | Green = settled. Neutral = open or partial before the deadline. Yellow = overdue 1 to 7 days. Red = overdue more than 7 days |

With `all_or_nothing`, a partial payment is recorded but does not change the status. The thresholds are named constants so they are easy to tune.

## MCP transport

- The server uses the official MCP Python SDK with the **Streamable HTTP** transport at `/mcp`.
- In testing, `initialize` negotiated protocol version `2025-11-25`.
- The legacy SSE transport is not used.
- The simulator is a real MCP client. It performs the `initialize` handshake, sends `notifications/initialized` and `tools/list`, then calls every tool through `tools/call`, reusing the session id. The "MCP Traffic" panel shows those actual messages.
- The `/api/tool/*` REST routes call the same tool functions directly. They exist for tests and are not part of the MCP surface.

## Trust and security boundaries

- The MCP SDK rejected requests with a foreign `Origin` header in testing.
- There is no bearer token, rate limiting or user authentication. Treat the server as a demo and do not expose it publicly beyond a short-lived tunnel.
- Secrets (for example `PAYEE_VPA`) come from environment variables. `.env` is git-ignored and `.env.example` documents the variables.
- Tests use temporary databases so they do not touch the demo database.

## What is simulated

| Part | Status |
|---|---|
| MCP server, detector, verdict engine, event store | Real |
| Simulator-to-server protocol traffic | Real MCP |
| Alexa+ device and Alexa+'s own language understanding | Simulated by the web simulator and its keyword intent rules |
| Payment verification | Not implemented |

## Known limitations and next steps

- **Parser sensitivity.** Regex parsing can misread complex sentences. For example, in *"Aman needs 1500 for rent, I gave him cash today and he promises to return it next Thursday"* the counterparty is read as "him". The detector flags this and asks before the deal can be locked. Model-based parsing (Amazon Bedrock) is the next planned step, behind the same parser interface, with the regex parser kept as a fallback.
- The "at most 3 questions, then apply defaults" rule is not enforced yet.
- Name matching is prefix-based and can require disambiguation.
- No authentication on the server.