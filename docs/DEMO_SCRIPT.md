# Faber Proof three-minute demo script

Target edited runtime: 2:35-2:50. Hard limit: under three minutes. The narration block
is mechanically checked at 388-396 words, which estimates 2:35-2:38 at 150 words per
minute and 2:46-2:50 at 140 words per minute. This does not replace a human timed
rehearsal.

Run:

```bash
python scripts/check_demo_script.py
```

## Timeline

| Time | Visual |
|---|---|
| 0:00-0:12 | Green ordinary tests and bad diff |
| 0:12-0:28 | Task's last-turn requirement |
| 0:28-0:45 | `$faber-proof` invocation with visible replay/live label |
| 0:45-1:02 | GPT-5.6 structured claims and approved selections |
| 1:02-1:25 | Red `BLOCK`, failed claim, and counterexample |
| 1:25-1:40 | Trust-boundary visual |
| 1:40-2:02 | Narrow Codex repair |
| 2:02-2:22 | Green ordinary tests and Faber Proof `PASS` |
| 2:22-2:40 | No-key replay, auditability, and impact |
| 2:40-2:47 | Closing tagline |

## Complete narration

<!-- NARRATION START -->
<!-- 0:00-0:12 -->
These ordinary tests are green, but this Codex patch is still wrong. On the final permitted turn, it throws away a complete report and says the budget was exhausted.

<!-- 0:12-0:28 -->
The task requires completed work to survive that exact boundary. The patch looks reasonable, and its early completion, cancellation, incomplete-work, and composition tests all pass. None of them exercises this two-turn case.

<!-- 0:28-0:45 -->
I invoke the repository's Faber Proof skill. This replay path is labeled, so anyone can reproduce it without an API key, account, network request, or provider SDK. Live mode uses the same strict parser and validator.

<!-- 0:45-1:02 -->
An independent GPT-5.6 planner receives the task, bounded redacted diff, mandatory claims, and an owner-approved proof catalog. It returns structured falsifiable claims and data-only template selections. It cannot provide commands, source code, imports, arbitrary paths, or a verdict.

<!-- 1:02-1:25 -->
Faber validates those bindings and executes only approved capabilities. BLOCK, despite green ordinary tests. The failed claim says a complete final report must be preserved on the last permitted turn. With these two responses, the patch returns budget exhausted instead of the premise and summary. That concrete counterexample is authoritative evidence, not model prose.

<!-- 1:25-1:40 -->
This is the trust boundary. GPT-5.6 plans what should be proved. Repository policy controls what may execute. Receipts feed deterministic policy. Failed evidence blocks; missing, stale, partial, or contradictory evidence goes to human review. Only complete passing evidence can produce PASS.

<!-- 1:40-2:02 -->
Codex now repairs the demonstrated defect. It moves the complete-report check ahead of the budget-exhaustion return. There is no rewrite, weakened contract, or generated command. The fix follows directly from the failed claim and observed boundary result.

<!-- 2:02-2:22 -->
The ordinary suite remains green. I rerun the same proof against the repaired candidate. Now Faber Proof returns PASS: all three required obligations have authoritative evidence, with zero failed or missing claims. The report is self-contained and keeps the plan, execution results, receipts, and integrity digests for audit.

<!-- 2:22-2:40 -->
The no-key replay is context-bound, not a new live model call. Tampered responses, another candidate's replay, unknown templates, path escapes, timeouts, truncated output, swapped receipts, and partial bundles fail closed. Forty-nine adversarial cases pass with zero unjustified passes, and the bad-to-repaired demo completes in seconds.

<!-- 2:40-2:47 -->
Faber Proof gives engineering teams a path from local Codex use to CI policy and stronger isolated runners. Codex can write the patch. Faber makes the patch prove itself.
<!-- NARRATION END -->

## Recording notes

- Keep `REPLAY - FAKE-DEVELOPMENT` visible while current committed fixtures are used.
- Use `LIVE` only after the guarded transaction records human-reviewed live provenance.
- Compress idle editing or provider wait time, never evidence or chronology.
- Do not show local user names, full paths, notifications, browser profiles, or secrets.
- Do not read digests aloud.
