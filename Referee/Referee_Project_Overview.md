# Referee — Project Overview & Build Brief

**Entry:** Build, Ship, Shape: Amazon Developer Hackathon (Devpost: amazonappdev2026.devpost.com)
**Primary track:** Alexa+ (self-hosted MCP server, Streamable HTTP, spec 2025-11-25 or later)
**Mini challenges:** AWS Builder and Open Source (each separate $5,000 + $5,000 AWS credits; a project can win only one track prize and one mini-challenge prize)
**Hard deadline:** Fri 23 Oct 2026, 12:00 PM PT = **Sat 24 Oct 2026, 12:30 AM IST**
**Personal submit-by target:** Fri 23 Oct 2026, **6:00 PM IST** (6.5 hours of buffer)
**Builder:** Ishaan (solo). This document is written to be handed to any AI coding assistant.

> Read this whole file before writing code. Sections 1–3 say what to build and why. Section 9 is the working agreement for the AI assistant. Section 8 is the bonus-points plan.

---

## 1. One-line pitch

Alexa reminders remember *when*. **Referee remembers *what you agreed*.**
Say a vague handshake deal out loud; Referee asks the few sharp questions that remove the vagueness, locks the exact terms, tracks payments and amendments across sessions, and later gives a neutral, deterministic verdict.

## 2. The problem (plain English)

Informal deals between friends, family, and freelancers ("I lent Aman 1,500, he'll pay Friday") fail because the terms are vague and shift later: Which Friday? Midnight or evening? Cash or UPI? What if he pays 1,000 first? Nobody records it, so everyone remembers a different version. The problem is tedious, tiny, and mostly ignored, which is why nobody builds for it.

Referee fixes the *vagueness at the moment of the deal*, and keeps an honest record afterwards.

**What it is not:** it does not verify real payments, move money, or create legally enforceable contracts. It is a neutral record of what the user says was agreed and paid. State this plainly in the demo, README, and Devpost text. (Not legal advice.)

## 3. Why this can score well (rubric mapping)

The four judging criteria are equally weighted: Tech Implementation, Design, Potential Impact, Quality of the Idea. Stage 1 is pass/fail: fits the theme and genuinely uses the required tech (a real MCP server).

| Criterion | What Referee shows |
|---|---|
| Tech Implementation | Real MCP server (official Python SDK, Streamable HTTP, spec 2025-11-25+), 7 tools, SQLite state across sessions, deterministic rule engine, Bedrock parsing, test suite, MCP traffic visible in demo |
| Design | Conversational flow with max 3 clarifying questions, defaults offered, read-back before locking, clear verdict card (green / yellow card / red card) |
| Potential Impact | Real, common, India-relevant problem (UPI era, informal lending, shared expenses); credible next steps; works for any currency |
| Quality of the Idea | Rubric explicitly calls "context-aware add-on that maintains state across sessions" creative. Referee's twist: a **rule-based vagueness detector** plus **amendment history** (moving goalposts made visible) |

**Pitch line for judges:** "The model parses; the rules decide."

**Awareness of related public entries (do NOT copy any code or structure):** BorrowBack (equipment loans, simulated, no money terms), Household Constitution (rules for the agent, not between people). No money-handshake entry with a vagueness detector was found on public GitHub as of 21 Oct 2026, but private entries may exist.

---

## 4. Product spec

### 4.1 Core user flow

1. User: "I lent Aman 1,500, he'll pay Friday."
2. Parser (Bedrock, with regex fallback) fills a **term sheet** (4.2).
3. Detector (pure rules, no AI) flags vague slots (4.3). Referee asks **one question at a time, maximum 3**, each with a suggested default. User may say "use defaults".
4. Referee reads the final terms back. User says "lock it". Deal becomes LOCKED. A UPI link and a WhatsApp share link are returned.
5. Later: "Aman paid 500" logs a payment. "Move the deadline to next Monday" logs an amendment. "Did Aman pay?" returns the verdict. "Who owes me what?" returns the ledger.

### 4.2 Term sheet (slots)

| Slot | Meaning | Notes |
|---|---|---|
| `direction` | Who owes whom | "I lent" vs "I borrowed". Never assume; ask if ambiguous |
| `counterparty` | Name of the other person | Must be a real name, not a pronoun |
| `amount_paise` | Integer minor units | Never use floats for money |
| `currency` | Default INR | Ask only if the user hints otherwise |
| `deadline_ts` | Absolute timestamp with timezone | Default timezone Asia/Kolkata |
| `payment_mode` | cash / UPI / bank / other | |
| `partial_policy` | `accept_partial` or `all_or_nothing` | Default `accept_partial`, deadline unchanged |
| `purpose` | Optional free text | Never required |

