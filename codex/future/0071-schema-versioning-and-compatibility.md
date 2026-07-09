# 0071 — Schema versioning and compatibility

## Goal

Prepare Faber Protocol for evolution without breaking existing trajectories, receipts, manifests, and datasets.

## Scope

Add or improve:

- schema registry
- version constants
- compatibility checks
- upgrade stubs
- deprecation warnings
- dataset manifest schema versions

## Requirements

- Every exported protocol object should identify schema/version.
- Dataset manifests should list schema versions seen.
- Validation should reject unknown required schema versions when unsafe.
- Add simple no-op upgrade path for current versions.
- Keep implementation lightweight.

## Tests

- known schema validates
- unknown future schema warns or fails by policy
- dataset manifest records schema versions
- upgrade stub preserves digest expectations where appropriate

## Acceptance criteria

Faber can grow protocol objects without corrupting early training/audit data.