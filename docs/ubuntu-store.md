# Ubuntu Store

## Goal

Graystone should be able to configure a machine to use AI Stores as a normal
APT source and then use ordinary commands such as:

    apt update
    apt install <package>

without requiring Internet access.

## Repository Form

Ubuntu content should ultimately be materialized as a native APT repository:

    vault/linux/ubuntu/
    ├── releases/
    │   └── ...
    └── apt/
        ├── pool/
        │   └── ...
        └── dists/
            └── noble/
                ├── Release
                └── main/
                    └── binary-amd64/
                        ├── Packages
                        └── Packages.gz

## NVIDIA 595 Recovery Work

A clean Daedalus installation with NVIDIA 595.84 was used to determine the
known-working Ubuntu package closure.

The resulting temporary closure manifest currently resides outside this Git
repository at:

    /home/nispoe/graystone/provisioning-data/nvidia-595-amd64-closure.tsv

It contains 192 exact package/version pairs.

This manifest is temporary evidence.

It must not become permanent documentation until reconstruction of the
repository is validated.

## Acquisition Findings

The working closure represents packages from multiple historical Ubuntu
archive states.

Therefore a single Ubuntu snapshot date cannot necessarily reconstruct the
entire closure.

The reconstruction process must support resolving each exact package/version
against Ubuntu Snapshot history.

Artifacts must be downloaded directly from official Ubuntu infrastructure.

No `.deb` packages are to be copied from the legacy provisioning-data
directory into AI Stores.

## Validation Requirement

Before the temporary closure manifest is promoted into a permanent module:

1. Reacquire all 192 exact package versions from Ubuntu.
2. Build a valid local APT repository.
3. Configure AI Forge/Daedalus to consume that repository.
4. Provision Daedalus from scratch.
5. Run the base-system Ansible stage.
6. Confirm NVIDIA 595.84 and its required kernel state work correctly.
7. Compare the resulting package state against the known-good installation.
8. Only then promote the closure TSV into the appropriate Git-managed module.

The temporary manifest can then be removed from provisioning-data.
