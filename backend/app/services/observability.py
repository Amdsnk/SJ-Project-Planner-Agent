"""Structured logging + OpenTelemetry / Application Insights wiring.

When ``APPLICATIONINSIGHTS_CONNECTION_STRING`` is configured, traces / logs
are exported to Azure Monitor. Otherwise, ``structlog`` formats human-readable
JSON to stdout, which Container Apps / Kubernetes can scrape.
"""
from __future__ import annotations

import logging
import sys

import structlog

from ..config import settings

_configured = False


def configure_logging() -> None:
    global _configured
    if _configured:
        return
    level = getattr(logging, settings.log_level.upper(), logging.INFO)

    timestamper = structlog.processors.TimeStamper(fmt="iso", utc=True)
    shared = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        timestamper,
    ]
    renderer = (
        structlog.processors.JSONRenderer()
        if settings.log_json or settings.app_env == "production"
        else structlog.dev.ConsoleRenderer(colors=False)
    )

    structlog.configure(
        processors=shared + [renderer],
        wrapper_class=structlog.make_filtering_bound_logger(level),
        logger_factory=structlog.PrintLoggerFactory(file=sys.stdout),
        cache_logger_on_first_use=True,
    )
    logging.basicConfig(level=level, format="%(message)s", stream=sys.stdout, force=True)
    _configured = True


def get_logger(name: str | None = None):
    if not _configured:
        configure_logging()
    return structlog.get_logger(name or "app")


def instrument_app(app) -> None:
    """Attach OpenTelemetry instrumentation if Application Insights is configured."""
    if not settings.appinsights_enabled:
        return
    try:
        from azure.monitor.opentelemetry.exporter import AzureMonitorTraceExporter
        from opentelemetry import trace
        from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
        from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
        from opentelemetry.sdk.resources import Resource
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import BatchSpanProcessor

        from ..database import engine

        resource = Resource.create({"service.name": "sj-planner-api", "service.version": app.version})
        provider = TracerProvider(resource=resource)
        provider.add_span_processor(BatchSpanProcessor(
            AzureMonitorTraceExporter.from_connection_string(
                settings.applicationinsights_connection_string
            )
        ))
        trace.set_tracer_provider(provider)
        FastAPIInstrumentor.instrument_app(app)
        SQLAlchemyInstrumentor().instrument(engine=engine)
        get_logger(__name__).info("observability_enabled", exporter="azure_monitor")
    except Exception as e:  # pragma: no cover — optional path
        get_logger(__name__).warning("observability_init_failed", error=str(e))
