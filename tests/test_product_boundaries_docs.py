from pathlib import Path


def test_product_boundaries_name_every_faber_surface() -> None:
    text = Path("docs/PRODUCT_BOUNDARIES.md").read_text(encoding="utf-8")

    for surface in [
        "Faber Protocol",
        "Faber Runner",
        "Faber Verifiers",
        "Faber Market",
        "Hosted coordination and settlement",
        "Premium models and training outputs",
    ]:
        assert surface in text


def test_product_boundaries_preserve_portability_and_commercial_honesty() -> None:
    text = Path("docs/PRODUCT_BOUNDARIES.md").read_text(encoding="utf-8")

    for phrase in [
        "works without a hosted Faber account",
        "does not make a verifier authoritative",
        "canonical protocol records",
        "high-intelligence-per-euro",
        "Open, private, and paid data",
        "TODO for legal review",
    ]:
        assert phrase in text


def test_protocol_doc_links_the_product_boundary() -> None:
    text = Path("docs/PROTOCOL.md").read_text(encoding="utf-8")

    assert "PRODUCT_BOUNDARIES.md" in text
