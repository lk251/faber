"""Hermes-like trace adapter stubs."""

from faber.adapters.hermes.scheduler_delivery_pilot import (
    scheduler_delivery_pilot_budget,
    scheduler_delivery_pilot_contract,
    scheduler_delivery_pilot_verifier_specs,
    scheduler_delivery_trajectory_requirement,
)
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
    "scheduler_delivery_pilot_budget",
    "scheduler_delivery_pilot_contract",
    "scheduler_delivery_pilot_verifier_specs",
    "scheduler_delivery_trajectory_requirement",
]
