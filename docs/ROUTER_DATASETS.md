# Router Training Dataset

Faber exports a canonical JSONL view for future routers that choose workers,
verifiers, budgets, and escalation policy. This issue defines records only; it
does not train a model or add an ML framework.

Features include task source and requirements, worker capability and trust,
model disclosure, harness and platform metadata, replayability, and verifier
policy. Labels include selected worker, selected verifier, selected budget,
outcome, cost, latency, review friction, reward, and integer value-per-euro.

Each record carries provenance and a trajectory quality report digest. PR-only
records are marked `weak`; RL-grade trace or episode records are `strong`.
Rejected, declined, timed-out, abandoned, failed-verifier, and failed attempts
can remain negative examples when policy and consent permit them.

Export filters training consent by default and accepts `router`, `supervised`, or
`all` permission. Customer/audit records without training permission do not enter
the router dataset.
