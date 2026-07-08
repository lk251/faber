# Quickstart

Run the canonical check:

```bash
nix develop --command just check
```

Run the local golden path:

```bash
nix develop --command just demo
```

Without Nix, use Python directly:

```bash
export PYTHONPATH=src
python -m faber.cli run-golden-path --store .faber/golden.sqlite3 --out .faber/golden_trajectory.json
```

The command creates a local task contract, worker, approved verifier spec, attempt,
verifier run, receipt, settlement, and exported trajectory. It does not call
GitHub, a payment provider, or a model provider.
