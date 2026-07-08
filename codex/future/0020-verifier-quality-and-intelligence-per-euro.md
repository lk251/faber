# 0020 - Verifier Quality And Intelligence Per Euro

## Goal

Add verifier evaluation and intelligence-per-euro metrics. Faber should measure
not only worker quality, but verifier quality.

## Scope

Add metrics for:

- verifier cost;
- verifier latency;
- agreement with hard verifier or human review;
- tie rate;
- uncertainty;
- false accept risk;
- false reject risk;
- improvement over pass@1 or first attempt;
- value per euro.

## Requirements

- Use local fixtures only.
- Do not add real model APIs.
- Add `VerifierEvaluation` or similar objects.
- Add docs explaining that paid verifier tiers can compete on accuracy, latency,
  and value per euro.

## Tests

Add tests for:

- metric calculations;
- zero-cost and zero-value edge cases;
- agreement calculations against fixture hard-verifier outcomes;
- value-per-euro using integer minor units.

## Acceptance Criteria

- Verifier quality can be compared without coupling to a provider.
- Metrics are deterministic and auditable.
- The docs preserve the distinction between verifier quality and settlement
  authority.
