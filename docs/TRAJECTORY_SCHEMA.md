# Trajectory Schema

A trajectory captures the scarce training and audit record for verified work.

## Supervised Learning Fields

Supervised learning can use task contract text, requirements, repository or
environment snapshot references, router decisions, worker capabilities, attempt
summaries, patch references, tool/action summaries, and final accepted outputs.

## Reinforcement and Preference Learning Fields

Reinforcement learning and preference learning can use accepted, rejected,
declined, failed, and abandoned attempts. Failed or declined work still teaches
routers which choices waste time, increase review friction, or fail verifier
policy.

Reward, cost, latency, verifier outcome, review friction, and settlement metadata
matter because Faber optimizes intelligence per euro rather than raw pass rate or
raw cheapness.

## Review and Verifier Quality

Human review signals should be captured without making human review the only
verifier. Human review can label ambiguity, maintainability, product fit, and
review friction.

Verifier quality may itself become a market and training signal. A verifier that
predicts durable acceptance, reduces disputes, and catches important failures is
valuable evidence.

## Dataset Export

Trajectories can be exported as canonical JSONL with one trajectory record per
line. Dataset manifests record source paths, record counts, schema versions,
accepted/rejected counts, total cost, total reward, margin, the JSONL digest, and
quality issues.

Stable split assignment uses deterministic hashing of the trajectory id into
`train`, `validation`, and `test`, so records stay in the same split across runs.

Quality checks flag missing receipts, router decisions, cost metadata, outcomes,
and digest mismatches where the payload includes enough information to verify a
digest.

Redaction hooks are explicit field-path replacements. They should be used before
sharing datasets outside the trust boundary when task descriptions, review notes,
or repository metadata contain sensitive information.
