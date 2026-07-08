from faber.contracts import TaskContract
from faber.digests import sha256_digest
from faber.environments import EnvironmentEvidence, environment_satisfies_contract

CREATED_AT = "2026-01-01T00:00:00Z"


def _contract(*, platform: str | None = None, minimum_level: str | None = None) -> TaskContract:
    environment: dict[str, object] = {}
    if platform is not None:
        environment["platform"] = platform
    if minimum_level is not None:
        environment["minimum_reproducibility_level"] = minimum_level
    return TaskContract(
        id="task-contract_environment",
        created_at=CREATED_AT,
        title="Cross-platform task",
        description="Verify environment evidence.",
        requirements=["tests"],
        verifier_ids=["verifier"],
        environment=environment,
    )


def test_nixos_environment_with_flake_digest() -> None:
    evidence = EnvironmentEvidence(
        id="environment-evidence_nixos",
        created_at=CREATED_AT,
        platform="nixos",
        os_family="NixOS",
        os_version="26.05",
        architecture="x86_64-linux",
        package_manager="nix",
        lockfile_digests={"flake.lock": sha256_digest("flake.lock")},
        runtime_versions={"python": "3.11.15"},
        setup_entrypoint=["nix", "develop"],
        verifier_command=["python", "-m", "pytest"],
        nix_flake_lock_digest=sha256_digest("flake.lock"),
        reproducibility_level="nix_flake",
        trust_level="runner_attested",
    )

    fit = environment_satisfies_contract(
        evidence,
        _contract(platform="nixos", minimum_level="nix_flake"),
    )

    assert evidence.digest().startswith("sha256:")
    assert evidence.to_dict()["nix_flake_lock_digest"] == sha256_digest("flake.lock")
    assert fit.accepted is True
    assert fit.to_dict()["minimum_reproducibility_level"] == "nix_flake"


def test_macos_environment_with_package_manager_metadata() -> None:
    evidence = EnvironmentEvidence(
        id="environment-evidence_macos",
        created_at=CREATED_AT,
        platform="macos",
        os_family="macOS",
        os_version="15.5",
        architecture="arm64",
        package_manager="homebrew",
        lockfile_digests={"uv.lock": sha256_digest("uv.lock")},
        runtime_versions={"python": "3.12.4", "xcode": "16.4"},
        setup_entrypoint=["uv", "sync"],
        verifier_command=["python", "-m", "pytest"],
        reproducibility_level="lockfile",
    )

    assert evidence.to_dict()["package_manager"] == "homebrew"
    assert evidence.to_dict()["runtime_versions"]["xcode"] == "16.4"


def test_windows_environment_with_tool_path_metadata() -> None:
    evidence = EnvironmentEvidence(
        id="environment-evidence_windows",
        created_at=CREATED_AT,
        platform="windows",
        os_family="Windows",
        os_version="11",
        architecture="x86_64",
        package_manager="winget",
        runtime_versions={"python": "3.11.15", "powershell": "7.5"},
        setup_entrypoint=["pwsh", "-File", "scripts/setup.ps1"],
        verifier_command=["python", "-m", "pytest"],
        tool_path_metadata={"python": "C:/Users/javie/AppData/Local/Programs/Python/python.exe"},
        reproducibility_level="declared",
    )

    assert "Python/python.exe" in evidence.to_dict()["tool_path_metadata"]["python"]


def test_ubuntu_container_environment_metadata() -> None:
    evidence = EnvironmentEvidence(
        id="environment-evidence_container",
        created_at=CREATED_AT,
        platform="container",
        os_family="ubuntu",
        os_version="24.04",
        architecture="x86_64",
        package_manager="apt",
        lockfile_digests={"requirements.txt": sha256_digest("requirements.txt")},
        runtime_versions={"python": "3.12"},
        setup_entrypoint=["docker", "run", "faber-test"],
        verifier_command=["pytest"],
        container_image_digest=sha256_digest("ubuntu:24.04-faber"),
        reproducibility_level="container",
        limitations=["base image may be rebuilt upstream"],
    )

    assert evidence.to_dict()["platform"] == "container"
    assert evidence.to_dict()["os_family"] == "ubuntu"
    assert evidence.digest().startswith("sha256:")


def test_task_requiring_nixos_rejects_non_nix_evidence() -> None:
    evidence = EnvironmentEvidence(
        id="environment-evidence_linux",
        created_at=CREATED_AT,
        platform="linux",
        os_family="ubuntu",
        os_version="24.04",
        architecture="x86_64",
        package_manager="apt",
        runtime_versions={"python": "3.12"},
        setup_entrypoint=["python", "-m", "pip", "install", "-e", "."],
        verifier_command=["pytest"],
        reproducibility_level="declared",
    )

    fit = environment_satisfies_contract(evidence, _contract(platform="nixos"))

    assert fit.accepted is False
    assert fit.platform_match is False
    assert fit.reasons == ["platform requirement not satisfied"]


def test_task_without_platform_constraint_accepts_cross_platform_evidence() -> None:
    windows = EnvironmentEvidence(
        id="environment-evidence_windows_free",
        created_at=CREATED_AT,
        platform="windows",
        os_family="Windows",
        os_version="11",
        architecture="x86_64",
        runtime_versions={"python": "3.11.15"},
        setup_entrypoint=["python", "-m", "pip", "install", "-e", "."],
        verifier_command=["python", "-m", "pytest"],
        reproducibility_level="declared",
    )
    macos = EnvironmentEvidence(
        id="environment-evidence_macos_free",
        created_at=CREATED_AT,
        platform="macos",
        os_family="macOS",
        os_version="15.5",
        architecture="arm64",
        runtime_versions={"python": "3.12.4"},
        setup_entrypoint=["uv", "sync"],
        verifier_command=["python", "-m", "pytest"],
        reproducibility_level="lockfile",
    )
    contract = _contract()

    assert environment_satisfies_contract(windows, contract).accepted is True
    assert environment_satisfies_contract(macos, contract).accepted is True
