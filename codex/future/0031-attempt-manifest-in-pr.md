# 0031 — Attempt manifest in pull requests

## Goal

Support optional `.faber/attempt.json` manifests in GitHub pull requests.

## Scope

Extend the GitHub adapter and protocol validators so a fake PR file map can include a Faber attempt manifest.

## Requirements

- Define an attempt manifest schema.
- Link manifest to task contract id/digest, attempt id, base revision, candidate revision, worker id, model/harness/runner metadata, environment digest, cost/latency, evidence level, and redaction policy.
- Missing manifest should be allowed.
- Malformed manifest should produce a clear validation warning or error object, not crash the adapter.
- Manifest data should be provenance-tagged.
- No real GitHub API calls.

## Tests

- valid manifest
- missing manifest
- malformed manifest
- manifest digest stability
- manifest attached to attempt and trajectory export

## Acceptance criteria

A solver can submit a normal PR plus `.faber/attempt.json`, giving Faber richer data without requiring a full runner trace.