### 4.3 Vagueness detector rules (the heart of the project)

Deterministic, unit-tested, no network calls. Publish as a standalone package (section 8.2).

| Rule ID | Triggers on | Question asked (with default) |
|---|---|---|
| `DEADLINE_RELATIVE` | weekday names, "next week", "tomorrow", "soon", "later" | "Friday 23 Oct, 11:59 PM IST?" |
| `DEADLINE_FUZZY` | "end of month", "by evening", "in a few days" | Offer a concrete date and time |
| `DEADLINE_CONDITIONAL` | "when he gets paid", "when I need it", "once he can" | "What date should it be due if that hasn't happened?" |
| `AMOUNT_FUZZY` | "around", "about", "~", "some", "a few", ranges | "Exactly how much?" |
| `AMOUNT_UNIT` | "1.5k", "2L", "half" | Echo the normalised number and confirm |
| `PARTY_PRONOUN` | he / she / they / "the guys" / group | "Who exactly? Give me a name." |
| `PARTY_AMBIGUOUS` | two stored counterparties match the same first name | "Aman Sharma or Aman Verma?" |
| `DIRECTION_UNCLEAR` | "gave", "got from", "settled with" | "Does Aman owe you, or do you owe Aman?" |
| `MODE_MISSING` | no cash/UPI/bank mention | "Cash, UPI, or bank transfer?" |
| `PARTIAL_MISSING` | no partial-payment rule stated | "If he pays part, does that count, with the deadline unchanged?" |

Behaviour rules:
- Ask in priority order: direction, counterparty, amount, deadline, mode, partial.
- One question per turn. At most 3 questions per deal; after that apply defaults and say which defaults were applied.
- Every question includes a proposed default so a one-word answer finishes it.
- Never lock a deal while a `DIRECTION_UNCLEAR`, `PARTY_PRONOUN`, or `AMOUNT_FUZZY` flag is open.

### 4.4 MCP tools (7)

Core 5 first. Items 6–7 are the approved extras; build them only after the core works end to end.

| # | Tool | Input | Output (structured) |
|---|---|---|---|
| 1 | `propose_deal` | `utterance: str` | `deal_id`, parsed slots, `open_flags[]`, `next_question` (or null), `defaults_applied[]` |
| 2 | `answer_question` | `deal_id`, `answer: str` | updated slots, remaining flags, next question or `ready_to_lock: true`, read-back text |
| 3 | `lock_deal` | `deal_id`, `confirm: true` | locked terms, `upi_link`, `whatsapp_share_link`, `locked_at`. Refuses if flags remain or `confirm` is not true |
| 4 | `log_payment` | `deal_id` or `counterparty`, `amount`, optional `mode`, optional `when` | updated balance, status, event id |
| 5 | `get_verdict` | `deal_id` or `counterparty` | verdict card payload (4.6) |
| 6 | `amend_deal` | `deal_id`, `field`, `new_value`, `reason?` | amendment event, original vs current terms, full amendment history. Never overwrites the original |
| 7 | `get_ledger` | optional `counterparty` | per-person net balances across all deals, each with status |

All tools return `structuredContent` plus a short, speakable `summary` string suitable for text-to-speech.

### 4.5 Data model (SQLite, append-only events)

```
deals(id, direction, counterparty, currency, mode, partial_policy,
      principal_paise, deadline_ts, status, purpose, raw_utterance,
      created_at, locked_at)

deal_events(id, deal_id, type, payload_json, ts)
  type ∈ created | term_set | locked | payment | amended
```

- Terms at lock time are frozen in the `locked` event. `amend_deal` appends an `amended` event; the original is never edited.
- Balance and status are **derived** by folding events, not stored separately.
- Optional stretch (about 20 lines): store `sha256(prev_hash + payload)` on each event for a tamper-evident chain. Skip if time is tight; do not over-claim it.

### 4.6 Verdict logic (deterministic, unit-tested)

Inputs: current terms (original plus amendments), payments, now.

