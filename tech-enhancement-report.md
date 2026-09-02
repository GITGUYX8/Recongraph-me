# Tech Enhancement Report — ReconGraph

**Date:** 2026-09-03
**Evaluation Lens:** ReconGraph is being evaluated as an enterprise financial reconciliation platform deployed on-premises for fewer than 100 users, with no protected technology choices. The priority is auditability, security, operational reliability, and maintainability for a small user population, not internet-scale throughput. Recommendations therefore favor a cohesive single-deployment architecture and proven components over additional distributed infrastructure.

---

## Executive Summary

- **CRITICAL:** Authentication is not production-safe: credentials are hard-coded (`admin/admin`, `auditor/auditor`), the JWT signing key is committed in source, and the API lacks a real user store or key rotation path (`recongraph-api/app/main.py:202-216`, `recongraph-api/app/auth.py:10`).
- **CRITICAL:** Authorization is incomplete. `/runs/{run_id}`, `/demo`, `/version`, and `/export/{run_id}` can be reached without the same auditor dependency used elsewhere, and the run lookup does not enforce tenant ownership. This is a direct Broken Object Level Authorization risk.
- **HIGH:** Persistence is split between raw `sqlite3`, a custom SQLite `Store`, and an unused SQLAlchemy/Alembic model layer. Standardize on PostgreSQL plus SQLAlchemy/Alembic for production, while retaining SQLite only for local tests.
- **HIGH:** `BackgroundTasks` and process-local `_runs_store` are not a durable job system. Use a real worker queue only if reconciliation is long-running; otherwise make the operation synchronous with a bounded request and persist status transactionally. Celery/Redis are currently installed but not wired.
- **HIGH:** The advertised deployment paths conflict with the stated on-prem target. Render/Vercel are demo deployment instructions; the production workflow references missing `requirements.txt` and `docker-compose.prod.yml`, then contains placeholder registry/Kubernetes commands.
- **HIGH:** The AI/vector stack is valuable for the copilot but over-provisioned for deterministic reconciliation. Keep Qdrant and Sentence Transformers behind an optional `ai`/`rag` install boundary; do not make every API installation pay the PyTorch/model cost.
- **MEDIUM:** MLflow and Evidently are useful for model lifecycle and drift investigations, but neither is a runtime dependency for the core API. Run them as training/operations tooling with a separately configured tracking store.
- **REMOVE:** The duplicate legacy export/run path, unused async database module, and unused Celery/Redis runtime dependencies should be removed or completed; dead alternatives are currently more dangerous than helpful.

---

## Current Stack Inventory

### Core Framework
- **Current:** Python 3.11+ package (`recongraph` 2.0.0), FastAPI 0.111.0, Uvicorn 0.29.0, Next.js 16.2.12 with React 19.2.4.
- **Usage:** The domain engine lives under `src/recongraph/`; the API is a separate application under `recongraph-api/app/`; the dashboard is a separate Next.js App Router application under `recongraph-ui/src/`.
- **Assessment:** FastAPI and the separated UI fit the platform. The domain package is sensibly modular and deterministic. The current deployment is a split demo topology rather than a cohesive on-prem production topology.

### Data Layer
- **Current:** Custom `sqlite3` `Store` at `recongraph-api/app/store.py`, direct SQLite feedback DB in `app/main.py`, plus SQLAlchemy 2.0.30, asyncpg, and Alembic 1.13.1 in `recongraph-api/requirements.txt`.
- **Usage:** `Store` persists runs/actions; `init_db()` creates `hitl_feedback.db`; `app/database.py` defines an async SQLAlchemy model but is not used by the request handlers; `scripts/01_enable_rls.sql` suggests a PostgreSQL/RLS direction.
- **Assessment:** SQLite is acceptable for a single-process prototype, but it is not a coherent enterprise persistence boundary. The duplicated paths make migrations, backups, concurrency, tenant isolation, and recovery ambiguous. PostgreSQL is the better production fit and is already anticipated by the dependency set.

