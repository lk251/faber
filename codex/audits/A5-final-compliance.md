# Audit A5 — Final rules, access, and submission compliance

## Eligibility

Run only after work item 0083 machine work is complete and the candidate submission
commit, README, Devpost draft, video package, final-audit tool, and generated artifacts
exist. Perform this audit before the final immutable submission tag and again against
the tag after human fields are complete.

## Objective

Find any rule, eligibility, access, provenance, timing, or artifact mismatch that could
disqualify an otherwise strong project or prevent judges from evaluating it.

Use current official OpenAI Build Week and Devpost pages as the source of truth. When
network access is unavailable, mark current-rule verification incomplete rather than
relying only on repository notes.

## Official-source verification

Record the date and exact official sources checked. Confirm current values for:

- submission deadline and timezone;
- eligible submission-period start;
- track names;
- required use of Codex and GPT-5.6;
- public video duration, hosting, and spoken-audio requirements;
- repository or test-access requirements;
- private repository judging addresses;
- README and installation requirements for developer tools;
- `/feedback` session ID requirement;
- supported-language or translation requirement;
- free judge access and judging-period availability;
- rules for pre-existing projects and meaningful extensions;
- post-deadline edit restrictions;
- judging criteria and tie-break order.

Use official domains only for the compliance determination. Note any change from
`docs/BUILD_WEEK_2026.md` as P0 until reconciled.

## Eligibility boundary

Verify from Git history, not prose alone:

- `build-week-2026-baseline` points to the last commit before the official start;
- surrounding commits and timestamps support that boundary;
- the Build Week delta tool runs against the candidate commit;
- every claimed new feature appears after the baseline;
- pre-existing Faber capabilities are described as foundation, not competition work;
- eligible commits have not been squashed or rewritten into an opaque history;
- the README, Devpost copy, video, and status file use the same boundary statement;
- live model fixtures and sample reports record honest provenance.

Flag any claim that cannot be tied to a post-baseline commit.

## Required technology evidence

Verify submission-visible evidence that:

- Codex implemented the majority of the new core functionality;
- the primary thread's real `/feedback` session ID is recorded;
- the repository-scoped director and product skills exist and are described accurately;
- the direct `gpt-5.6` path uses the official API integration implemented in the repo;
- final replay bundles are `live-reviewed`, not fake fixtures mislabeled as real;
- GPT-5.6's role is material to the product rather than decorative;
- replay is represented honestly as a bound reproduction path;
- human technical and product decisions are stated.

Do not accept a placeholder, inferred session ID, or undocumented model provenance.

## Repository and judge access

Verify or obtain explicit human attestation for:

- exact repository URL;
- private/public status;
- access granted to every current official judging address;
- invitations accepted or access confirmed from a separate clean context;
- final candidate commit and tag visible to judges;
- submodules, large files, releases, or private dependencies accessible;
- no required secret, paid account, or external approval;
- judge access remains active through the required period;
- install and replay commands work from the judge-visible repository state.

The auditor must not claim external access is verified solely because a local clone
works.

## Video compliance

Inspect the final uploaded video and record:

- public URL;
- public playback while signed out;
- exact duration below three minutes;
- audible spoken explanation;
- explicit Codex and GPT-5.6 use;
- actual product demonstration rather than slides only;
- no secret, personal notification, private repository token, or hidden sensitive path;
- honest live/replay labels;
- no copyrighted third-party music or media used without documented permission;
- final candidate behavior matches the submitted commit;
- description contains the correct project and repository context where appropriate.

A local video file or private/unlisted state that violates current rules is not
sufficient.

## Devpost field consistency

Compare the final entered submission or a complete preview against:

- `docs/DEVPOST_SUBMISSION.md`;
- top-level README;
- final video;
- judge quickstart;
- status and audit reports;
- final tag.

Check:

- project name and tagline;
- Developer Tools category;
- one-sentence description;
- problem, solution, novelty, technical implementation, impact, and decisions;
- Codex session ID;
- repository URL;
- video URL;
- screenshots and captions;
- supported platforms;
- model identifier;
- pre-existing/new-work statement;
- limitations and non-claims;
- final commit/tag.

Flag contradictory metrics, test counts, model names, dates, claims, or URLs.

## Technical final state

Run or inspect current signed evidence for:

- clean working tree;
- full tests;
- Ruff;
- mypy;
- available Nix check;
- build and wheel contents;
- clean-install audit;
- no-key demo scorecard;
- guarded live proof evidence;
- adversarial evals;
- privacy audit;
- deterministic report regeneration;
- final submission audit script;
- baseline-to-final delta;
- tag pointing to the audited commit.

If a result is older than a material source change, rerun it.

## Link and artifact review

Check every user-visible reference in README, Devpost preview, video description, and
judge quickstart:

- repository paths exist with correct case;
- sample reports open;
- commands match current CLI;
- images render;
- video is public;
- no placeholder remains;
- no localhost, private file URI, machine path, or expiring link is used;
- checksums and final audit digests match;
- generated artifacts contain no fixture secret or personal path.

## Deadline and freeze

Record:

- current Madrid time and official deadline in Madrid time;
- planned submission margin;
- candidate tag and audit completion time;
- which human-only steps remain;
- post-deadline change restrictions;
- required judge-availability period.

Treat an unsubmitted Devpost draft, pending repository invitation, missing video upload,
or missing `/feedback` ID as P0 regardless of code quality.

## Deliverable

Write:

```text
codex/build-week/audits/A5-final-compliance-report.md
```

Include:

- official sources and verification timestamp;
- exact candidate commit and tag;
- eligibility-boundary result;
- required-technology result;
- repository-access attestations;
- video result;
- Devpost field consistency;
- technical audit results;
- link/artifact results;
- remaining human actions in exact order;
- P0/P1/P2 findings;
- final verdict.

Update the audit queue and finding ledger.

## Verdicts

Use:

```text
not-green
  Any P0 is open, any required official fact is unverified, or the candidate/tag is not
  the exact audited state.

green-with-P1
  No P0 remains, submission is compliant and runnable, but a non-disqualifying judging
  weakness remains.

green
  All official requirements, access, provenance, links, human fields, and technical
  audit gates are complete against the exact final tag.
```

Do not produce `green` before the public video, repository access, `/feedback` ID,
Devpost submission, and final audited tag are real and verified.