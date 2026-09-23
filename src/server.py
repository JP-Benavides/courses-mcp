from pathlib import Path
import sys

# Support the package import when this file is launched directly.
if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from fastmcp import FastMCP
from fastmcp.server.providers import FileSystemProvider

mcp = FastMCP("AdvisorMCP", providers=[FileSystemProvider(Path(__file__).parent/ "tools")])

def main():
    mcp.run(transport="http", host="127.0.0.1", port=8000)


if __name__ == "__main__":
    main()
