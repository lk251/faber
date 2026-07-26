"""Publish Faber verification receipts through a fake GitHub boundary."""

from __future__ import annotations

from faber.adapters.github.client import FakeGitHubClient, GitHubPublication
from faber.receipts import VerificationReceipt


def receipt_publication_payload(receipt: VerificationReceipt) -> dict[str, object]:
    result = "accepted" if receipt.accepted else "rejected"
    return {
        "schema": "faber.github.receipt_publication.v1",
        "authority": "faber.verification_receipt",
        "result": result,
        "receipt_id": receipt.id,
        "receipt_digest": receipt.digest(),
        "task_contract_id": receipt.task_contract_id,
        "task_contract_digest": receipt.task_contract_digest,
        "attempt_id": receipt.attempt_id,
        "candidate_revision": receipt.candidate_revision,
        "verifier_id": receipt.verifier_id,
        "result_digest": receipt.result_digest,
        "failure_reasons": receipt.failure_reasons,
    }


def render_receipt_publication_body(receipt: VerificationReceipt) -> str:
    payload = receipt_publication_payload(receipt)
    result = "accepted" if receipt.accepted else "rejected"
    return "\n".join(
        [
            f"Faber verification result: {result}",
            _publication_summary(receipt),
            ("Authority: task-authorized verifier receipt. Candidate CI remains signal only."),
            f"Receipt: {payload['receipt_id']}",
            f"Receipt digest: {payload['receipt_digest']}",
            f"Task contract: {payload['task_contract_id']}",
            f"Task contract digest: {payload['task_contract_digest']}",
            f"Attempt: {payload['attempt_id']}",
            f"Candidate revision: {payload['candidate_revision']}",
            f"Verifier: {payload['verifier_id']}",
            f"Result digest: {payload['result_digest']}",
            _next_action(receipt),
        ]
    )


def _publication_summary(receipt: VerificationReceipt) -> str:
    if receipt.accepted:
        return "Summary: the task-authorized verifier accepted this candidate revision."
    reasons = (
        "; ".join(receipt.failure_reasons) if receipt.failure_reasons else "unspecified failure"
    )
    return (
        "Summary: the task-authorized verifier rejected this candidate revision. "
        f"Failure reasons: {reasons}."
    )


def _next_action(receipt: VerificationReceipt) -> str:
    if receipt.accepted:
        return (
            "Next action: maintainer may review the bound IDs and digests, then apply "
            "merge policy and receipt-gated settlement policy separately."
        )
    return (
        "Next action: inspect verifier failure reasons, update the candidate revision, "
        "and rerun Faber verification."
    )


def publish_verification_receipt(
    client: FakeGitHubClient,
    receipt: VerificationReceipt,
    *,
    repository: str,
    target_kind: str,
    target_number: int | None = None,
) -> GitHubPublication:
    """Record a receipt publication against an issue, PR, or check-like surface."""

    payload = receipt_publication_payload(receipt)
    body = render_receipt_publication_body(receipt)
    if target_kind == "issue":
        if target_number is None:
            raise ValueError("issue publication requires target_number")
        return client.create_issue_comment(
            repository=repository,
            issue_number=target_number,
            body=body,
            payload=payload,
        )
    if target_kind == "pull_request":
        if target_number is None:
            raise ValueError("pull request publication requires target_number")
        return client.create_pull_request_comment(
            repository=repository,
            pull_request_number=target_number,
            body=body,
            payload=payload,
        )
    if target_kind == "check":
        return client.create_check_record(repository=repository, body=body, payload=payload)
    raise ValueError(f"unsupported GitHub publication target: {target_kind}")
