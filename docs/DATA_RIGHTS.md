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

`DatasetWithdrawal` is independent of content deletion. An active withdrawal
marks a trajectory unavailable for future training exports while the minimal
audit view can remain. Dataset manifests report input count, total excluded
count, and the subset excluded specifically because of withdrawal.

`apply_deletion_request()` removes scoped private trace fields and returns the
retained audit view, a `TombstoneRecord`, and a `DeletionReport`. The tombstone
binds the original and retained record digests. The report also binds the
request, retention policy, removed-field digests, preserved receipt references,
and tombstone digest.

These hashes prove which records and fields the deletion operation addressed.
They do not reconstruct deleted content and must not be described as retaining
that content.

`DatasetExportPolicy` gives each export a purpose such as `rl`, `supervised`,
`research`, `evaluation`, `public_dataset`, or `audit`. Export requires the
repository/task policy, every required consent grant, visibility, and data
license to permit that purpose. Audit access does not imply training permission.

Local mode can apply a withdrawal or deletion to one exported record and retain
the report beside it. Hosted operation will require authenticated requests,
propagation across replicas and derived datasets, access logs, backup policy,
and jurisdiction-specific review. Those hosted and legal obligations remain
future work; these protocol records are not legal advice or a retention mandate.
