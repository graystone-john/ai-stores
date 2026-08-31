# Ubuntu NVIDIA 595.84

This module reconstructs the Ubuntu APT package set used by Graystone for the
validated NVIDIA 595.84 open-driver installation on Ubuntu Noble amd64.

## Target

- Distribution: Ubuntu
- Release: Noble
- Architecture: amd64
- Driver package: nvidia-driver-595-open
- Driver version: 595.84-0ubuntu0.24.04.1
- Validated kernel: 6.8.0-100-generic

## Manifest

`amd64-closure.tsv` contains the exact package/version closure captured from a
clean, working Daedalus installation.

The manifest is reconstruction metadata only. Package artifacts are always
reacquired directly from official Ubuntu infrastructure.

## Reconstruction

Run:

    scripts/build-apt-repository

The script:

1. Reads the exact package/version closure.
2. Resolves historical versions through Ubuntu Snapshot using APT.
3. Downloads canonical `.deb` artifacts directly from Ubuntu.
4. Validates the acquired package/version set against the manifest.
5. Materializes a normal APT repository under:

       vault/linux/ubuntu/apt/

6. Generates `Packages`, `Packages.gz`, and `Release` metadata.

## Vault

The reconstructed repository is not committed to Git.

Expected layout:

    vault/linux/ubuntu/apt/
    ├── pool/
    │   └── main/
    │       └── *.deb
    └── dists/
        └── noble/
            ├── Release
            └── main/
                └── binary-amd64/
                    ├── Packages
                    └── Packages.gz

## Validation

This module is considered validated only after:

- all manifest package/version pairs are acquired,
- the APT repository indexes are valid,
- offline APT resolution succeeds,
- NVIDIA installs successfully from AI Stores,
- and the AI Forge base-system regression succeeds on a freshly provisioned
  Daedalus.
