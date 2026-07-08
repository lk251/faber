# Hermes external pilot task contract

Selected target: `NousResearch/hermes-agent` issue #48628, the managed-install
lazy dependency startup guard.

The executable fixture lives in `src/faber/adapters/hermes/pilot.py` and defines:

- the `TaskContract`;
- three local verifier specs;
- a provider-free work budget placeholder;
- a matching example attempt manifest;
- evidence-policy validation for required trace level.

## Boundaries

- Re-check the upstream issue before any real work.
- Do not require production credentials or private user data.
- Prefer local verifier commands.
- Require at least Level 1 evidence and prefer Level 2 trace JSONL.
- Keep payment provider integrations out of scope.
- Treat Faber artifacts as supplemental evidence, not upstream endorsement.
