# Faber Proof recording and submission checklist

Official requirements were last re-verified on 2026-07-26 against the Build Week
Devpost rules, FAQ, and official OpenAI product documentation. The submission deadline
has passed. Before editing Devpost, confirm a timely submission exists or obtain explicit
organizer authorization for the intended change.

## Before recording

- [ ] Human confirms deadline/submission status or organizer authorization.
- [ ] Exact final candidate commit is selected and the working tree is clean.
- [ ] `build-week-2026-baseline` resolves to `64f775c`.
- [ ] Full final machine audit passes at the selected candidate.
- [ ] Required independent audits are green with no open P0 finding.
- [ ] Guarded live capture is complete and committed fixtures say `live-reviewed`, or
  every displayed fallback is visibly labeled `REPLAY - FAKE-DEVELOPMENT`.
- [ ] Generated bad/repaired reports pass bundle validation and the privacy audit.
- [ ] Terminal is 120x34 or larger with 18-20 px text.
- [ ] Browser report zoom and subtitle-safe crop have been rehearsed.
- [ ] Desktop notifications, mail, chat, bookmarks, profiles, and unrelated tabs are
  hidden.
- [ ] API keys, local user names, absolute paths, and private repository material do not
  appear anywhere on screen.
- [ ] Microphone level, room noise, and spoken audio have been checked with a short test.
- [ ] Capture is 1920x1080 or better.
- [ ] No copyrighted music, stock footage, logos, or third-party media are included.

## Rehearsal

- [ ] `python scripts/check_demo_script.py` passes.
- [ ] A complete spoken rehearsal is between 2:35 and 2:50.
- [ ] The final edit is under three minutes with margin.
- [ ] The first 12 seconds show green tests and state that the patch is still wrong.
- [ ] The red `BLOCK` and concrete counterexample are legible by 1:25.
- [ ] The trust-boundary explanation is at least ten seconds and states that the model
  plans while approved evidence decides.
- [ ] The Codex repair is narrow and visibly tied to the failed claim.
- [ ] Ordinary tests remain green after the repair.
- [ ] The green `PASS` is shown before 2:22.
- [ ] Codex and GPT-5.6 usage are both explained aloud.
- [ ] No digest is read aloud.
- [ ] Replay is never described as a new live call.

## Final edit

- [ ] Dead time is removed without falsifying execution or chronology.
- [ ] Cuts from live activity to replay footage have a persistent `REPLAY` label.
- [ ] Captions or a transcript are included when practical.
- [ ] Captions remain inside the lower safe region and do not cover verdicts.
- [ ] Audio is intelligible on laptop speakers and headphones.
- [ ] The final duration is recorded: `HUMAN_GATE::VIDEO_DURATION`.
- [ ] The exact audited commit/tag appears in the video description:
  `HUMAN_GATE::FINAL_SUBMISSION_REF`.
- [ ] A frame-by-frame secret and notification review is complete.

## Upload and access

- [ ] Video uploaded to YouTube with public visibility.
- [ ] Public URL recorded: `HUMAN_GATE::PUBLIC_YOUTUBE_URL`.
- [ ] Playback succeeds in an incognito or signed-out browser.
- [ ] Spoken audio is present in the public version.
- [ ] Resolution is 1080p or better after processing.
- [ ] Video remains under three minutes after YouTube processing.
- [ ] Repository URL and exact final commit are in the description.
- [ ] No copyright or age/access restriction blocks judges.

## Repository and Devpost

- [ ] Private repository shared with `testing@devpost.com`.
- [ ] Private repository shared with `build-week-event@openai.com`.
- [ ] Access verified from a separate clean context and retained through judging.
- [ ] `/feedback` session ID is
  `019f6d53-0a3d-71d3-abd7-749dc4a3784c`.
- [ ] Devpost category is Developer Tools.
- [ ] Project text matches `docs/DEVPOST_SUBMISSION.md`.
- [ ] Images use the original sources in `docs/submission-assets/`.
- [ ] Video, repository, session ID, and permitted final commit/tag fields are entered.
- [ ] Devpost preview matches the audited repository state.
- [ ] Submission or modification is permitted under the verified deadline status.
- [ ] Final public/permission checks are repeated after saving.

## Final tag

Do not create `build-week-2026-submission` until every machine, audit, live-provenance,
access, video, and legally permitted submission field is complete. After tagging, run
the final audit from a clean clone at the tag and record the report digest. Never move
the tag silently.

Machine-candidate audit:

```bash
python scripts/final_submission_audit.py \
  --run-machine-checks \
  --require machine \
  --json-out docs/generated/FINAL_SUBMISSION_AUDIT.json \
  --markdown-out docs/generated/FINAL_SUBMISSION_AUDIT.md
```

This may exit zero while the report says `human_status=incomplete`. To require every
human gate and receive exit code 2 until they are complete:

```bash
python scripts/final_submission_audit.py --run-machine-checks --require submission
```

Update only `codex/build-week/submission-human-gates.json` with real attestations and
values. Never mark a gate complete based on inference.
