# Faber Proof Performance Evidence

- Status: **pass**
- Machine: `hb2`
- Platform: `Windows 10`
- Python: `3.11.15`
- Replay provenance: `fake-development`
- Total bad/repaired demo: **8.890471 seconds**
- Total output: **232260 bytes**
- Privacy findings: **0**

| Candidate | Verdict | Replay plan (s) | Proof execution (s) | Report generation (s) | Bundle bytes |
|---|---:|---:|---:|---:|---:|
| bad | **block** | 0.00965 | 0.542495 | 0.00398 | 120325 |
| repaired | **pass** | 0.008006 | 0.491538 | 0.002776 | 108685 |

Thresholds are deliberately generous smoke limits. They catch severe regressions without treating shared CI wall-clock variance as a product failure.

Peak memory is not recorded because the demo launches child Git and Python processes and this stdlib harness cannot measure their portable aggregate peak.
