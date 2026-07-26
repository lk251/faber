# Faber Proof demo shot list

Target edited runtime: 2:35-2:50. Hard submission limit: under three minutes. The
complete narration is in `docs/DEMO_SCRIPT.md`.

## Capture setup

- Record at 1920x1080 or higher, 30 or 60 frames per second.
- Use a 16:9 crop and keep all critical text inside the central 1600x850 region.
- Terminal: 120 columns by at least 34 rows, 18-20 px monospace font, opaque background.
- Browser report zoom: 100% initially; use 125% only for the failed-claim close-up.
- Keep the lower 12% clear for captions and the outer 5% clear for player controls.
- Hide bookmarks, extensions, user profile, notifications, clock, full local paths,
  unrelated tabs, and repository content.
- Use a clean recording account or browser profile. Disable notification banners.
- Never show `OPENAI_API_KEY`, environment panes, shell history containing secrets,
  provider dashboards, private messages, or the local user name.
- Use only the original Faber reports and committed SVG assets. No music or third-party
  media.

## Repository state

Before each take:

```powershell
git status -sb
git branch --show-current
git rev-parse HEAD
git rev-list -n 1 build-week-2026-baseline
```

Record the exact final candidate revision in the video description. The working tree
must be clean. Use a fresh `.faber/video-demo` output directory. Pre-position commands
for pacing, but execute the real commands or clearly label a pre-recorded replay.

## Timeline

| Time | Screen | Exact content and action |
|---|---|---|
| 0:00-0:12 | Terminal, bad candidate | Show four ordinary tests passing and the tiny candidate diff. Keep both green tests and the suspicious budget check visible. |
| 0:12-0:28 | Task contract | Show the last-turn preservation requirement and the two-turn input. Highlight the exact expected complete report. |
| 0:28-0:45 | Codex + skill | Invoke `$faber-proof` or show the exact equivalent Faber command. Display `MODE: REPLAY` prominently when using the no-key path. |
| 0:45-1:02 | Plan summary | Show GPT-5.6 claims, severity, and approved template IDs. Do not show raw provider output or imply that model prose is authority. |
| 1:02-1:25 | Blocked report | Open `.faber/video-demo/bad/report.html`. Keep red `BLOCK`, failed claim, expected/observed result, and bounded counterexample above the fold. Zoom to 125% for five seconds. |
| 1:25-1:40 | Trust boundary asset | Show `docs/submission-assets/trust-boundary.svg`. Point from advisory plan to owner-approved execution to deterministic verdict. |
| 1:40-2:02 | Codex repair | Show the narrow diff moving the complete-report check before budget exhaustion. Compress idle editing time without falsifying the change. |
| 2:02-2:22 | Rerun and passing report | Show ordinary tests still green, rerun the same proof, then open `.faber/video-demo/repaired/report.html` with green `PASS` and 3/3 required obligations. |
| 2:22-2:40 | Comparison asset | Show `docs/submission-assets/demo-comparison.svg`, the no-key command, and the audit/eval facts. Keep `REPLAY: FAKE-DEVELOPMENT` visible until live-reviewed fixtures exist. |
| 2:40-2:47 | Closing | Return to the two reports or comparison visual and speak the tagline. |

## Live versus replay labels

- A real guarded provider run may be labeled `LIVE` only when its metadata says
  `live-reviewed` and the human review transaction completed.
- Current committed fixtures must be labeled `REPLAY - FAKE-DEVELOPMENT`.
- If a live provider call is slow or unavailable, cut to previously captured replay
  output and keep the replay label visible. Do not imply that the replay footage is the
  live call.
- Never expose an API key while proving the live adapter exists.

## Report framing

Blocked report first viewport:

- red `BLOCK`;
- task and bad candidate revision;
- failed last-turn claim;
- expected complete report;
- observed `budget_exhausted`;
- bounded two-turn transcript;
- `REPLAY` or `LIVE` provenance label.

Passing report first viewport:

- green `PASS`;
- repaired candidate revision;
- 3 required, 3 passed, 0 failed, 0 missing;
- same boundary obligation;
- deterministic reason code;
- provenance label.

Do not scroll through digests or logs in real time. They remain in the report for audit.

## Take ledger

For every retained take, record:

| Take | Commit | Mode | Output directory | Audio checked | Secrets checked |
|---|---|---|---|:---:|:---:|
| `HUMAN_GATE::VIDEO_TAKE_ID` | `HUMAN_GATE::FINAL_SUBMISSION_REF` | `HUMAN_GATE::VIDEO_MODE` | `.faber/video-demo` | No | No |

The take ledger is intentionally incomplete until the human recording gate.
