import pytest

from faber.adapters.github.contracts import issue_to_task_contract
from faber.adapters.github.events import GitHubIssueRef
from faber.adapters.github.installation import GitHubInstallation
from faber.attempts import Attempt
from faber.contracts import TaskContract
from faber.digests import sha256_digest
from faber.errors import ScopeError, SettlementError, ValidationError
from faber.money import Money
from faber.receipts import VerificationReceipt
from faber.settlement import Settlement


def test_invalid_digest_strings_fail_early() -> None:
    with pytest.raises(ValidationError, match="patch_digest.*sha256"):
        Attempt(
            task_contract_id="task-contract",
            worker_id="worker",
            base_revision="base",
            candidate_revision="candidate",
            summary="Bad digest",
            patch_digest="not-a-digest",
        )


def test_empty_ids_fail_with_field_name() -> None:
    with pytest.raises(ValidationError, match="id"):
        TaskContract(
            id="",
            title="No id",
            description="Invalid contract.",
            requirements=["have id"],
            verifier_ids=["verifier"],
        )


def test_settlement_failure_uses_settlement_error_type() -> None:
    receipt = VerificationReceipt(
        task_contract_id="task-contract",
        task_contract_digest=sha256_digest({"contract": 1}),
        attempt_id="attempt",
        worker_id="worker",
        verifier_id="verifier",
        verifier_digest=sha256_digest({"verifier": 1}),
        base_revision="base",
        candidate_revision="candidate",
        accepted=False,
        metrics={},
        failure_reasons=["failed"],
        result_digest=sha256_digest({"accepted": False}),
    )
    settlement = Settlement.from_receipt(receipt, Money("EUR", 1000))

    with pytest.raises(SettlementError, match="cannot mark rejected work as paid"):
        settlement.mark_paid(receipt)


def test_github_scope_failure_uses_scope_error_type() -> None:
    installation = GitHubInstallation(
        installation_id=123,
        account_login="lk251",
        selected_repository_full_names=["lk251/faber"],
        permissions={"issues": "read"},
    )

    with pytest.raises(ScopeError, match="outside the GitHub installation scope"):
        issue_to_task_contract(
            GitHubIssueRef(
                repository_full_name="lk251/other",
                issue_number=1,
                title="Out of scope",
                body="Should fail.",
            ),
            installation=installation,
            verifier_ids=["verifier"],
        )


def test_metadata_extensions_remain_allowed() -> None:
    contract = TaskContract(
        title="Extensible metadata",
        description="Keep adapter metadata flexible.",
        requirements=["allow metadata"],
        verifier_ids=["verifier"],
        environment={
            "adapter": "github",
            "labels": ["triage"],
            "future_extension": {"arbitrary": True, "count": 1},
        },
    )

    assert contract.environment["future_extension"] == {"arbitrary": True, "count": 1}
