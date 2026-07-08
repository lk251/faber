# Hermes best-of-N selection pilot

This pilot uses deterministic fake attempts for a Hermes-related task candidate
to demonstrate Faber's selection policy without calling model APIs or external
services.

## Selection rule

1. Candidate attempts are collected for the same `TaskContract`.
2. Advisory ranking records can score attempts in integer thousandths with an
   uncertainty field.
3. Accepted authoritative verifier receipts dominate advisory scores.
4. If no accepted authoritative receipt exists, the highest advisory score wins,
   with lower uncertainty and then attempt id as deterministic tie-breakers.
5. Rejected or unselected attempts remain in the dataset export with
   `selection_outcome: rejected`.

## Pilot fixture

For the selected external pilot candidate, Faber can create three attempts:

- an attempt with a high advisory score but no hard receipt;
- an attempt with a lower advisory score but accepted hard verifier receipt;
- an attempt rejected by the hard verifier.

The selection record stores budget used, selected attempt id, rejected
alternatives, advisory scores, authoritative receipt id when present, and
uncertainty. Advisory records do not authorize settlement by themselves.
