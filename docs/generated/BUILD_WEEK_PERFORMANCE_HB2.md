# Faber Proof Performance Evidence

- Status: **pass**
- Machine: `hb2`
- Platform: `Windows 10`
- Python: `3.11.15`
- Replay provenance: `fake-development`
- Total bad/repaired demo: **6.258291 seconds**
- Total output: **232259 bytes**
- Privacy findings: **0**

| Candidate | Verdict | Replay plan (s) | Proof execution (s) | Report generation (s) | Bundle bytes |
|---|---:|---:|---:|---:|---:|
| bad | **block** | 0.009933 | 0.525121 | 0.004091 | 120324 |
| repaired | **pass** | 0.008773 | 0.524117 | 0.002984 | 108685 |

Thresholds are deliberately generous smoke limits. They catch severe regressions without treating shared CI wall-clock variance as a product failure.

Peak memory is not recorded because the demo launches child Git and Python processes and this stdlib harness cannot measure their portable aggregate peak.
