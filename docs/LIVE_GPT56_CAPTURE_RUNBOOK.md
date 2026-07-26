# Guarded GPT-5.6 demo capture

## Human gate

The committed Build Week replay fixtures are `fake-development`. This runbook prepares
the later human-reviewed transaction that can replace them with real, context-bound
`gpt-5.6` responses.

Do not run this in CI. Do not paste an API key into a command, shell history, report,
issue, or committed file. The capture remains a human gate because Javier must supply
the credential, inspect the result, and approve the changed fixtures.

## Preconditions

1. Check out `build-week/faber-proof`.
2. Pull the final candidate and confirm the worktree is clean.
3. Install the optional live adapter:

   ```bash
   python -m pip install ".[live-openai]"
   ```

4. Set `OPENAI_API_KEY` in the current process using the operating system's secure
   local mechanism. Do not print it.
5. Confirm the account can call the requested `gpt-5.6` model.

The wrapper itself rechecks the key's presence, exact branch, clean worktree, task,
catalog, proof policy, prompt/schema context, candidate revisions, and existing replay
provenance before the first provider call.

## One command

From the repository root:

```bash
python examples/build-week-proof/scripts/capture_live_reviewed_demo.py --reviewer "Javier"
```

The optional `--expected-branch` and `--manifest` flags are for an intentional branch
or local manifest-path change. Do not use them merely to bypass a failed preflight.

## Transaction

The command performs one guarded transaction:

1. Fails before any provider call when the key is absent, without printing its value.
2. Requires the expected branch and a clean worktree.
3. Rebuilds the committed task, catalog, and policy and compares their digests.
4. Materializes the original repository and exact bad and repaired candidate commits.
5. Creates each bounded, redacted, context-bound planner request separately.
6. Calls the existing strict live adapter separately for bad and repaired candidates.
7. Records requested/returned model IDs, response IDs, usage, latency, and binding
   digests when the provider returns them.
8. Stages both captures outside the accepted fixture and validates them with the same
   parser and plan validator used by replay.
9. Requires ordinary `PASS`/`PASS` and Faber Proof `BLOCK`/`PASS`, including the
   material last-turn counterexample.
10. Generates portable reports, scans staged and generated artifacts for the actual key,
    secret patterns, machine paths, raw output, and external assets, then validates
    bundle digests.
11. Replaces reviewed fixture files only after all checks pass, and reruns the complete
    no-key replay demo against the installed result.
12. Writes a review manifest and restores the original fixture if any post-install
    step fails.

Successful output is canonical JSON with:

```text
status: installed-live-reviewed
offline_demo.bad.ordinary_tests: PASS
offline_demo.bad.faber_verdict: BLOCK
offline_demo.repaired.ordinary_tests: PASS
offline_demo.repaired.faber_verdict: PASS
privacy_audit.status: PASS
```

The review manifest defaults to:

```text
.faber/live-gpt56-review-manifest.json
```

It lists every changed fixture path and before/after digest. `.faber/` remains local;
the reviewed, sanitized fixture and sample-report changes are the files considered for
commit.

## Human review after success

1. Keep the API key set only as long as needed, then remove it from the process.
2. Read `.faber/live-gpt56-review-manifest.json`.
3. Confirm both `requested_model` and `returned_model` are the intended real model and
   both captures have real response IDs.
4. Inspect `git diff -- examples/build-week-proof`.
5. Confirm `examples/build-week-proof/replays/provenance.json` says
   `live-reviewed`, names the reviewer/time, and binds the exact bundle digests.
6. Open both generated reports and confirm the bad failed claim/counterexample and
   repaired passing coverage are visible.
7. Rerun the offline checks:

   ```bash
   faber demo proof --mode replay --out-dir .faber/build-week-demo
   faber audit-proof-artifacts .faber/build-week-demo examples/build-week-proof/expected
   python scripts/check_development_report_regeneration.py --check
   python -m pytest -q tests/test_proof_demo.py tests/test_openai_proof_planner.py
   ```

8. Route the final reviewed bundles through the required independent provenance/security
   audit before the submission tag.

Do not commit the local manifest if it contains operational metadata that is not needed
for the public fixture. The sanitized fixture provenance is the repository record.

## Failure behavior

- Missing key, wrong branch, dirty worktree, or authority mismatch fails before a call.
- A failure while capturing or validating either candidate leaves the accepted fixture
  unchanged.
- A failure after installation restores the complete pre-transaction fixture.
- A privacy finding prevents acceptance and does not echo the detected key.
- A provider refusal, timeout, malformed response, unexpected model, wrong binding,
  ordinary-test failure, or wrong proof contrast is a failed transaction.

Do not manually copy one successful candidate into the fixture after the other fails.
The bad and repaired responses form one reviewed unit.

## Credential-free test evidence

The wrapper is tested with injected fake capture and demo functions only:

```bash
python -m pytest -q \
  tests/test_proof_demo.py::test_guarded_live_capture_uses_fake_backend_and_completes_transaction \
  tests/test_proof_demo.py::test_guarded_live_capture_rolls_back_after_post_install_failure \
  tests/test_proof_demo.py::test_guarded_live_capture_preflight_never_calls_provider_without_key_or_clean_branch
```

These tests prove transaction, rollback, and preflight behavior. They do not establish
live model provenance. No provider call is made by the tests or ordinary CI.
