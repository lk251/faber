# Trajectory Validation CLI

Faber validates local artifacts before submission or dataset export. Every
validation command prints one canonical JSON report with a short summary,
structured details, warnings, and errors.

```text
python -m faber.cli validate-attempt .faber/attempt.json
python -m faber.cli validate-trace .faber/trace.jsonl
python -m faber.cli validate-trajectory path/to/trajectory.json
python -m faber.cli trajectory-quality path/to/trajectory.json
```

Exit code `0` means valid, `2` means valid with a quality warning, and `1`
means invalid. A PR-only trajectory normally returns `2`: it can be valid
customer and audit work while remaining low-evidence and non-RL-grade.

Trajectory reports identify audit eligibility, supervised-learning eligibility,
RL-grade eligibility, training consent, training-export eligibility, redaction
status, task requirement satisfaction, and missing fields. Invalid field errors
name the field and expected shape so harnesses can correct artifacts before
submission.
