from mcp.server.mcpserver import MCPServer

# Create the MCP server
mcp = MCPServer("Referee", dependencies=["mcp"])

@mcp.tool()
def ping() -> str:
    """A simple hello-world ping tool to verify MCP connectivity."""
    return "pong"

if __name__ == "__main__":
    mcp.run()