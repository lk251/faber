# Human Review Receipts

Human review is first-class verification evidence, but it is not automatically
authoritative. `HumanReviewReceipt` binds a reviewer reference and maintainer
relationship to a task, attempt, criteria, outcome, timestamp, comments digest,
and `ReviewFrictionSignal`.

Core records do not store long review prose by default. They retain a digest and
optional reference. Public export removes a private comments reference while
retaining outcome and friction labels when policy permits them.

A task `VerificationPolicy` may classify human review as advisory,
supplementary, or authoritative. Only an authoritative approved review under an
authoritative policy can produce a normal `VerificationReceipt` for settlement.
By default, human review cannot override a rejected hard verifier. A task would
need to opt into that override explicitly and should do so only when the hard
check is not intended as a non-negotiable acceptance condition.

This keeps deterministic checks, probabilistic advice, and maintainer judgment
composable while preserving the rule that settlement follows an authoritative
receipt.
