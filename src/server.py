from pathlib import Path
from fastmcp import FastMCP
from fastmcp.server.providers import FileSystemProvider

mcp = FastMCP("AdvisorMCP", providers=[FileSystemProvider(Path(__file__).parent/ "tools")])

if __name__ == "__main__":
    mcp.run()
