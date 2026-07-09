# Trace Privacy And Redaction

Faber does not require private prompts, chain-of-thought, finetune weights,
private model weights, or proprietary harness internals. A useful trace records
observable process structure: context classes, actions, tool types, verifier
feedback, timing, costs, failures, interventions, and outcomes.

`RedactionPolicy` supports field-level replacement and event-type exclusion.
`SensitiveFieldPattern` provides a small local detector for obvious credential
shapes and sensitive key names. Detector findings retain only a field path,
pattern name, and value digest; the matched value is not copied into the report.

`RedactionReport` binds the source digest, redacted digest, replaced field paths,
excluded event types, and detector findings. Stable reports make it possible to
audit what was removed without retaining the removed content.

`PrivateTraceEnvelope` records trace visibility, content reference, digest, and
whether a redaction report is required before export. Public dataset export
excludes private and restricted envelopes. Authorized restricted exports can use
redacted traces when the data-rights policy and all required consent grants also
permit the export.

Redaction and RL usefulness are separate questions. Removing private content
does not inherently destroy learning value when ordered context, action/tool,
verifier/outcome events, environment evidence, reward, and consent remain.
Removing whole event classes can make a trace non-RL-grade when it erases that
required process structure, and the trajectory quality report should say so.
