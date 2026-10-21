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