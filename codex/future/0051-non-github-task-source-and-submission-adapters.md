# 0051 — Non-GitHub task source and submission adapters

## Goal

Keep GitHub as the first adapter without making GitHub the only way to create tasks or submit attempts.

## Scope

Add generic interfaces for:

- `TaskSourceAdapter`
- `SubmissionAdapter`
- `ArtifactReference`
- `ExternalTaskReference`
- local filesystem task source
- simple JSON task source

## Requirements

- GitHub remains an adapter, not the core.
- Local task sources should support the same task contract/attempt/trajectory lifecycle.
- Artifact references should support patches, commits, files, generated outputs, and non-code artifacts.
- No web server.
- No external API calls.

## Tests

- local JSON task becomes TaskContract
- local patch/artifact becomes Attempt
- non-GitHub attempt can satisfy trajectory requirements
- GitHub-specific fields do not leak into core objects

## Acceptance criteria

Faber can support future non-GitHub labor markets and benchmarks without rewiring the core protocol.