"""PipelineConfig defaults and env override tests."""

import pytest

pytestmark = pytest.mark.no_api


def test_default_values(monkeypatch):
    # Isolate from .env file and env var overrides to verify code defaults
    for key in (
        "PIPELINE_MAX_RETRIES",
        "PIPELINE_ESCALATION_THRESHOLD_USD",
        "PIPELINE_REFUND_WINDOW_DAYS",
        "PIPELINE_FALLBACK_ENABLED",
        "PIPELINE_MAX_MESSAGE_LENGTH",
    ):
        monkeypatch.delenv(key, raising=False)
    from refund_pilot.core.config import PipelineConfig

    config = PipelineConfig(_env_file=None)
    assert config.max_retries == 1
    assert config.escalation_threshold_usd == 500.0
    assert config.refund_window_days == 30
    assert config.fallback_enabled is True
    assert config.max_message_length == 2000


def test_env_override(monkeypatch):
    monkeypatch.setenv("PIPELINE_MAX_RETRIES", "5")
    monkeypatch.setenv("PIPELINE_ESCALATION_THRESHOLD_USD", "1000.0")
    from refund_pilot.core.config import PipelineConfig

    config = PipelineConfig()
    assert config.max_retries == 5
    assert config.escalation_threshold_usd == 1000.0
