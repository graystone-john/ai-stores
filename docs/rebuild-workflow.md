# Rebuild Workflow

AI Stores should eventually support reconstruction from a fresh Git clone.

The intended workflow is:

    git clone ai-stores
        ->
    install/bootstrap required tooling
        ->
    select modules to reconstruct
        ->
    Ansible orchestrates module builds
        ->
    modules acquire canonical artifacts from upstream
        ->
    materialize Vault
        ->
    validate
        ->
    make artifacts available to AI Forge

Individual modules should be independently rebuildable.

Examples:

    ansible-playbook playbooks/ubuntu-nvidia-595.84.yaml

or future equivalents for:

    Python package stores
    Node/npm stores
    GitHub source stores
    Ubuntu releases
    Ubuntu package repositories

Rebuilding one module should not require rebuilding unrelated sections of the
Vault.
