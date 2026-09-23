# courses-mcp
Easier than making an appointment with your advisor


# Tech Stack 

- MCP Framework - FastMCP 
- Language - Python 
- DB - Supabase 
- Package manager - uv 
- Hosting - Cloudflare 


# Start MCP 
`uv run courses-mcp`

Starts Streamable HTTP at `http://127.0.0.1:8000/mcp`.
Direct execution with `python src/server.py` is also supported.

- If running with stdio, change server.py to say `mcp.run()`
or
- If running with Streamable HTTP, change server.py to say `mcp.run(transport="http", host="127.0.0.1", port=8000)`

- Each developer creates their own ngrok tunnel to their local server on port `8000` using `ngrok http 8000`.
- Each developer is responsible for configuring authentication and access control before exposing their server. Owning the tunnel does not authenticate callers.

- Add /mcp to the end of the ngrok URL, when adding the MCP to your LLM provider





# Local Testing 

Run all automated tests with `./run_tests.sh`. The script uses uv to install
development dependencies and run pytest. Pass pytest options as needed, for
example `./run_tests.sh -v` or `./run_tests.sh -k course_details`.

1 - Download Chatgpt on Desktop 
2 - Go to Settings and add an MCP 
3 - Connect using `stdio` and enter: 
    - Command to Launch -> uv 
    - Arguments -> run, src/server.py 
    - Working Directory -> Location of `courses-mcp` folder 
- confirm with running /mcp on Chatgpt CLI or viewing list of MCP's on Chatgpt Desktop


# Deployment 
- Plan is to deploy on Cloudflare
