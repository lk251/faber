import pytest

from faber.adapters.github.markers import parse_contract_marker, render_contract_marker
from faber.contracts import TaskContract


def test_contract_marker_renders_and_parses_inside_human_text() -> None:
    contract = TaskContract(
        id="task-contract_marker",
        created_at="2026-01-01T00:00:00Z",
        title="Marker contract",
        description="Render a marker.",
        requirements=["round trip"],
        verifier_ids=["verifier"],
        repository="lk251/faber",
    )

    text = f"Human intro\n\n{render_contract_marker(contract)}\n\nHuman outro"
    parsed = parse_contract_marker(text)

    assert parsed.contract_id == contract.id
    assert parsed.contract_digest == contract.digest()
    assert parsed.contract["title"] == "Marker contract"


def test_contract_marker_rejects_digest_mismatch() -> None:
    contract = TaskContract(
        id="task-contract_marker",
        created_at="2026-01-01T00:00:00Z",
        title="Marker contract",
        description="Render a marker.",
        requirements=["round trip"],
        verifier_ids=["verifier"],
        repository="lk251/faber",
    )
    marker = render_contract_marker(contract)
    tampered = marker.replace("Marker contract", "Tampered contract")

    with pytest.raises(ValueError, match="digest mismatch"):
        parse_contract_marker(tampered)
