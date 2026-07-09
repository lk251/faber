"""Data-only task templates, verification policy, and evidence/budget presets."""

from __future__ import annotations

from dataclasses import dataclass, field

from faber import schemas
from faber.budgets import FundingSource, RefundPolicy, WorkBudget
from faber.contracts import TaskContract
from faber.digests import sha256_digest
from faber.errors import ValidationError
from faber.ids import new_id, utc_now
from faber.money import Money
from faber.trajectory_quality import TRAJECTORY_QUALITY_ORDER, TrajectoryRequirement
from faber.validation import (
    require_mapping,
    require_non_empty_string,
    require_schema,
    require_string_list,
)

HUMAN_REVIEW_MODES = {"none", "advisory", "authoritative", "supplementary"}


@dataclass(frozen=True)
class VerificationPolicy:
    hard_verifier_ids: list[str]
    human_review: str = "none"
    advisory_ranking: bool = False
    human_can_override_hard_failure: bool = False
    authoritative_probabilistic_verifier_ids: list[str] = field(default_factory=list)
    budget_constraints: dict[str, object] = field(default_factory=dict)
    schema: str = schemas.VERIFICATION_POLICY

    def __post_init__(self) -> None:
        require_schema(self.schema, schemas.VERIFICATION_POLICY)
        require_string_list(
            self.hard_verifier_ids,
            "hard_verifier_ids",
            allow_empty=False,
        )
        if self.human_review not in HUMAN_REVIEW_MODES:
            raise ValidationError(
                f"human_review must be one of {sorted(HUMAN_REVIEW_MODES)}"
            )
        if not isinstance(self.advisory_ranking, bool):
            raise ValidationError("advisory_ranking must be a boolean")
        if not isinstance(self.human_can_override_hard_failure, bool):
            raise ValidationError("human_can_override_hard_failure must be a boolean")
        require_string_list(
            self.authoritative_probabilistic_verifier_ids,
            "authoritative_probabilistic_verifier_ids",
        )
        require_mapping(self.budget_constraints, "budget_constraints")

    def to_dict(self) -> dict[str, object]:
        return {
            "schema": self.schema,
            "hard_verifier_ids": self.hard_verifier_ids,
            "human_review": self.human_review,
            "advisory_ranking": self.advisory_ranking,
            "human_can_override_hard_failure": self.human_can_override_hard_failure,
            "authoritative_probabilistic_verifier_ids": (
                self.authoritative_probabilistic_verifier_ids
            ),
            "budget_constraints": self.budget_constraints,
        }

    @classmethod
    def from_dict(cls, payload: dict[str, object]) -> VerificationPolicy:
        return cls(
            hard_verifier_ids=require_string_list(
                payload.get("hard_verifier_ids"),
                "hard_verifier_ids",
                allow_empty=False,
            ),
            human_review=_string_default(payload, "human_review", "none"),
            advisory_ranking=_bool_default(payload, "advisory_ranking", False),
            human_can_override_hard_failure=_bool_default(
                payload,
                "human_can_override_hard_failure",
                False,
            ),
            authoritative_probabilistic_verifier_ids=require_string_list(
                payload.get("authoritative_probabilistic_verifier_ids", []),
                "authoritative_probabilistic_verifier_ids",
            ),
            budget_constraints=dict(
                require_mapping(
                    payload.get("budget_constraints", {}),
                    "budget_constraints",
                )
            ),
            schema=_string_default(payload, "schema", schemas.VERIFICATION_POLICY),
        )


