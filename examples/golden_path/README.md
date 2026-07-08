# Golden Path Example

This directory is intentionally small. The golden path CLI uses deterministic
in-repo objects and writes runtime artifacts to `.faber/`.

Run:

```bash
python -m faber.cli run-golden-path --store .faber/golden.sqlite3 --out .faber/golden_trajectory.json
```
