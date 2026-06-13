# Refund Pilot

**Production-Grade AI Refund Agent — LangGraph + Claude + FastAPI + React 19**

[![Python 3.12](https://img.shields.io/badge/python-3.12-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688.svg)](https://fastapi.tiangolo.com/)
[![LangGraph](https://img.shields.io/badge/LangGraph-0.3-orange.svg)](https://langchain-ai.github.io/langgraph/)
[![Docker](https://img.shields.io/badge/Docker-Compose-2496ED.svg)](https://docs.docker.com/compose/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

An e-commerce refund agent built for production. Customer messages arrive at a React chat UI, get enqueued as Celery tasks, and are processed by a deterministic 5-node LangGraph pipeline that enforces a written refund policy via Claude tool forcing at `temperature=0`. Decisions stream back word-by-word over SSE. Every run is auditable in a JWT-protected admin dashboard — full LangGraph trace tree, policy clauses cited, token counts, latency, and a LangSmith trace link. The full observability stack (OTel → Prometheus + Loki + Tempo → Grafana) runs in Docker Compose alongside the app.

**Key properties:** injection-resistant dual-layer (keyword pre-filter + system prompt hardening) · structured output via tool calling (no parsing) · multi-turn short-circuit on terminal decisions · graceful regex fallback when Claude API unavailable · single-transaction DB writes · horizontally scalable workers.

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│  React 19 + Vite (served via Nginx)                              │
│  ┌──────────────────┐  ┌──────────────────────────────────────┐  │
│  │   Chat Window    │  │   Admin Dashboard                     │  │
│  │  SSE streaming   │  │   runs table · trace tree · metrics   │  │
│  └────────┬─────────┘  └───────────────┬──────────────────────┘  │
└───────────┼────────────────────────────┼────────────────────────┘
            │ HTTP / SSE                 │ HTTP (JWT-protected)
┌───────────▼────────────────────────────▼────────────────────────┐
│  FastAPI (stateless, async)                                       │
│  POST /api/v1/conversations/{id}/message  → enqueue Celery task  │
│  GET  /api/v1/conversations/{id}/stream   → SSE (Redis poll)     │
│  GET  /api/v1/admin/runs                  → paginated run list   │
│  GET  /api/v1/admin/runs/{id}             → full trace           │
└──────┬───────────────────────────────────────────────────────────┘
       │ Celery task
┌──────▼──────────────────────┐   ┌──────────────────────────────┐
│  Redis                       │   │  PostgreSQL 17               │
│  • Celery broker             │   │  customers · orders          │
│  • SSE result key (300s TTL) │   │  conversations · chat_msgs   │
│  • Per-customer rate limit   │   │  agent_runs (JSONB trace)    │
└──────┬──────────────────────┘   │  escalations · admin_users   │
       │ worker consumes          └──────────────────────────────┘
┌──────▼──────────────────────────────────────────────────────────┐
│  Celery Worker (scale: docker compose scale worker=N)            │
│  └─► LangGraph Agent (deterministic, no loops)                  │
│       validate_request → query_customer_db → check_eligibility   │
│       → (escalate | generate_response) → log_run                │
└──────────────────────────────────────────────────────────────────┘

Observability: OTel Collector → Prometheus + Loki + Tempo → Grafana
LangSmith: per-node token traces
```

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Agent | LangGraph · Claude (Anthropic) · tool forcing · `temperature=0` |
| Backend | FastAPI (async) · Celery · Redis · PostgreSQL 17 · SQLAlchemy 2.x async |
| Frontend | React 19 · Vite · Zustand · TanStack Query · SSE streaming |
| Observability | OTel Collector → Prometheus + Loki + Tempo → Grafana · LangSmith |
| Infrastructure | Docker Compose · Nginx · Alembic migrations · multi-stage builds |

---

## Quickstart

No build required. Three pre-built images on Docker Hub:

| Image | Docker Hub |
|-------|-----------|
| Backend | `sherozshaikh/refund-pilot-backend:latest` |
| Worker | `sherozshaikh/refund-pilot-worker:latest` |
| Frontend | `sherozshaikh/refund-pilot-frontend:latest` |

**1. Clone the repo:**

```bash
git clone https://github.com/sherozshaikh/refund-pilot.git
cd refund-pilot
```

**2. Create your `.env`:**

```bash
cp .env.example .env
```

Set these two required fields — everything else has working defaults:

```dotenv
ANTHROPIC_API_KEY=sk-ant-...
JWT_SECRET_KEY=<python -c "import secrets; print(secrets.token_hex(32))">
```

**3. Bring up the whole stack:**

```bash
make up
```

This pulls images, starts everything detached (`docker compose up -d`), and prints the access URLs — local login plus the public tunnel URLs.

First boot seeds 15 synthetic customers + 30 orders automatically. Wait ~15 seconds.

| Service | URL | Credentials |
|---------|-----|-------------|
| Chat UI (login gate) | http://localhost | `GATE_USER` / `GATE_PASS` (default `admin` / `admin`) |
| API docs | http://localhost:8000/docs | — |
| Grafana | http://localhost:3000 | admin / admin |
| Prometheus | http://localhost:9090 | — |
| Public tunnel URLs | from `make urls` | ephemeral `*.trycloudflare.com` |

The Chat UI sits behind a login gate (nginx + njs). Visiting http://localhost shows a login page first; log out at `/logout`.

`make up` also publishes ephemeral public https URLs via Cloudflare quick tunnels (no Cloudflare account needed): one for the login-gated frontend and one for Grafana. These URLs regenerate on every restart — retrieve them anytime with `make urls` (or `./scripts/cf-urls.sh`). The public frontend is protected by the login gate, but **Grafana exposed publicly is only protected by its own admin/admin login** — change it or do not share the URL.

See [docs/docker-quickstart.md](docs/docker-quickstart.md) for model swap, policy config, scaling, and troubleshooting.

---

## Screenshots

### Chat — Approved Refund
![chat-approved](docs/images/chat-approved.png)

### Chat — Denied Refund
![chat-denied](docs/images/chat-denied.png)

### Chat — Escalated (High-Value Order)
![chat-escalated](docs/images/chat-escalated.png)

### Chat — Prompt Injection Blocked (User View)
![chat-injection-user](docs/images/chat-injection-user.png)

### Chat — Prompt Injection (Admin View)
![chat-injection-admin](docs/images/chat-injection-admin.png)

### Chat — Fallback Decision
![chat-fallback](docs/images/chat-fallback.png)

### Chat — Fallback (Admin View)
![chat-fallback-admin](docs/images/chat-fallback-admin.png)

### Admin — Run List
![admin-runs-table](docs/images/admin-runs-table.png)

### Admin — Approved Run Trace
![admin-trace-approved](docs/images/admin-trace-approved.png)

### Admin — Denied Run Trace
![admin-trace-denied](docs/images/admin-trace-denied.png)

### Admin — Escalated Run Trace
![admin-trace-escalated](docs/images/admin-trace-escalated.png)

### Grafana — Overview Dashboard
![grafana-dashboard](docs/images/grafana-dashboard.png)

### Grafana — HTTP & Infra + Injection Metrics
![grafana-http-infra](docs/images/grafana-http-infra-injection.png)

### Grafana — Prompt Cache Efficiency
![grafana-cache](docs/images/grafana-cache-efficiency.png)

### Grafana — Tempo Distributed Traces
![grafana-tempo](docs/images/grafana-tempo.png)

### Prometheus — Targets
![prometheus-targets](docs/images/prometheus-targets.png)

### LangSmith — Run List
![langsmith-run-list](docs/images/langsmith-run-list.png)

### LangSmith — Trace Detail
![langsmith-trace](docs/images/langsmith-trace.png)

---

## Architecture Diagrams

### System Architecture
![system-architecture](docs/images/system-architecture.png)

### Refund Request Lifecycle
![refund-lifecycle](docs/images/refund-request-lifecycle.png)

### LangGraph Agent Pipeline
![langgraph-agent-pipeline](docs/images/langgraph-agent-pipeline.png)

### Database Schema
![database-schema](docs/images/database-schema.png)

### Observability Stack
![observability-stack](docs/images/observability-stack.png)

---

## Agent Design

Five-node deterministic pipeline — no loops, no tool selection, no free-form planning:

```
validate_request → query_customer_db → check_refund_eligibility
  → (escalate_to_human | generate_response) → log_run
```

| Property | Detail |
|----------|--------|
| **Tool forcing** | Claude constrained to call `record_decision` exactly once — no free text |
| **`temperature=0`** | Deterministic policy enforcement across identical inputs |
| **Injection resistance** | Keyword pre-filter in `validate_request` + system prompt hardening in `generate_response` |
| **Multi-turn short-circuit** | Turn 2+ restates prior terminal decision without re-running the pipeline |
| **Graceful fallback** | Regex handler produces `decision=fallback` when Claude API unavailable |
| **Single DB transaction** | `log_run` writes `AgentRun` + `Escalation` atomically via `flush()` + `commit()` |

See [docs/agent-design.md](docs/agent-design.md) for full design documentation.

---

## Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `ANTHROPIC_API_KEY` | ✅ | — | Claude API key |
| `JWT_SECRET_KEY` | ✅ | — | Admin auth secret — generate: `python -c "import secrets; print(secrets.token_hex(32))"` |
| `GATE_USER` | — | `admin` | Frontend login-gate username |
| `GATE_PASS` | — | `admin` | Frontend login-gate password |
| `GATE_SECRET` | — | — | Session-cookie signing secret (HMAC) — use a random value: `openssl rand -hex 24` |
| `CLAUDE_MODEL` | — | `claude-haiku-4-5` | Model ID |
| `LANGCHAIN_API_KEY` | — | — | LangSmith tracing (optional) |
| `DATABASE_URL` | — | postgres://... (compose default) | PostgreSQL async URL |
| `REDIS_URL` | — | `redis://redis:6379/0` | Redis URL |
| `FRONTEND_URL` | — | `http://localhost` | CORS origin |
| `OTEL_EXPORTER_OTLP_ENDPOINT` | — | unset (no export) | Set to `http://otel-collector:4318/v1/traces` in Docker |
| `PIPELINE_ESCALATION_THRESHOLD_USD` | — | `500` | Auto-escalate above this amount |
| `PIPELINE_REFUND_WINDOW_DAYS` | — | `30` | Eligibility window in days |
| `PIPELINE_FALLBACK_ENABLED` | — | `true` | Regex fallback when Claude unavailable |

See `.env.example` for the full list with comments.

---

## Development

```bash
make up         # pull images, start the whole stack detached, print access URLs
make install    # uv sync
make migrate    # alembic upgrade head
make seed       # 15 customers + 30 orders
make test       # 88 tests — no API key required
make lint       # ruff check + mypy strict (src/ only)
make format     # ruff format
make dev        # docker compose up --build (foreground)
```

### Scale Workers

```bash
docker compose scale worker=4
```

---

## Makefile Reference

```
Stack (one command):
  make up               pull images, start whole stack detached, print access URLs
  make pull             docker compose pull
  make urls / tunnels   print the public cloudflared tunnel URLs (ephemeral)
  make restart          docker compose restart
  make ps               docker compose ps

Setup:
  make install          uv sync — install Python deps
  make migrate          alembic upgrade head
  make seed             seed 15 customers + 30 orders

Development:
  make dev              docker compose up --build (foreground)
  make down             docker compose down
  make down-clean       docker compose down -v (wipe volumes)
  make test             pytest (no API key required)
  make lint             ruff check + mypy strict (src/ only)
  make format           ruff format
  make pre-commit       pre-commit run --all-files

Docker:
  make docker-build     gate check (clean → format → lint → pre-commit → test → hadolint) then build all 3 images locally
  make docker-push      push locally built images to Docker Hub (run docker-build + verify first)
  make hadolint         lint all Dockerfiles

Ops:
  make logs             docker compose logs -f
  make shell-db         psql into PostgreSQL container
```

---

## Author

**Sheroz Shaikh** — [Portfolio](https://sherozshaikh.github.io/) | [GitHub](https://github.com/sherozshaikh) | [LinkedIn](https://www.linkedin.com/in/shaikh-sheroz-07s/)
