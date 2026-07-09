"""GitHub task templates rendered into provider-neutral contracts."""

from faber.templates import (
    TaskContractTemplate,
    VerificationPolicy,
    pr_only_evidence_preset,
)


def github_bug_template() -> TaskContractTemplate:
    return TaskContractTemplate(
        name="github-bugfix",
        template_kind="bugfix",
        requirements=["Resolve the issue.", "Pass hard tests and lint checks."],
        verification_policy=VerificationPolicy(
            hard_verifier_ids=["verifier.tests", "verifier.lint"],
        ),
        evidence_preset=pr_only_evidence_preset(),
        task_source="github.issue",
        default_environment={"adapter": "github"},
    )
