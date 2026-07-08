# Hermes attempt manifest example

`attempt_manifest_48628.json` is a static example of the `.faber/attempt.json`
metadata a contributor could attach to a PR for the selected Hermes Agent lazy
dependency pilot candidate.

It is an example fixture only. It does not call GitHub, require Hermes as a
dependency, or claim upstream maintainer endorsement.

Generate a similar manifest from local metadata:

```powershell
python -m faber.cli generate-attempt-manifest `
  --out .faber/attempt.json `
  --task-contract-id task-contract_hermes_nixos_lazy_deps_48628 `
  --task-contract-digest sha256:1111111111111111111111111111111111111111111111111111111111111111 `
  --base-revision upstream-base-revision `
  --candidate-revision candidate-pr-revision `
  --worker-id worker_external_solver_example `
  --environment-digest sha256:2222222222222222222222222222222222222222222222222222222222222222 `
  --harness-family generic-agent-harness `
  --runner-name local `
  --runner-version example `
  --evidence-level 3
```

Validate it:

```powershell
python -m faber.cli validate-attempt-manifest .faber/attempt.json
```
