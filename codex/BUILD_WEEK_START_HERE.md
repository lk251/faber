# Faber Proof — Build Week execution entrypoint

This file is the single entrypoint for the OpenAI Build Week 2026 implementation.
The objective is not merely to submit. The objective is to maximize the probability of
winning first place in the **Developer Tools** track while preserving Faber's core
architecture.

## The only instruction Javier should need to give Codex

```text
Use $build-week-director and continue until the next human-only gate.
```

If the skill is not visible yet, restart Codex once and use:

```text
Read codex/BUILD_WEEK_START_HERE.md and execute the next incomplete Build Week work item.
```

Do not ask Javier to copy a work-item prompt into chat. The prompts are already in
`codex/future/`, and progress is tracked in `codex/build-week/STATUS.md`.

When `codex/build-week/OFFLINE_CONTINUATION.md` is present and explicitly invoked, a
missing `OPENAI_API_KEY` is a deferred provenance gate rather than a stop for unrelated
machine work. Keep development replays honestly labeled, skip only work that actually
depends on the deferred gate, and continue through eligible 0082 and 0083 machine work.

## Product decision

The submission is **Faber Proof**.

> Codex can write the patch. Faber makes the patch prove itself.

Faber Proof turns an AI-generated code change into a proof-carrying patch:

1. A fresh, independent GPT-5.6 Sol call reads the task contract and a bounded,
   redacted diff.
2. It decomposes the change into explicit behavioral claims and maps them to a bounded
   catalog of approved proof templates.
3. Faber validates the plan, materializes data-only probes, executes approved verifier
   policy, and emits digest-bound evidence.
4. The result is `PASS`, `BLOCK`, or `HUMAN_REVIEW`, with a self-contained report that
   shows exactly which claim failed and the counterexample.
5. Codex consumes that evidence to repair the patch and reruns the proof.

This is deliberately not a generic AI code reviewer. The novel product is
**proof-carrying patches for agentic software development**.

## Read order for every implementation session

1. `AGENTS.md`
2. `docs/CODEX_SESSION_HANDOFF.md`
3. `docs/BUILD_WEEK_2026.md`
4. `docs/FABER_PROOF_PRODUCT.md`
5. `codex/build-week/STATUS.md`
6. `codex/build-week/RESET_STRATEGY.md`
7. `codex/build-week/AUDIT_QUEUE.md`
8. The next incomplete prompt in `codex/future/`

## Autonomous execution protocol

1. Work on branch `build-week/faber-proof`. Create it from the current canonical
   `master` if it does not exist.
2. Address any open P0 audit finding before new feature work.
3. Otherwise select the first incomplete eligible **P0 machine slice** in
   `codex/build-week/STATUS.md`. A deferred human-only slice does not block independent
   later machine work when the status explicitly records that separation.
4. Implement exactly that item. Preserve the global invariants in `AGENTS.md` and the
   Build Week product constraints.
5. Add or update tests before changing verification, routing, evidence, or decision
   behavior.
6. Run the acceptance commands named in the prompt plus the closest available full
   checks:

   ```bash
   python -m pytest
   python -m ruff check .
   python -m mypy src
   ```

   Run `nix develop --command just check` when Nix is available. State precisely when
   it is not available.
7. Update `codex/build-week/STATUS.md` with the commit, tests, demo state, and next
   item. Update `docs/CODEX_SESSION_HANDOFF.md` when the recommended next action
   changes.
8. Make one focused commit for the work item. Do not squash eligible Build Week
   history.
9. Continue to the next eligible P0 machine item without waiting for Javier. Record
   eligible independent audits but do not stop solely for audit scheduling. Stop only
   when a human gate blocks the selected work, an actual P0 failure prevents progress,
   or the working tree cannot be made safe.

## Human-only gates

These actions remain human-only, but they block only work that actually depends on
them. During an explicitly authorized offline continuation, defer them and finish all
independent machine work:

- Entering secrets or an OpenAI API key.
- Requesting or redeeming hackathon credits.
- Sharing the private repository with the judging addresses.
- Calling `/feedback` and recording the returned Codex session ID.
- Recording a human voiceover, uploading the public YouTube video, or submitting the
  Devpost form.
- Approving any external publication, payment, third-party contribution, or use of
  private data.

Do not request `/feedback` again after its session ID is recorded. Never mark a
deferred gate complete without the real value or explicit human attestation.

Everything else should be completed autonomously with deterministic fakes or replay
fixtures when live credentials are unavailable.

## Using fresh GPT-5.6 resets

Use one primary implementation thread for the core vertical slice, ideally work items
0077 through 0081. This is the thread whose `/feedback` session ID should represent the
majority of core work.

Use fresh reset sessions for independent audits only after their implementation gates
are eligible. The instruction is:

```text
Use $build-week-auditor and run the next eligible independent audit.
```

The reset plan and prompts are already in:

```text
codex/build-week/RESET_STRATEGY.md
codex/build-week/AUDIT_QUEUE.md
codex/audits/
```

The audits cover architecture and authority, adversarial security, clean installation,
judge comprehension, and final compliance. They write durable findings for the primary
director to address. Do not use resets to create competing product architectures.

## Win-oriented priority order

The official judging criteria are equally weighted, and technological implementation
is the first tie-break criterion. Every P0 feature must improve at least one criterion
without materially weakening another.

1. **Technological implementation** — direct GPT-5.6 structured-output integration,
   deep Codex use, fail-closed policy, deterministic evidence, adversarial evaluation.
2. **Design** — one-command demo, no-key replay, polished evidence viewer, coherent
   start-to-finish workflow.
3. **Potential impact** — a concrete solution for maintainers who must trust
   AI-generated changes.
4. **Quality of the idea** — proof-carrying patches, not another prose review bot.

Prefer a complete vertical slice over breadth. Payments, marketplace behavior,
training, external pilots, a GitHub App, and autonomous publication are out of scope
until the submission is frozen.

## Mandatory demonstration

The original demonstration repository must prove all of the following in replay mode:

```text
Bad AI patch:
  ordinary tests = PASS
  Faber Proof = BLOCK
  report contains the failed claim and a concrete counterexample

Repaired AI patch:
  ordinary tests = PASS
  Faber Proof = PASS
  all required proof obligations have authoritative evidence
```

Live mode must reproduce the same plan with `gpt-5.6` closely enough to produce the
same verdict, but judges must be able to run replay mode without an API key, network,
account, or rebuild.

## Definition of submittable

The project is submittable only when:

- Pre-existing Faber and Build Week additions are clearly separated.
- The direct GPT-5.6 path and deterministic replay path both exist.
- Model output is structured data and can never define executable commands.
- The bad-patch/fixed-patch demo works from a clean installation.
- A repository-scoped Codex skill is available under `.agents/skills/faber-proof/`.
- A self-contained HTML evidence report communicates the result in under five
  seconds.
- Adversarial cases cannot produce an unjustified `PASS`.
- The README contains installation, supported platforms, test instructions, Codex
  collaboration evidence, and GPT-5.6 usage.
- The final video is public, narrated, and under three minutes.
- The submitted commit matches an immutable final tag and all links and repository
  permissions have been checked from a clean context.
- Every required independent audit is green and no P0 audit finding remains open.

Do not start the P1 stretch item until every P0 gate is green.