@dataclass(frozen=True)
class EvidenceRequirementPreset:
    name: str
    minimum_quality_tier: str
    allowed_quality_tiers: list[str]
    require_rl_grade: bool = False
    require_training_eligible: bool = False
    environment_requirements: dict[str, object] = field(default_factory=dict)
    schema: str = schemas.EVIDENCE_REQUIREMENT_PRESET

    def __post_init__(self) -> None:
        require_schema(self.schema, schemas.EVIDENCE_REQUIREMENT_PRESET)
        require_non_empty_string(self.name, "name")
        if self.minimum_quality_tier not in TRAJECTORY_QUALITY_ORDER:
            raise ValidationError("minimum_quality_tier is invalid")
        tiers = require_string_list(
            self.allowed_quality_tiers,
            "allowed_quality_tiers",
            allow_empty=False,
        )
        if any(tier not in TRAJECTORY_QUALITY_ORDER for tier in tiers):
            raise ValidationError("allowed_quality_tiers contains an invalid tier")
        if self.minimum_quality_tier not in tiers:
            raise ValidationError("allowed_quality_tiers must include minimum_quality_tier")
        if not isinstance(self.require_rl_grade, bool):
            raise ValidationError("require_rl_grade must be a boolean")
        if not isinstance(self.require_training_eligible, bool):
            raise ValidationError("require_training_eligible must be a boolean")
        require_mapping(self.environment_requirements, "environment_requirements")

    def trajectory_requirement(self) -> TrajectoryRequirement:
        return TrajectoryRequirement(
            id=f"trajectory-requirement_preset_{self.name}",
            created_at="1970-01-01T00:00:00Z",
            minimum_quality_tier=self.minimum_quality_tier,
            require_rl_grade=self.require_rl_grade,
            require_training_eligible=self.require_training_eligible,
        )

    def to_dict(self) -> dict[str, object]:
        return {
            "schema": self.schema,
            "name": self.name,
            "minimum_quality_tier": self.minimum_quality_tier,
            "allowed_quality_tiers": self.allowed_quality_tiers,
            "require_rl_grade": self.require_rl_grade,
            "require_training_eligible": self.require_training_eligible,
            "environment_requirements": self.environment_requirements,
        }

    @classmethod
    def from_dict(cls, payload: dict[str, object]) -> EvidenceRequirementPreset:
        return cls(
            name=require_non_empty_string(payload.get("name"), "name"),
            minimum_quality_tier=require_non_empty_string(
                payload.get("minimum_quality_tier"),
                "minimum_quality_tier",
            ),
            allowed_quality_tiers=require_string_list(
                payload.get("allowed_quality_tiers"),
                "allowed_quality_tiers",
                allow_empty=False,
            ),
            require_rl_grade=_bool_default(payload, "require_rl_grade", False),
            require_training_eligible=_bool_default(
                payload,
                "require_training_eligible",
                False,
            ),
            environment_requirements=dict(
                require_mapping(
                    payload.get("environment_requirements", {}),
                    "environment_requirements",
                )
            ),
            schema=_string_default(
                payload,
                "schema",
                schemas.EVIDENCE_REQUIREMENT_PRESET,
            ),
        )


@dataclass(frozen=True)
class BudgetPreset:
    name: str
    amount: Money
    purpose_allocations: dict[str, Money]
    trace_quality_bonus_policy: dict[str, object] = field(default_factory=dict)

    def __post_init__(self) -> None:
        require_non_empty_string(self.name, "name")
        if not isinstance(self.amount, Money):
            raise ValidationError("amount must be Money")
        require_mapping(self.purpose_allocations, "purpose_allocations")
        allocated_minor_units = sum(
            item.minor_units for item in self.purpose_allocations.values()
        )
        if allocated_minor_units > self.amount.minor_units:
            raise ValidationError("purpose allocations cannot exceed preset amount")
        require_mapping(
            self.trace_quality_bonus_policy,
            "trace_quality_bonus_policy",
        )

    def create_budget(
        self,
        *,
        funding_source: FundingSource,
        target_kind: str,
        target_ref: str,
        verification_policy: VerificationPolicy,
        budget_id: str | None = None,
        created_at: str | None = None,
    ) -> WorkBudget:
        if funding_source.currency != self.amount.currency:
            raise ValidationError("funding source currency must match budget preset")
        return WorkBudget(
            id=budget_id or new_id("work-budget"),
            created_at=created_at or utc_now(),
            funding_source_id=funding_source.id,
            amount=self.amount,
            target_kind=target_kind,
            target_ref=target_ref,
            verifier_policy={
                "required_verifier_ids": verification_policy.hard_verifier_ids,
                "human_review": verification_policy.human_review,
                "advisory_ranking": verification_policy.advisory_ranking,
                "budget_constraints": verification_policy.budget_constraints,
            },
            purpose_allocations=dict(self.purpose_allocations),
            refund_policy=RefundPolicy(
                id=f"refund-policy_preset_{self.name}",
                created_at=created_at or utc_now(),
            ),
            metadata={"budget_preset": self.name},
        )

    def marker_binding(
        self,
        contract: TaskContract,
        budget: WorkBudget,
    ) -> dict[str, object]:
        if budget.metadata.get("budget_preset") != self.name:
            raise ValidationError("work budget is not bound to this budget preset")
        return {
            "preset": self.name,
            "task_contract_id": contract.id,
            "task_contract_digest": contract.digest(),
            "work_budget_id": budget.id,
            "work_budget_digest": budget.digest(),
        }

    def to_dict(self) -> dict[str, object]:
        return {
            "name": self.name,
            "amount": self.amount.to_dict(),
            "purpose_allocations": {
                name: amount.to_dict()
                for name, amount in sorted(self.purpose_allocations.items())
            },
            "trace_quality_bonus_policy": self.trace_quality_bonus_policy,
        }


