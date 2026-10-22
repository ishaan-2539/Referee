# Referee

**Alexa reminders remember *when*. Referee remembers *what you agreed*.**

Referee is a self-hosted [MCP](https://modelcontextprotocol.io) server (Streamable HTTP) for informal money deals between friends, family and freelancers. Say a vague handshake deal out loud, such as *"I lent Aman 1,500, he'll pay Friday"*. Referee asks the few short questions that remove the vagueness, locks the exact terms, tracks payments and amendments across sessions, and later gives a neutral, deterministic verdict.

Built for the **Build, Ship, Shape: Amazon Developer Hackathon** (track: **Alexa+**; mini challenge: **Open Source**, via the standalone [vagueterms](https://github.com/ishaan-2539/vagueterms) package). All code in this repository was written inside the hackathon window.

> **The model parses; the rules decide.** Language understanding is used only to fill a term sheet. Whether a term is vague, and who owes what, is decided by plain deterministic Python that is unit-tested and never calls a network.

---

## What Referee is not

Referee does **not** verify real payments, move money, or create a legally enforceable contract. It is a neutral record of what the user *says* was agreed and paid. It is not legal advice.

---

## How it works

1. **Propose.** *"I lent Aman 1,500, he'll pay Friday."* A parser fills a term sheet (direction, counterparty, amount, deadline, payment mode, partial-payment policy).
2. **Clarify.** The vagueness detector flags weak terms (which Friday? who is "he"? cash or UPI?). Referee asks one question at a time, each with a suggested default, so a one-word answer finishes it.
3. **Lock.** Referee reads the terms back. After *"lock it"*, the deal is frozen and returns a UPI link and a WhatsApp share link so the other person can reply "agreed".
4. **Track.** *"Aman paid 500"* logs a payment. *"Move the deadline"* logs an amendment. The original terms are never overwritten.
5. **Judge.** *"Did Aman pay?"* returns a verdict card (green, neutral, yellow card, red card). *"Who owes me what?"* returns the ledger.

### Verdict rules (deterministic)

| Colour | Meaning |
|---|---|
| Green | Fully settled |
| Neutral | Open or partially paid, deadline not yet passed |
| Yellow card | Overdue 1 to 7 days |
| Red card | Overdue more than 7 days |

With `all_or_nothing`, a partial payment is recorded but the status does not change.

---

## MCP tools

| Tool | Purpose |
|---|---|
| `propose_deal` | Parse an utterance, create a draft deal, return open flags and the next question |
| `answer_question` | Answer the current clarifying question; returns remaining flags or `ready_to_lock` |
| `lock_deal` | Freeze the terms (refused while blocking flags remain); returns UPI and WhatsApp links |
| `log_payment` | Record a payment by deal id or counterparty (oldest deal first for one person) |
| `get_verdict` | Verdict card and a speakable one-liner |
| `amend_deal` | Append an amendment event; the original terms are kept |
| `get_ledger` | Net balances per person across all deals |
| `ping` | Health check |

Every tool returns structured JSON plus a short, speakable `summary` string.

---

## Vagueness detector (`vagueterms`)

The detector is published as its own open-source package, **[vagueterms](https://github.com/ishaan-2539/vagueterms)**, and Referee imports it at runtime.

| Rule | Triggers on |
|---|---|
| `DIRECTION_UNCLEAR` | Nobody said who owes whom |
| `PARTY_PRONOUN` | "he", "she", "they", "the guys", missing name |
| `PARTY_AMBIGUOUS` | The name matches an existing counterparty |
| `AMOUNT_FUZZY` | "around", "about", "some", "a few", or no amount |
| `AMOUNT_UNIT` | "1.5k", "2L", "half" (confirm the number) |
| `DEADLINE_RELATIVE` | Weekday names, "tomorrow", "next week" |
| `DEADLINE_FUZZY` | "end of month", "by evening", "soon" |
| `DEADLINE_CONDITIONAL` | "when he gets paid", "once he can" |
| `MODE_MISSING` | No cash, UPI or bank mention |
| `PARTIAL_MISSING` | No partial-payment rule |

Blocking flags (a deal cannot be locked while one is open): `DIRECTION_UNCLEAR`, `PARTY_PRONOUN`, `PARTY_AMBIGUOUS`, `AMOUNT_FUZZY`.

---

## Architecture

```
Browser simulator (chat + mic) = MCP client
        |  JSON-RPC over Streamable HTTP
        v
Referee server (Starlette)
   |-- /mcp            real MCP endpoint (Streamable HTTP, official Python SDK)
   |-- /api/tool/...   plain REST helper calling the same tool functions (used by tests)
   |-- detector        vagueterms (pure Python)
   |-- parser          regex + dateutil (an experimental Bedrock hook exists, off by default)
   |-- store           SQLite, append-only hash-chained event log
   `-- verdict         deterministic engine
```

**Event log.** State is derived by folding events (`created`, `term_set`, `locked`, `payment`, `amended`). Each event stores `sha256(prev_hash + type + payload + timestamp)`, and `verify_deal_integrity` re-checks the chain. This makes edits to past events *detectable*; it is tamper-evident, not tamper-proof, because someone with write access to the database file could rewrite the whole chain.

---

## Real vs simulated

| Part | Status |
|---|---|
| MCP server with 7 tools at `/mcp` (Streamable HTTP, official Python SDK) | **Real** |
| Vagueness detector, verdict engine, event log, hash-chain check | **Real**, unit-tested |
| UPI link (`upi://pay?...`) and WhatsApp share link | **Real** link formats. The UPI link needs `PAYEE_VPA`; without it, no link is produced |
| Utterance parsing | **Real**, but rule-based (regex + `dateutil`). An optional Amazon Bedrock parser exists in `parser.py` behind `ENABLE_BEDROCK=true`, but it is **experimental and has never been run** (no AWS account was available), so Referee does not claim AWS integration |
| Alexa+ device | **Simulated.** The web simulator stands in for Alexa+; no physical Alexa device or Alexa+ preview access was used |
| Simulator to server link | **Real MCP.** The simulator is an MCP client: it performs the `initialize` handshake, sends `notifications/initialized`, `tools/list` and every `tools/call` to `/mcp` over Streamable HTTP, and reuses the session id. The "MCP Traffic" panel shows those actual JSON-RPC messages, and the header pill shows the protocol version the server negotiated |
| Simulator intent matching | **Simulated.** The simulator turns what you type or say into tool calls with simple keyword rules, standing in for Alexa+'s own language understanding |
| Payments | **Not verified.** Referee records what the user says happened |
| Demo deals (`python -m referee.seed`) | **Seed data**, clearly fictional |

---

## Setup

Requires Python 3.11+.

```bash
git clone https://github.com/ishaan-2539/referee.git
git clone https://github.com/ishaan-2539/vagueterms.git

cd referee
python -m venv .venv
# macOS/Linux: source .venv/bin/activate
# Windows:     .venv\Scripts\activate

pip install -e ../vagueterms
pip install -e ".[dev]"
```

Optional configuration (copy `.env.example` to `.env`, or set environment variables):

| Variable | Meaning |
|---|---|
| `PAYEE_VPA` | Your UPI ID, used to build the UPI link |

Experimental and untested: `ENABLE_BEDROCK=true` with `pip install -e ".[bedrock]"` and AWS credentials enables the Bedrock parser (`AWS_REGION`, `BEDROCK_MODEL_ID`). It is off by default and the project does not need it.

## Run

```bash
uvicorn referee.server:app --port 8000
```

- Simulator: <http://localhost:8000/>
- MCP endpoint: `http://localhost:8000/mcp`

Inspect the real protocol:

```bash
npx @modelcontextprotocol/inspector
```

Choose transport **Streamable HTTP**, URL `http://localhost:8000/mcp`, then Connect.

Load demo data (this **wipes** `referee.db` first):

```bash
python -m referee.seed
```

## Test

```bash
pytest
```

---

## Try this demo flow

1. *"I lent Aman 1500, he'll pay Friday"* and answer the questions (try "yes" to accept defaults).
2. *"Lock it"*: terms freeze; UPI and WhatsApp links appear.
3. *"Aman paid 500"*: the balance updates.
4. *"Did Aman pay?"*: the verdict card.
5. *"Who owes me what?"*: the ledger.

---

## Known limitations

- Deadlines are stored as naive datetimes and treated as UTC by the verdict engine. IST-aware deadlines are not implemented yet.
- The "at most 3 questions, then apply defaults" rule is not enforced.
- The simulator uses keyword-based intent matching, not a language model, so it only understands the phrasings in the demo flow.
- Name matching is prefix-based, so after "Aman (2)" exists, "Aman" is ambiguous and must be disambiguated.
- No authentication, `Origin` check or rate limiting on the server. It is a demo, not hardened for public exposure.

## Repository layout

```
src/referee/
  server.py      MCP tools, Starlette app, simulator bridge
  parser.py      regex/dateutil parser + optional Bedrock parser
  store.py       SQLite append-only event log with hash chain
  verdict.py     deterministic verdict engine
  links.py       UPI and WhatsApp link builders
  models.py      term sheet model
  seed.py        demo seed data
  simulator/     web simulator (index.html, app.js)
tests/           pytest suite
docs/            ARCHITECTURE.md
FRICTION_NOTES.md  raw developer-experience notes from the build
```

## License

MIT, see [LICENSE](LICENSE).
