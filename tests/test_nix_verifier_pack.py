from dataclasses import replace

from faber.contracts import TaskContract
from faber.digests import sha256_digest
from faber.nix_verifiers import (
    NIX_LOCKFILE_VERIFIER_ID,
    FakeNixVerifierFixture,
    evaluate_fake_nix_lockfile,
    evaluate_fake_nix_verifier,
    nix_reproducibility_verifier_pack,
)


def _contract() -> TaskContract:
    pack = nix_reproducibility_verifier_pack()
    return TaskContract(
        id="task-contract_nix_pack_test",
        created_at="2026-07-09T00:00:00Z",
        title="Opt-in Nix verifier pack test",
        description="Exercise a replayable task under an explicitly selected Nix pack.",
        requirements=["Pass the selected reproducibility verifier pack."],
        verifier_ids=pack.verifier_ids,
        environment={
            "required_platforms": ["nixos"],
            "minimum_reproducibility_level": "nix_flake",
            "nix_verifier_pack": pack.contract_requirement(),
        },
    )


def test_nix_verifier_spec_digests_are_stable() -> None:
    first = nix_reproducibility_verifier_pack()
    second = nix_reproducibility_verifier_pack()

    assert first.digest() == second.digest()
    assert [spec.digest() for spec in first.specs] == [spec.digest() for spec in second.specs]
    assert len(first.specs) == 6


def test_task_requiring_nix_pack_validates_verifier_references() -> None:
    pack = nix_reproducibility_verifier_pack()
    contract = _contract()

    assert pack.validate_contract(contract) == []

    missing_reference = replace(contract, verifier_ids=contract.verifier_ids[:-1])
    assert pack.validate_contract(missing_reference) == [
        f"task contract is missing Nix verifier reference {pack.verifier_ids[-1]}"
    ]


def test_fake_nix_verifier_success_and_failure_are_digest_bound() -> None:
    spec = nix_reproducibility_verifier_pack().specs[0]
    success = evaluate_fake_nix_verifier(
        spec,
        FakeNixVerifierFixture(
            verifier_id=spec.verifier_id,
            exit_code=0,
            stdout="all checks passed\n",
            metrics={"checks": 4},
        ),
    )
    failure = evaluate_fake_nix_verifier(
        spec,
        FakeNixVerifierFixture(
            verifier_id=spec.verifier_id,
            exit_code=1,
            stderr="evaluation failed\n",
            metrics={"checks": 1},
        ),
    )

    assert success.passed is True
    assert success.metrics["execution_mode"] == "fake"
    assert success.logs_digest == sha256_digest({"stdout": "all checks passed\n", "stderr": ""})
    assert failure.passed is False
    assert failure.failure_reasons == ["fake Nix verifier exited with code 1"]
    assert success.result_digest() != failure.result_digest()


def test_missing_lockfile_warns_or_fails_by_policy() -> None:
    pack = nix_reproducibility_verifier_pack()
    lock_spec = next(spec for spec in pack.specs if spec.verifier_id == NIX_LOCKFILE_VERIFIER_ID)

    warning = evaluate_fake_nix_lockfile(lock_spec, lockfile_digest=None, policy="warning")
    failure = evaluate_fake_nix_lockfile(lock_spec, lockfile_digest=None, policy="failure")
    present = evaluate_fake_nix_lockfile(
        lock_spec,
        lockfile_digest=sha256_digest("flake.lock fixture"),
        policy="failure",
    )

    assert warning.passed is True
    assert warning.metrics["status"] == "warning"
    assert failure.passed is False
    assert failure.failure_reasons == ["flake.lock is missing"]
    assert present.passed is True
    assert present.metrics["lockfile_present"] is True
