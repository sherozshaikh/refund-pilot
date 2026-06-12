"""OpenTelemetry initialisation."""

import os

from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import SERVICE_NAME, Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

_DEFAULT_ENDPOINT = "http://otel-collector:4318/v1/traces"


def configure_telemetry(service_name: str = "refund-pilot") -> None:
    """Set up OTel tracer with OTLP export to collector.

    Skips exporter registration when OTEL_EXPORTER_OTLP_ENDPOINT is unset —
    prevents BatchSpanProcessor noise in local/test environments where the
    Docker Compose collector is not running.
    """
    resource = Resource(attributes={SERVICE_NAME: service_name})
    provider = TracerProvider(resource=resource)
    endpoint = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT")
    if endpoint:
        exporter = OTLPSpanExporter(endpoint=endpoint)
        provider.add_span_processor(BatchSpanProcessor(exporter))
    trace.set_tracer_provider(provider)
