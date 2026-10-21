# ROADMAP.md: Referee build tracker (for the AI assistant)

> **AI: read this file FIRST, every session, before doing anything else.**
> Then read `Referee_Project_Overview.md` sections 4, 5 and 9 if you have not in this session.
> This file is the single source of truth for "where are we". Update it before you stop.

---

## 0. START HERE (update this block every session)

```
CURRENT PHASE:      3 (Polish)
CURRENT TASK:       P3.1 Bedrock parser (Amazon Nova + regex fallback)
LAST COMPLETED:     Phase 2 (Tools 1-7, Links, Simulator UI, MCP Inspector protocol)
LAST SESSION NOTE:  Phase 2 verified green! All 7 MCP tools live over Streamable HTTP (/mcp). Simulator UI with Web Speech API & JSON-RPC traffic panel fully functional. Ready to add Bedrock parser fallback and polish docs.
BLOCKERS:           none
LAST UPDATED:       21 Oct 2026 10:50 PM IST
```

### Session protocol
1. Read this file. Go to `CURRENT TASK`. Do NOT start from scratch or re-plan.
2. Run `pytest` (once tests exist) to confirm the baseline is green before changing anything.
3. Work tasks in order. Tick `[x]` only when the task's **Done when** is actually true (run it, don't assume).
4. After each task: commit with a clear message, update `START HERE`, then move on.
5. Before stopping or when context is getting long: fill `LAST SESSION NOTE` with exact next step.
6. Anything annoying with a tool/SDK/docs: append one raw line to `FRICTION_NOTES.md` (format in section 7). Never invent entries.
7. If a task is stuck for more than 30 minutes: write the exact error in Blockers, propose the cut, ask the builder.

### Hard rules (from the overview, section 9)
- Do not add scope outside the overview sections 4 and 7. Ask first.
- Money = integer paise. Datetimes timezone-aware, default `Asia/Kolkata`.
- Detector and verdict engine are pure functions, unit-tested, no network. The model never decides a verdict.
- No secrets in git. Use env vars and `.env.example`.
- Be honest in README and video about what is simulated (Alexa+ host, UPI verification).
- Original work only. Do not copy other entries.

---

## 1. Timeline (IST) and cut line

| When | Goal |
|---|---|
| Wed 21 Oct evening (optional head start) | Phase 0 |
| Thu 22 Oct, to ~2 PM | Phase 1 (detector + tools 1-3) |
| Thu 22 Oct, 2 PM to ~10 PM | Phase 2 (tools 4-7, links, simulator) |
| Fri 23 Oct, 8 AM to 12 PM | Phase 3 (polish). **FEATURE FREEZE 12 PM** |
| Fri 23 Oct, 12 PM to 6 PM | Phase 4 (video, docs, Devpost, **SUBMIT by 6 PM**) |
| Fri 6 PM to Sat 12:30 AM | Buffer only. Fix broken links/access. No new work |

**Hard deadline:** Sat 24 Oct 12:30 AM IST (Fri 23 Oct 12:00 PM PT). Submissions cannot be edited after.

**CUT LINE (binding):** If tools 1-5 plus detector do not work by Thursday night, drop tools 6-7 and the fancy card. A polished 5-tool demo beats a shaky 7-tool one.

---

## 2. Phase 0: Setup

- [ ] **P0.1 Repo.** Create public GitHub repo `referee`, add MIT `LICENSE` in root, README stub, `.gitignore`, `.env.example`. First commit dated inside the window.
  - Done when: repo is public and the License shows in the GitHub About section.
- [ ] **P0.2 Project skeleton.** `pyproject.toml`, `src/referee/`, `tests/`, `docs/`, `FRICTION_NOTES.md` (empty with header). Python 3.11+, venv, `pip install "mcp[cli]" pytest python-dateutil`.
  - Done when: `pytest` runs (even with zero tests) and `python -c "import mcp"` works.
- [ ] **P0.3 Hello-world MCP.** FastMCP server, one `ping` tool, `transport="streamable-http"`, endpoint `/mcp`.
  - Done when: MCP Inspector (`npx @modelcontextprotocol/inspector`) connects and lists `ping`.
- [ ] **P0.4 Protocol version check.** In Inspector confirm `initialize` negotiates **2025-11-25 or later**. If older, upgrade the SDK. Log any trouble in FRICTION_NOTES.
  - Done when: the negotiated version is written here: `______`.
