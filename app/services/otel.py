"""OpenTelemetry OTLP export (traces + metrics). No-op when OTLP endpoint is unset."""

from __future__ import annotations

import logging
import os

from aaf.config import Settings

_log = logging.getLogger("aaf.otel")
_configured = False


def _parse_otlp_headers(raw: str) -> dict[str, str]:
    out: dict[str, str] = {}
    for part in raw.replace(";", ",").split(","):
        part = part.strip()
        if not part or "=" not in part:
            continue
        k, v = part.split("=", 1)
        k, v = k.strip(), v.strip()
        if k:
            out[k] = v
    return out


def configure_otel(settings: Settings) -> None:
    global _configured
    if _configured:
        return
    endpoint = (settings.otel_exporter_otlp_endpoint or "").strip().rstrip("/")
    if not endpoint:
        return

    try:
        from opentelemetry import metrics, trace
        from opentelemetry.exporter.otlp.proto.http.metric_exporter import OTLPMetricExporter
        from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
        from opentelemetry.sdk.metrics import MeterProvider
        from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
        from opentelemetry.sdk.resources import Resource
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import BatchSpanProcessor
    except ImportError as e:  # pragma: no cover
        _log.warning("OpenTelemetry packages not installed; skipping OTLP setup: %s", e)
        return

    resource = Resource.create(
        {
            "service.name": settings.otel_service_name or "aaf-governance",
            "deployment.environment": settings.app_env,
        }
    )

    headers = _parse_otlp_headers(settings.otel_exporter_otlp_headers or "")
    trace_endpoint = f"{endpoint}/v1/traces"
    metrics_endpoint = f"{endpoint}/v1/metrics"

    span_exporter = OTLPSpanExporter(endpoint=trace_endpoint, headers=headers or None)
    tracer_provider = TracerProvider(resource=resource)
    tracer_provider.add_span_processor(BatchSpanProcessor(span_exporter))
    trace.set_tracer_provider(tracer_provider)

    metric_exporter = OTLPMetricExporter(endpoint=metrics_endpoint, headers=headers or None)
    reader = PeriodicExportingMetricReader(
        metric_exporter, export_interval_millis=settings.otel_metric_export_interval_ms
    )
    meter_provider = MeterProvider(resource=resource, metric_readers=[reader])
    metrics.set_meter_provider(meter_provider)

    os.environ.setdefault("OTEL_SERVICE_NAME", settings.otel_service_name or "aaf-governance")

    _configured = True
    _log.info("OpenTelemetry OTLP enabled (endpoint=%s)", endpoint)


def instrument_fastapi(app) -> None:
    """Attach FastAPI instrumentation once routes are registered."""
    if getattr(app, "_aaf_otel_instrumented", False):
        return
    if not _configured:
        return
    try:
        from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
    except ImportError:  # pragma: no cover
        return
    FastAPIInstrumentor.instrument_app(
        app,
        excluded_urls="/health,/metrics,/favicon.ico",
    )
    app._aaf_otel_instrumented = True  # type: ignore[attr-defined]


def shutdown_otel() -> None:
    global _configured
    if not _configured:
        return
    try:
        from opentelemetry import metrics as otel_metrics
        from opentelemetry import trace

        tracer_provider = trace.get_tracer_provider()
        if hasattr(tracer_provider, "shutdown"):
            tracer_provider.shutdown()
        meter_provider = otel_metrics.get_meter_provider()
        if hasattr(meter_provider, "shutdown"):
            meter_provider.shutdown()
    except Exception as exc:  # noqa: BLE001
        _log.debug("OTel shutdown: %s", exc)
    finally:
        _configured = False
