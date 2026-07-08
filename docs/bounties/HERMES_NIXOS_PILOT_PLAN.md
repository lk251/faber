# Hermes Nix/NixOS pilot plan

Plan date: 2026-07-08.

Selected default target: [NousResearch/hermes-agent #48628](https://github.com/NousResearch/hermes-agent/issues/48628),
`perf: lazy_deps runs the ensurepip->pip bootstrap on every launch for managed/read-only installs (NixOS)`.

This is a Faber pilot design, not an upstream commitment. Re-check issue state,
comments, and current Hermes code before implementation. Do not claim Hermes
lacks tier-one NixOS support unless upstream maintainers say that directly.

## Why this target

The issue is a good Faber pilot because it has:

- a concrete user-visible symptom: repeated managed-install startup cost;
- objective verifier potential: assert no doomed ensurepip/pip subprocess is
  launched on managed/read-only installs;
- strong environment evidence: NixOS/read-only-store behavior;
- no need for production credentials or hosted services;
- a bounded implementation path with docs and tests.

Runner-up Nix/NixOS candidates remain useful if #48628 is solved before the
pilot starts:

- [#58937](https://github.com/NousResearch/hermes-agent/issues/58937):
  Python 3.13 sealed Nix venv bump.
- [#43810](https://github.com/NousResearch/hermes-agent/issues/43810):
  `extraPythonPackages` collision filtering.
- [#48897](https://github.com/NousResearch/hermes-agent/issues/48897):
  stable/classic Nix compatibility, likely too broad unless split.

## TaskContract fixture

This fixture is intentionally static and provider-neutral. It can later be
serialized through Faber's normal `TaskContract` path.

```json
{
  "schema": "faber.task_contract.v1",
  "id": "task-contract_hermes_nixos_lazy_deps_48628",
  "created_at": "2026-07-08T00:00:00Z",
  "title": "Hermes managed-install lazy dependency startup guard",
  "description": "For NousResearch/hermes-agent issue #48628, prevent managed/read-only installs such as NixOS from repeatedly attempting doomed ensurepip/pip lazy dependency installs at startup. Preserve clear remediation for unavailable optional backends.",
  "requirements": [
    "Verify the upstream issue is still open and applicable before implementation.",
    "Add a managed/read-only install guard before lazy dependency install attempts.",
    "Do not run ensurepip or pip when the install cannot persist.",
    "Surface a clear unavailable-feature remediation for missing optional backend dependencies.",
    "Add objective tests for the managed/read-only path.",
    "Update user or developer docs if behavior or remediation changes.",
    "Attach .faber/attempt.json with at least Level 1 evidence.",
    "Prefer a Faber Runner trace JSONL with environment, verifier, and command events."
  ],
  "verifier_ids": [
    "verifier.hermes.lazy-deps.managed-install",
    "verifier.hermes.lazy-deps.docs",
    "verifier.hermes.faber-artifacts"
  ],
  "task_source": "github.issue",
  "repository": "NousResearch/hermes-agent",
  "environment": {
    "issue_number": 48628,
    "issue_url": "https://github.com/NousResearch/hermes-agent/issues/48628",
    "required_platforms": ["nixos"],
    "minimum_reproducibility_level": "nix_flake",
    "evidence_level_required": 1,
    "evidence_level_preferred": 2
  },
  "reward": null
}
```

## Verifier specs

These are pilot verifier definitions, not claims that matching tests already
exist upstream. The implementer should adapt names and paths to the current
Hermes tree.

### `verifier.hermes.lazy-deps.managed-install`

Purpose: prove the core behavior for #48628.

Suggested command:

```text
nix develop --command python -m pytest tests/test_lazy_deps_managed_install.py
```

Expected checks:

- fake or monkeypatched managed install returns true;
- optional backend dependency is configured but absent;
- lazy dependency resolution does not invoke ensurepip or pip;
- result is a clear feature-unavailable/remediation path;
- process-level negative caching prevents repeated work when appropriate.

### `verifier.hermes.lazy-deps.docs`

Purpose: prove user-facing remediation is documented.

Suggested command:

```text
nix develop --command python -m pytest tests/test_lazy_deps_docs.py
```

Expected checks:

- managed/read-only install remediation appears in docs or help text;
- docs do not instruct NixOS users to mutate the read-only store;
- workaround flags such as disabling lazy installs are described if still valid.

### `verifier.hermes.faber-artifacts`

Purpose: prove Faber pilot evidence was attached.

Suggested command:

```text
python -m faber.cli validate-attempt-manifest .faber/attempt.json
```

If no CLI command exists at pilot time, use a small repository-local validation
script that imports Faber's `AttemptManifest` parser and validates the JSON.

Expected checks:

- `.faber/attempt.json` exists and matches the task contract id/digest;
- environment evidence records NixOS/read-only-store context and flake lock digest
  when available;
- trace policy is explicit;
- if `.faber/trace.jsonl` is included, the trace digest is stable.

## Evidence requirements

Minimum:

- Level 1 evidence: PR plus `.faber/attempt.json`.
- `EnvironmentEvidence` for the NixOS or managed/read-only test environment.
- Verifier outputs bound to the exact commit under review.

Preferred:

- Level 2 evidence: Faber Runner trace JSONL.
- Trace events for upstream issue inspection, environment capture, verifier runs,
  code changes, docs changes, and final result.
- Redaction policy showing no private prompts, credentials, or production data.

## Upstream contribution path

1. Re-check #48628 state and current Hermes lazy dependency code.
2. If the issue remains valid, open or use a branch named like
   `faber/48628-managed-lazy-deps`.
3. Add tests that fail before implementation.
4. Implement the smallest managed/read-only install guard that preserves existing
   non-managed behavior.
5. Add docs or help text for the managed-install remediation.
6. Run the verifier specs and capture Faber artifacts.
7. Open an upstream PR with the issue link, verifier commands, and a concise
   explanation that Faber artifacts are supplemental evidence.

## Out of scope

- No real payment provider.
- No hosted service dependency.
- No claim that Hermes maintainers endorsed Faber.
- No broad stable-Nix refactor.
- No requirement to expose private prompts, credentials, or proprietary harness
  internals.

## Launch checklist

- #48628 is still open or maintainers confirm the task is still useful.
- A current Hermes checkout is available on a Nix-capable machine.
- Verifier commands are updated to match the current tree.
- Faber task contract digest is generated from the final fixture.
- `.faber/attempt.json` validates.
- Risk review for funded external work is complete before any real bounty or PR.
