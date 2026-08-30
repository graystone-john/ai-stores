# Provenance and Acquisition Policy

## Canonical Source Rule

Artifacts stored in AI Stores must be acquired directly from authoritative
upstream sources whenever practical.

Examples include:

- Ubuntu archives and Ubuntu Snapshot
- official Python/PyPI sources
- official Node.js distribution sources
- npm registries
- official GitHub repositories and releases

## Evidence Is Not Canonical Content

Existing machines, caches, old provisioning directories, and previously
downloaded bundles may be used as evidence to determine:

- exact package names
- exact versions
- dependency closures
- hashes
- platform requirements
- previously validated combinations

Their artifact files must not simply be copied into AI Stores and declared
canonical.

Instead:

    historical evidence
        ->
    identify exact upstream artifact
        ->
    acquire from authoritative upstream
        ->
    verify
        ->
    place into Vault

## Native Artifact Preservation

Preserve upstream-native artifact formats and repository semantics wherever
practical.

Examples:

- `.deb` packages remain `.deb`
- Ubuntu packages are presented through an APT repository
- Python packages retain wheel/sdist artifacts
- npm packages retain native package artifacts
- GitHub source is retained in upstream-native forms

Avoid Graystone-specific monolithic bundles when a native repository format
can provide normal dependency resolution.

## Validation

A reconstructed store is not considered validated solely because acquisition
succeeded.

Validation may include:

- package/version comparison
- hash verification
- dependency-resolution tests
- offline installation tests
- full AI Forge provisioning regression tests
