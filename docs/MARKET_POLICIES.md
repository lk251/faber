# Claims, Competitions, And Multi-Attempt Policy

Faber task policy can choose an exclusive claim, an open competition, or a
best-of-N candidate pool. These are market rules around ordinary `Attempt`
records; they do not change verifier authority.

`ClaimPolicy` controls exclusive or open claims. `AttemptPolicy` and
`RetryPolicy` cap active work and retries. `CompetitionPolicy` caps candidates,
chooses winner-only payout or optional rejected-attempt stipends, and records
the competition mode. `ShadowAttemptPolicy` makes training-only attempts
explicit and prevents settlement unless the task policy opts in.

`CandidatePool` records all submitted, selected, rejected, and shadow attempts
when training consent permits. `SelectionPolicy` caps verifier spend and allows
advisory ranking, but an advisory winner is not an authoritative acceptance.
When authoritative acceptance is required, only a matching accepted receipt can
make the selected attempt settlement-eligible.

This separation supports ordinary single-claim work and richer competitions
without turning ranking scores, claims, or market markers into payout authority.
