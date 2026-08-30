# AI Stores Architecture

## Purpose

AI Stores is Graystone's durable offline software and artifact repository.

The project is intended to make important software reconstructable,
inspectable, reproducible, and usable without Internet access.

AI Stores has two complementary layers.

## Modules

`modules/` contains reconstruction knowledge.

A module may contain:

- artifact or package manifests
- exact package/version closures
- upstream provenance information
- acquisition configuration
- validation rules
- executable rebuild scripts
- module-specific documentation

The module hierarchy mirrors the artifact hierarchy.

Example:

    modules/linux/ubuntu/nvidia/595.84/...

describes content ultimately materialized into:

    vault/linux/ubuntu/...

Modules are committed to Git.

## Vault

`vault/` contains the actual artifact payloads.

Examples include:

- Ubuntu `.deb` packages
- APT repository indexes
- Ubuntu installation ISOs
- Python packages
- Python runtimes
- Node.js runtimes
- npm packages
- GitHub source releases or repositories

The Vault is not committed to Git.

It should be possible to delete the Vault and reconstruct supported portions
of it from the Git-managed modules and upstream sources.

## Ansible

`ansible/` provides high-level orchestration.

Ansible should invoke tested lower-level module tooling rather than embedding
all acquisition logic directly into playbooks.

A typical rebuild flow is:

    Ansible playbook
        ->
    module definition
        ->
    acquisition/build script
        ->
    authoritative upstream
        ->
    Vault
        ->
    validation

## Relationship to AI Forge

AI Forge consumes AI Stores.

AI Forge defines machines and how they are provisioned.

AI Stores defines and preserves the software and artifacts needed to perform
that provisioning.

AI Forge should not become the canonical repository for third-party software
artifacts.

AI Stores should not contain AI Forge's transient machine provisioning state.

## Transitional State

At present, existing artifact trees including `linux/`, `python/`, `node/`,
and `github/` still exist at the AI Stores repository root.

These locations are temporarily gitignored.

They will be migrated under `vault/` after all active consumers are updated
and regression tested.
