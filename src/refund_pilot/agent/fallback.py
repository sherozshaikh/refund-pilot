"""FallbackHandler: regex pattern matching to canned policy responses."""

import re

FALLBACK_PATTERNS: list[tuple[str, str]] = [
    (r"\brefund\b", "refund_policy_standard"),
    (r"\bcancel\b", "cancellation_policy"),
    (r"\breturn\b", "return_policy"),
    (r"\bbroken\b|\bdefective\b", "defective_item_policy"),
    (r"\bescalat", "escalation_info"),
]

FALLBACK_RESPONSES: dict[str, str] = {
    "refund_policy_standard": (
        "We're experiencing a temporary issue processing your refund request. "
        "Our team has been notified and will review your request within 1–2 business days. "
        "No decision has been made at this time."
    ),
    "cancellation_policy": (
        "We're experiencing a temporary issue processing your cancellation request. "
        "Our team has been notified and will review your request within 1–2 business days. "
        "No decision has been made at this time."
    ),
    "return_policy": (
        "We're experiencing a temporary issue processing your return request. "
        "Our team has been notified and will review your request within 1–2 business days. "
        "No decision has been made at this time."
    ),
    "defective_item_policy": (
        "We're experiencing a temporary issue processing your request regarding a defective item. "
        "Our team has been notified and will review your request within 1–2 business days. "
        "No decision has been made at this time."
    ),
    "escalation_info": (
        "Your request has been escalated to our customer success team for review. "
        "You will be contacted within 1–2 business days. "
        "No decision has been made at this time."
    ),
}


class FallbackHandler:
    """Return canned policy response when Claude API is unavailable."""

    def handle(self, message: str) -> str | None:
        """Return matching canned response or None if no pattern matches."""
        lower = message.lower()
        for pattern, key in FALLBACK_PATTERNS:
            if re.search(pattern, lower):
                return FALLBACK_RESPONSES[key]
        return None
