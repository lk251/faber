import pytest

from faber.money import Money


def test_money_uses_integer_minor_units() -> None:
    assert Money("EUR", 1234).to_dict() == {"currency": "EUR", "minor_units": 1234}


def test_money_rejects_float_amounts() -> None:
    with pytest.raises(TypeError):
        Money("EUR", 12.34)  # type: ignore[arg-type]


def test_money_rejects_negative_amounts() -> None:
    with pytest.raises(ValueError):
        Money("EUR", -1)