@dataclass(frozen=True)
class TaskContractTemplate:
    name: str
    template_kind: str
    requirements: list[str]
    verification_policy: VerificationPolicy
    evidence_preset: EvidenceRequirementPreset
    task_source: str = "template"
    default_environment: dict[str, object] = field(default_factory=dict)
    schema: str = schemas.TASK_CONTRACT_TEMPLATE

    def __post_init__(self) -> None:
        require_schema(self.schema, schemas.TASK_CONTRACT_TEMPLATE)
        require_non_empty_string(self.name, "name")
        require_non_empty_string(self.template_kind, "template_kind")
        require_string_list(self.requirements, "requirements", allow_empty=False)
        if not isinstance(self.verification_policy, VerificationPolicy):
            raise ValidationError("verification_policy must be a VerificationPolicy")
        if not isinstance(self.evidence_preset, EvidenceRequirementPreset):
            raise ValidationError("evidence_preset must be an EvidenceRequirementPreset")
        require_non_empty_string(self.task_source, "task_source")
        require_mapping(self.default_environment, "default_environment")

    def render(
        self,
        *,
        title: str,
        description: str,
        repository: str | None = None,
        environment: dict[str, object] | None = None,
        reward: Money | None = None,
        contract_id: str | None = None,
        created_at: str | None = None,
    ) -> TaskContract:
        rendered_environment = dict(self.default_environment)
        rendered_environment.update(self.evidence_preset.environment_requirements)
        if environment:
            rendered_environment.update(environment)
        rendered_environment["task_type"] = self.template_kind
        rendered_environment["verification_policy"] = self.verification_policy.to_dict()
        return TaskContract(
            id=contract_id or new_id("task-contract"),
            created_at=created_at or utc_now(),
            title=title,
            description=description,
            requirements=list(self.requirements),
            verifier_ids=list(self.verification_policy.hard_verifier_ids),
            task_source=self.task_source,
            repository=repository,
            environment=rendered_environment,
            trajectory_requirement=self.evidence_preset.trajectory_requirement().to_dict(),
            reward=reward,
        )

    def to_dict(self) -> dict[str, object]:
        return {
            "schema": self.schema,
            "name": self.name,
            "template_kind": self.template_kind,
            "requirements": self.requirements,
            "verification_policy": self.verification_policy.to_dict(),
            "evidence_preset": self.evidence_preset.to_dict(),
            "task_source": self.task_source,
            "default_environment": self.default_environment,
        }

    def digest(self) -> str:
        return sha256_digest(self.to_dict())

    @classmethod
    def from_dict(cls, payload: dict[str, object]) -> TaskContractTemplate:
        allowed = {
            "schema",
            "name",
            "template_kind",
            "requirements",
            "verification_policy",
            "evidence_preset",
            "task_source",
            "default_environment",
        }
        unsupported = sorted(set(payload) - allowed)
        if unsupported:
            raise ValidationError(f"unsupported template fields: {unsupported}")
        verification = payload.get("verification_policy")
        evidence = payload.get("evidence_preset")
        if not isinstance(verification, dict):
            raise ValidationError("verification_policy must be a mapping")
        if not isinstance(evidence, dict):
            raise ValidationError("evidence_preset must be a mapping")
        return cls(
            name=require_non_empty_string(payload.get("name"), "name"),
            template_kind=require_non_empty_string(
                payload.get("template_kind"),
                "template_kind",
            ),
            requirements=require_string_list(
                payload.get("requirements"),
                "requirements",
                allow_empty=False,
            ),
            verification_policy=VerificationPolicy.from_dict(verification),
            evidence_preset=EvidenceRequirementPreset.from_dict(evidence),
            task_source=_string_default(payload, "task_source", "template"),
            default_environment=dict(
                require_mapping(
                    payload.get("default_environment", {}),
                    "default_environment",
                )
            ),
            schema=_string_default(payload, "schema", schemas.TASK_CONTRACT_TEMPLATE),
        )


