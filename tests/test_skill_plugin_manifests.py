from faber.attempts import Attempt
from faber.contracts import TaskContract
from faber.digests import sha256_digest
from faber.money import Money
from faber.receipts import VerificationReceipt
from faber.skill_plugins import (
    PermissionDeclaration,
    SkillPluginManifest,
    load_skill_plugin_manifest,
    scan_skill_plugin_manifest,
)

CREATED_AT = "2026-01-01T00:00:00Z"


def test_safe_fixture_passes_and_can_be_bound_to_verifier_receipt() -> None:
    manifest = load_skill_plugin_manifest("tests/fixtures/skill_plugins/safe_skill.json")
    scan = scan_skill_plugin_manifest(
        manifest,
        scan_id="skill-plugin-scan_safe_fixture",
        created_at=CREATED_AT,
    )
    verifier_run = scan.to_verifier_run(verifier_id="verifier.skill-plugin-manifest")
    contract = TaskContract(
        id="task-contract_skill_plugin_scan",
        created_at=CREATED_AT,
        title="Validate skill/plugin manifest",
        description="Check declared platforms, permissions, dependencies, and verifier ids.",
        requirements=["Run manifest scanner."],
        verifier_ids=["verifier.skill-plugin-manifest"],
        task_source="manifest_fixture",
        reward=Money("EUR", 100),
    )
    attempt = Attempt(
        id="attempt_skill_plugin_scan",
        created_at=CREATED_AT,
        task_contract_id=contract.id,
        worker_id="worker_manifest_scanner",
        base_revision="base",
        candidate_revision="candidate",
        summary="Scanned safe fixture.",
        patch_digest=sha256_digest(manifest.to_dict()),
    )
    receipt = VerificationReceipt.from_verifier_run(contract, attempt, verifier_run)

    assert scan.passed is True
    assert scan.issues == []
    assert verifier_run.passed is True
    assert receipt.accepted is True
    assert receipt.verifier_id == "verifier.skill-plugin-manifest"


def test_missing_platform_declaration_is_flagged() -> None:
    manifest = load_skill_plugin_manifest("tests/fixtures/skill_plugins/missing_platform.json")
    scan = scan_skill_plugin_manifest(
        manifest,
        scan_id="skill-plugin-scan_missing_platform",
        created_at=CREATED_AT,
    )

    assert scan.passed is False
    assert any(issue.field == "supported_platforms" for issue in scan.issues)
    assert any("missing platform declaration" in issue.message for issue in scan.issues)


def test_missing_dependency_declaration_is_flagged() -> None:
    manifest = load_skill_plugin_manifest("tests/fixtures/skill_plugins/missing_dependency.json")
    scan = scan_skill_plugin_manifest(
        manifest,
        scan_id="skill-plugin-scan_missing_dependency",
        created_at=CREATED_AT,
    )

    assert scan.passed is False
    assert any(issue.field == "dependencies" for issue in scan.issues)
    assert any("missing dependency declaration: python" == issue.message for issue in scan.issues)


def test_permission_manifest_digest_is_stable() -> None:
    left_permission = PermissionDeclaration(
        id="permission_digest_fixture",
        created_at=CREATED_AT,
        name="read-repository",
        scope="workspace",
        justification="Read fixture files.",
    )
    right_permission = PermissionDeclaration(
        id="permission_digest_fixture",
        created_at=CREATED_AT,
        name="read-repository",
        scope="workspace",
        justification="Read fixture files.",
    )
    left = SkillPluginManifest(
        id="skill-plugin-manifest_digest_fixture",
        created_at=CREATED_AT,
        component_type="skill",
        name="digest-fixture",
        version="1",
        description="Stable digest fixture.",
        supported_platforms=["windows"],
        permissions=[left_permission],
        dependencies=[],
        verifier_ids=["verifier.skill-plugin-manifest"],
    )
    right = SkillPluginManifest(
        id="skill-plugin-manifest_digest_fixture",
        created_at=CREATED_AT,
        component_type="skill",
        name="digest-fixture",
        version="1",
        description="Stable digest fixture.",
        supported_platforms=["windows"],
        permissions=[right_permission],
        dependencies=[],
        verifier_ids=["verifier.skill-plugin-manifest"],
    )

    assert left_permission.digest() == right_permission.digest()
    assert left.digest() == right.digest()
