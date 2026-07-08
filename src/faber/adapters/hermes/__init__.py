"""Hermes-like trace adapter stubs."""

from faber.adapters.hermes.traces import (
    HERMES_TRACE_ADAPTER_NAME,
    adapt_hermes_trace_file,
    adapt_hermes_trace_payload,
    load_hermes_trace_fixture,
)

__all__ = [
    "HERMES_TRACE_ADAPTER_NAME",
    "adapt_hermes_trace_file",
    "adapt_hermes_trace_payload",
    "load_hermes_trace_fixture",
]
