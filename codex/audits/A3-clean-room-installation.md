# Audit A3 — Clean-room installation and judge reproduction

## Eligibility

Run only after work item 0082 is complete. Use a fresh temporary directory, virtual
environment, and clean clone or exported archive at the exact implementation commit.
Do not run primarily from the developer checkout.

## Objective

Determine whether an unfamiliar judge can install Faber Proof and reproduce the blocked
and passing reports without hidden local state, credentials, network-dependent product
behavior, or repository-specific environment variables.

A failure of the documented no-key path is P0.

## Isolation requirements

Before installing:

- record platform, operating-system version, Python version, shell, and commit;
- clear `PYTHONPATH` and repository-specific environment variables;
- confirm no editable Faber installation is active;
- confirm the working directory is outside the developer checkout;
- avoid reusing `.faber/`, build, wheel, cache, or virtual-environment directories from
  implementation work;
- record whether dependency downloads are cached, while ensuring the demo itself makes
  no provider or external-service call.

Where possible, perform one audit on Linux and one on Windows using independent
sessions or CI evidence.

## Installation paths

Test every path the judge documentation advertises, at minimum:

### Wheel path

1. Build wheel and sdist from the exact commit.
2. Create a fresh environment.
3. Install the wheel outside the source tree.
4. Verify the imported package location is inside that environment, not the checkout.
5. Run `faber --help`, `faber doctor`, and the proof demo.

### Fresh-clone path

Follow `docs/JUDGE_QUICKSTART.md` or the current draft using only its commands. Do not
correct unstated prerequisites from memory. Record every ambiguity.

### Base versus live extra

- Confirm base installation succeeds and imports without the OpenAI SDK.
- Confirm live mode fails with a useful message when the optional SDK or key is absent.
- When the live extra is installed, confirm no provider call occurs in replay mode.

## Required reproduction

Run the documented no-key command and verify:

```text
bad ordinary tests: PASS
bad Faber Proof: BLOCK
bad failed required claims: 1 or the documented exact value
bad concrete counterexamples: at least 1
repaired ordinary tests: PASS
repaired Faber Proof: PASS
repaired failed and missing required claims: 0
```

Open both reports from disk and confirm:

- no local server or external asset is needed;
- blocked and passing states render correctly;
- the blocked counterexample is above the fold;
- relative artifact links work after moving the whole bundle to another directory;
- no absolute developer path or user name appears;
- the report agrees with JSON artifacts and process status.

## Packaging checks

Inspect the built wheel and sdist for:

- required Python modules;
- CLI entrypoint;
- proof schemas and templates;
- example or fixture data used by the advertised command;
- skill files when the installation or quickstart claims they are packaged;
- accidental inclusion of `.git`, `.faber`, virtual environments, keys, caches,
  unreviewed live responses, or machine-specific artifacts;
- license and project metadata consistency.

Verify that running from a directory whose name contains spaces works.

## Cross-platform checks

Test or obtain current CI evidence for:

- path separators;
- executable invocation;
- temporary directories;
- line endings and digest stability;
- report file URLs;
- activation commands;
- console encoding;
- symlink behavior where supported;
- Windows drive handling.

Do not advertise a platform based solely on theoretical compatibility.

## Documentation usability

Time a first run while following only the judge quickstart. Record:

- number of commands;
- time from clone/archive to terminal comparison;
- time to open reports;
- errors or decisions not explained by the docs;
- whether expected output is precise enough to detect a bad run;
- whether troubleshooting covers actual failure modes.

The no-key path should be five commands or fewer per platform, excluding opening files.

## Deliverable

Write:

```text
codex/build-week/audits/A3-clean-room-installation-report.md
```

Include:

- exact environment and commit;
- commands copied verbatim from docs;
- install and imported-package locations;
- wheel/sdist contents checked;
- demo scorecard and artifact digests;
- timing;
- platform results;
- P0/P1/P2 findings;
- documentation ambiguities;
- verdict.

Update the audit queue and finding ledger.

## Green criteria

Return `green` only when:

- a fresh environment outside the checkout installs the built artifact;
- the base install has no hidden OpenAI SDK requirement;
- the documented no-key command reproduces the exact demo reversal;
- both reports open locally and remain portable;
- no hidden local state, provider call, credential, or external repository is required;
- advertised platform paths are tested or honestly limited;
- no P0 or unresolved P1 installation finding remains.