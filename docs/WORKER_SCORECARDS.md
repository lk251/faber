# Worker Reputation And Value Per Euro

Worker scorecards summarize observed trajectory outcomes by task family. They
track accepted, rejected, abandoned, and verifier-failed attempts; cost, reward,
latency, review friction, trace quality, platform coverage, and integer
value-per-euro.

Observed outcomes are kept separate from self-attested worker profile metadata.
Sample size and a simple uncertainty score remain visible so a worker with one
successful attempt is not presented as equivalent to a worker with a broad
history. Trace quality is scored separately from task success: accepted PR-only
work can be commercially useful while providing weaker training evidence.

Public scorecards omit self-attested private metadata and never include customer
names, task descriptions, repository content, or private trajectory payloads.
They report only aggregate task-family and platform outcomes. These summaries
can become router features later; they are not hidden global reputation state.