- [ ] **P0.5 Devpost + AWS.** Join the hackathon on Devpost (builder does this). Request Bedrock model access (builder does this; check the console for the Nova model ID in the region). Builder checks for free-tier credit.
  - Done when: builder confirms. If Bedrock is not available, continue with the regex fallback only.
- [ ] **P0.6 Second repo.** Create public repo `vagueterms` (MIT, created inside the window) with `pyproject.toml` and README stub.
  - Done when: `pip install -e ../vagueterms` works from the referee venv.

---

## 3. Phase 1: Core (detector + tools 1-3)

- [ ] **P1.1 Term sheet model.** Dataclass/pydantic `TermSheet` with slots from overview 4.2 (`direction, counterparty, amount_paise, currency, deadline_ts, payment_mode, partial_policy, purpose`).
- [ ] **P1.2 Detector in `vagueterms`.** Implement the 10 rules from overview 4.3 as pure functions: `DEADLINE_RELATIVE, DEADLINE_FUZZY, DEADLINE_CONDITIONAL, AMOUNT_FUZZY, AMOUNT_UNIT, PARTY_PRONOUN, PARTY_AMBIGUOUS, DIRECTION_UNCLEAR, MODE_MISSING, PARTIAL_MISSING`.
  - Priority order for questions: direction, counterparty, amount, deadline, mode, partial.
  - Max 3 questions per deal, one per turn, every question has a default. Then apply defaults and report them.
  - Blocking flags (deal cannot lock): `DIRECTION_UNCLEAR`, `PARTY_PRONOUN`, `AMOUNT_FUZZY`.
  - Done when: `pytest` green for every rule with positive and negative cases, plus the "today is Friday" and week-boundary date edge cases.
- [ ] **P1.3 Parser.** `parser.py`: regex + `dateparser`/`dateutil` fallback first (this is the guaranteed path). Bedrock structured-JSON parse is added in P3.x, behind the same interface.
  - Done when: "I lent Aman 1,500, he'll pay Friday" yields direction=lent, counterparty=Aman, amount_paise=150000, deadline flagged relative.
- [ ] **P1.4 Store.** `store.py`: SQLite, tables `deals` and `deal_events` (overview 4.5), append-only. Balance/status derived by folding events.
  - Done when: tests prove events are never updated and the state folds correctly.
- [ ] **P1.5 Tool 1 `propose_deal`.** Returns `deal_id, slots, open_flags[], next_question, defaults_applied[]`, plus `structuredContent` and a speakable `summary`.
- [ ] **P1.6 Tool 2 `answer_question`.** Updates slots, returns remaining flags, next question or `ready_to_lock: true`, and read-back text. Supports "use defaults".
- [ ] **P1.7 Tool 3 `lock_deal`.** Requires `confirm: true`; refuses if blocking flags remain. Freezes terms in a `locked` event. Returns `upi_link`, `whatsapp_share_link`, `locked_at` (links can be stubbed until P2.4).
  - **PHASE 1 DONE when:** in MCP Inspector, `propose_deal` -> `answer_question` -> `lock_deal` works end to end, and detector tests are green. Commit and tag `phase1`.

---

## 4. Phase 2: Rest (tools 4-7, links, simulator)

- [ ] **P2.1 Verdict engine `verdict.py`.** Pure function per overview 4.6: `paid, balance, status (OPEN/PARTIALLY_PAID/SETTLED/OVERDUE), days_overdue, colour` (green / neutral / yellow 1-7 days / red >7). `all_or_nothing` records partials without changing status. Thresholds are constants.
  - Done when: tests cover each status, each colour boundary (day 0, 1, 7, 8), amendments, and all_or_nothing.
- [ ] **P2.2 Tool 4 `log_payment`.** By `deal_id` or `counterparty` (use `PARTY_AMBIGUOUS` if two match). Returns updated balance, status, event id.
- [ ] **P2.3 Tool 5 `get_verdict`.** Returns the verdict card payload and one-liner, e.g. "Verdict: Aman owes ₹500. Deadline passed 2 days ago. Yellow card."
  - **CORE DONE when P2.1-P2.3 pass in Inspector. Check the cut line (section 1) now.**
