# Docker Quickstart

Run the full stack on any machine with Docker — no git clone, no build.

## Prerequisites

- Docker 24+ with Compose v2
- An [Anthropic API key](https://console.anthropic.com/)

## 1. Clone the repo

```bash
git clone https://github.com/sherozshaikh/refund-pilot.git
cd refund-pilot
```

> The repo contains `docker-compose.yml`, `.env.example`, and observability config files (Prometheus, Loki, Tempo, Grafana, OTel Collector) that the stack mounts at runtime. No build step required — images are pulled from Docker Hub.

## 2. Create your `.env`

```bash
cp .env.example .env
```

Open `.env` and set the two required fields — everything else has working defaults:

```dotenv
# REQUIRED — get from https://console.anthropic.com/
ANTHROPIC_API_KEY=sk-ant-...

# REQUIRED — generate with: python -c "import secrets; print(secrets.token_hex(32))"
JWT_SECRET_KEY=your-generated-secret

# OPTIONAL — enables LangSmith trace links in admin dashboard
LANGCHAIN_API_KEY=ls__...

# OPTIONAL — enables Tempo distributed traces in Grafana (correct for Docker Compose)
OTEL_EXPORTER_OTLP_ENDPOINT=http://otel-collector:4318/v1/traces
```

## 3. Pull images and start

```bash
docker compose pull
docker compose up -d
```

Images pulled from Docker Hub:

| Image | Tag |
|-------|-----|
| `sherozshaikh/refund-pilot-backend` | `latest` |
| `sherozshaikh/refund-pilot-worker` | `latest` |
| `sherozshaikh/refund-pilot-frontend` | `latest` |

First boot automatically runs Alembic migrations and seeds 15 synthetic customers + 30 orders. Wait ~15 seconds for healthchecks to pass.

## 4. Open the stack

| Service | URL | Credentials |
|---------|-----|-------------|
| Chat UI | http://localhost | — |
| API docs (Swagger) | http://localhost:8000/docs | — |
| Grafana | http://localhost:3000 | admin / admin |
| Prometheus | http://localhost:9090 | — |

## 5. Send a refund request

1. Open http://localhost
2. Select a customer from the dropdown
3. Select an order
4. Type a refund request and press Enter
5. Watch the agent stream its decision in real time

## 6. Inspect traces

**Grafana → Explore → Tempo → Run query** — no filter needed. Every request produces an OTLP trace with spans for each LangGraph node.

**LangSmith** (requires `LANGCHAIN_API_KEY`): full token-level traces with tool calls visible at the run URL shown in the admin dashboard.

## Model selection

Swap Claude model in `.env` — no rebuild needed:

```dotenv
CLAUDE_MODEL=claude-haiku-4-5       # default — fast, low cost
CLAUDE_MODEL=claude-sonnet-4-6      # higher accuracy
CLAUDE_MODEL=claude-opus-4-8        # highest capability
```

Restart after changing:

```bash
docker compose up -d --no-build backend worker
```

## Policy thresholds

All agent policy rules are env-configurable — no rebuild needed:

```dotenv
PIPELINE_ESCALATION_THRESHOLD_USD=500   # auto-escalate orders above this amount
PIPELINE_REFUND_WINDOW_DAYS=30          # eligibility window in days
PIPELINE_MAX_RETRIES=3                  # Claude API retry limit
PIPELINE_FALLBACK_ENABLED=true          # regex fallback when API unavailable
PIPELINE_RATE_LIMIT_REQUESTS=5          # max requests per customer per window
PIPELINE_RATE_LIMIT_WINDOW_SECONDS=60   # rate-limit window in seconds
PIPELINE_SSE_POLL_TIMEOUT_SECONDS=120   # SSE stream timeout before fallback response
PIPELINE_TOOL_CACHE_TTL_SECONDS=1800    # Redis TTL for cached customer/order results
PIPELINE_CELERY_CONCURRENCY=1           # Celery worker threads per container
```

## Scale workers

```bash
docker compose scale worker=4
```

Monitor queue depth in Grafana → Refund Pilot dashboard → Celery Queue Depth panel.

## Stop

```bash
docker compose down          # keep volumes (DB + Redis)
docker compose down -v       # wipe all volumes
```

## Troubleshooting

**Backend not starting** — check `ANTHROPIC_API_KEY` is set and valid in `.env`.

**Tempo returning no traces** — verify `OTEL_EXPORTER_OTLP_ENDPOINT=http://otel-collector:4318/v1/traces` is in `.env`. Send a fresh chat message then query Tempo.

**LangSmith links not clickable** — `LANGCHAIN_API_KEY` not set or expired. Get a new key at [smith.langchain.com](https://smith.langchain.com) → Settings → API Keys.

**Rate limit errors (429)** — each customer is limited to 5 requests per 60-second window (configurable via `PIPELINE_RATE_LIMIT_REQUESTS` / `PIPELINE_RATE_LIMIT_WINDOW_SECONDS`). Switch customer from the dropdown.