- `paid_paise = sum(payments)`, `balance_paise = principal - paid`
- Status: `OPEN`, `PARTIALLY_PAID`, `SETTLED`, `OVERDUE` (derived when now > deadline and balance > 0)
- `days_overdue` = whole days past the current deadline
- Card colour (thresholds are tunable constants):
  - green: SETTLED
  - neutral: OPEN or PARTIALLY_PAID before deadline
  - **yellow card:** overdue 1–7 days
  - **red card:** overdue more than 7 days
- If `partial_policy = all_or_nothing`, a partial payment is recorded but does not change status.
- Verdict payload: status, colour, balance, days overdue, original terms, amendment history, payment list, plain-English one-liner. Example one-liner: "Verdict: Aman owes ₹500. Deadline passed 2 days ago. Yellow card."

### 4.7 Links

- **UPI link** (real standard): `upi://pay?pa=<payee_vpa>&pn=<name>&am=<amount>&cu=INR&tn=<note>`. The payee VPA is the lender's own, supplied once via a config/env value or a `set_profile` helper. If absent, omit the link rather than fabricate one.
- **WhatsApp share:** `https://wa.me/?text=<urlencoded terms text>` so the counterparty can reply "agreed". This reduces the one-sided-lock weakness.

---

## 5. Architecture and tech stack (mostly free)

```
Browser simulator (chat + mic)  ──►  Simulator host (intent → tool calls)
                                              │  MCP client
                                              ▼
Alexa+ (real, optional) ───────►  Referee MCP server  /mcp  (Streamable HTTP)
                                   ├─ detector (pure Python)
                                   ├─ SQLite (events)
                                   ├─ verdict engine
                                   └─ Bedrock parser (fallback: regex)
```

| Layer | Choice | Cost |
|---|---|---|
| Language | Python 3.11+ | Free |
| MCP server | Official `mcp` Python SDK (`pip install "mcp[cli]"`), FastMCP, `transport="streamable-http"`, endpoint `/mcp` | Free |
| State | SQLite (stdlib `sqlite3`) | Free |
| Tests | `pytest` | Free |
| Parser | Amazon Bedrock (an Amazon Nova model; check the console for the model ID available in your region) **with a deterministic regex/dateparser fallback** so the project works at zero cost | Pennies; hackathon AWS credit codes are exhausted, so check whether your AWS account has free-tier credit |
| Simulator UI | Single HTML + vanilla JS; browser Web Speech API for the mic (Chrome) | Free |
| HTTPS for testing | Cloudflare Tunnel (`cloudflared`) or similar free tunnel | Free |
| Optional hosting | A free tier (for example Render; free instances may cold-start) | Free |
| Repo, video | GitHub (public), YouTube (public), OBS Studio for screen recording | Free |
| MCP debugging | MCP Inspector (`npx @modelcontextprotocol/inspector`) | Free |

Notes for the AI assistant:
- Confirm via MCP Inspector that `initialize` negotiates protocol **2025-11-25 or later**. If the installed SDK negotiates an older version, upgrade it.
- The legacy SSE transport is not accepted by Alexa+. Use Streamable HTTP only.
- The simulator host may be rule-based or Bedrock-based. Show the MCP JSON-RPC traffic in a side panel; it proves the server is really called.
- Mount simulator routes next to `/mcp` (FastMCP custom routes or a small Starlette parent app).
- Add an `Origin` check and an optional bearer token on `/mcp` if the server is public.
- Alexa+ account linking is **optional**; do not build OAuth. Real Alexa+ onboarding uses the `alexa-ai` CLI and needs an Alexa developer account and Alexa+ preview access, which may not be available. The rules allow a **simulated Alexa+ experience** instead, provided the repo contains the simulator's source and the video clearly shows it working.

---

## 6. Hackathon rules checklist (from the official rules; re-verify on the Devpost Rules page before submitting)

**Eligibility:** age of majority in country of residence; India is allowed. Solo is fine.

**Project requirements**
- [ ] Project is new or significantly updated during the window (31 Aug – 23 Oct 2026). Referee is new: first commit must be dated inside the window, and the Devpost text must say so.
- [ ] Alexa+ track: working self-hosted MCP server (spec 2025-11-25+, Streamable HTTP) **or** a simulated Alexa+ experience with its source in the repo.
- [ ] Repo **actually calls** the MCP technology at runtime (import and entry point in code), not only mentioned in the README.
- [ ] Repo has clear setup and run instructions.
- [ ] Original work, solely owned by the entrant; third-party SDKs and data used per their licenses.
- [ ] Nothing in the project is derived from Amazon/Devpost-funded or contracted work.

