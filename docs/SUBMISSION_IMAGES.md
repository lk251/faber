# Faber Proof submission image plan

Use only original Faber visuals. Final PNG/JPEG files may be captured manually from the
deterministic reports and committed SVG sources; no screenshot tool is required by the
build.

## Common capture rules

- Preferred source canvas: 1600x900 or 1920x1080, 16:9.
- Minimum exported width: 1200 px.
- Keep critical text inside the central 90% and leave 8% at the bottom for platform
  overlays.
- Use opaque backgrounds and preserve the red/green verdict contrast.
- Hide browser chrome, local paths, user names, notifications, private tabs, and API
  credentials.
- Keep provenance visible. Until guarded live review is complete, label report captures
  `REPLAY - FAKE-DEVELOPMENT`.
- Do not add third-party logos, stock images, fonts, screenshots, or media.
- Run the artifact privacy audit before upload.

## Image 1 - blocked report above the fold

Source:

```text
.faber/build-week-demo/bad/report.html
```

Capture:

- 1600x900 viewport at 100% zoom; use 125% only if all required fields remain visible.
- Include red `BLOCK`, task title, bad candidate, failed claim, expected/observed
  result, bounded two-turn counterexample, and replay/live label.
- Exclude long digest tables and local report path.

Caption:

> Ordinary tests pass, but Faber Proof blocks the patch with the exact failed
> last-turn claim and a concrete two-turn counterexample.

Suggested output name: `faber-proof-blocked-report.png`.

## Image 2 - passing report above the fold

Source:

```text
.faber/build-week-demo/repaired/report.html
```

Capture:

- Match Image 1's 1600x900 viewport and crop.
- Include green `PASS`, repaired candidate, 3/3 required obligations, zero failed or
  missing obligations, and provenance label.
- Keep the same task and claim framing so the reversal is immediate.

Caption:

> Codex makes the narrow evidence-driven repair; ordinary tests remain green and all
> required Faber Proof obligations pass.

Suggested output name: `faber-proof-passing-report.png`.

## Image 3 - comparison

Committed source:

```text
docs/submission-assets/demo-comparison.svg
```

Export at 1600x900 without changing text or colors. The visible message must remain:

```text
Ordinary tests: PASS -> PASS
Faber Proof:    BLOCK -> PASS
```

Caption:

> The same green ordinary suite hides the bad patch; approved executable evidence
> creates the decisive BLOCK-to-PASS reversal.

Suggested output name: `faber-proof-comparison.png`.

## Image 4 - trust boundary

Committed source:

```text
docs/submission-assets/trust-boundary.svg
```

Export at 1600x900. Preserve all three zones:

1. untrusted task, diff, and model plan;
2. repository-approved bounded execution;
3. authoritative receipts and deterministic verdict.

Caption:

> GPT-5.6 plans falsifiable obligations; repository-approved evidence and deterministic
> policy decide.

Suggested output name: `faber-proof-trust-boundary.png`.

## Final image gate

- [ ] Captures come from the exact audited commit/tag.
- [ ] Bad and repaired report labels match actual provenance.
- [ ] Text remains legible in the Devpost preview.
- [ ] Captions do not claim live output while fixtures are `fake-development`.
- [ ] `faber audit-proof-artifacts` reports zero covered findings for all upload files.
- [ ] Human confirms every uploaded image matches the final repository and permitted
  Devpost state.