def pr_only_evidence_preset() -> EvidenceRequirementPreset:
    return EvidenceRequirementPreset(
        name="pr-only",
        minimum_quality_tier="pr_only",
        allowed_quality_tiers=["pr_only", "manifest", "trace", "episode"],
    )


def rl_grade_evidence_preset() -> EvidenceRequirementPreset:
    return EvidenceRequirementPreset(
        name="rl-grade",
        minimum_quality_tier="trace",
        allowed_quality_tiers=["trace", "episode"],
        require_rl_grade=True,
        require_training_eligible=True,
    )


def bugfix_template() -> TaskContractTemplate:
    return TaskContractTemplate(
        name="bugfix",
        template_kind="bugfix",
        requirements=["Implement the fix.", "Pass hard tests and lint checks."],
        verification_policy=VerificationPolicy(
            hard_verifier_ids=["verifier.tests", "verifier.lint"],
        ),
        evidence_preset=pr_only_evidence_preset(),
    )


def documentation_template() -> TaskContractTemplate:
    return TaskContractTemplate(
        name="documentation",
        template_kind="documentation",
        requirements=["Update the requested documentation.", "Pass documentation checks."],
        verification_policy=VerificationPolicy(
            hard_verifier_ids=["verifier.docs"],
            human_review="supplementary",
        ),
        evidence_preset=pr_only_evidence_preset(),
    )


def nixos_harness_template() -> TaskContractTemplate:
    return TaskContractTemplate(
        name="nixos-harness",
        template_kind="harness",
        requirements=["Provide reproducible package evidence.", "Pass harness smoke checks."],
        verification_policy=VerificationPolicy(
            hard_verifier_ids=["verifier.nix.flake", "verifier.harness.smoke"],
        ),
        evidence_preset=EvidenceRequirementPreset(
            name="nixos-trace",
            minimum_quality_tier="trace",
            allowed_quality_tiers=["trace", "episode"],
            environment_requirements={
                "required_platforms": ["nixos"],
                "require_lock_digest": True,
            },
        ),
    )


def rl_grade_template() -> TaskContractTemplate:
    return TaskContractTemplate(
        name="rl-grade-work",
        template_kind="training-eligible-work",
        requirements=["Pass hard verification.", "Provide RL-grade process evidence."],
        verification_policy=VerificationPolicy(
            hard_verifier_ids=["verifier.tests"],
        ),
        evidence_preset=rl_grade_evidence_preset(),
    )


def _string_default(payload: dict[str, object], field_name: str, default: str) -> str:
    value = payload.get(field_name, default)
    if not isinstance(value, str):
        raise ValidationError(f"{field_name} must be a string")
    return require_non_empty_string(value, field_name)


def _bool_default(payload: dict[str, object], field_name: str, default: bool) -> bool:
    value = payload.get(field_name, default)
    if not isinstance(value, bool):
        raise ValidationError(f"{field_name} must be a boolean")
    return value