**Repository access (pick one)**
- Public repo **with a visible open-source license file** (License shown in the About section), **or**
- Private repo shared with Devpost's required email (see the "What to Submit" section on the Devpost page) **and** these GitHub users: `knmeiss`, `giolaq`, `anishamalde`, `mosesroth`, `emersonsklar`.
- Invites expire after 7 days and each person must accept. Add them **on submit day**.
- Recommended: public repo with MIT license (also needed for the Open Source mini challenge).

**Submission items (Devpost form)**
- [ ] Text description (features and how it works)
- [ ] GitHub repo URL
- [ ] Demo video **under 3 minutes**, public on YouTube or Vimeo, in English, showing the project working on the intended platform; judges are not required to watch beyond 3:00
- [ ] No third-party trademarks or copyrighted music/footage in the video
- [ ] Product feedback for **every** tool, API, or SDK used (mandatory)
- [ ] Track selected: Alexa+; mini challenges selected: AWS Builder, Open Source
- [ ] If any part existed before the window: explanation of what changed (not expected here)
- [ ] Optional: feature requests, friction log entries

**Other rules**
- Submissions cannot be edited after the deadline.
- Judges may judge from the text and video alone, so the video carries the project.
- Winners are verified (identity and role in creating the submission) and must complete tax forms; prizes are paid after affidavit.
- Fabricating content, tampering with the process, or violating the rules can lead to disqualification.

---

## 7. Build plan (target: submitted by 6 PM IST on 23 Oct)

| Phase | Window (IST) | Goal | Done when |
|---|---|---|---|
| 0 Setup | Thu 22 Oct, first 1–2 h | Join Devpost hackathon; create public GitHub repo with MIT license and README stub (first commit in window); install Python deps, Inspector; request Bedrock model access; start `FRICTION_NOTES.md` | Repo public; hello-world MCP tool visible in Inspector |
| 1 Core | Thu 22 Oct, to ~2 PM | Detector + unit tests; SQLite events; tools 1–3 | `propose_deal` → `answer_question` → `lock_deal` works end to end in Inspector; detector tests green |
| 2 Rest | Thu 22 Oct, 2 PM – ~10 PM | Tools 4–5 (payments, verdict); then 6–7 (amend, ledger); UPI and WhatsApp links; simulator page with verdict card | Full demo story runs start to finish |
| 3 Polish | Fri 23 Oct, 8 AM – 12 PM | Tunnel or deploy; card styling; README; tests green; error handling | **Feature freeze at 12 PM IST on 23 Oct** |
| 4 Ship | Fri 23 Oct, 12 PM – 6 PM | Record video; write friction log and product feedback; Devpost form; add reviewers if private; **submit** | Submission confirmation received |
| Buffer | 6 PM IST → deadline (12:30 AM IST Sat) | Fix only broken links or access problems | — |

**Cut line:** if the core (tools 1–5 plus detector) is not working by Thursday night, drop tools 6–7 and the fancy card. A polished 5-tool demo beats a shaky 7-tool one.

**Explicitly out of scope:** user accounts, counterparty app, notifications, group splits, payment verification, OCR, anything on-chain.

---

## 8. Bonus points and extra prizes — everything to do

### 8.1 Friction log (up to **10% judging bonus**)

How it is scored: Amazon's internal review team assesses friction-log entries at the Stage 1 down-select and passes a recommended bonus (up to 10%) to the Stage 2 panel, which adds it to the final score. Entries are therefore judged on being **specific, reproducible, and actionable**.

**Integrity rule (important):** entries must describe things that **actually happened** to the builder. Never invent or pad friction entries. The aim is genuine developer-experience feedback; fabricated logs could hurt credibility and risk disqualification. Fewer true, detailed entries beat many vague ones. Aim for roughly 6–10 real entries.

**Entry template** (all fields requested by the rules):

```
## FL-<n>: <short title>
- Tool / API / SDK: <e.g. mcp Python SDK vX, Bedrock, MCP Inspector, alexa-ai CLI, Alexa+ simulator, Devpost docs>
- Task attempted: <what you were trying to do>
- Steps taken: <numbered, reproducible>
- Expected: <what you thought would happen>
- Actual: <what happened, include exact error text or a screenshot filename>
- Severity: <Blocker | Major | Minor | Cosmetic>
- Workaround used: <what you did, or "none">
- Suggestion: <specific, actionable change for the owning team>
```

