# Schema versioning and compatibility

Every exported Faber record carries a schema ID in the form
`faber.<family>.v<positive-integer>`. Version constants live in `faber.schemas`;
`faber.schema_registry.protocol_schema_registry()` turns those constants into the
runtime registry.

## Compatibility policy

- A registered current schema is safe to read.
- A registered deprecated schema remains readable but returns an explicit
  deprecation warning.
- An unknown future version fails in strict mode before required fields are
  deserialized.
- Warning mode preserves an unknown record as opaque data and reports it as
  incompatible. Warning mode is not permission to interpret unknown fields.
- An unregistered historical version also requires an explicit upgrader; version
  numbers alone do not prove compatibility.

Protocol validation paths should use strict mode whenever an unknown record could
affect verification, settlement, rights, or training eligibility. Import/archive
tools may use warning mode to retain opaque records for later migration.

## Upgrades

`upgrade_record()` is the upgrade boundary. For every current v1 record it performs
a deep-copy no-op and reports identical source and target digests. This proves that
calling the upgrade layer does not silently mutate current audit data.

Future upgrades must register a family/version-specific transformation, document
which fields are added or reinterpreted, and test both pre-upgrade and post-upgrade
digests. The current implementation deliberately refuses cross-version upgrades
because no v2 schema exists yet.

## Dataset manifests

Dataset export walks each normalized record recursively and lists every represented
Faber schema ID in `DatasetManifest.schema_versions`. This includes nested task,
attempt, manifest, trace, receipt, settlement, rights, and trajectory-quality
records rather than only the top-level trajectory schema.

The dataset manifest itself uses `faber.dataset_manifest.v1`. Schema inventory does
not imply that every record is compatible; ingestion must still validate required
schemas under the selected compatibility policy.
