"""Shared Faber error types."""

from __future__ import annotations


class FaberError(Exception):
    """Base class for Faber-specific failures."""


class ValidationError(FaberError, ValueError):
    """A protocol object failed explicit validation."""


class DigestMismatchError(ValidationError):
    """A digest field does not match the expected digest."""


class ScopeError(ValidationError):
    """An adapter reference is outside an allowed scope."""


class SettlementError(ValidationError):
    """A settlement invariant was violated."""


class VerifierError(FaberError, RuntimeError):
    """A verifier registry or runner operation failed."""


class ProtocolVersionError(ValidationError):
    """A record uses an unsupported protocol schema version."""
