"""Router decision records."""

from __future__ import annotations

from dataclasses import dataclass, field

from faber import schemas
from faber.contracts import TaskContract
from faber.digests import sha256_digest
from faber.ids import new_id, utc_now
from faber.money import Money
from faber.validation import (
    require_mapping,
    require_non_empty_string,
    require_schema,
    require_sequence,
)
from faber.workers import (
    PLATFORM_SUPPORT,
    WorkerProfile,
    WorkerRegistry,
    worker_metadata_trust_score,
    worker_supported_platforms,
)


@dataclass(frozen=True)
class RouterDecision:
    """A record of how Faber selected a worker or orchestration policy."""

    task_contract_id: str
    selected_worker_id: str
    rejected_alternatives: list[dict[str, object]]
    estimated_cost: Money
    expected_value: Money
    policy_name: str
    policy_version: str = "1"
    decision_factors: dict[str, object] = field(default_factory=dict)
    id: str = field(default_factory=lambda: new_id("router-decision"))
    created_at: str = field(default_factory=utc_now)
    schema: str = schemas.ROUTER_DECISION

    def __post_init__(self) -> None:
        require_schema(self.schema, schemas.ROUTER_DECISION)
        require_non_empty_string(self.id, "id")
        require_non_empty_string(self.created_at, "created_at")
        require_non_empty_string(self.task_contract_id, "task_contract_id")
        require_non_empty_string(self.selected_worker_id, "selected_worker_id")
        require_sequence(self.rejected_alternatives, "rejected_alternatives")
        require_non_empty_string(self.policy_name, "policy_name")
        require_non_empty_string(self.policy_version, "policy_version")
        require_mapping(self.decision_factors, "decision_factors")

    def to_dict(self) -> dict[str, object]:
        return {
            "schema": self.schema,
            "id": self.id,
            "created_at": self.created_at,
            "task_contract_id": self.task_contract_id,
            "selected_worker_id": self.selected_worker_id,
            "rejected_alternatives": self.rejected_alternatives,
            "estimated_cost": self.estimated_cost.to_dict(),
            "expected_value": self.expected_value.to_dict(),
            "policy_name": self.policy_name,
            "policy_version": self.policy_version,
            "decision_factors": self.decision_factors,
        }

    def digest(self) -> str:
        return sha256_digest(self.to_dict())


@dataclass(frozen=True)
class WorkerScore:
    worker_id: str
    score: int
    estimated_cost: Money
    expected_value: Money
    factors: dict[str, object]


class BaselineRouter:
    """Deterministic value-oriented baseline router."""

    policy_name = "baseline-value-router"
    policy_version = "1"

    def route(
        self,
        contract: TaskContract,
        registry: WorkerRegistry,
        *,
        currency: str = "EUR",
    ) -> RouterDecision:
        workers = [
            worker
            for worker in registry.list_workers()
            if worker.availability_status == "available"
            and (
                not worker.supported_task_sources
                or contract.task_source in worker.supported_task_sources
            )
            and _supports_required_platforms(worker, _required_platforms(contract))
        ]
        if not workers:
            raise ValueError("no available workers support this task")
        scores = [score_worker(contract, worker, currency=currency) for worker in workers]
        scores.sort(key=lambda item: (-item.score, item.estimated_cost.minor_units, item.worker_id))
        selected = scores[0]
        rejected = [
            {
                "worker_id": score.worker_id,
                "score": score.score,
                "estimated_cost": score.estimated_cost.to_dict(),
                "expected_value": score.expected_value.to_dict(),
                "decision_factors": score.factors,
            }
            for score in scores[1:]
        ]
        return RouterDecision(
            task_contract_id=contract.id,
            selected_worker_id=selected.worker_id,
            rejected_alternatives=rejected,
            estimated_cost=selected.estimated_cost,
            expected_value=selected.expected_value,
            policy_name=self.policy_name,
            policy_version=self.policy_version,
            decision_factors=selected.factors,
        )


