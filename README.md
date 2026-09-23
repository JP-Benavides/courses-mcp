# courses-mcp
Easier than making an appointment with your advisor


# Tech Stack 

- MCP Framework - FastMCP 
- Language - Python 
- DB - Supabase 
- Package manager - uv 
- Hosting - Cloudflare 


# Start Local MCP

You need `uv` and OpenSSL installed. Run these commands from the project folder.

**1. Set up your environment.** Copy `.env.example` to `.env` if you don't already
have one, then fill in `SUPABASE_URL` and `SUPABASE_PUBLISHABLE_KEY`.

**2. Create auth keys once.** Skip this if `.auth/private.pem` and `.auth/public.pem` already exist.

```bash
mkdir -p .auth
chmod 700 .auth
(umask 077; openssl genpkey -algorithm RSA -pkeyopt rsa_keygen_bits:2048 -out .auth/private.pem) #creates private key 
openssl pkey -in .auth/private.pem -pubout -out .auth/public.pem #creates public key 
```

**3. Generate your token and start the server.** Replace `jp` with your name.

```bash
uv run python -m src.middleware.auth.generate_bearer_token jp
```

-You can also run this instead, if you want to have a token with a specific amount of validity time (in hours).ok
```bash
uv run python -m src.middleware.auth.generate_bearer_token jp --hours 720 
```

-Start Server
```bash
uv run python -m src.server
```

**4. Connect your MCP client.**

- URL: `http://127.0.0.1:8000/mcp`
- Authorization header: `Bearer <paste your token here>`

Tokens last 24 hours. Run the token command again when yours expires.
Keep tokens and `.auth/private.pem` private.

For remote access, run `ngrok http 8000` and use `https://<your-tunnel-host>/mcp`
with the same token.

### How auth works

The private key signs a token containing your name, expiration time, and
`courses:read` permission. Your client sends that token with each request.
The server uses the public key to check the signature, expiration, expected
issuer and audience, and permission before allowing access.

This is manual token authentication: there is no login page or OAuth flow.
Anyone holding a token can use it until it expires. Individual tokens cannot
currently be revoked; replacing the key pair and restarting the server
invalidates all old tokens.

# Local Testing 

Run all automated tests with `./run_tests.sh`. The script uses uv to install
development dependencies and run pytest. Pass pytest options as needed, for
example `./run_tests.sh -v` or `./run_tests.sh -k course_details`.

# Deployment 
- Plan is to deploy on Cloudflare