### Auth
- **Current:** `python-jose[cryptography]` 3.3.0, FastAPI OAuth2 bearer helper, HS256 JWTs, hard-coded demo credentials and secret.
- **Usage:** `app/auth.py` creates/decodes tokens; only selected endpoints use `require_auditor`; the login endpoint is implemented directly in `app/main.py`.
- **Assessment:** Suitable only as a demo. For on-prem enterprise use, integrate with the organization's OIDC/LDAP/SSO provider. If local auth is mandatory, use a database-backed user store, Argon2id password hashes, secret management, short-lived access tokens, refresh/revocation controls, and explicit tenant/role checks.

### Testing
- **Current:** pytest 8+, Hypothesis 6+, mypy 1+, approximately 100 domain/API-focused tests, Python 3.11/3.12 CI matrix.
- **Assessment:** The deterministic engine has unusually strong property and adversarial coverage. Missing production tests include authenticated endpoint authorization, tenant cross-access, upload limits/encoding failures, database migrations, worker retry/idempotency, and browser/API integration.

### Infrastructure / Deployment
- **Current:** Two Dockerfiles, Render Blueprint, Vercel/Render deployment guide, GitHub Actions test workflow, and a second production workflow with placeholder Docker/Kubernetes steps.
- **Assessment:** Not aligned with on-prem deployment. Kubernetes is unnecessary for fewer than 100 users unless the organization already operates it. A versioned Compose or systemd deployment with PostgreSQL, optional Redis/Qdrant, reverse proxy, backups, and health checks is the right initial target.

### Observability
- **Current:** Standard Python logging, request IDs, MLflow tracking in training code, Evidently drift script, and copilot audit logging.
- **Assessment:** Good beginnings but no defined metrics backend, traces, alerting, log redaction policy, or operational SLOs. Request IDs alone are correlation, not observability.

### Other Significant Dependencies

| Dependency | Version | Usage Depth | Category | Maintenance Status |
|---|---:|---|---|---|
| FastAPI | 0.111.0 | heavy | API framework | active, pinned behind current releases |
| SQLAlchemy | 2.0.30 | light/incomplete | data access | active, pinned behind current 2.0 releases |
| Alembic | 1.13.1 | light | migrations | active, pinned behind current releases |
| PostgreSQL driver (`asyncpg`) | 0.29.0 | unused in handlers | database | active, currently not connected |
| Celery | 5.4.0 | dependency only | jobs | active, not wired |
| Redis client | 5.0.4 | dependency only | broker/cache | active, not wired |
| Qdrant client | 1.10.1 | moderate | vector retrieval | active, version old relative to current ecosystem |
| Sentence Transformers | 3.0.1 | moderate | embeddings/reranking | active, v5/v6 migration path exists |
| LightGBM | >=4.0 | training only | ML | active |
| MLflow | 2.15.1 | training only | experiment tracking | active, major current architecture has evolved |
| Evidently | unpinned | script only | drift evaluation | active but unpinned |
| `python-jose` | 3.3.0 | light/security-critical | JWT | aging; replace or isolate |
| Next.js | 16.2.12 | heavy | UI framework | active; current docs show 16.3.4 |

---

## Recommendations

### 1. Replace Demo Authentication With Managed Enterprise Identity — CRITICAL

**Current:** Hard-coded usernames/passwords and a source-controlled HS256 secret (`recongraph-api/app/main.py:202-216`, `recongraph-api/app/auth.py:10-23`).
**Recommendation:** Use OIDC Authorization Code + PKCE through the enterprise identity provider and validate signed JWTs using the provider's JWKS. If SSO is unavailable, implement a database-backed local identity service using Argon2id, environment/secret-manager configuration, token rotation, rate limiting, and an administrator bootstrap procedure that runs once.
**Rationale:** On-prem enterprise users still require credential lifecycle, auditability, revocation, and secret rotation. The current scheme lets anyone with repository access mint tokens and makes the demo credentials a live production backdoor. FastAPI provides security primitives, but it does not replace an identity system.

