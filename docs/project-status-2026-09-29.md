# Courses project status — September 29, 2026

## Contents

1. [Executive diagnosis](#executive-diagnosis)
2. [Scope and repository state](#scope-and-repository-state)
3. [Committed changes, chronologically](#committed-changes-chronologically)
4. [Local migration: before and after](#local-migration-before-and-after)
5. [Complete MCP capability inventory](#complete-mcp-capability-inventory)
6. [Complete website flow inventory](#complete-website-flow-inventory)
7. [Architecture and configuration dependencies](#architecture-and-configuration-dependencies)
8. [Prioritized execution backlog](#prioritized-execution-backlog)
9. [Explicitly deferred scope](#explicitly-deferred-scope)
10. [Verification and limitations](#verification-and-limitations)
11. [File-by-file working-tree appendix](#file-by-file-working-tree-appendix)

## Executive diagnosis

The project has a working catalog-tool implementation and a real Supabase account website. Its local working trees contain a substantial, uncommitted migration from developer-issued JWTs to Supabase OAuth. The immediate work is to reconcile documentation, preserve the migration as a reviewable change, configure the shared provider and public endpoints, and verify the complete assistant connection. Local tests pass; production readiness and deployed OAuth compatibility have not been established.

Three distinctions prevent misleading conclusions:

- **Committed versus local:** checking out either recorded HEAD does not reproduce all OAuth behavior described here. New, untracked authentication and consent files are essential parts of the migration.
- **Implemented versus configured:** token verification, consent, grant management, and request-specific database clients exist in code. Supabase OAuth settings, hook installation, audience-array compatibility, RLS policies, and live assistant behavior remain unverified.
- **Current versus planned:** website `PRODUCT.md` still describes a starter/demo and future manual token issuance. The current code already supports real accounts and locally implements provider-issued OAuth. Transcript processing is explicitly deferred, not a missing MVP prerequisite.

The old MCP token-generation utility remains in the repository, but its locally signed tokens cannot authenticate against the new OAuth server. The website neither issues MCP credentials nor stores an assistant's access or refresh tokens. Supabase owns issuance and grants; the assistant owns its token lifecycle.

## Scope and repository state

This report covers the sibling repositories `courses-mcp` and `courses-website` as inspected on **2026-09-29**. Paths below are relative to the named repository. Evidence includes current README files, website `PRODUCT.md`, source, local Git history/diffs, and checks run during this audit. No private environment values are reproduced.

| Repository | Local branch / HEAD | Tracking relationship | Working-tree scope before this report |
| --- | --- | --- | --- |
| MCP | `main`, `5e34e53` | Equal to local `origin/main` | 16 modified tracked files; 549 insertions, 372 deletions; six untracked files |
| Website | `feat/mcp-token-gen`, `6674f0e` | One commit ahead of local `origin/feat/mcp-token-gen` | Five modified tracked files; 72 insertions, 46 deletions; five untracked files |
| Website main | `main`, `6ad12f3` | Equal to local `origin/main` | Not the checked-out branch |

**Remote-tracking refs were not freshly fetched.** “Ahead” and “equal” describe local reference comparisons, not current GitHub state. Diff totals exclude untracked content and this document. Branch name `feat/mcp-token-gen` does not establish that the website generates tokens.

Neither repository had staged changes. The MCP audit recorded 26 commits, four recorded remote branches merged into main, and no tags. Three retained stashes are separate from active changes: MCP `stash@{0}` is WIP on `feat/mcp-auth` at `e0ae205`, and `stash@{1}` is WIP on `fix/dependancy-bugs` at `ae27145`; their stats reflect older authentication work. Website `stash@{0}` is WIP on `main` at `0462dba`, with README-only changes in its stats. None was applied or deleted. Review their contents before any cleanup.

## Committed changes, chronologically

### MCP

| Date | Commits | Delivered change |
| --- | --- | --- |
| Sep 16 | `ff3afab` | Initial repository. |
| Sep 21 | `c8f6378`, `7c959f0`, `52b0c10` | Source/test layout, Supabase and environment dependencies, database connector. |
| Sep 22 | `29f3d2b` | Initial program discovery, course-code and detail tools; unit tests and test runner. |
| Sep 23 | `68c9d1e`, merge `1a2c653` | Move from stdio to streamable HTTP and merge MVP tools. |
| Sep 23 | `d7f5b7b`, `e0ae205`, `ebe17d8`, `ae27145`, merge `c2180ca` | README cleanup, branch integration, uv startup entry point, cached Supabase client and related tests. The cache is superseded locally. |
| Sep 23–24 | `eadf94f`, `6b9e269`, `3d6370e`, `e999ca7`, merge `cde0153` | Manual JWT authentication, generation instructions, configurable issuer/audience. This authentication model is superseded locally. |
| Sep 24 | `e10b6e8` | Expanded discovery, search, overview, prerequisite-related tools and description similarity. |
| Sep 24 | `b3766e7`, `ff88a02` | Token-bucket limits: five requests/second, burst 15; advisor instructions for tool use and evidence boundaries. |
| Sep 24 | `647feb4`, `f845c07` | Correct prerequisite semantics, remove redundant tooling, document discovery. |
| Sep 24 | `a4d9847`, `412aea5` | Restore deprecated `compare_courses` compatibility alias; describe course details as retrieval. |
| Sep 24 | `279c1c7`, merge `5e34e53` | Integrate rate-limiting branch into current main. |

### Website

| Date | Commits | Delivered change |
| --- | --- | --- |
| Sep 23 | `25614d3`, `0462dba` | Initial README and stack documentation. |
| Sep 24 | `f550c0c`, `0d7b32d` | Select Next.js; establish Bun application scaffold. |
| Sep 25 | `a41ff4d` | Import Figma-derived interface, landing page and sample course presentation. |
| Sep 28 | `610324b` | Next.js API organization, health endpoint and backend documentation. |
| Sep 28 | `87c7911` | Supabase sign-in/signup, sessions and callback integration. |
| Sep 28 | `aa1772d`, merge `6ad12f3` | Account deletion and sign-in branch integration. |
| Sep 28 | `6674f0e` | Replace demo token-generation presentation with configured public MCP URL; current feature-branch HEAD. |

None of the local OAuth additions below is represented by a new commit in the recorded HEAD history.

## Local migration: before and after

| Area | Committed baseline | Current local implementation |
| --- | --- | --- |
| Authority | Locally signed RS256 developer JWT, local public-key file, custom `courses:read` scope | Supabase issuer/JWKS, ES256 or RS256, resource-bound audience; `openid offline_access` advertised |
| Identity | Developer identity in issued tokens | Verified UUID user subject plus project issuer; non-anonymous authenticated account and provider-issued OAuth client ID required |
| Server construction | Authentication/server factory in token utility | Factory in `src/server.py`; dedicated config, identity and provider modules |
| Database | Cached shared Supabase client | Scoped client carrying verified request token and publishable key, with explicit HTTP cleanup and no persisted session |
| Rate-limit key | Previous developer/client-oriented identity | Project issuer plus user UUID, shared across that user's tokens and sessions |
| Tool registration | Existing read-only tools | Same nine tool names with OAuth security metadata and scoped database access |
| Website setup | Public URL and prototype connection presentation | Public URL plus real OAuth grant listing/revocation; no simulated credential issuance |
| Login return | Ordinary callback to application | Restricted consent return path preserving `authorization_id` through signup/Google callback |
| Consent | Absent | `/oauth/consent`, account gate, provider request details, approve/deny and validated provider redirects |
| Provider setup | Manual key/token instructions | Audience-hook SQL templates and OAuth configuration guidance |

The verifier checks issuer, signature, algorithm, expiry, not-before timing, canonical audience, UUID subject, `role: authenticated`, `is_anonymous: false`, and a nonempty printable client ID without surrounding whitespace. Ordinary website-session tokens, anonymous-user tokens, ID tokens and legacy locally signed tokens are not accepted as MCP authorization. The token utility remains available for local legacy use; it is not a fallback access route.

The migration does **not** install database policies, provision a Supabase project, deploy either service, add persistent usage accounting, or implement student academic storage. `src/middleware/sessions/init_session.py` is empty; its presence does not establish a session-storage feature.

## Complete MCP capability inventory

Sources: `src/tools/catalog.py`, `src/tools/discovery.py`, `src/middleware/auth/system_prompt.py`, and `README.md`. There are **nine registered names and eight unique operations**. All tools are read-only and encode responses as TOON.

| Tool / inputs | Implemented behavior and boundary |
| --- | --- |
| `list_programs()` | Lists distinct valid program identifiers, program names and schools; paginates stored rows and omits blank program identifiers. |
| `course_codes(program?, school?, program_name?)` | Requires at least one nonempty filter; combines supplied exact matches and returns sorted distinct codes across pages. |
| `course_details(codes)` | Retrieves one or multiple courses with program, school, metadata and prerequisite evidence; normalizes input code case/whitespace, aligns metadata keys and reports unmatched codes. Supports comparisons by returning evidence, not by making an equivalency judgment. |
| `compare_courses(codes)` | Deprecated compatibility alias of `course_details`; not an additional comparison engine. |
| `search_courses(query, program?, school?, limit=20)` | Case-insensitive keyword search across codes, program/school fields, titles and descriptions; all query words must match. Returns ranked matches and total count. Optional database filters are exact. |
| `program_overview(program, limit=20, offset=0)` | Program count, names, schools, course summaries and pagination/next offset. |
| `find_similar_courses(code, limit=10)` | Word-frequency cosine similarity over descriptions, after normalization and stop-word/short-word removal. Recomputes vectors each call; no semantic model, stored vectors or embedding cache. |
| `check_prerequisites(code, completed_codes)` | Evaluates top-level stored JSON groups: every course in required groups, at least one in alternative groups, all groups satisfied. Returns evidence and tri-state course-requirement result. |
| `courses_unlocked_by(code, limit=20)` | Scans top-level prerequisite groups for complete normalized course-code references; returns possible follow-on courses, original groups and total candidates. Other requirements may remain unmet. |

Discovery limits are 1–100. Missing metadata stays missing. An empty prerequisite array represents no stored course prerequisites; missing, malformed or unknown groups remain unresolved. `not_completed_references` can include unused alternatives and must not be interpreted as unmet requirements. Enrollment eligibility stays `unverified`: grades, permissions and other conditions are not evaluated.

Only similarity uses vectorization, and that vectorization measures vocabulary overlap. Search is lexical. Neither tool establishes educational equivalence, transfer credit, live availability or suitability. The advisor prompt instructs clients to distinguish facts from recommendations, resolve course ambiguity, preserve prerequisite uncertainty and avoid inventing schedules, seats or degree applicability. Instructions guide assistant behavior; they do not add data or enforcement capabilities.

Search/overview apply supported filters in Supabase, then process records in Python; other discovery operations can scan the catalog. Discovery fetches paginated data but processes the full retrieved result set before limiting returned matches. Pagination does not remove that cost.

Rate limiting covers authenticated MCP requests, including initialization/discovery, at five requests/second and burst 15 by default. Notifications do not consume capacity. Excess requests receive MCP error `-32000`, not HTTP 429. Buckets are process-local, reset on restart and are not shared across replicas. Unauthenticated local calls use a shared fallback; HTTP authentication remains separate.

## Complete website flow inventory

Sources: `app/`, `components/`, `lib/supabase/`, `lib/server/`, `proxy.ts`, `data/courses.ts` and `README.md`.

| Flow | Code state and remaining boundary |
| --- | --- |
| Public landing | Imported Coursebook design, introductory content, sign-in navigation and animated ticker. Thirty sample course records are static; this is not a live catalog browser. “How it works” has no action. |
| Screen navigation | Landing, sign-in and profile selected through React state on `/`; they do not each have an independent URL. Consent has its own route. |
| Email signup | Email/password and full name; name saved in Auth metadata. Supports confirmation-required and immediate-session configurations. |
| Email login | Supabase credential submission, pending/error states and profile transition. Live credentials/email delivery were not tested. |
| Google login | Provider sign-in and callback wiring; external provider configuration remains necessary. |
| Confirmation/callback | `/auth/callback` exchanges code for cookie-backed session; safe consent return carries authorization request across login. Invalid/expired exchanges display an error. PKCE confirmation requires the originating browser's verifier cookie. |
| Session restoration | Server `getUser()` verifies initial user; proxy refreshes cookies and client auth events update the UI. Proxy is not route authorization. |
| Profile | Displays metadata name, falling back to email; avatar account menu and MCP panel. No profile editor, academic-context tab or stored transcript. |
| MCP setup | Configured endpoint and example prompt can be copied; missing endpoint disables URL copy, clipboard failures offer manual copying. Copying does not connect an assistant. |
| OAuth consent | Requires real non-anonymous account; loads provider authorization request, displays client/account, return address and scopes; approves or denies through Supabase. Expired/missing requests require restart. Existing grants may produce provider redirects. |
| Consent protections | Restricts post-login return to local consent route; rechecks account before decisions; uses provider-returned redirect URLs with scheme/credential checks. Client names are labeled developer-supplied. |
| Connected apps | Lists actual Supabase OAuth grants, including loading, empty, failure/retry and pending states. Disconnect rechecks account and revokes selected client grant. A grant alone does not prove MCP reachability. |
| Sign out | Local website logout with failure handling; does not revoke assistant authorization. |
| Delete account | Avatar menu → confirmation dialog with Cancel initially focused → `DELETE /api/account`. Checks Origin and verified current user; server-only admin client deletes that Auth account. Errors preserve screen/session; success clears browser cookies and reloads landing. |
| Health | `GET /api/health` returns `{"status":"ok"}`; it does not check Supabase or MCP. |

Account deletion currently concerns Supabase Auth and its metadata. There is no profile table, academic store or transcript cleanup implementation to claim. Already-issued access tokens may remain usable until expiry even after disconnect or account deletion. The website does not maintain an immediate JWT revocation list.

## Architecture and configuration dependencies

The website is one Next.js application with server routes, not a separate frontend plus API deployment. Its package manifest uses Next.js 16.3.6, React 19.2.8, TypeScript, Tailwind 4, Bun, `@supabase/ssr` and `@supabase/supabase-js`. Server-only privileged code is isolated under `lib/server/`.

MCP uses Python ≥3.13, uv, FastMCP, Supabase, PyJWT crypto, python-dotenv, TOON and newly explicit httpx. It listens on `127.0.0.1:8000` over HTTP behind a public HTTPS proxy/tunnel. Supabase supplies accounts, authorization metadata, consent-request state, code/PKCE exchange, refresh and signing keys; MCP publishes resource metadata and the unauthenticated discovery challenge.

```text
Assistant → public MCP /mcp → OAuth discovery → Supabase
                                               ↓
                                  website /oauth/consent
                                               ↓
                                   login + approve/deny
                                               ↓
Assistant ← provider code/token exchange ← Supabase
Assistant → MCP token verification → per-request Supabase database client
```

The nonnegotiable configuration invariant is:

```text
website NEXT_PUBLIC_MCP_URL
  = MCP_PUBLIC_URL + "/mcp"
  = resource audience configured in the SQL hook
```

All participants must use the same Supabase project. `MCP_PUBLIC_URL` is an HTTPS origin without a path, query or credentials; the canonical endpoint includes `/mcp` without a trailing slash. A changed tunnel hostname requires coordinated updates. Website `NEXT_PUBLIC_` values are bundled at build time, so deployed URL changes require rebuilding.

| Component | Configuration dependency |
| --- | --- |
| MCP | `SUPABASE_URL`, publishable key, `MCP_PUBLIC_URL`, matching ES256/RS256 algorithm; optional positive finite rate and positive integer burst overrides |
| Website browser/SSR | Public Supabase URL/publishable key and full public MCP endpoint |
| Account deletion | Server-only `SUPABASE_SECRET_KEY`, with legacy service-role fallback; never browser-public configuration |
| Supabase Auth | Website Site URL, OAuth Server enabled, `/oauth/consent` authorization path, allowed callback/return URLs, asymmetric signing key, dynamic or manual OAuth client registration and exact callbacks |
| Audience hook | Reviewed installation, canonical resource replacement, integration with any existing hook, and activation in Auth settings |
| Database access | Verified user token forwarded with publishable key; database grants/RLS determine actual allowed rows |

The SQL templates add `aud: ["authenticated", canonical-resource]` for authenticated, non-anonymous OAuth tokens with provider client IDs; ordinary website sessions retain their audience. Other claims are preserved. The general template aborts installation if its placeholder remains. The ngrok copy is environment-specific review material, not evidence it has run. Initial issuance, refresh issuance, hook acceptance and PostgREST audience-array compatibility still need deployed verification.

The hook applies to **every qualifying OAuth client in the project**, not a client allowlist. Confirm that this is the intended access policy before installation; this observation alone does not establish a vulnerability. Remote hook, deployment and RLS state are **unknown**. No repository-defined RLS policies or versioned course schema/index/ingestion/freshness contract were found; that does not prove they are absent remotely.

OIDC scopes do not confer row permissions. Request-specific clients expose identity to future RLS policies but do not create isolation. Website logout, grant revocation and access-token expiry are distinct lifecycle events.

## Prioritized execution backlog

Categories: **documented plan** means a repository statement; **external verification** means a provider/deployment check; **recommended improvement** is this review's suggestion, not an invented product obligation. Execute P0 in order, with policy verification completed before exposing private data.

| Priority / category | Action and evidence | Dependency | Definition of done |
| --- | --- | --- | --- |
| P0.1 — recommended improvement | Reconcile `PRODUCT.md`, old `README 2.md`, and `lib/server/README.md` (“No services exist yet” despite admin client); replace “get your token” in `components/landing-page.tsx:61` and align hosting/JWT guidance. | Agree current product scope. | Docs/copy match Auth/OAuth implementation and verification limits; transcript deferral retained. |
| P0.2 — recommended improvement | Review and commit the complete migration across both repos; appendix identifies untracked runtime dependencies. | Documentation reconciliation and code review. | Reproducible commits include required source/tests/templates, exclude private env/keys, and identify compatible repo revisions. |
| P0.3 — external verification | Choose canonical reachable HTTPS URLs; configure same-project OAuth, signing keys, callbacks and client registration. Evidence: both READMEs and `auth/config.py`. | Host/tunnel and provider access. | Exact URL invariant recorded; metadata/discovery and callback routing work with the intended client. |
| P0.4 — external verification | Confirm intended all-client audience policy; review/install/enable hook, preserving any existing hook. | P0.3 and owner access-policy decision. | Initial/refreshed tokens have correct audience/claims; website sessions unchanged; MCP and database accept intended tokens. No tokens logged. |
| P0.5 — documented plan + external verification | Owner configures RLS and checks access. Both READMEs explicitly defer policy installation/testing. | Data-access model and P0.4. | Intended shared catalog reads succeed; two-account tests prove appropriate isolation for any user-owned/private rows and rejected unauthorized access. |
| P0.6 — external verification | Run complete account-to-assistant acceptance sequence. | P0.3–5 as applicable. | Signup/confirmation, email/Google login, approve/deny, code exchange, tool calls, refresh/restart, website logout, disconnect and post-revocation renewal behave as documented; record token-expiry window. |
| P1.1 — documented plan + external verification | Select and validate deployment. MCP README plans Cloudflare; website README names Cloudflare but also Vercel/Cloudflare. Default `next.config.ts`; no deployment/CI configuration observed. | Compatible hosting/runtime decision. | Production build passes, deployment settings are documented, HTTPS services and routes are verified; restart/rollback process is executable. |
| P1.2 — recommended improvement | Add component-level consent/disconnect tests; browser acceptance/accessibility across login, grant retry, clipboard and delete dialog. Current OAuth tests focus on helpers. | Configured test environment. | Allow/deny/revoke interactions and failure/account-change states tested; keyboard/focus/responsiveness checked; disposable deletion verified. |
| P1.3 — recommended improvement | Resolve inert “How it works”; explain `offline_access` in consent rather than raw fallback scope text. | Copy/product choice. | Button has intended behavior or is removed; refresh-access meaning is clear. Small polish, not an OAuth blocker. |
| P1.4 — documented plan | Decide final product name; README explicitly requests rename before launch. | Owner naming decision. | Visible copy, metadata and docs consistently use approved name without unsupported affiliation claims. |
| P1.5 — recommended improvement | Add CI for existing tests, type checking, lint and production build; no repository CI configuration found. | Selected supported runtimes and release process. | Clean-checkout pipeline runs required checks and distinguishes application failures from bundled-script warnings. |
| P1.6 — recommended improvement + external verification | Test JWKS rotation/unavailability, Supabase/database outages, timeouts and recovery. Local passing tests do not establish deployed resilience. | Staging environment and controlled failure scenarios. | Invalid/unverifiable tokens remain rejected; failure/recovery and key-cache behavior are recorded without credential logging or authentication bypass. |
| P2.1 — documented plan | Evaluate semantic embeddings stored in Supabase/pgvector. MCP README describes this future improvement. | Relevance baseline, cost/model decision, schema/refresh design. | Measured retrieval improvement; regeneration keyed to description/model changes; equivalence limitations retained. |
| P2.2 — recommended improvement | Load-test scans before result limiting and repeated similarity work. Details/code lists lack bounds; search/follow-on lack offset/cursors. Consider bounded responses/pagination if measurements justify them. | Representative data, concurrency and agreed performance targets. | Latency, memory and payload measurements justify indexing/caching/bounds; result correctness and permissions preserved. |
| P2.3 — recommended improvement | Add durable usage metrics or distributed limits only if usage tracking/multiple replicas are selected. Stale PRODUCT mentions usage tracking; current limits are in memory. | Product decision, retention policy, deployment topology. | Agreed usage semantics and cross-replica behavior tested; no claim of current persistence. |
| P2.4 — recommended improvement | Document/version course schema, indexes, ingestion and freshness contract; none found in repository evidence. | Data-owner decisions and inspection of actual database/ingestion setup. | Field/prerequisite semantics, provenance, refresh ownership and freshness expectations are documented; required schema/index changes become reproducible. |

Optional password recovery, profile editing, live seats/schedules, degree-audit features and independent screen URLs require product decisions. They are not established launch obligations. CI and operational monitoring are reasonable follow-up recommendations once a deployment target and release process are selected.

An IP/HTTP traffic limiter is also a deployment-dependent recommendation: the existing user-level MCP limiter is not that protection. Replacing the placeholder `pyproject.toml` description and clarifying the legacy generator's status are low-priority maintenance tasks.

### Ordered live acceptance checklist

Use disposable accounts and the intended assistant client; record outcomes without token contents.

1. [ ] Start logged out; add the canonical MCP endpoint and verify the unauthenticated discovery/authorization path.
2. [ ] Sign up and confirm email, or use Google; verify the same authorization request survives login/callback. Repeat with an existing account.
3. [ ] Deny a request and confirm no connection; restart, allow, and complete provider code/PKCE exchange.
4. [ ] Run `list_programs` and a course query successfully against intended data.
5. [ ] Verify wrong-audience, ordinary-session and anonymous tokens are rejected; never weaken audience validation to pass.
6. [ ] Refresh access and reconnect after client restart; validate refreshed audience and database access.
7. [ ] Log out of the website; verify the assistant remains authorized.
8. [ ] Sign back in and disconnect; verify further refresh fails. An already-issued JWT may work until expiry.
9. [ ] With two users, verify intended shared catalog reads and isolation/denial for any private records under actual deployed policies.
10. [ ] Cancel then confirm disposable account deletion; verify Auth removal, cleared website session and defined assistant/token-expiry behavior.

## Explicitly deferred scope

Website `PRODUCT.md` explicitly says future unofficial-transcript upload, parsing, student review and submission must **not** be implemented now. No upload UI, parser, Storage integration, academic record schema or transcript deletion workflow exists. The imported export also lacks the future academic-context tab; an empty personalization page remains a stated historical scope item, not a delivered flow.

If that scope is later approved, it needs its own storage, consent, retention, correction, RLS and deletion design. It must not block the present OAuth/catalog milestone. Conversation-provided completed courses already support prerequisite checks without transcript storage.

## Verification and limitations

Checks run during this audit:

| Check | Reported result | What it establishes |
| --- | --- | --- |
| MCP pytest | 78 tests plus 14 subtests passed; one AnyIO deprecated-alias warning | Local authentication, connection isolation, catalog/discovery and rate-limit regression coverage |
| Website `bun test tests/` | 17 tests, 67 assertions passed | Mocked callback, account deletion and OAuth helper behavior |
| Website lint | Zero errors, 94 warnings, all in bundled `.agents/skills/impeccable/scripts` | No reported application-source lint failures; warnings remain in bundled skill scripts |
| `./node_modules/.bin/tsc --noEmit --incremental false` | Passed | Local TypeScript type checking |
| MCP `git diff --check` | Passed | No tracked-patch whitespace errors reported |
| Production build | Not run | No production compilation/rendering or deployment compatibility claim |
| Live services | Not checked | No live signup/email/Google, OAuth hook, audience-array, database/RLS, ChatGPT or deployment verification claim |

Mocked and local tests do not prove the deployed configuration or provider token-hook compatibility. Source inspection supports implementation claims, not successful integration. No private env values were inspected for this report, and no SQL was installed, live account deleted, service deployed or remote refs fetched.

## File-by-file working-tree appendix

`M` = tracked modification; `?` = untracked at initial inspection. This appendix describes the local migration, not every unchanged file in either repository.

### MCP: 16 tracked modifications

| Status / file | Change |
| --- | --- |
| M `.env.example` | Replace manual JWT configuration with OAuth project/resource/signing settings. |
| M `README.md` | OAuth setup, hook, lifecycle, scoped DB access and verification boundaries. |
| M `pyproject.toml` | Explicit httpx dependency. |
| M `src/db/connection.py` | Remove global cached client; scoped verified-user client and HTTP cleanup. |
| M `src/middleware/auth/generate_bearer_token.py` | Remove server factory/auth setup; retain legacy token utility. |
| M `src/middleware/rate_limiter/rate_limiter.py` | User identity bucket derived from verified issuer/subject. |
| M `src/server.py` | Build OAuth server with middleware, instructions and tool provider. |
| M `src/tools/catalog.py` | OAuth metadata; scoped database contexts for catalog operations/alias. |
| M `src/tools/discovery.py` | OAuth metadata and scoped catalog reads. |
| M `tests/test_auth.py` | OAuth verifier/configuration/discovery and rejection regression coverage. |
| M `tests/test_connection.py` | Request isolation, forwarded identity and resource lifecycle coverage. |
| M `tests/test_course_codes.py` | Adapt database mocks to context-managed client. |
| M `tests/test_course_details.py` | Adapt database mocks to context-managed client. |
| M `tests/test_discovery.py` | Adapt discovery database fixture. |
| M `tests/test_rate_limiter.py` | Authenticated-user identity behavior. |
| M `uv.lock` | Dependency declaration lock update. |

### MCP: six pre-existing untracked files

| File | Purpose |
| --- | --- |
| `AGENTS.MD` | Project editing/delegation instructions. |
| `src/middleware/auth/config.py` | Validate HTTPS origins and signing algorithm; derive issuer/resource. |
| `src/middleware/auth/identity.py` | Read verified token, normalize UUID and form rate identity. |
| `src/middleware/auth/provider.py` | Supabase verifier/provider and shared tool security metadata. |
| `supabase/mcp_access_token_hook.sql` | General audience-hook installation template. |
| `supabase/mcp_access_token_hook.ngrok.sql` | Environment-specific hook copy for review; not installation evidence. |

This report adds `docs/project-status-2026-09-29.md`; it is excluded from the baseline counts above.

### Website: five tracked modifications and five untracked files

| Status / file | Change |
| --- | --- |
| M `README.md` | Explain consent, account/grant lifecycle and remaining live checks. |
| M `app/auth/callback/route.ts` | Resume only approved local consent return path. |
| M `components/mcp-tab.tsx` | Integrate actual connected-app management and revised setup instructions. |
| M `components/sign-in-page.tsx` | Preserve consent destination through signup/Google and notify successful authentication. |
| M `tests/auth-callback.test.mjs` | Consent-return callback regression test. |
| ? `app/oauth/consent/page.tsx` | Dedicated consent route and request parameters. |
| ? `components/connected-apps.tsx` | Load/retry/revoke grants with account checks and feedback. |
| ? `components/oauth-consent.tsx` | Account-gated request details and approve/deny interface. |
| ? `lib/supabase/oauth.ts` | Safe return/redirect helpers and verified-account/grant checks. |
| ? `tests/oauth.test.mjs` | OAuth helper and account validation regression coverage. |

Unchanged but important evidence: website `PRODUCT.md` and `README 2.md` need reconciliation; `data/courses.ts` remains sample content; `next.config.ts` remains default; MCP `system_prompt.py` supplies advising boundaries and `sessions/init_session.py` remains empty.
