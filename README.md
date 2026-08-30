# Graystone AI Stores

Graystone AI Stores is the durable, reproducible artifact repository for the
Graystone environment.

Its purpose is not merely to cache files. AI Stores preserves upstream-native
software artifacts together with the information and tooling required to
reconstruct selected portions of the store from authoritative upstream
sources.

## Core Model

AI Stores is divided conceptually into two major layers:

- `modules/` — the catalog, manifests, provenance information, and rebuild logic
- `vault/` — the actual reconstructed artifact payloads

The Vault is intentionally excluded from Git. A Git clone of this repository
should contain the knowledge and automation necessary to reconstruct it.

## Repository Areas

- `ansible/` — orchestration for rebuilding and validating AI Stores
- `docs/` — architecture, policy, and operational documentation
- `modules/` — reconstruction definitions organized using the same taxonomy as
  the Vault
- `vault/` — large downloaded artifacts and native repositories; gitignored

## Artifact Taxonomy

The intended structure is:

    modules/
      linux/
        ubuntu/
      github/
      node/
      python/

    vault/
      linux/
        ubuntu/
      github/
      node/
      python/

A module acts both as an index describing what belongs in the corresponding
Vault area and as the executable recipe for rebuilding it.

## Principles

1. Canonical artifacts are acquired directly from authoritative upstream
   sources.
2. Existing machines and legacy caches may be used as evidence, but their
   artifacts are not promoted into AI Stores.
3. Upstream-native formats and repository conventions are retained wherever
   practical.
4. Manifests identify exact versions and dependency closures required by
   Graystone-supported software and systems.
5. Acquisition and validation are separate concerns.
6. Large artifact payloads are reproducible and are therefore not committed
   to Git.
