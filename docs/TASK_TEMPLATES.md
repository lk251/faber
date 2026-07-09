# Task Templates And Verification Policy

Task templates are data, not executable code. A template combines ordinary
requirements, a `VerificationPolicy`, an evidence preset, and default
environment metadata, then renders an ordinary `TaskContract`.

The verification vocabulary expresses hard verifier ids, human review mode,
advisory ranking, and budget constraints. Evidence presets express minimum and
allowed trajectory tiers, RL-grade and training-eligibility requirements, and
platform evidence. Budget presets use integer `Money`, purpose allocations, and
optional trace-quality bonus policy; their marker binding records contract and
budget digests.

Built-in templates cover generic bugfixes, documentation work, RL-grade work,
and an opt-in reproducible harness task. The GitHub bug template lives in the
GitHub adapter and still renders a normal core contract. Template parsing
rejects unknown fields, so templates cannot smuggle arbitrary code execution
into task creation.
