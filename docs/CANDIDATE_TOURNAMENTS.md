# Cost-Aware Candidate Tournaments

Candidate tournaments spend a bounded verifier budget to rank multiple attempts.
Small pools use a full round robin. Larger pools use reduced pivot comparisons.
Every `CandidateComparison` records the pair, preference probability,
uncertainty, integer-minor-unit verifier cost, latency, and stable digest.

`TournamentResult` records the schedule, comparison count, selected attempt,
rejected alternatives, budget exhaustion, total cost, latency, uncertainty, and
any authoritative receipt. Accepted hard verifier receipts dominate advisory
tournament scores. Without an authoritative receipt, the result is ranking
evidence only and cannot release settlement.

Tournament records can annotate every candidate trajectory, including rejected
alternatives. This preserves useful negative and preference data while keeping
comparison spend explicit and deterministic. The initial scorer is a local fake;
future probabilistic scorer adapters remain replaceable.
