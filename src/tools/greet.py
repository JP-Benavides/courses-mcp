from fastmcp.tools import tool

@tool
def greet(name: str) -> str:
    return f"Hello, {name}!"