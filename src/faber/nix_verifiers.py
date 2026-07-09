"""Opt-in local verifier policy for Nix replayability evidence."""

from __future__ import annotations

from dataclasses import dataclass, field

from faber.contracts import TaskContract
from faber.digests import sha256_digest
from faber.errors import ValidationError
from faber.validation import (
    require_digest,
    require_mapping,
    require_non_empty_string,
)
from faber.verifiers import VerifierRun, VerifierSpec

PACK_ID = "verifier-pack.nix-reproducibility"
PACK_VERSION = "1"
CREATED_AT = "2026-07-09T00:00:00Z"
NIX_LOCKFILE_VERIFIER_ID = "verifier.nix.lockfile-digest"
MISSING_LOCKFILE_POLICIES = {"warning", "failure"}


@dataclass(frozen=True)
class FakeNixVerifierFixture:
    """Deterministic verifier output for CI systems where Nix is unavailable."""

    verifier_id: str
    exit_code: int
    stdout: str = ""
    stderr: str = ""
    metrics: dict[str, object] = field(default_factory=dict)

    def __post_init__(self) -> None:
        require_non_empty_string(self.verifier_id, "verifier_id")
        if not isinstance(self.exit_code, int) or isinstance(self.exit_code, bool):
            raise ValidationError("exit_code must be an integer")
        if not isinstance(self.stdout, str):
            raise ValidationError("stdout must be a string")
        if not isinstance(self.stderr, str):
            raise ValidationError("stderr must be a string")
        require_mapping(self.metrics, "metrics")

    def to_dict(self) -> dict[str, object]:
        return {
            "verifier_id": self.verifier_id,
            "exit_code": self.exit_code,
            "stdout": self.stdout,
            "stderr": self.stderr,
            "metrics": self.metrics,
        }

    def digest(self) -> str:
        return sha256_digest(self.to_dict())


@dataclass(frozen=True)
class NixVerifierPack:
    """Reusable verifier specs selected explicitly by a task contract."""

    specs: list[VerifierSpec]
    missing_lockfile_policy: str = "failure"
    id: str = PACK_ID
    version: str = PACK_VERSION
    created_at: str = CREATED_AT
    schema: str = "faber.nix_verifier_pack.v1"

    def __post_init__(self) -> None:
        require_non_empty_string(self.id, "id")
        require_non_empty_string(self.version, "version")
        require_non_empty_string(self.created_at, "created_at")
        require_non_empty_string(self.schema, "schema")
        if not self.specs:
            raise ValidationError("Nix verifier pack requires at least one verifier spec")
        verifier_ids = self.verifier_ids
        if len(verifier_ids) != len(set(verifier_ids)):
            raise ValidationError("Nix verifier pack verifier_ids must be unique")
        _require_missing_lockfile_policy(self.missing_lockfile_policy)

    @property
    def verifier_ids(self) -> list[str]:
        return [spec.verifier_id for spec in self.specs]

    def to_dict(self) -> dict[str, object]:
        return {
            "schema": self.schema,
            "id": self.id,
            "version": self.version,
            "created_at": self.created_at,
            "missing_lockfile_policy": self.missing_lockfile_policy,
            "specs": [spec.to_dict() for spec in self.specs],
        }

    def digest(self) -> str:
        return sha256_digest(self.to_dict())

    def contract_requirement(self) -> dict[str, object]:
        """Return the explicit environment requirement stored on an opting-in task."""

        return {
            "pack_id": self.id,
            "pack_version": self.version,
            "pack_digest": self.digest(),
            "required_verifier_ids": self.verifier_ids,
            "missing_lockfile_policy": self.missing_lockfile_policy,
            "execution_scope": "local-verifier-not-production-sandbox",
        }

    def validate_contract(self, contract: TaskContract) -> list[str]:
        """Validate an opted-in task without affecting unrelated contracts."""

        errors: list[str] = []
        raw_requirement = contract.environment.get("nix_verifier_pack")
        if not isinstance(raw_requirement, dict):
            return ["task contract does not opt into a Nix verifier pack"]
        if raw_requirement.get("pack_id") != self.id:
            errors.append("task contract references a different Nix verifier pack")
        if raw_requirement.get("pack_digest") != self.digest():
            errors.append("task contract Nix verifier pack digest does not match")
        declared_ids = raw_requirement.get("required_verifier_ids")
        if declared_ids != self.verifier_ids:
            errors.append("task contract Nix verifier pack references are not canonical")
        for verifier_id in self.verifier_ids:
            if verifier_id not in contract.verifier_ids:
                errors.append(f"task contract is missing Nix verifier reference {verifier_id}")
        return errors