- [ ] **P2.4 Links `links.py`.** UPI link (`upi://pay?pa=...&pn=...&am=...&cu=INR&tn=...`) from env `PAYEE_VPA`; omit if not set. WhatsApp `https://wa.me/?text=<urlencoded>`. Unit-tested.
- [ ] **P2.5 Tool 6 `amend_deal`** (only if the cut line allows). Appends an `amended` event; never edits the original. Returns original vs current terms and full history.
- [ ] **P2.6 Tool 7 `get_ledger`** (only if the cut line allows). Per-person net balances with status.
- [ ] **P2.7 Simulator.** `src/referee/simulator/` single `index.html` + `app.js`: chat box, mic via Web Speech API, intent -> MCP tool calls (rule-based is fine), **side panel showing raw MCP JSON-RPC traffic**, verdict card (green / neutral / yellow / red). Mount next to `/mcp`.
  - Done when: the full demo story runs start to finish: lend -> questions -> lock -> payment -> amend -> new session -> verdict -> ledger.
- [ ] **P2.8 Seed data** for the demo, clearly labelled "seed data" in code and README.

---

## 5. Phase 3: Polish (feature freeze 12 PM IST Fri)

- [ ] **P3.1 Bedrock parser.** Utterance -> term-sheet JSON via an Amazon Nova model; same interface as the regex parser; automatic fallback to regex on any error. Model never decides verdicts.
  - Done when: works with creds, and the demo still works with Bedrock disabled. If access is unavailable, skip and say so honestly in the docs.
- [ ] **P3.2 Security + errors.** `Origin` check, optional bearer token on `/mcp`, friendly tool errors, no stack traces to the client.
- [ ] **P3.3 Tunnel/deploy.** `cloudflared` tunnel (or free host) so `/mcp` is reachable over HTTPS. Note any problems in FRICTION_NOTES.
- [ ] **P3.4 Card styling** and a visual check on a phone-width screen.
- [ ] **P3.5 README.** What/why, setup, run, test, tools table, **real vs simulated**, "not legal advice / no payment verification", license.
- [ ] **P3.6 `docs/ARCHITECTURE.md`** (short, one diagram).
- [ ] **P3.7 Full test pass.** `pytest` green. Inspector shows the tools and protocol >= 2025-11-25.
- [ ] **P3.8 FEATURE FREEZE at 12 PM IST.** Only bug fixes after this.

---

## 6. Phase 4: Ship (submit by 6 PM IST Fri 23 Oct)

- [ ] **P4.1 Demo video** (under 3:00, English, public on YouTube, no copyrighted music). Follow overview section 10. First 20 seconds: finished yellow-card verdict. Say clearly what is simulated.
- [ ] **P4.2 Friction log.** Expand `FRICTION_NOTES.md` into `docs/FRICTION_LOG.md` using the template in the overview 8.1. Ask the builder for any missing details. **Do not invent anything not in the notes.** Roughly 6-10 real entries.
- [ ] **P4.3 Product feedback** (`docs/PRODUCT_FEEDBACK.md`): mandatory, covers every tool/API/SDK used, which AWS services and how, what worked, what did not, would you build again.
- [ ] **P4.4 `vagueterms` repo polished:** README with examples, tests green, `pip install -e .` works, imported by Referee.
- [ ] **P4.5 Devpost form:** description, repo URL, video URL, Track = Alexa+, mini challenges = AWS Builder and Open Source (note: only one mini-challenge prize can be won), Open Source fields (contribution URL, repo URL, GitHub username, description), feedback, friction log. Re-check the Rules page for any changes.
- [ ] **P4.6 Final checks.** Repo public with the visible MIT license, first commit inside the window (31 Aug-23 Oct), no secrets in git history, links open while logged out.
- [ ] **P4.7 SUBMIT** and save the confirmation. Target: before 6 PM IST.

---

## 7. FRICTION_NOTES.md format (raw, one line each)

`Thu 3:40pm | Inspector | session id lost after restart, no clear error`

Save exact error text and screenshots in `docs/friction/`. Only log what really happened.

---

## 8. Decision log (append, newest last)

| Date/time | Decision | Why |
|---|---|---|
| | | |

## 9. Blockers log

| Date/time | Blocker (exact error) | Proposed cut / workaround | Status |
|---|---|---|---|
| | | | |

## 10. Out of scope (do not build)

User accounts, counterparty app, notifications, group splits, payment verification, OCR, OAuth/account linking, anything on-chain.