def score_worker(
    contract: TaskContract,
    worker: WorkerProfile,
    *,
    currency: str = "EUR",
) -> WorkerScore:
    task_text = " ".join([contract.title, contract.description, *contract.requirements]).casefold()
    required_platforms = _required_platforms(contract)
    supported_platforms = worker_supported_platforms(worker)
    platform_matches = [
        platform
        for platform in required_platforms
        if _platform_requirement_satisfied(platform, supported_platforms)
    ]
    capability_matches = [
        capability
        for capability in worker.capabilities
        if capability.casefold() in task_text
        or capability.casefold() in {item.casefold() for item in worker.supported_languages}
    ]
    source_match = (
        not worker.supported_task_sources or contract.task_source in worker.supported_task_sources
    )
    accepted = _int_value(worker.reputation.get("accepted_attempts", 0))
    rejected = _int_value(worker.reputation.get("rejected_attempts", 0))
    verifier_failures = _int_value(worker.reputation.get("verifier_failures", 0))
    estimated_cost = worker.cost_model or Money(currency, 0)
    capability_score = len(capability_matches) * 100
    platform_score = len(platform_matches) * 75
    source_score = 50 if source_match else -100
    reputation_score = accepted * 20 - rejected * 30 - verifier_failures * 20
    metadata_trust_score = worker_metadata_trust_score(worker)
    expected_minor_units = max(
        0,
        5000
        + capability_score * 20
        + platform_score * 20
        + reputation_score * 10
        + source_score * 10
        + metadata_trust_score * 10,
    )
    expected_value = Money(estimated_cost.currency, expected_minor_units)
    score = expected_value.minor_units - estimated_cost.minor_units
    return WorkerScore(
        worker_id=worker.id,
        score=score,
        estimated_cost=estimated_cost,
        expected_value=expected_value,
        factors={
            "capability_matches": capability_matches,
            "source_match": source_match,
            "accepted_attempts": accepted,
            "rejected_attempts": rejected,
            "verifier_failures": verifier_failures,
            "required_platforms": required_platforms,
            "supported_platforms": supported_platforms,
            "platform_matches": platform_matches,
            "metadata_trust_score": metadata_trust_score,
            "score": score,
        },
    )


def route_task(
    contract: TaskContract,
    registry: WorkerRegistry,
    *,
    currency: str = "EUR",
) -> RouterDecision:
    return BaselineRouter().route(contract, registry, currency=currency)


def _int_value(value: object) -> int:
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, int):
        return value
    if isinstance(value, str) and value.isdigit():
        return int(value)
    return 0


def _required_platforms(contract: TaskContract) -> list[str]:
    platforms: set[str] = set()
    required = contract.environment.get("required_platforms")
    if isinstance(required, list):
        platforms.update(_normalize_platform(item) for item in required if isinstance(item, str))
    platform = contract.environment.get("platform")
    if isinstance(platform, str):
        platforms.add(_normalize_platform(platform))
    task_text = " ".join([contract.title, contract.description, *contract.requirements]).casefold()
    for known_platform in PLATFORM_SUPPORT:
        if known_platform in task_text:
            platforms.add(known_platform)
    return sorted(platforms)


def _supports_required_platforms(worker: WorkerProfile, required_platforms: list[str]) -> bool:
    if not required_platforms:
        return True
    supported_platforms = worker_supported_platforms(worker)
    return all(
        _platform_requirement_satisfied(platform, supported_platforms)
        for platform in required_platforms
    )


def _platform_requirement_satisfied(platform: str, supported_platforms: list[str]) -> bool:
    if platform in supported_platforms:
        return True
    return platform == "linux" and "nixos" in supported_platforms


def _normalize_platform(value: str) -> str:
    normalized = value.strip().casefold().replace("_", "-")
    aliases = {
        "darwin": "macos",
        "mac-os": "macos",
        "mac": "macos",
        "nix": "nixos",
        "remote": "remote-runner",
    }
    return aliases.get(normalized, normalized)