**Workflow for a builder with no time to write these:**
1. During the build, append one raw line to `FRICTION_NOTES.md` the moment something annoys you: timestamp, tool, 5–10 words. Example: `Thu 3:40pm | Inspector | session id lost after restart, no clear error`.
2. Save exact error messages and screenshots in `docs/friction/`.
3. At the end, give the raw notes to an AI (Claude works well) to expand into the template above. The AI must ask for missing details (expected vs actual, steps) and must **not** invent anything not in the notes.
4. Save as `docs/FRICTION_LOG.md` in the repo **and** paste into the Devpost friction field.

**Places friction is likely to occur (watch for these; log only what really happens):**
- SDK protocol-version negotiation vs the required 2025-11-25
- Streamable HTTP session handling and Inspector behaviour
- Tunnel/HTTPS setup for remote testing
- `alexa-ai` CLI install, login, or add-on scaffolding (if attempted)
- Alexa+ preview or simulator access
- Bedrock model access approval, region, quota, or latency
- Devpost form fields or repo-sharing steps
- Gaps in the Alexa+ MCP docs (for example, tool-result rendering or card support)

### 8.2 Open Source mini challenge ($5,000 + $5,000 AWS credits)

Requirement: a **new, additional** open-source project, or a contribution (branch, fork, or PR; need not be merged) to a public repo, made **during the window**, alongside the primary submission.

Plan: publish the vagueness detector as its own repo, **`vagueterms`**:
- Separate public GitHub repo, MIT license visible, created inside the window
- Pure Python, no network dependency, README with examples, a real test suite, installable with `pip install -e .`
- Referee imports it (so it is genuinely used, not decorative)
- Rule table from section 4.3 documented as the public API

Do not use "added a license file to the main repo" as the contribution; the rules call trivial changes "obvious".

Required fields on Devpost for this challenge: contribution URL, repo URL, GitHub username, and a short description of what you did, how it works, and why it matters.

Optional extra (if time remains): a small genuine PR (docs fix or bug fix) to a public MCP-related repo, linked as a second contribution. Only if it is real.

### 8.3 AWS Builder mini challenge ($5,000 + $5,000 AWS credits)

Requirement: use AWS services with **documented integrations**. Qualifies: Bedrock, AgentCore, Strands SDK, SageMaker, Kiro Crew.
- Use Bedrock for utterance → term-sheet parsing, with structured JSON output.
- In the Product Feedback answer, describe which AWS services were used and how (the rules require this there).
- Keep the regex fallback so the demo never depends on AWS being up.
- Judges' "obvious" example for this challenge is a single Bedrock text-generation call. Make the integration meaningful: a constrained parse step feeding a deterministic rule engine, with the model never deciding the verdict.

### 8.4 Other ways to score

- **Product feedback:** mandatory; make it thorough and honest (tools used, what worked, what needs work, onboarding experience, would you build again and why).
- **Optional feature requests:** description, why it matters, priority (Critical / Important / Nice-to-have). Cheap and appreciated.
- **First 30 seconds of the video** show the finished verdict card, then rewind to the story.
- **Visible tests and clean git history** (commits dated inside the window) support "built during the hackathon".
- **Be honest about what is simulated** (Alexa+ host, UPI payment verification). Overclaiming is penalised in credibility; judges reward clarity.
- **MCP Apps** are listed as a creative Alexa+ feature. Only claim it if the verdict card is genuinely delivered as an MCP App resource; otherwise call it a "card rendered in the simulator".

---

## 9. Working agreement for the AI assistant

1. **Follow the spec; ask before changing scope.** Do not add features outside sections 4 and 7.
2. **Build in order:** detector + tests → tools 1–3 → tools 4–5 → extras. Each step must run and be demonstrable in MCP Inspector before moving on.
3. **Determinism first:** the detector and verdict logic must be pure functions with unit tests. The model never decides a verdict.
4. **Money is integers** (paise). Timezone-aware datetimes (default Asia/Kolkata). Test the date parsing around "Friday" edge cases (today is Friday, week boundaries).
5. **No fake data presented as real.** Seed demo data may exist but must be labelled as seed data.
6. **Don't copy other hackathon entries.** Original work only.
7. **Keep secrets out of git** (AWS keys, tokens). Use environment variables and `.env.example`.
8. **Log friction honestly:** whenever the builder hits a tool or docs problem, append a raw line to `FRICTION_NOTES.md` and keep the exact error text.
9. **Keep the README current:** setup, run, test, tools table, what is real vs simulated, license.
10. **Report blockers early** with the exact error and the proposed cut.

