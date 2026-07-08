"""Strict integer minor-unit money representation."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Money:
    """Money stored only as non-negative integer minor units."""

    currency: str
    minor_units: int

    def __post_init__(self) -> None:
        if isinstance(self.minor_units, bool) or not isinstance(self.minor_units, int):
            raise TypeError("money minor_units must be an integer")
        if self.minor_units < 0:
            raise ValueError("money minor_units cannot be negative")
        if len(self.currency) != 3 or not self.currency.isalpha():
            raise ValueError("currency must be a three-letter code")

    def to_dict(self) -> dict[str, object]:
        return {
            "currency": self.currency.upper(),
            "minor_units": self.minor_units,
        }
