# FRICTION_NOTES.md

Wed 6:48pm | Setup | Started project skeleton
Wed 7:00pm | mcp SDK | FastMCP renamed to MCPServer in mcp v2.x breaking v1 code imports
Wed 7:05pm | MCP Inspector | Manual toggle required to connect server before negotiating protocol 2025-11-25
Wed 7:25pm | Virtualenv | Moving project folder broke pip launcher hardcoded absolute paths, required recreation
Wed 8:00pm | Pylance | Strict type checking flagged Optional return values in tests requiring explicit is not None assertions
Wed 8:50pm | Store/Detector | Schema column name mismatch (principal_paise/mode vs amount_paise/payment_mode) broke ready_to_lock status
Wed 10:15pm | Simulator UI | Flexbox container overflow pushed chat input box off-screen after two message exchanges
Wed 10:20pm | Simulator Host | Deal context lost after lock, causing log_payment and get_verdict to fail without active deal_id
Wed 10:22pm | vagueterms / Server | Affirmative "yes" responses failed to register, trapping user in infinite clarifying question loop
Wed 10:30pm | MCP Inspector | Default filesystem server failed on Windows due to unmapped /tmp directory
Wed 10:35pm | Starlette / MCP SDK | Mount("/mcp") issued automatic 307 redirect to /mcp/, breaking Inspector POST requests with 404
Wed 10:38pm | Pylance / MCP SDK | FastMCP class import raised attribute error due to SDK rename to MCPServer in mcp.server.mcpserver
Wed 10:42pm | Starlette / MCP SDK | POST /mcp failed with 500 Internal Server Error (RuntimeError: Task group is not initialized) due to unhandled Starlette lifespan context
Wed 11:05pm | Pylance / Bedrock | Import "boto3" missing from pyproject.toml dependencies causing reportMissingImports
Wed 11:25pm | Simulator UI | String matching in app.js missed named queries ("Did Aman pay?"), routing queries to propose_deal and trapping users in a clarification loop
Wed 11:35pm | Simulator UI | Intent classification order prioritized active deal state over general queries and cancellation commands, trapping user in rigid Q&A procedures
Wed 11:50pm | Server / Verdict | Single-deal payment logging caused total balance confusion when multiple deals existed for the same counterparty; resolved via FIFO waterfall logic
Wed 11:58pm | Simulator / Server | Duplicate counterparties caused merged ledgers without confirmation; resolved with PARTY_AMBIGUOUS disambiguation and conversational chitchat interceptors
Thu 10:05pm | Detector | AMOUNT_FUZZY re-evaluated raw utterance keywords ("about") on subsequent turns, causing infinite "Exactly how much?" clarification loops
Thu 10:12pm | Pytest / Store | Test runner used DEFAULT_DB_PATH (referee.db) instead of isolated temp fixtures, polluting live demo database with test entities
Thu 10:20pm | Server / Waterfall | log_payment silently truncated overpayments against outstanding balances without raising an error or returning a warning
Thu 10:30pm | Simulator UI | Numeric parsing regex in app.js matched before commas in formatted currency strings ("1,500" -> ₹1) and stale browser caching hid JS updates
Thu 10:38pm | Parser / Detector | Counterparty regex swallowed quantity terms ("Aman 5 lakh"), decimal paise dropped, and relative deadline prompts hardcoded day strings
Thu 10:45pm | Server / Matching | Prefix-based string comparison (startswith) in party matching caused false positive collisions between distinct names like Ram/Ramesh
Thu 10:52pm | Packaging | Unpinned mcp dependency broke server imports, vagueterms missing from pyproject.toml, and missing root README.md failed editable pip installs