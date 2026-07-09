# Task And Submission Adapters

Faber Protocol does not depend on a particular forge, benchmark, or market.
`TaskSourceAdapter` converts an `ExternalTaskReference` into an ordinary
`TaskContract`. `SubmissionAdapter` converts typed `ArtifactReference` records
into an ordinary `Attempt`. Verification, trajectory validation, and settlement
then use the same core lifecycle regardless of source.

Artifact kinds cover patches, commits, files, generated outputs, and non-code
work. Each reference binds a locator to a content digest and optional media type;
the locator is not treated as authority.

The local adapters provide two account-free paths:

- `LocalJsonTaskSource` reads one task JSON file;
- `LocalFilesystemTaskSource` reads `task.json` from a directory;
- `LocalFilesystemSubmissionAdapter` binds local artifacts into an attempt.

These adapters perform no external API calls and require no server. Platform
adapters may add platform metadata at their own boundary, but platform-specific
issue, pull-request, installation, or webhook fields are not part of the generic
task-source and submission contracts.
