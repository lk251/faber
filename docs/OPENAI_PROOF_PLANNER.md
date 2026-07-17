# OpenAI proof-planner development

Faber's base and replay paths have no OpenAI dependency. Install the optional live
adapter only when a guarded live run is required:

```bash
python -m pip install -e ".[live-openai]"
```

Work item 0078 was syntax-checked against `openai` 2.45.0 in a disposable environment.
The package constraint is deliberately limited to that documented major-version line.

The live adapter uses the Responses API with:

- default model `gpt-5.6`;
- an explicit `https://api.openai.com/v1` base URL; environment overrides are
  rejected;
- a catalog-derived strict JSON schema under `text.format`;
- explicit `reasoning.effort="medium"`, timeout, output bound, and disabled SDK retries;
- `store=False` and no tools;
- one Faber-owned transient retry and at most one invalid-output retry;
- the same local parser and catalog validation used by replay mode.

This shape follows the official [Structured Outputs
guide](https://developers.openai.com/api/docs/guides/structured-outputs), [Responses API
reference](https://developers.openai.com/api/reference/resources/responses/methods/create),
[GPT-5.6 model page](https://developers.openai.com/api/docs/models/gpt-5.6-sol), and
[official Python SDK](https://github.com/openai/openai-python). The SDK remains optional
because a judge must be able to inspect and run replay without an account, key, or
network.

## Guarded live smoke

The live smoke test is disabled unless both variables are present:

```bash
FABER_LIVE_OPENAI_TEST=1 OPENAI_API_KEY=... \
  python -m pytest tests/test_openai_proof_planner_live.py -q -s
```

On success it writes a sanitized replay bundle beneath `.faber/`. It prints only the
plan digest, response ID, model ID, and bundle location. Never enable `OPENAI_LOG` for
the smoke run, never commit its raw output, and review the sanitized bundle before using
it as a checked-in fixture.

Replay execution requires the bundle digest from a trusted repository manifest or the
in-memory live result. A digest recomputed from an untrusted bundle does not
authenticate it; the external pin distinguishes tamper detection from a
self-consistent checksum.

Terminal authentication, permission, refusal, schema, policy, redaction, and replay
errors fail closed. They expose a stable category and safe summary rather than provider
exception text, request headers, request bodies, or credential values.
