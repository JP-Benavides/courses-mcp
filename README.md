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

- You can also run this instead if you want a token with a specific validity period (in hours).
```bash
uv run python -m src.middleware.auth.generate_bearer_token jp --hours 720 
```

**Start the server.**

```bash
uv run src/server.py
```

Generate your bearer token and configure it in your MCP client separately.

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

# Rate limiting

The server uses FastMCP's token-bucket middleware, configured in
`src/middleware/rate_limiter/rate_limiter.py`. Each authenticated developer can
make a burst of 15 MCP requests, with capacity replenishing at 5 requests per
second. New sessions or tokens for the same developer share the allowance.
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
