# Risk review

Funded external work should pass a lightweight risk review before money is
reserved or agent execution starts.

Risk review covers:

- private data exposure;
- credentials or account access;
- external write actions;
- legal or regulated domains;
- security-sensitive repositories;
- payment/provider assumptions;
- maintainer consent and upstream norms;
- trace privacy and redaction;
- false accept risk;
- reputational risk.

## Risk levels

- `local-only low risk`
- `open-source repo low/medium risk`
- `external-service risk`
- `private-data risk`
- `regulated-domain risk`
- `security-sensitive risk`

High-risk levels require explicit human review metadata with `human_reviewed`,
`approved`, and `reviewer` before a task is ready for funding or agent execution.

Task contracts can provide protocol flags in `environment`, such as
`requires_credentials`, `private_data`, `external_write_actions`,
`regulated_domain`, `security_sensitive`, `payment_provider_integrations`,
`maintainer_consent`, `trace_redaction_required`, `false_accept_risk`, and
`reputational_risk`.
