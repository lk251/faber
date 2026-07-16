# Work item 0076 — Build Week control plane and eligibility baseline

## Objective

Establish a defensible competition boundary, a clean implementation branch, and a
reproducible status baseline before changing product code.

This work item exists because Faber predates the hackathon and only work added during
the submission period will be judged.

## Required context

Read, in order:

1. `AGENTS.md`
2. `docs/CODEX_SESSION_HANDOFF.md`
3. `codex/BUILD_WEEK_START_HERE.md`
4. `docs/BUILD_WEEK_2026.md`
5. `docs/FABER_PROOF_PRODUCT.md`
6. `codex/build-week/STATUS.md`

## Tasks

### 1. Establish the implementation branch

Inspect the current branch and working tree.

- Create or switch to `build-week/faber-proof` from the current canonical `master`.
- Do not discard, stage, or merge unrelated local changes.
- Record the starting branch head in the status file.

### 2. Identify and tag the eligibility baseline

Compute the latest commit strictly before the official submission-period start:

```bash
git rev-list -1 --before="2026-07-13T09:00:00-07:00" master
```

Validate the result with surrounding log entries and author/committer dates. Create an
annotated tag:

```text
build-week-2026-baseline
```

The annotation must state that the tag marks the last pre-submission Faber commit for
competition accounting. Do not move an existing tag silently; fail and report if it
already exists at a different commit.

### 3. Add a Build Week delta tool

Create a small deterministic script, preferably `scripts/build_week_delta.py`, that can
compare the baseline tag with a target ref and emit either Markdown or JSON containing:

- baseline and target commit SHAs;
- commit count;
- dated commit list;
- changed file list and line statistics when available;
- files grouped into pre-existing, Build Week core, demo, tests, docs, and submission
  support;
- a warning when the baseline tag is missing;
- a warning when commits have author or committer dates before the submission period;
- a warning when the working tree is dirty.

Use only local Git commands. Do not require GitHub, network access, or a new runtime
dependency.

Add focused tests using a temporary Git repository. Tests must cover:

- missing baseline tag;
- a valid commit range;
- a dirty working tree;
- deterministic JSON output;
- paths with spaces;
- Windows-safe invocation and decoding assumptions.

### 4. Record the boundary

Update `docs/BUILD_WEEK_2026.md` and `codex/build-week/STATUS.md` with the actual:

- baseline SHA;
- current branch starting SHA;
- tag verification result;
- eligible commit count at the time of this work item;
- active primary-session designation;
- current validation results.

Add a concise `Build Week 2026` section near the top of `README.md` that says:

- Faber predates the competition;
- the competition entry is the new Faber Proof extension;
- only the post-baseline extension is claimed as Build Week work;
- the full judge instructions will be completed by work item 0083.

Do not yet rewrite the whole README.

### 5. Override the normal handoff temporarily

Update `docs/CODEX_SESSION_HANDOFF.md` so its recommended next action is the Faber Proof
Build Week queue through the submission deadline. Preserve the external-pilot material
as the post-submission roadmap; do not delete it.

The handoff must direct fresh sessions to:

```text
codex/BUILD_WEEK_START_HERE.md
codex/build-week/STATUS.md
```

### 6. Re-establish the repository validation baseline

Run the full available checks before product changes:

```bash
python -m pytest
python -m ruff check .
python -m mypy src
```

Also run:

```bash
nix develop --command just check
```

when Nix is available. Record exact versions, counts, and unavailable tooling in the
handoff and status file.

## Constraints

- Do not implement proof protocol or OpenAI integration in this item.
- Do not rewrite Git history.
- Do not squash the planning commits already added during the eligible period.
- Do not claim pre-existing Faber features as new.
- Do not perform any external publication or repository-sharing action.
- Keep all scripts dependency-free and cross-platform.

## Acceptance criteria

- `build-week/faber-proof` is the active implementation branch.
- `build-week-2026-baseline` exists at the verified last pre-period commit.
- The delta script emits deterministic output and has focused tests.
- README, competition document, handoff, and status all state the actual boundary.
- Full available checks pass, or every failure is precisely documented and is not
  caused by this work item.
- The working tree is clean after one focused commit.
- `codex/build-week/STATUS.md` marks 0076 complete and names 0077 as next.

## Commit

Use one focused commit with a message similar to:

```text
Implement work item 0076 Build Week control plane
```

Do not proceed to 0077 with an uncommitted or ambiguous eligibility state.