def nix_reproducibility_verifier_pack(
    *,
    package_module: str = "faber",
    cli_command: list[str] | None = None,
    docs_command: list[str] | None = None,
    missing_lockfile_policy: str = "failure",
) -> NixVerifierPack:
    """Build the default six-verifier Nix pack with overridable project smokes."""

    require_non_empty_string(package_module, "package_module")
    _require_missing_lockfile_policy(missing_lockfile_policy)
    cli_smoke = cli_command or ["python", "-m", "faber.cli", "doctor"]
    docs_smoke = docs_command or [
        "python",
        "-m",
        "pytest",
        "tests/test_cli_smoke.py",
        "-q",
    ]
    specs = [
        _spec(
            "verifier.nix.flake-check",
            "Nix flake check",
            "Evaluates the flake and its declared checks.",
            ["nix", "flake", "check"],
            timeout=900,
        ),
        _spec(
            "verifier.nix.develop-smoke",
            "Nix development shell smoke",
            "Starts the declared development shell and runs a deterministic command.",
            ["nix", "develop", "--command", "python", "-c", "print('nix-smoke')"],
            timeout=300,
        ),
        _spec(
            NIX_LOCKFILE_VERIFIER_ID,
            "Nix lockfile digest",
            "Requires flake.lock and emits its Nix content hash.",
            ["nix", "hash", "file", "flake.lock"],
        ),
        _spec(
            "verifier.nix.package-import",
            "Nix package import smoke",
            "Imports the project package inside the development shell.",
            [
                "nix",
                "develop",
                "--command",
                "python",
                "-c",
                f"import {package_module}",
            ],
            timeout=300,
        ),
        _spec(
            "verifier.nix.cli-smoke",
            "Nix local CLI smoke",
            "Runs the project CLI smoke inside the development shell.",
            ["nix", "develop", "--command", *cli_smoke],
            timeout=300,
        ),
        _spec(
            "verifier.nix.docs-command",
            "Nix documentation command validation",
            "Runs the project's executable documentation command checks.",
            ["nix", "develop", "--command", *docs_smoke],
            timeout=300,
        ),
    ]
    return NixVerifierPack(
        specs=specs,
        missing_lockfile_policy=missing_lockfile_policy,
    )


def evaluate_fake_nix_verifier(
    spec: VerifierSpec,
    fixture: FakeNixVerifierFixture,
) -> VerifierRun:
    """Convert a fake fixture into an ordinary digest-bound verifier run."""

    if fixture.verifier_id != spec.verifier_id:
        raise ValidationError("fake Nix fixture verifier_id does not match verifier spec")
    failure_reasons = (
        []
        if fixture.exit_code == 0
        else [f"fake Nix verifier exited with code {fixture.exit_code}"]
    )
    return _fixture_run(spec, fixture, failure_reasons=failure_reasons)


def evaluate_fake_nix_lockfile(
    spec: VerifierSpec,
    *,
    lockfile_digest: str | None,
    policy: str,
) -> VerifierRun:
    """Evaluate lockfile evidence in fake mode under warning/failure policy."""

    if spec.verifier_id != NIX_LOCKFILE_VERIFIER_ID:
        raise ValidationError("lockfile evaluation requires the Nix lockfile verifier spec")
    _require_missing_lockfile_policy(policy)
    if lockfile_digest is not None:
        require_digest(lockfile_digest, "lockfile_digest")
        fixture = FakeNixVerifierFixture(
            verifier_id=spec.verifier_id,
            exit_code=0,
            stdout=f"{lockfile_digest}\n",
            metrics={
                "lockfile_present": True,
                "lockfile_digest": lockfile_digest,
                "status": "passed",
                "missing_lockfile_policy": policy,
            },
        )
        return _fixture_run(spec, fixture, failure_reasons=[])
    passed = policy == "warning"
    fixture = FakeNixVerifierFixture(
        verifier_id=spec.verifier_id,
        exit_code=0 if passed else 1,
        stderr="flake.lock is missing\n",
        metrics={
            "lockfile_present": False,
            "status": "warning" if passed else "failed",
            "missing_lockfile_policy": policy,
        },
    )
    return _fixture_run(
        spec,
        fixture,
        failure_reasons=[] if passed else ["flake.lock is missing"],
    )


def _spec(
    verifier_id: str,
    name: str,
    description: str,
    command: list[str],
    *,
    timeout: int = 60,
) -> VerifierSpec:
    suffix = verifier_id.removeprefix("verifier.nix.").replace(".", "-")
    return VerifierSpec(
        id=f"verifier-spec_nix_{suffix}",
        created_at=CREATED_AT,
        verifier_id=verifier_id,
        name=name,
        version=PACK_VERSION,
        description=description,
        command_template=command,
        allowed_timeout_seconds=timeout,
    )


def _fixture_run(
    spec: VerifierSpec,
    fixture: FakeNixVerifierFixture,
    *,
    failure_reasons: list[str],
) -> VerifierRun:
    logs_digest = sha256_digest({"stdout": fixture.stdout, "stderr": fixture.stderr})
    return VerifierRun(
        id=f"verifier-run_fake_{fixture.digest().split(':', 1)[1][:24]}",
        created_at=CREATED_AT,
        verifier_id=spec.verifier_id,
        name=spec.name,
        version=spec.version,
        command=spec.command(),
        passed=fixture.exit_code == 0,
        metrics={
            **fixture.metrics,
            "execution_mode": "fake",
            "exit_code": fixture.exit_code,
            "output_digest": logs_digest,
        },
        failure_reasons=failure_reasons,
        logs_digest=logs_digest,
        metadata={
            "verifier_spec_digest": spec.digest(),
            "fixture_digest": fixture.digest(),
            "local_verifier_only": True,
            "production_sandbox": False,
        },
    )


def _require_missing_lockfile_policy(policy: str) -> str:
    if policy not in MISSING_LOCKFILE_POLICIES:
        raise ValidationError(
            f"missing lockfile policy must be one of {sorted(MISSING_LOCKFILE_POLICIES)}"
        )
    return policy
