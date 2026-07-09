# Data Rights, Consent, And Licensing

Faber separates three outcomes that are easy to conflate:

- customer work may be useful and accepted;
- minimal receipts may need to remain available for audit;
- trajectory content may or may not be permitted for training or publication.

`TrainingUsePolicy` records repository defaults and stricter task-level policy.
It lists permitted uses, required consent parties, visibility, audit retention,
and public export permission. The resolver intersects permitted uses and keeps
the more restrictive visibility when both levels apply.

`TrajectoryConsent` records the overall training-use decision. Its
`ConsentGrant` entries separately identify the solver/operator and repository
owner/customer, the uses each party granted, the grant time, and provenance.
Absence of consent is not consent.

`DataLicense` is protocol metadata describing intended permitted uses and a
license reference. It is not a legal conclusion. License terms, product flows,
and jurisdiction-specific obligations require later legal review.

Visibility is explicit:

- `public` may be eligible for a public dataset when policy and consent agree;
- `restricted` is limited to an explicitly authorized private boundary;
- `private` is excluded from public export.

`RetentionPolicy` and `DeletionRequest` distinguish private trace content from
audit-critical receipts. A deletion or training-withdrawal request can remove
private process evidence while retaining the contract, attempt identity,
authoritative receipt, settlement reference, and a digest of what was removed.
This is a product and protocol requirement, not a statement about legal
retention duties.

`DatasetExportPolicy` gives each export a purpose such as `rl`, `supervised`,
`research`, `evaluation`, `public_dataset`, or `audit`. Export requires the
repository/task policy, every required consent grant, visibility, and data
license to permit that purpose. Audit access does not imply training permission.
