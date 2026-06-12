from prometheus_client import Counter, Histogram

# ---------------------------------------------------------------------------
# Business: decisions
# ---------------------------------------------------------------------------

REFUND_REQUESTS = Counter(
    "refund_requests_total",
    "Refund requests processed, labelled by outcome",
    ["decision"],  # approved | denied | escalated | fallback
)

# ---------------------------------------------------------------------------
# Business: cost & tokens
# ---------------------------------------------------------------------------

TOKENS_INPUT = Counter(
    "refund_tokens_input_total",
    "Cumulative Claude input tokens consumed",
)

TOKENS_OUTPUT = Counter(
    "refund_tokens_output_total",
    "Cumulative Claude output tokens consumed",
)

TOKENS_PER_REQUEST_INPUT = Histogram(
    "refund_tokens_input_per_request",
    "Input token count distribution per request",
    buckets=[50, 100, 200, 400, 600, 800, 1000, 1500, 2000],
)

TOKENS_PER_REQUEST_OUTPUT = Histogram(
    "refund_tokens_output_per_request",
    "Output token count distribution per request",
    buckets=[10, 25, 50, 100, 200, 400, 600, 800, 1024],
)

REFUND_COST_USD = Counter(
    "refund_cost_usd_total",
    "Cumulative estimated Claude API cost (USD, Haiku 4.5 pricing)",
)

COST_PER_REQUEST = Histogram(
    "refund_cost_per_request_usd",
    "Cost distribution per individual request (USD)",
    buckets=[0.00005, 0.0001, 0.0002, 0.0005, 0.001, 0.002, 0.005],
)

# ---------------------------------------------------------------------------
# Performance: latency
# ---------------------------------------------------------------------------

REFUND_LATENCY = Histogram(
    "refund_request_latency_seconds",
    "End-to-end task latency (agent start → result written to Redis)",
    buckets=[0.5, 1.0, 2.0, 3.0, 5.0, 8.0, 10.0, 15.0, 20.0, 30.0, 60.0],
    labelnames=["decision"],
)

# ---------------------------------------------------------------------------
# Security
# ---------------------------------------------------------------------------

INJECTION_DETECTED = Counter(
    "refund_injection_detected_total",
    "Requests where prompt injection signal was detected",
)

INJECTION_BY_DECISION = Counter(
    "refund_injection_by_decision_total",
    "Injection detections cross-tabbed with final decision — did injection attempts succeed?",
    ["decision"],
)

# ---------------------------------------------------------------------------
# Reliability
# ---------------------------------------------------------------------------

FALLBACK_USED = Counter(
    "refund_fallback_total",
    "Times fallback handler fired instead of Claude (API down/quota)",
)

TASK_FAILURES = Counter(
    "refund_task_failures_total",
    "Celery task hard failures (exception escaped agent, no result written)",
)

# ---------------------------------------------------------------------------
# Conversation depth
# ---------------------------------------------------------------------------

CONVERSATION_HISTORY_LEN = Histogram(
    "refund_conversation_history_messages",
    "Number of prior messages loaded for multi-turn context",
    buckets=[0, 1, 2, 3, 5, 7, 10],
)

# ---------------------------------------------------------------------------
# Prompt cache efficiency
# ---------------------------------------------------------------------------

CACHE_CREATION_TOKENS = Counter(
    "refund_cache_creation_tokens_total",
    "Tokens written to prompt cache (first miss — 25% surcharge applies)",
)

CACHE_READ_TOKENS = Counter(
    "refund_cache_read_tokens_total",
    "Tokens read from prompt cache (cache hit — 90% cheaper than input tokens)",
)
