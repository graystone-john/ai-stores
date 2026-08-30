# Repository Layout

The intended long-term layout is:

    ai-stores/
    ├── ansible/
    │   ├── playbooks/
    │   └── roles/
    │       └── ai-stores/
    │           └── tasks/
    │
    ├── docs/
    │
    ├── modules/
    │   ├── linux/
    │   │   └── ubuntu/
    │   ├── github/
    │   ├── node/
    │   └── python/
    │
    ├── vault/
    │   ├── linux/
    │   │   └── ubuntu/
    │   ├── github/
    │   ├── node/
    │   └── python/
    │
    ├── .gitignore
    └── README.md

## modules/

Git-managed reconstruction definitions.

The hierarchy intentionally mirrors `vault/`.

For versioned software, modules should preserve meaningful version boundaries.

Example:

    modules/linux/ubuntu/nvidia/
      595.84/
        noble-amd64-kernel-6.8.0-100/
          module.yaml
          manifest.tsv
          scripts/
          README.md

This allows multiple supported versions to coexist for rollback,
reproducibility, and future hardware requirements.

## vault/

Large reconstructed artifact content.

The Vault may contain native repository structures such as:

    vault/linux/ubuntu/
      releases/
      apt/

    vault/python/
      pypi/
      runtimes/
      tooling/

    vault/node/
      npm/
      runtimes/

    vault/github/

The entire `vault/` directory is gitignored.

## ansible/

Ansible is the orchestration surface for rebuilding sections of the Vault.

Module-specific acquisition logic should normally remain inside the
corresponding module rather than being duplicated inside Ansible.
