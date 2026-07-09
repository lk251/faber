# Fake GitHub funded product loop

`faber.adapters.github.funded_product_loop` demonstrates the complete Faber product
path without network access, credentials, custody, or payment providers:

1. A fake GitHub issue becomes a provider-neutral `TaskContract` and local
   `WorkBudget`.
2. Human-readable issue text carries both task and funded-budget markers.
3. A fake PR supplies `.faber/attempt.json`, trace JSONL, and a trace manifest.
4. A platform-owned fake verifier produces the authoritative receipt.
5. `WorkBudgetLedger` registers, reserves, and settles exact integer minor units.
6. The normalized trajectory is checked for RL-grade process, environment, reward,
   and consent evidence.
7. The dataset exporter includes only RL-grade, training-eligible records.

Webhook-shaped deliveries and budget operations are submitted twice in the fixture.
Their idempotency keys produce one event per logical operation.

The negative paths are part of the same function: omitting the trace downgrades the
episode and removes the trace bonus; omitting consent excludes training export; and
a rejected authoritative verifier blocks settlement and releases the reservation.
GitHub candidate CI remains signal only throughout the flow.