### Definition of done

- [ ] `pytest` green (detector, verdict, tools)
- [ ] MCP Inspector shows 7 tools; `initialize` negotiates ≥ 2025-11-25
- [ ] Demo story runs end to end in the simulator
- [ ] Public repo with visible MIT license, run instructions, first commit inside the window
- [ ] `vagueterms` repo public, tested, imported by Referee
- [ ] Video under 3:00, public, English, no copyrighted music
- [ ] Friction log, product feedback, and Devpost form complete
- [ ] Reviewers added (if repo is private) and submission confirmed before 6 PM IST on 23 Oct

---

## 10. Demo video script (target 2:40, hard cap 3:00)

| Time | Scene |
|---|---|
| 0:00–0:20 | Hook: show the finished **yellow-card verdict** with the one-liner, then: "Reminders remember when. Referee remembers what you agreed." |
| 0:20–1:10 | Voice: "I lent Aman 1,500, he'll pay Friday." Referee asks 2–3 sharp questions with defaults; read-back; "lock it"; UPI and WhatsApp links appear |
| 1:10–1:40 | "Aman paid 500." Balance updates. "Move the deadline to Monday." Amendment history shows original vs new |
| 1:40–2:10 | Next day (new session): "Did Aman pay?" → verdict card. "Who owes me what?" → ledger |
| 2:10–2:30 | Brief look at MCP JSON-RPC traffic and test suite; say what is simulated and what is real |
| 2:30–2:40 | Close: real MCP server, rule-based detector published as open source, built with Bedrock |

Record with OBS. Use your own voice or original audio only. Upload as public on YouTube.

---

## 11. Repository layout (suggested)

```
referee/
├─ README.md            # what/why, run, test, tools, real vs simulated, license
├─ LICENSE              # MIT, visible in repo root
├─ .env.example
├─ pyproject.toml
├─ src/referee/
│  ├─ server.py         # FastMCP app, 7 tools, /mcp
│  ├─ parser.py         # Bedrock parse + regex fallback
│  ├─ verdict.py        # deterministic engine
│  ├─ store.py          # SQLite events
│  ├─ links.py          # UPI + wa.me builders
│  └─ simulator/        # host + static UI (index.html, app.js)
├─ tests/
├─ docs/
│  ├─ FRICTION_LOG.md
│  ├─ PRODUCT_FEEDBACK.md
│  ├─ friction/         # screenshots and raw errors
│  └─ ARCHITECTURE.md
└─ FRICTION_NOTES.md    # raw notes during the build
# separate public repo: vagueterms/  (MIT, detector package + tests)
```

---

## 12. Known risks and honest weaknesses

- **Crowded track.** Many public Alexa+ entries exist; execution quality, a real working MCP server, and the video decide this.
- **One-sided record.** Referee cannot prove the other person agreed or that money moved. Mitigation: share link, honest framing.
- **Time.** About 36 working hours. The cut line in section 7 is binding.
- **Alexa+ access.** Real device or preview access may be unavailable; the simulated path is explicitly allowed.
- **Bedrock access or cost.** Mitigated by the regex fallback.
- **Builder has another event right after the deadline.** Submit early; do not use the last night as working time.

---

## 13. Quick reference

- Devpost page: amazonappdev2026.devpost.com (Rules, Resources, FAQs, Updates tabs)
- Alexa+ MCP Toolkit quickstart: developer.amazon.com/docs/alexaplus/add-ons/mcp-toolkit-quickstart
- Reviewer GitHub usernames (private-repo option): knmeiss, giolaq, anishamalde, mosesroth, emersonsklar
- Prizes in play for this entry: Alexa+ track (1st $25,000 / 2nd $15,000 / 3rd $4,000) plus one mini challenge ($5,000 each)
- Judging: Stage 1 pass/fail on theme fit and real use of required tech; Stage 2 four equal criteria; friction log bonus up to 10%
- Judging period 9–20 Nov 2026; winners around 3 Dec 2026
