# Nix verifier pack

Faber provides an opt-in local verifier pack for tasks where Nix replayability is
part of the task contract. It does not change the requirements of ordinary Faber
tasks and it is not a production sandbox.

`faber.nix_verifiers.nix_reproducibility_verifier_pack()` defines checks for:

- `nix flake check`;
- development-shell startup;
- `flake.lock` presence and content hash;
- package import inside the shell;
- a local CLI smoke command;
- an executable documentation command check.

The package module, CLI command, documentation command, and missing-lockfile policy
can be selected when constructing the pack. The default commands match this
repository. A task opts in by storing `pack.contract_requirement()` under
`TaskContract.environment["nix_verifier_pack"]` and referencing all returned
verifier IDs.

## Fake mode

Windows and other CI systems without Nix can validate orchestration with
`FakeNixVerifierFixture`. `evaluate_fake_nix_verifier()` converts the fixture into
an ordinary `VerifierRun` with:

- a digest of captured stdout and stderr;
- structured exit-code and execution-mode metrics;
- the verifier-spec and fixture digests;
- an explicit marker that the run is local and not a production sandbox.

Fake mode proves Faber's verifier plumbing, not Nix reproducibility. It must not be
reported as a real Nix verifier result.

Missing `flake.lock` evidence may be a warning or a hard failure according to the
pack policy. A present lockfile records its digest in structured metrics.
