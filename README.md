<div align="center">

# ⚽ Referee

### Alexa reminders remember *when*. Referee remembers *what you agreed*.

A voice-first MCP server that turns vague handshake deals into exact, trackable terms,
then gives a neutral verdict when someone asks, "Did he pay?"

![License: MIT](https://img.shields.io/badge/license-MIT-green)
![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-blue)
![MCP spec 2025-11-25](https://img.shields.io/badge/MCP-2025--11--25-purple)
![Transport: Streamable HTTP](https://img.shields.io/badge/transport-Streamable%20HTTP-orange)

[Demo video](#demo) · [Quickstart](#quickstart) · [MCP tools](#mcp-tools) · [How it works](#how-it-works) · [Limitations](#known-limitations)

</div>

---

## Why this exists

> *"I lent Aman 1,500, he'll pay Friday."*

Which Friday? Midnight or evening? Cash or UPI? What if he pays 1,000 first? Nobody writes it down, so a month later everyone remembers a different version.

Informal deals between friends, family and freelancers fail because the **terms are vague** and **shift later**. The problem is small, tedious and almost always ignored, which is exactly why Referee exists.

Referee fixes the vagueness **at the moment of the deal**, then keeps an honest record afterwards:

1. You say the deal out loud.
2. Referee asks the few short questions that remove the vagueness (at most one per turn, each with a default, so "yes" is a valid answer).
3. It reads the exact terms back and locks them.
4. It tracks payments and amendments across sessions, and **never overwrites the original terms**.
5. Later, it gives a deterministic verdict: green, neutral, yellow card or red card.

> **The parser fills slots. The rules decide.** Language understanding is only used to fill a term sheet. Whether a term is vague, and who owes what, is decided by plain Python that is unit-tested and never touches the network.

### What Referee is *not*

Referee does **not** verify real payments, move money, or create a legally enforceable contract. It is a neutral record of what the user *says* was agreed and paid. It is not legal advice.

---

## Demo

<!-- TODO before submitting: replace the line below with your public YouTube link -->
**Video (under 3 minutes):** _add your YouTube link here_

<!-- Optional: add a screenshot of the verdict card at docs/screenshot.png, then uncomment:
![Referee verdict card](docs/screenshot.png)
-->

### Example conversation

These are real tool responses from the server (`summary` is the speakable text returned by every tool):

| You say | Referee replies |
|---|---|
| *"I lent Aman 1,500, he'll pay Friday."* | "Got it! I've noted the agreement. Is Friday 11:59 PM IST acceptable as the exact deadline?" |
| *"Yes."* | "Got it. How will this be paid: cash, UPI, or bank transfer?" |
| *"Lock it."* | "Locked! I've finalized the agreement with Aman for ₹1500. You can share the WhatsApp confirmation link or use the UPI link when paying." |
| *"Aman paid 500."* | "Logged payment of ₹500 from Aman. Overall remaining total owed across all active deals with Aman is now ₹1000." |
| *"Did Aman pay?"* | "Verdict: Aman owes you ₹1000. Status: PARTIALLY_PAID." |
| *"Who owes me what?"* | "Aman owes you ₹1000 (PARTIALLY_PAID). Net total: ₹1000 owed to you across active deals." |

---

## How it works

```
 You (voice or text)
        │
        ▼
 ┌──────────────┐   term sheet   ┌─────────────────────┐
 │   Parser     │ ─────────────► │  Vagueness detector │  pure rules, no network
 │ regex+dateutil│               │     (vagueterms)    │
 └──────────────┘                └──────────┬──────────┘
                                            │ flags + next question
                                            ▼
                                  ┌─────────────────────┐
                                  │  Append-only events │  SQLite, hash-chained
                                  └──────────┬──────────┘
                                            │ fold events
                                            ▼
                                  ┌─────────────────────┐
                                  │   Verdict engine    │  pure function
                                  └─────────────────────┘
```

**Term sheet.** Every deal is reduced to eight slots: `direction`, `counterparty`, `amount_paise`, `currency`, `deadline_ts`, `payment_mode`, `partial_policy`, `purpose`.

**Clarifying questions.** The detector ranks open flags in this order: direction, counterparty, amount, deadline, mode, partial-payment rule. Referee asks one at a time and offers a default so a one-word answer finishes it.

**Blocking flags.** A deal cannot be locked while `DIRECTION_UNCLEAR`, `PARTY_PRONOUN`, `PARTY_AMBIGUOUS` or `AMOUNT_FUZZY` is open.

**Event log.** State is never stored directly. It is derived by folding events (`created`, `term_set`, `locked`, `payment`, `amended`). Terms at lock time are frozen, and an amendment appends a new event instead of editing the old one. Each event stores `sha256(prev_hash + type + payload + timestamp)`, and `verify_deal_integrity` re-checks the chain. This makes edits to past events **detectable**. It is tamper-evident, not tamper-proof, since anyone with write access to the database file could rewrite the whole chain.

**Money and time.** Money is always integer paise, never floats. Datetimes are timezone-aware and default to `Asia/Kolkata`.

### Verdict rules

| Card | Meaning |
|---|---|
| 🟢 Green | Fully settled |
| ⚪ Neutral | Open or partially paid, deadline not yet passed |
| 🟡 Yellow card | Overdue 1 to 7 days |
| 🔴 Red card | Overdue more than 7 days |

With `all_or_nothing`, a partial payment is recorded but the status does not change.

---

## MCP tools

Referee exposes its tools at `/mcp` over **Streamable HTTP** (MCP spec 2025-11-25), built on the official Python SDK. Every tool returns structured JSON plus a short speakable `summary`.

| Tool | What it does |
|---|---|
| `propose_deal` | Parse an utterance, create a draft deal, return open flags and the next question |
| `answer_question` | Answer the current clarifying question; returns remaining flags or `ready_to_lock` |
| `lock_deal` | Freeze the terms (refused while blocking flags remain); returns UPI and WhatsApp links |
| `log_payment` | Record a payment by deal id or counterparty (oldest deal first for one person) |
| `get_verdict` | Verdict card plus a speakable one-liner |
| `amend_deal` | Append an amendment event; the original terms are kept |
| `get_ledger` | Net balances per person across all deals |
| `ping` | Health check |

### The vagueness detector (`vagueterms`)

The detector is published as its own open-source package, **[vagueterms](https://github.com/ishaan-2539/vagueterms)**, and Referee imports it at runtime.

| Rule | Triggers on |
|---|---|
| `DIRECTION_UNCLEAR` | Nobody said who owes whom |
| `PARTY_PRONOUN` | "he", "she", "they", "the guys", or a missing name |
| `PARTY_AMBIGUOUS` | The name matches an existing counterparty |
| `AMOUNT_FUZZY` | "around", "about", "some", "a few", or no amount |
| `AMOUNT_UNIT` | "1.5k", "2L", "half" (confirm the number) |
| `DEADLINE_RELATIVE` | Weekday names, "tomorrow", "next week" |
| `DEADLINE_FUZZY` | "end of month", "by evening", "soon" |
| `DEADLINE_CONDITIONAL` | "when he gets paid", "once he can" |
| `MODE_MISSING` | No cash, UPI or bank mention |
| `PARTIAL_MISSING` | No partial-payment rule |

---

## Real vs simulated

Being clear about this matters more than looking impressive.

| Part | Status |
|---|---|
| MCP server with 7 tools at `/mcp` (Streamable HTTP, official Python SDK) | ✅ **Real** |
| Vagueness detector, verdict engine, event log, hash-chain check | ✅ **Real**, unit-tested |
| UPI link (`upi://pay?...`) and WhatsApp share link | ✅ **Real** link formats. The UPI link needs `PAYEE_VPA`; without it, no link is produced |
| Simulator ↔ server connection | ✅ **Real MCP.** The simulator performs the `initialize` handshake, sends `notifications/initialized`, `tools/list` and every `tools/call` to `/mcp`, and reuses the session id. The "MCP Traffic" panel shows the actual JSON-RPC messages |
| Utterance parsing | ⚠️ **Real but rule-based** (regex + `dateutil`). No LLM is used. See [Known limitations](#known-limitations) |
| Alexa+ device | 🧪 **Simulated.** The web simulator stands in for Alexa+. No physical Alexa device or Alexa+ preview access was used |
| Simulator intent matching | 🧪 **Simulated.** Simple keyword rules turn what you type or say into tool calls, standing in for Alexa+'s own language understanding |
| Payments | ❌ **Not verified.** Referee records what the user says happened |
| Demo deals (`python -m referee.seed`) | 🧪 **Seed data**, clearly fictional |

---

## Quickstart

Requires **Python 3.11+**.

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

**Run the server and simulator:**

```bash
uvicorn referee.server:app --port 8000
```

- Simulator: <http://localhost:8000/>
- MCP endpoint: `http://localhost:8000/mcp`

**Inspect the real protocol** with the MCP Inspector:

```bash
npx @modelcontextprotocol/inspector
```

Choose transport **Streamable HTTP**, enter `http://localhost:8000/mcp`, then click Connect.

**Load demo data** (this **wipes** `referee.db` first):

```bash
python -m referee.seed
```

**Run the tests:**

```bash
pytest
```

### Configuration

Copy `.env.example` to `.env`, or set environment variables.

| Variable | Meaning |
|---|---|
| `PAYEE_VPA` | Your UPI ID, used to build the UPI payment link (optional) |

### Try the demo flow

1. Say *"I lent Aman 1500, he'll pay Friday"* and answer the questions (try "yes" to accept the defaults).
2. Say *"Lock it"*. The terms freeze and the UPI and WhatsApp links appear.
3. Say *"Aman paid 500"*. The balance updates.
4. Say *"Did Aman pay?"*. The verdict card appears.
5. Say *"Who owes me what?"*. The ledger appears.

---

## Known limitations

Honest list, in rough order of importance:

- **Parser sensitivity.** Parsing is regex + `dateutil` only. Complex phrasing such as *"Aman needs 1500 for rent, I gave him cash today and he promises to return it next Thursday"* can produce wrong slots. In that sentence the amount, cash mode and deadline are read correctly, but the counterparty is read as "him". The deterministic detector flags this and asks *"Who exactly?"* before the deal can be locked, so a misparse is caught instead of silently stored. I had no AWS account during the hackathon, so LLM-based parsing (Amazon Bedrock) is the next item on the [roadmap](#roadmap).
- **Simulator intent matching is keyword-based.** It only understands the phrasings in the demo flow.
- **The "at most 3 questions, then apply defaults" rule is not enforced yet.**
- **Name matching is prefix-based.** After "Aman (2)" exists, "Aman" becomes ambiguous and must be disambiguated.
- **No authentication or rate limiting.** In testing, the MCP SDK rejected requests with a foreign `Origin` header, but there is no bearer token. This is a demo, not hardened for public exposure.
- **Deadlines default to Asia/Kolkata.** There is no per-user timezone setting.

---

## Roadmap

- [ ] LLM-based utterance parsing (Amazon Bedrock) behind the same parser interface, with the regex parser kept as an automatic fallback. The model would only fill slots; rules would still decide.
- [ ] Enforce the 3-question cap and apply defaults afterwards.
- [ ] A proposed default for every clarifying question.
- [ ] Real Alexa+ integration through the Alexa developer tooling.
- [ ] A counterparty confirmation flow, to reduce the one-sided-record weakness.
- [ ] Per-user timezone and currency settings.

---

## Built for

**Build, Ship, Shape: Amazon Developer Hackathon**

- **Track:** Alexa+ (self-hosted MCP server, Streamable HTTP)
- **Mini challenge:** Open Source, via the standalone [vagueterms](https://github.com/ishaan-2539/vagueterms) package
- **AWS services:** none used. Parsing is rule-based.
- All code in this repository was written inside the hackathon window.

## Repository layout

```
src/referee/
  server.py      MCP tools, Starlette app, simulator bridge
  parser.py      regex + dateutil utterance parser
  store.py       SQLite append-only event log with hash chain
  verdict.py     deterministic verdict engine
  links.py       UPI and WhatsApp link builders
  models.py      term sheet model
  seed.py        demo seed data
  simulator/     web simulator (index.html, app.js)
tests/           pytest suite
docs/            ARCHITECTURE.md, FRICTION_LOG.md, PRODUCT_FEEDBACK.md
FRICTION_NOTES.md  raw developer-experience notes from the build
```

## License

MIT. See [LICENSE](LICENSE).

> Referee is a record-keeping tool, not legal advice. It does not verify payments or create enforceable contracts.