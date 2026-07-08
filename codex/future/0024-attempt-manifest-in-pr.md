# 0024 - Attempt Manifest In Pull Requests

## Goal

Support optional `.faber/attempt.json` manifests in pull requests.

## Scope

- Define the `.faber/attempt.json` schema.
- Teach the GitHub adapter to read and parse the manifest from a fake PR file
  map.
- Link PR attempts to `WorkerProfile`, model and harness metadata, runner
  metadata, environment digest, cost and latency, trace level, and redaction
  policy.
- Keep the manifest optional.
- If present, validate it strictly.
- Invalid manifests should not crash the adapter. They should produce a clear
  validation error or evidence warning.

## Requirements

- Use the fake GitHub client only.
- Do not add real GitHub API calls.
- Do not add real model APIs.
- Preserve stable serialization and digests.
- Do not require private chain-of-thought, proprietary prompts, or finetune
  details.

## Tests

Add tests for:

- valid manifest;
- missing manifest;
- malformed manifest;
- manifest digest stability;
- evidence warnings for invalid manifests.

## Docs

Add an example `.faber/attempt.json` manifest with disclosure levels and trust
levels.

## Acceptance Criteria

- PR-only attempts continue to work.
- Manifest-backed attempts carry richer metadata into Faber Protocol records.
- GitHub remains an adapter, not the source of protocol authority.
