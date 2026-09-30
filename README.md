# courses-mcp
Easier than making an appointment with your advisor


# Tech Stack 

- MCP Framework - FastMCP 
- Language - Python 
- DB - Supabase 
- Package manager - uv 
- Hosting - Cloudflare 


# OAuth setup for MCP clients

Supabase Auth handles accounts, login, consent, authorization codes, and refresh
tokens for MCP clients. This server is the protected resource.
Users must have a non-anonymous Supabase account before authorizing access.
The companion frontend is `../courses-website`.

## Configure Supabase and MCP clients

1. Enable **Authentication → OAuth Server** in the same Supabase project as the
   website. Set the website's deployed HTTPS Site URL and authorization path
   `/oauth/consent`. Configure the website's existing login/confirmation redirect
   URLs as well, including `/auth/callback` with the return path used to resume
   consent after signup confirmation or Google login. Set the website's existing
   `NEXT_PUBLIC_MCP_URL` to the canonical HTTPS MCP endpoint ending in `/mcp`.
   See [Supabase setup](https://supabase.com/docs/guides/auth/oauth-server/getting-started).
2. Use an asymmetric Supabase signing key, **ES256** or **RS256**. Match the
   algorithm in the MCP environment. Legacy HS256 project secrets are not used.
3. Enable **dynamic client registration** under Authentication → OAuth Server.
   Compatible desktop and other MCP clients can register with Supabase using
   their callback URL and PKCE. Require explicit user approval on the website's
   consent screen. A manually registered OAuth client also works.
4. Install and enable the audience hook after configuring its resource placeholder.
   Then connect an MCP client to the canonical HTTPS MCP URL, ending in `/mcp`.

[Supabase's MCP authentication guide](https://supabase.com/docs/guides/auth/oauth-server/mcp-authentication)
covers registration, consent, and PKCE. Supabase publishes authorization-server metadata; FastMCP publishes
protected-resource metadata and an unauthenticated `401` discovery challenge.

## Bind access tokens to this MCP

Default Supabase access tokens have `aud: "authenticated"`; this server rejects
that audience alone. The required resource is exactly `MCP_PUBLIC_URL + "/mcp"`.
Use [supabase/mcp_access_token_hook.sql](supabase/mcp_access_token_hook.sql) as a
reviewable installation template, **not an automatically applied migration**:
For the current ngrok origin, a ready-to-review copy is
[supabase/mcp_access_token_hook.ngrok.sql](supabase/mcp_access_token_hook.ngrok.sql).

1. Replace its resource URL placeholder. The resource URL must
   match the MCP public URL, including `/mcp` and excluding a trailing slash.
2. If the project already has a Custom Access Token hook, merge this logic into
   that hook; do not discard existing claims or hook behavior.
3. Run the reviewed SQL in the Supabase SQL editor, then select
   `public.courses_mcp_access_token_hook` under **Authentication → Hooks → Custom
   Access Token**. The template aborts installation with unresolved placeholders.
4. Verify both initial OAuth issuance and refresh issuance. An authenticated,
   non-anonymous OAuth user's token should contain
   `aud: ["authenticated", "https://your-host/mcp"]` for any Supabase-issued
   OAuth client ID. Ordinary website sessions retain their original audience.
   Do not copy tokens into logs or public JWT debugging websites.

The hook changes the audience for authenticated, non-anonymous OAuth tokens with
a provider-issued client ID and preserves the remaining claims. It does not accept a client-supplied arbitrary
resource or user metadata as authority. Supabase documents
[client-specific audience customization](https://supabase.com/docs/guides/auth/oauth-server/token-security).
The two audiences intentionally allow the MCP and the project's database API to
consume this token: [PostgREST supports audience arrays](https://postgrest.org/en/stable/references/auth.html#jwt-claims-validation).
**Hook acceptance, refreshed tokens, and database API compatibility still need
verification against the deployed Supabase project.** Do not relax MCP audience
validation if project configuration rejects this setup.

The verifier checks the project issuer, JWKS signature, configured algorithm,
expiration, resource audience, UUID user subject, `role: authenticated`,
`is_anonymous: false`, and a nonempty provider-issued OAuth client ID. Ordinary website tokens,
anonymous accounts, ID tokens, and legacy locally signed tokens cannot authorize
MCP requests. Tool metadata requests `openid offline_access`. This project's
Supabase metadata advertises both scopes; `offline_access` requests ongoing
refresh access, though live issuance with that scope still needs verification.
OAuth scopes do not grant database permissions;
there is no custom `courses:read` scope in this integration.

## Start the server

Install `uv`, copy `.env.example` to `.env` if needed, and populate its settings.
Keep the website and server on the same Supabase project. `MCP_PUBLIC_URL` must
be an HTTPS **origin**, without `/mcp`, a query, or credentials. For local testing,
use the HTTPS origin of a tunnel forwarding to port 8000; update the hook when
that public resource URL changes.

```bash
uv sync
uv run python -m src.server
```

The server listens on `127.0.0.1:8000`; expose it through your HTTPS proxy/tunnel.
MCP clients connect to `https://your-host/mcp` and manage their access and refresh
tokens. A desktop client's saved connection can renew access across restarts while
its grant and refresh token remain valid; access tokens themselves expire.
The old `generate_bearer_token.py` remains a local utility only; its output is
not accepted by this OAuth server. No private signing key is needed here.

## Logout, disconnect, and database access

Website logout ends only the current website session (`scope: "local"`).
It does not disconnect ChatGPT. The website's connected-app controls revoke the
chosen Supabase OAuth grant separately, preventing further renewal. This server
validates JWTs locally; a previously issued access token may remain usable until
its expiration. Configure a suitable access-token lifetime in Supabase.

Database queries use a separate client per request with the verified user's
access token and the publishable key. No service-role key or global user session
is used. This supplies the identity that future RLS policies can inspect; it
**does not create row isolation by itself**. RLS policies are not installed by
this change. The owner will configure them and test cross-user isolation later.
OIDC scopes are not a substitute for those policies.

## Integration checks still required

Automated local tests do not prove the live provider/ChatGPT connection. After
configuring the project, check account signup/login, approve and deny, OAuth
code exchange with the resource parameter, token audience/signature, database
queries, refresh, website logout preserving ChatGPT access, and grant revocation
preventing renewal. After RLS is configured, test allowed reads and cross-user
isolation using two real accounts. No live OAuth or RLS verification is claimed.

# Rate limiting

The server uses FastMCP's token-bucket middleware, configured in
`src/middleware/rate_limiter/rate_limiter.py`. Each authenticated user can
make a burst of 15 MCP requests, with capacity replenishing at 5 requests per
second. New sessions or tokens for the same user share the allowance.
Tool calls and other MCP requests (including initialization and tool discovery)
consume capacity; notifications do not.

Optional `.env` settings override the defaults:

```dotenv
MCP_RATE_LIMIT_PER_SECOND=5
MCP_RATE_LIMIT_BURST=15
```

Restart the server after changing these settings. Both must be positive; burst
must be an integer. Excess requests receive an MCP rate-limit error (`-32000`),
not an HTTP 429; clients should pause before retrying.

Limits are in memory per server process and reset on restart. They are not
shared across workers or replicas. HTTP authentication still rejects invalid
tokens before this middleware; this is not an IP-based HTTP traffic limiter.
Local calls without an authenticated token share one fallback allowance.

# Local Testing

Run all automated tests with `./run_tests.sh`. The script uses uv to install
development dependencies and run pytest. Pass pytest options as needed, for
example `./run_tests.sh -v` or `./run_tests.sh -k course_details`.

# Catalog tools

All tools are read-only and return TOON. Restart the server after adding tools.

| Tool | Purpose |
| --- | --- |
| `list_programs()` | Discover valid program and school filters. |
| `course_codes(program?, school?, program_name?)` | List codes using exact filters. |
| `course_details(codes)` | Retrieve or compare courses with program, school, prerequisites, aligned metadata fields, and explicit unmatched codes. |
| `compare_courses(codes)` | Deprecated alias of `course_details(codes)` kept for backward compatibility. |
| `search_courses(query, program?, school?, limit=20)` | Search codes, programs, schools, titles and descriptions; all query words must match, ignoring case. |
| `program_overview(program, limit=20, offset=0)` | Get counts, schools, names and a page of course records. |
| `find_similar_courses(code, limit=10)` | Rank related descriptions by word-frequency cosine similarity. |
| `check_prerequisites(code, completed_codes)` | Check the prerequisites column's required/alternative groups against completed courses. |
| `courses_unlocked_by(code, limit=20)` | Find possible follow-on courses listing the code in the top-level `prerequisites` JSON groups' `courses` arrays. |

New discovery tools accept limits from 1 to 100. Program and school filters are
exact matches; input codes in course details, similarity and prerequisite tools
ignore case and normalize whitespace. Missing metadata remains missing.
Similarity does not establish course equivalence or transfer credit.

Both prerequisite tools read the top-level `prerequisites` column, not metadata
or description text. `check_prerequisites` requires every course in a `required`
group and at least one in an `alternative` group; all groups must be satisfied.
It returns per-group results and `course_requirements_met` (true, false, or null
when unresolved). An empty array means no stored course prerequisites; missing,
malformed, or unknown groups remain unresolved. `not_completed_references` can
include unused alternatives and is not a list of missing requirements.
Overall enrollment eligibility stays `unverified`; grades, permission, and other
non-course conditions are not evaluated. Original prerequisite groups are preserved.
`courses_unlocked_by` scans all catalog rows, matches complete codes in the
`prerequisites` column (ignoring case and normalizing whitespace), and preserves
the stored groups and their types. It returns candidates rather than confirmed
unlocks: additional prerequisite groups may still need to be satisfied. The
`total_candidates` count includes all matches; `limit` caps the returned list.

Discovery currently reads catalog pages and processes them in Python without
database migrations, embeddings or external AI services. Search and overview
apply supplied program/school filters in the database; other discovery tools
scan the catalog. Large catalogs may need database-side search and indexing.

## Vectorization and similarity limitations

Currently, **only `find_similar_courses` uses vectorization**. It lowercases
descriptions, splits them into words, removes short words and a small set of
common words, and builds word-frequency vectors. It then ranks courses by
cosine similarity between those vectors. No semantic embedding model is used.

This is a vocabulary-overlap baseline, not a measure of meaning or educational
equivalence. It can miss related topics expressed with different words and
overrate descriptions that share generic academic language. It does not
understand negation, course level, or learning objectives. Treat its scores as
word-overlap signals, not confidence scores for course recommendations.
The tool fetches the catalog and recomputes these vectors on every call;
vectors are not currently cached or stored in the database.

`search_courses` uses case-insensitive keyword matching, not vectorization or
semantic search. The course details, overview, and prerequisite tools do not use
vectorization either.

Planned improvement (not implemented): generate semantic embeddings for course
descriptions, store them in Supabase with pgvector, and regenerate them only
when the description or embedding model changes. Course-to-course similarity
could then query stored vectors without generating embeddings on each request.
Any future semantic text search would also need to embed the user's query.
Embedding-based results would still need relevance checks and would not establish
course equivalence, transfer credit, or enrollment eligibility.

# Deployment 
- Plan is to deploy on Cloudflare
