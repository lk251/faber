import importlib
import socket
import tomllib
from pathlib import Path

from faber.cli import main
from faber.runtime import RuntimeMode, future_hosted_boundary, local_runtime_boundary


def test_local_commands_run_without_credentials_or_network(
    tmp_path: Path,
    monkeypatch,
    capsys,
) -> None:
    for name in [
        "GITHUB_TOKEN",
        "OPENAI_API_KEY",
        "ANTHROPIC_API_KEY",
        "STRIPE_SECRET_KEY",
    ]:
        monkeypatch.delenv(name, raising=False)

    def reject_network(*args, **kwargs):
        raise AssertionError("local CLI attempted network access")

    monkeypatch.setattr(socket, "create_connection", reject_network)

    assert main(["doctor"]) == 0
    capsys.readouterr()
    assert (
        main(
            [
                "demo-funded-trajectory",
                "--out-dir",
                str(tmp_path / "funded-demo"),
                "--json",
            ]
        )
        == 0
    )


def test_core_imports_are_provider_free() -> None:
    pyproject = tomllib.loads(Path("pyproject.toml").read_text(encoding="utf-8"))

    assert pyproject["project"]["dependencies"] == []
    for module_name in [
        "faber",
        "faber.contracts",
        "faber.receipts",
        "faber.trajectories",
        "faber.runtime",
    ]:
        assert importlib.import_module(module_name) is not None


def test_runtime_boundaries_keep_hosted_mode_future_only() -> None:
    local = local_runtime_boundary()
    hosted = future_hosted_boundary()

    assert local.mode == RuntimeMode.LOCAL
    assert local.account_required is False
    assert local.external_api_required is False
    assert local.telemetry_enabled is False
    assert local.implementation_status == "available"
    assert hosted.mode == RuntimeMode.HOSTED_FUTURE
    assert hosted.implementation_status == "future-design-only"
    assert hosted.digest() != local.digest()


def test_local_mode_docs_state_no_telemetry_and_command_scope() -> None:
    text = Path("docs/LOCAL_AND_HOSTED_MODES.md").read_text(encoding="utf-8")

    for phrase in [
        "No account is required",
        "No telemetry is emitted",
        "Fake GitHub adapters",
        "Local-only CLI commands",
        "Hosted mode is future work",
        "does not isolate verifier network access",
    ]:
        assert phrase in text
