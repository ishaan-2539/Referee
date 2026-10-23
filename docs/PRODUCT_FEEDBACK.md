# Product Feedback: Referee (Amazon Developer Hackathon 2026)

**Track:** Alexa+ (self-hosted MCP server, Streamable HTTP, spec 2025-11-25, with a simulated Alexa+ web experience)
**Mini challenge:** Open Source (standalone `vagueterms` package)
**AWS services used:** None. Parsing is rule-based (`regex` + `dateutil`); no AWS service is called.

## 1. Alexa+ MCP documentation

I read the MCP and Alexa+ material extensively while building. The core protocol guidance (initialize handshake, `tools/list`, `tools/call`, session handling over Streamable HTTP) was clear and I could verify my server against it with MCP Inspector. Two areas were missing or confusing:

- **Embedding in ASGI frameworks.** There is no canonical example of mounting `streamable_http_app()` inside an existing Starlette or FastAPI app. I hit a 307 redirect on `Mount("/mcp")` and a `Task group is not initialized` error caused by the child app's lifespan not running (see friction log FL-2 and FL-3). A short, copy-pasteable example with the lifespan handling would have saved me a long debugging session.
- **Visual vs. spoken output.** Referee returns a structured verdict card (status, colour, balance, days overdue) plus a speakable `summary`. I could not find guidance on how structured tool output should be shaped for Alexa+ screen surfaces versus text-to-speech, so I made my own convention: every tool returns structured JSON plus a short speakable `summary`.

## 2. `alexa-ai` CLI and real access

I did not use the `alexa-ai` CLI and did not have access to a physical Alexa device or Alexa+ preview. I took the simulated-experience path: a web app that acts as a real MCP client against my server. It performs the `initialize` handshake (protocol `2025-11-25`), sends `notifications/initialized` and `tools/list`, then calls every tool via `tools/call` over Streamable HTTP, reusing the session id. A live "MCP Traffic" panel shows the actual JSON-RPC messages. Only the Alexa+ device and its own language understanding are simulated (the simulator uses keyword intent rules). The source for the simulator is included in the repository.

## 3. MCP Python SDK and future use

**What I used it for:** the entire server. Seven tools (`propose_deal`, `answer_question`, `lock_deal`, `log_payment`, `get_verdict`, `amend_deal`, `get_ledger`) plus a `ping` health check, served at `/mcp`.

**What worked well:**
- The `@mcp.tool()` decorator generates tool schemas from Python type hints and docstrings, so adding a tool is a few lines.
- `streamable_http_app()` gave a working Streamable HTTP transport with sessions out of the box, and the SDK rejected requests with a foreign `Origin` header in my testing.
- Returning plain dictionaries produced both text content and structured content, which made the client easy to write.

**What needs work:**
- The `FastMCP` to `MCPServer` rename in v2.x broke the v1-style code found in most tutorials (FL-1). A migration note or compatibility alias would help.
- Embedding in an existing ASGI app needs documentation (FL-2, FL-3).
- Error messages for lifespan problems should point at the cause.

**Would I build with it again?** Yes. It gives a clean separation between a natural-language front end and a deterministic Python back end. In Referee, the MCP layer only handles conversation and transport, while the vagueness detector (`vagueterms`), the verdict engine and the SQLite append-only event log decide everything that matters. That makes the behaviour testable and trustworthy, which is important for anything involving money.

**MCP Inspector:** useful for checking the real protocol (Streamable HTTP, session id, tool listing). Onboarding had two small snags: the connect step needs to be toggled manually and the default demo server assumes a `/tmp` path that does not exist on Windows (FL-9). Otherwise I would use it again.

## 4. Devpost and hackathon resources

- **Resource constraints.** I am a student builder without AWS Bedrock credits, so paid cloud LLM access was not an option. I built a deterministic, zero-cost parsing engine (`regex` + `dateutil`) that runs fully offline with no API latency and no cloud cost. The trade-off is limited handling of complex sentences. Referee's rules engine catches misparses and asks a clarifying question before a deal can be locked, rather than silently storing a wrong term. LLM-based parsing through Bedrock is the next step on my roadmap, behind the same parser interface.
- **Devpost.** The track guidelines were clear and the SDK, simulator and sample material made it easy to get started. An explicit template for the friction log (the 10% bonus) earlier in the submission window would have made it easier to record entries as I went rather than reconstructing them from notes.

## Work done during the hackathon

Referee and the `vagueterms` package were both created and written during the submission window. All code, tests and documentation in both repositories are new for this hackathon.

## Open Source mini challenge

`vagueterms` is a separate, MIT-licensed package (10 deterministic rules, with a positive and a negative unit test for each) that Referee imports at runtime. It is published independently so others can reuse it for any informal-agreement or voice-assistant project.

## Optional feature requests

- **Important:** a reference example of embedding the Streamable HTTP app inside Starlette/FastAPI, including lifespan handling.
- **Important:** guidance on structured tool output for Alexa+ screen surfaces versus speakable summaries.
- **Nice-to-have:** a published Alexa+ simulator or test harness, so builders without device access can validate multi-turn flows against something official.
