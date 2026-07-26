from dataclasses import replace

from faber.environments import environment_satisfies_contract, reproducibility_rank
from faber.platform_fixtures import (
    cross_platform_harness_fixtures,
    validate_cross_platform_harness_fixtures,
)
from faber.trajectory_quality import validate_trajectory_quality


def test_all_cross_platform_fixtures_validate() -> None:
    fixtures = cross_platform_harness_fixtures()

    assert {fixture.platform_family for fixture in fixtures} == {
        "nixos",
        "linux",
        "macos",
        "windows",
        "container",
        "remote-runner",
    }
    assert validate_cross_platform_harness_fixtures(fixtures) == []
    assert all(
        validate_trajectory_quality(fixture.trajectory_record).is_rl_grade for fixture in fixtures
    )


def test_nix_fixture_has_the_strongest_replay_evidence() -> None:
    fixtures = cross_platform_harness_fixtures()
    nix = next(fixture for fixture in fixtures if fixture.platform_family == "nixos")
    other_ranks = [
        reproducibility_rank(fixture.environment_evidence.reproducibility_level)
        for fixture in fixtures
        if fixture.platform_family != "nixos"
    ]

    assert nix.environment_evidence.reproducibility_level == "nix_flake"
    assert nix.environment_evidence.nix_flake_lock_digest is not None
    assert reproducibility_rank("nix_flake") > max(other_ranks)


def test_desktop_platform_traces_remain_training_eligible() -> None:
    fixtures = cross_platform_harness_fixtures()

    for platform in ["linux", "macos", "windows"]:
        fixture = next(item for item in fixtures if item.platform_family == platform)
        report = validate_trajectory_quality(fixture.trajectory_record)

        assert report.training_eligibility.allows("rl")
        assert report.process_evidence.satisfies_rl_process
        assert report.is_rl_grade
        assert report.environment_replayability.level == "lockfile"


def test_platform_specific_contract_rejects_incompatible_attempt() -> None:
    windows = next(
        fixture
        for fixture in cross_platform_harness_fixtures()
        if fixture.platform_family == "windows"
    )
    nix_only = replace(
        windows.contract,
        title="NixOS-only fixture",
        description="Validate an attempt that requires NixOS replay evidence.",
        requirements=["Run under NixOS."],
        environment={
            **windows.contract.environment,
            "required_platforms": ["nixos"],
            "minimum_reproducibility_level": "nix_flake",
        },
    )

    fit = environment_satisfies_contract(windows.environment_evidence, nix_only)

    assert fit.accepted is False
    assert fit.platform_match is False
    assert fit.reproducibility_match is False
