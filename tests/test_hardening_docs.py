from pathlib import Path

TERMS = [
    "Faber for GitHub",
    "Faber Market",
    "Faber Protocol",
    "Faber Runner",
    "Faber Verifiers",
    "Faber Orchestration",
]

ROOT_OBJECTS = [
    "TaskContract",
    "Attempt",
    "VerifierRun",
    "VerificationReceipt",
    "Trajectory",
    "Settlement",
    "WorkerProfile",
    "RouterDecision",
    "MarketEvent",
]

FORBIDDEN_CORE_TERMS = [
    "agent-bounty-market",
    "hackathon",
    "Stripe",
    "NVIDIA",
    "Hermes",
    "Motoko",
    "OpenAI",
    "Anthropic",
    "Google",
]


def _read(path: str) -> str:
    return Path(path).read_text(encoding="utf-8")


def test_hardening_docs_exist() -> None:
    assert Path("docs/ROADMAP.md").exists()
    assert Path("docs/OPEN_QUESTIONS.md").exists()


def test_product_terms_are_aligned_in_main_docs() -> None:
    documents = {
        "README.md": _read("README.md"),
        "AGENTS.md": _read("AGENTS.md"),
        "docs/NAMING.md": _read("docs/NAMING.md"),
    }

    for path, text in documents.items():
        for term in TERMS:
            assert term in text, f"{term} missing from {path}"


def test_protocol_root_objects_are_aligned() -> None:
    protocol = _read("docs/PROTOCOL.md")
    agents = _read("AGENTS.md")

    for object_name in ROOT_OBJECTS:
        assert f"`{object_name}`" in protocol
        assert f"`{object_name}`" in agents
    assert "SettlementEvent" not in protocol


def test_core_source_has_no_reference_repo_or_vendor_names() -> None:
    for path in Path("src/faber").rglob("*.py"):
        if "adapters" in path.parts:
            continue
        text = path.read_text(encoding="utf-8")
        for term in FORBIDDEN_CORE_TERMS:
            assert term not in text, f"{term} leaked into {path}"