**Trade-offs:**

| Gain | Lose |
|---|---|
| SSO, centralized offboarding, MFA, and auditable identity | Identity-provider integration and operator configuration |
| No long-lived signing secret in application source | More setup than the current two-user demo |
| Better role and tenant claims | Need to test JWKS rotation and clock skew |

**Migration effort:** Medium — add OIDC configuration and issuer/audience validation, replace `/token`, then add an explicit local-auth fallback only if required.
**Evidence:** [FastAPI security documentation](https://fastapi.tiangolo.com/tutorial/security/oauth2-jwt/), [OWASP API Security Top 10](https://owasp.org/www-project-api-security/), [python-jose project](https://github.com/mpdavis/python-jose).

### 2. Enforce Object-Level and Tenant-Level Authorization Everywhere — CRITICAL

**Current:** Several run and demo endpoints are public, and `tenant_id` is accepted in JWT claims but is not used by `Store` queries. `get_run(run_id)` fetches solely by identifier.
**Recommendation:** Require authentication on every non-health endpoint, pass the authenticated tenant into every repository query, add tenant columns and composite indexes/foreign keys, and enforce ownership on runs, packets, exports, feedback, and copilot context. Use separate admin-only dependencies for administration and keep health/readiness intentionally unauthenticated.
**Rationale:** UUIDs are not authorization. This application handles financial records and explicitly claims tenant isolation in its documentation, so authorization must be applied at the data access boundary rather than selectively at route declarations. This is the highest-impact correctness/security improvement for an enterprise deployment.

**Trade-offs:**

| Gain | Lose |
|---|---|
| Prevents cross-tenant financial data exposure | Repository and test signatures must change |
| Centralized, reviewable authorization policy | Demo endpoints need an explicit demo mode or test identity |
| Enables auditable access decisions | Existing data requires tenant backfill |

**Migration effort:** Medium — add a request principal, tenant-scoped repository methods, migration constraints, and negative authorization tests.
**Evidence:** [OWASP API1: Broken Object Level Authorization](https://owasp.org/API-Security/editions/2023/en/0xa1-broken-object-level-authorization/), [OWASP API5: Broken Function Level Authorization](https://owasp.org/API-Security/editions/2023/en/0xa5-broken-function-level-authorization/).

### 3. Consolidate Production Persistence on PostgreSQL and Alembic — HIGH

**Current:** `Store` owns one SQLite connection, feedback uses another direct SQLite connection, and SQLAlchemy/Alembic models are disconnected (`recongraph-api/app/store.py`, `recongraph-api/app/main.py:86-140`, `app/database.py`).
**Recommendation:** Make PostgreSQL the sole production database, model runs, source records, derived artifacts, packet actions, feedback, users, and audit events in SQLAlchemy, and run all schema changes through Alembic. Keep a SQLite test profile only where it provides fast unit-test value. Use PostgreSQL JSONB for immutable result payloads initially, then normalize query-heavy fields.
**Rationale:** PostgreSQL supplies transactional concurrency, durable backups, mature operational tooling, and a clear place to implement tenant policies. SQLAlchemy 2 and Alembic are already present, so completing this direction is lower risk than maintaining a custom persistence layer. At this scale, one PostgreSQL instance is enough; no separate graph database is justified.

**Trade-offs:**

| Gain | Lose |
|---|---|
| Transactions, backups, concurrent workers, and reliable migrations | A database service must be operated on-prem |
| One source of truth for runs and feedback | Migration/backfill work from SQLite |
| Future row-level security and reporting queries | More schema design than JSON-only storage |

**Migration effort:** High — define canonical models, create an Alembic baseline, dual-write temporarily, verify counts/checksums, then remove direct SQLite code.
**Evidence:** [SQLAlchemy asyncio documentation](https://docs.sqlalchemy.org/en/20/orm/extensions/asyncio.html), [Alembic documentation](https://alembic.sqlalchemy.org/en/latest/), [PostgreSQL documentation](https://www.postgresql.org/docs/current/).

### 4. Choose a Durable Job Model for Reconciliation — HIGH

**Current:** `/reconcile` reads entire uploads into memory and schedules `_run_reconciliation_task` with FastAPI `BackgroundTasks`; status is also held in process-local `_runs_store` (`app/main.py:234-304`). Celery and Redis are installed but unused.
**Recommendation:** First measure actual reconciliation duration and concurrency. For fewer than 100 users, use a synchronous endpoint for small files or a PostgreSQL-backed jobs table plus one dedicated worker process for long jobs. Adopt Celery + Redis only when retries, queue isolation, scheduled work, or parallel workers are demonstrated requirements; if adopted, wire task IDs, retry policy, idempotency keys, dead-letter handling, and durable result state.
**Rationale:** Starlette/FastAPI background tasks do not provide durable delivery or recovery after process termination. A process-local status map also disappears on restart and diverges across multiple workers. The recommendation deliberately avoids deploying Redis/Celery merely because they are already in requirements.

**Trade-offs:**

| Gain | Lose |
|---|---|
| Durable status and restart recovery | Worker lifecycle and job-state complexity |
| Controlled CPU/memory isolation from HTTP requests | More deployment components if Celery is selected |
| Retry and idempotency guarantees | Need to store uploads outside request memory |

**Migration effort:** Low for a jobs-table worker; High for Celery/Redis — define job schema first, then select the queue based on measured workload.
**Evidence:** [FastAPI background task guidance](https://fastapi.tiangolo.com/tutorial/background-tasks/), [Celery introduction](https://docs.celeryq.dev/en/stable/getting-started/introduction.html).

### 5. Align the On-Prem Deployment With a Single Supported Topology — HIGH

**Current:** Documentation directs users to Vercel and Render, while the CI workflow builds missing `docker-compose.prod.yml`, installs missing root `requirements.txt`, and contains placeholder registry/Kubernetes commands (`DEPLOYMENT.md`, `.github/workflows/production.yml`).
**Recommendation:** Make on-prem Compose or systemd the supported production path: reverse proxy/TLS, API, UI, PostgreSQL, optional worker, optional Redis, and optional Qdrant on a private network. Pin image digests or build from a locked dependency set, add database backup/restore procedures, and make CI build and smoke-test the exact deployment artifact. Keep Render/Vercel explicitly labeled as demo-only.
**Rationale:** Kubernetes adds control-plane and operational cost without solving a demonstrated problem at this scale. A single host or small VM set can run this platform reliably if backups, health checks, restart policy, and patching are handled. The current production workflow creates false confidence because its deploy steps do not deploy.

**Trade-offs:**

| Gain | Lose |
|---|---|
| Reproducible on-prem deployment matching stated requirements | Less automatic horizontal scaling than Kubernetes |
| Smaller failure and operator surface | Manual or scripted upgrades |
| Easier backup, restore, and network isolation | A future Kubernetes migration if scale changes materially |

**Migration effort:** Medium — create a real production Compose file, secrets template, reverse-proxy config, backup runbook, and CI smoke test.
**Evidence:** [Next.js self-hosting guidance](https://nextjs.org/docs/app/guides/self-hosting), [FastAPI deployment concepts](https://fastapi.tiangolo.com/deployment/concepts/), [PostgreSQL backup and restore documentation](https://www.postgresql.org/docs/current/backup.html).

### 6. Make AI and Vector Retrieval Optional Runtime Capabilities — HIGH

**Current:** Core package dependencies include Anthropic, LightGBM, MLflow, Qdrant, Sentence Transformers, and Evidently. The API requirements repeat MLflow/Qdrant/Sentence Transformers even though deterministic reconciliation is the primary path.
**Recommendation:** Split extras into `ml`, `ai`, `rag`, and `ops` groups. Keep the deterministic engine and API install small; load RAG/embedding components behind explicit configuration and startup checks. For on-prem privacy, default to local embeddings and disable external LLM calls unless an operator explicitly configures an approved endpoint.
**Rationale:** Qdrant is a credible self-hosted vector engine and Sentence Transformers supports bi-encoders, cross-encoders, and sparse retrieval, but the current application should not require model downloads and PyTorch just to reconcile CSVs. The existing documentation reports Recall@5 of 60%, so adding infrastructure alone is not evidence of production quality; improve retrieval evaluation and domain data first.

**Trade-offs:**

| Gain | Lose |
|---|---|
| Smaller API image and faster cold starts | More packaging profiles and configuration paths |
| Clear privacy boundary for on-prem deployments | AI features are unavailable until explicitly provisioned |
| Deterministic core remains usable during vector/LLM outage | More integration testing between optional capabilities |

**Migration effort:** Medium — move imports/configuration behind extras, define a no-AI mode, and add startup capability reporting.
**Evidence:** [Qdrant overview and deployment options](https://qdrant.tech/documentation/overview/), [Qdrant secure self-hosting](https://qdrant.tech/documentation/tutorials-operations/secure-qdrant/), [Sentence Transformers documentation](https://www.sbert.net/).

### 7. Separate ML Experiment Tracking From Runtime Serving — MEDIUM

**Current:** MLflow is a production dependency but is used primarily in `candidate_model.py` training code; Evidently is used by `scripts/detect_drift.py`.
**Recommendation:** Move MLflow and Evidently to an `ops`/training environment. For a small on-prem team, run MLflow only when model training is active, with PostgreSQL as backend store and an on-prem artifact location. Promote a model by immutable version and record model/config hashes in decision traces.
**Rationale:** MLflow is a strong fit for reproducible training and model lineage, but embedding its server and artifact concerns in every API image is unnecessary. Evidently should generate scheduled reports or CI checks, not silently become a runtime dependency. This preserves the project's explainability goal while reducing production attack and failure surface.

**Trade-offs:**

| Gain | Lose |
|---|---|
| Smaller and more stable API runtime | Separate training/operations environment |
| Better artifact governance and model promotion | Operators must manage MLflow storage/backups |
| Explicit model reproducibility | Less convenience for ad hoc runtime experiments |

**Migration effort:** Low — move dependency groups and define model artifact/version configuration; medium if deploying a shared MLflow server.
**Evidence:** [MLflow Tracking](https://mlflow.org/docs/latest/ml/tracking/), [MLflow self-hosting architecture](https://mlflow.org/docs/latest/self-hosting/architecture/).

### 8. Replace or Isolate `python-jose` and Upgrade Pinned Dependencies — MEDIUM

**Current:** `python-jose[cryptography]==3.3.0`, FastAPI 0.111.0, SQLAlchemy 2.0.30, Qdrant 1.10.1, Sentence Transformers 3.0.1, and Uvicorn 0.29.0 are pinned to older versions; `evidently` is unpinned.
**Recommendation:** Perform a compatibility upgrade in a lockfile-based branch. Prefer a maintained JOSE implementation such as PyJWT for standard JWT validation or the OIDC provider's supported library; retain `python-jose` only if its required JWE/JWK feature set is proven. Pin all direct and transitive production dependencies with hashes and scan them in CI.
**Rationale:** The problem is not that every pinned package is abandoned. The problem is security-critical auth and old pins being treated as a maintenance strategy without a recurring update process. Sentence Transformers' current documentation includes v5/v6 migration guidance, and current Next.js documentation reports a newer 16.x release than the UI pin; upgrades should be tested, not applied blindly.

**Trade-offs:**

| Gain | Lose |
|---|---|
| Security fixes and supported runtime combinations | Upgrade regressions and migration testing |
| Reproducible builds with known transitive versions | Lockfile maintenance |
| Simpler standard JWT API with PyJWT | Fewer JOSE feature permutations than a full JOSE package |

**Migration effort:** Medium — generate lockfiles, run compatibility tests, and upgrade one dependency family at a time.
**Evidence:** [python-jose repository](https://github.com/mpdavis/python-jose), [Sentence Transformers migration guide](https://www.sbert.net/docs/migration_guide.html), [Next.js documentation](https://nextjs.org/docs).

---

## Overkill & Simplification Opportunities

### Kubernetes — REMOVE / DEFER

- **What it is:** Referenced as the production deployment target in `.github/workflows/production.yml`.
- **Why it's overkill:** Fewer than 100 on-prem users do not justify a Kubernetes control plane for this two-application system. The repository has no manifests, no real `kubectl` step, and no evidence of multi-node availability requirements.
- **What to do instead:** Use Docker Compose or systemd with a reverse proxy and explicit backup/restore automation. Revisit Kubernetes only when there are multiple independently scaled services or an existing organizational platform mandate.
- **Complexity saved:** Removes cluster lifecycle, ingress, secret, storage, and deployment-controller operations.

### Celery + Redis — REMOVE / DEFER

- **What it is:** Installed in API requirements but not used by the request path.
- **Why it's overkill:** The current job is a single background function and the target population is small. Installing a broker and worker framework without wiring durable jobs adds operational burden without reliability benefit.
- **What to do instead:** Use synchronous processing for small uploads or a PostgreSQL jobs table with one worker process. Adopt Celery only after measured queue/retry requirements.
- **Complexity saved:** Removes two services, broker configuration, result backend decisions, and an untested failure mode.

### MLflow in the API Image — SIMPLIFY

- **What it is:** A full experiment-tracking platform included in runtime dependencies.
- **Why it's overkill:** Training code is separate from the request path. The API needs a model artifact and metadata, not an experiment UI.
- **What to do instead:** Keep MLflow in a training/operations environment and deploy immutable model artifacts with hashes.
- **Complexity saved:** Smaller images, fewer vulnerabilities, and fewer runtime services.

### Qdrant for Deterministic Reconciliation — SIMPLIFY

- **What it is:** A vector database used by RAG/copilot components.
- **Why it's overkill:** It is useful for GST rule retrieval, not for the core structured CSV matching path. For a small corpus, PostgreSQL full-text search or a local in-process index can cover basic search until retrieval benchmarks justify Qdrant.
- **What to do instead:** Keep Qdrant optional for the copilot; use deterministic matching and database queries for source records.
- **Complexity saved:** Avoids coupling financial matching availability to a separate vector service.

### Duplicate Persistence and Export Paths — REMOVE

- **What it is:** `Store`-backed `/runs/{run_id}/export` and legacy `_runs_store`-backed `/export/{run_id}`, plus two SQLite feedback implementations.
- **Why it's overkill:** Two paths create inconsistent response shapes, retention behavior, and authorization coverage. The legacy route is also less durable.
- **What to do instead:** Select one repository and one export contract, then delete the legacy route and direct `sqlite3` feedback code after migration.
- **Complexity saved:** One data model, one authorization path, and one set of tests.

---

## Architecture & System Design Assessment

### What's working well
- The deterministic domain engine is separated from the web API and UI, which supports independent testing and future interfaces.
- The evidence/decision-trace model aligns well with financial auditability and the project's explainability principle.
- The test suite emphasizes metamorphic, adversarial, identity, conservation, and tenant-isolation behavior rather than only happy-path examples.
- FastAPI's typed request/response model and OpenAPI generation are appropriate for an internal enterprise API.
- Qdrant supports self-hosted deployment and payload filtering if the RAG feature becomes operationally justified.

### What's missing
- Real identity integration, secret management, token revocation, password policy, and audit events for authentication and review actions.
- Uniform authentication and tenant-scoped object authorization across all endpoints.
- A single durable database, schema migration gate, backup verification, retention policy, and disaster-recovery runbook.
- Durable job state, idempotency, retry policy, upload storage, and resource quotas for reconciliation workloads.
- Strict CORS allowlist, TLS termination, security headers, request body limits at the proxy, and rate limits on login/upload/feedback.
- Structured logs with PII redaction, metrics for queue depth/latency/errors, traces across API-worker-database, and alerts.
- CI that installs the declared project, builds the actual images, runs migration tests, scans dependencies/images, and exercises authenticated API flows.

### What's over-engineered
- Kubernetes is referenced without any manifests or demonstrated scale requirement.
- Celery and Redis are dependencies without an implemented task queue.
- MLflow, Evidently, Qdrant, and Sentence Transformers are installed for an API whose primary value proposition is a deterministic engine.
- Multiple persistence models and legacy API paths increase surface area without increasing capability.

### Suggested target architecture
Use a modular monolith: one FastAPI service owns the deterministic engine, auth integration, API, and persistence boundary; one Next.js UI is served behind the same on-prem reverse proxy. PostgreSQL is the system of record. Add one worker process and Redis only if measured reconciliation duration requires asynchronous execution, and run Qdrant only when the copilot is enabled. Keep source records immutable and store derived results, trace hashes, model hashes, and review actions transactionally.

```text
Users -> TLS reverse proxy -> Next.js UI
                         -> FastAPI API -> PostgreSQL
                                      -> optional worker -> PostgreSQL
                                      -> optional Qdrant (RAG only)
                                      -> approved local/external LLM (optional)
```

---

## Dependency Health Summary

| Dependency | Version | Last Release | Status | Action |
|---|---:|---|---|---|
| FastAPI | 0.111.0 | Current docs/registry show newer releases | active | upgrade/test |
| Uvicorn | 0.29.0 | current releases newer | active | upgrade/test |
| SQLAlchemy | 2.0.30 | 2.0.52 released 2026-08-11 | active | upgrade |
| Alembic | 1.13.1 | current docs show 1.19.1 | active | upgrade |
| asyncpg | 0.29.0 | newer releases exist | active | use after DB consolidation |
| Celery | 5.4.0 | 5.6.3 stable docs | active | remove unless queue is implemented |
| redis | 5.0.4 | newer releases exist | active | remove unless queue/cache is implemented |
| python-jose | 3.3.0 | aging project line | aging | replace/isolate |
| passlib | 1.7.4 | legacy API line | aging | replace with Argon2id library |
| Qdrant client | 1.10.1 | newer releases exist | active | optionalize and upgrade |
| Sentence Transformers | 3.0.1 | v5/v6 migration docs available | active | upgrade deliberately |
| scikit-learn | >=1.3,<unbounded | rolling | active | lock version |
| LightGBM | >=4.0,<unbounded | rolling | active | lock version |
| MLflow | 2.15.1 | current docs describe MLflow 3 | active | move to ops environment and upgrade |
| Evidently | unpinned | rolling | active | pin and move to ops environment |
| Next.js | 16.2.12 | docs show 16.3.4 | active | upgrade after UI smoke tests |
| React | 19.2.4 | active | active | keep with Next compatibility testing |

---

## Action Plan (Prioritized)

### Immediate (this sprint)
- [ ] Remove hard-coded credentials and JWT secret; add startup validation for required auth configuration.
- [ ] Require authentication on every data endpoint and enforce tenant ownership in every run/packet/feedback query.
- [ ] Restrict CORS to the actual UI origin and disable credentialed wildcard CORS.
- [ ] Remove or quarantine unauthenticated `/demo`, `/version`, and legacy export behavior for production profiles.
- [ ] Add negative tests for cross-tenant run, packet, export, and feedback access.

### Short-term (next 1-2 sprints)
- [ ] Choose PostgreSQL as the production system of record and make SQLAlchemy/Alembic the only persistence path.
- [ ] Replace `BackgroundTasks` plus `_runs_store` with a durable jobs table/worker; add idempotency and restart recovery.
- [ ] Publish one supported on-prem deployment artifact and repair CI references to missing files/placeholders.
- [ ] Add proxy/API limits, structured redacted logs, metrics, migration checks, image/dependency scanning, and authenticated smoke tests.
- [ ] Split runtime dependencies into deterministic-core, API, AI/RAG, ML, and ops groups.

### Medium-term (next quarter)
- [ ] Integrate OIDC/LDAP/SSO and map enterprise groups to explicit application roles.
- [ ] Add PostgreSQL backup restore drills, retention policies, and documented RPO/RTO targets.
- [ ] Establish model promotion, artifact hashing, retrieval evaluation, and drift review gates.
- [ ] Add OpenTelemetry-compatible traces and operational dashboards for API, jobs, database, RAG, and LLM calls.

### Cleanup (when convenient)
- [ ] Delete the unused async database module or complete its adoption; do not retain a parallel ORM path.
- [ ] Remove Celery/Redis if the jobs-table design is sufficient.
- [ ] Remove the duplicate legacy export route and direct SQLite feedback initialization after migration.
- [ ] Remove demo-only Render/Vercel instructions from production deployment documentation or label them explicitly.

---

## Sources

### API, Security, and Deployment
- https://fastapi.tiangolo.com/ — FastAPI capabilities, security, background tasks, and deployment documentation.
- https://fastapi.tiangolo.com/tutorial/security/oauth2-jwt/ — OAuth2/JWT implementation guidance.
- https://owasp.org/www-project-api-security/ — API Security Top 10 and risk definitions.
- https://owasp.org/API-Security/editions/2023/en/0xa1-broken-object-level-authorization/ — BOLA guidance.
- https://owasp.org/API-Security/editions/2023/en/0xa5-broken-function-level-authorization/ — function-level authorization guidance.
- https://nextjs.org/docs/app/guides/self-hosting — Next.js self-hosting considerations.

### Database and Jobs
- https://docs.sqlalchemy.org/en/20/orm/extensions/asyncio.html — SQLAlchemy async engine/session support and current 2.0 release information.
- https://alembic.sqlalchemy.org/en/latest/ — migration workflow and current Alembic documentation.
- https://www.postgresql.org/docs/current/ — PostgreSQL supported versions, transactions, security, maintenance, backup, and replication documentation.
- https://docs.celeryq.dev/en/stable/getting-started/introduction.html — Celery stable version, broker/worker model, and operational capabilities.
- https://redis.io/docs/latest/develop/clients/redis-py/ — redis-py client and server requirement.

### AI, Retrieval, and ML Operations
- https://qdrant.tech/documentation/overview/ — Qdrant architecture, self-hosting, filtering, replication, and operational limits.
- https://qdrant.tech/documentation/tutorials-operations/secure-qdrant/ — securing self-hosted Qdrant.
- https://www.sbert.net/ — Sentence Transformers encoders, reranking, sparse retrieval, and deployment options.
- https://www.sbert.net/docs/migration_guide.html — Sentence Transformers v5/v6 migration guidance.
- https://mlflow.org/docs/latest/ml/tracking/ — MLflow tracking, backend/artifact stores, model registry requirements, and self-hosting.
- https://mlflow.org/docs/latest/self-hosting/architecture/ — MLflow self-hosting architecture.

### Authentication Dependencies
- https://github.com/mpdavis/python-jose — python-jose maintenance/activity signals and cryptographic backend guidance.
- https://github.com/pyca/bcrypt — bcrypt maintenance, limitations, and recommendation to consider Argon2id or scrypt.
- https://argon2-cffi.readthedocs.io/ — Argon2id implementation option for local password authentication.
