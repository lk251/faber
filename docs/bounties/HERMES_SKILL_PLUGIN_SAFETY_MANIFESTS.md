# Hermes-style skill/plugin safety manifests

This is a Faber planning path for declared metadata around agent skills and
plugins. It uses fake fixtures only and does not audit, judge, or depend on
upstream Hermes internals.

## Manifest fields

Each manifest declares:

- component type: `skill` or `plugin`;
- supported platforms;
- requested permissions and risk level;
- dependencies and version constraints;
- verifier ids that can check the manifest;
- free-form metadata for fixture expectations.

## Scanner behavior

The scanner checks only declarations inside the manifest. It flags:

- missing platform declarations;
- missing dependency declarations listed in `metadata.expected_dependencies`;
- absent permissions as a warning;
- absent verifier ids as a warning.

The scan can be represented as a `VerifierRun`, which lets a task contract bind
manifest checks to a normal Faber `VerificationReceipt` when that is useful.
