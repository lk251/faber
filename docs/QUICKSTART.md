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

## Funded RL-grade walkthrough

Run the complete fake funded-task product loop:

```bash
python -m faber.cli demo-funded-trajectory --out-dir .faber/funded-demo
```

Or use the matching recipe:

```bash
just demo-funded-trajectory
```

The command writes issue markers, the PR attempt manifest and trace, verifier run,
authoritative receipt, local budget settlement, validated RL-grade trajectory,
permitted training dataset, and a digest-rich run summary. All data and integrations
are local and fake.
