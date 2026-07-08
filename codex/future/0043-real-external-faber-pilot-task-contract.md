# 0043 — Real external Faber pilot task contract

## Goal

Create a complete Faber task contract for one selected external open-source issue, likely from Hermes Agent if it remains the best candidate after ranking.

## Scope

- choose target issue after survey
- write task contract fixture
- define verifier specs
- define work budget placeholder
- define evidence level requirement
- define trace and attempt manifest expectations
- define acceptance and rejection criteria

## Requirements

- Do not select a high-risk task requiring production credentials or private user data.
- Prefer local reproduction and local verifier commands.
- Require at least Level 1 evidence; prefer Level 2.
- Include maintainer-friendly upstream contribution path.
- Include rollback or failure policy.
- Keep payment/provider integrations out of scope.

## Tests

- task contract validates
- verifier specs validate
- work budget placeholder validates
- required evidence level is enforced
- example attempt manifest validates

## Acceptance criteria

Faber is ready to run one real external task through its protocol with trace, verifier, and budget structure.