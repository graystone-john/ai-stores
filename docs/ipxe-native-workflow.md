# Graystone native iPXE workflow

This package adds two scripts to the existing repositories. It does not replace
the existing amd64 `capture-installed-apt-closure` script or the Ansible task
that acquires Ubuntu's legacy iPXE package.

| Location | Commands |
| --- | --- |
| `ai-stores/scripts/ipxe-artifacts` | `snapshot-index`, `capture`, `acquire`, `verify`, `dependencies`, `build` |
| `ai-forge/scripts/ipxe-loader` | `status`, `deploy`, `rollback`, `record-test` |

## Scope and current evidence

The tested upstream commit is `ff6e52063e0b37062394fe37b9788af25175e7af`.
The controller is Ubuntu 24.04 ARM64; the output target is x86-64 UEFI.
The Aquantia PCI ID is `1d6a:14c0`, iPXE driver name `AQC13`, provisioning MAC
`d8:5e:d3:0e:b8:3c`, reserved IP `10.10.10.21`.

The supplied conversation photo establishes DHCP and HTTP success for the
historical automatic diagnostic binary. It does not validate a newly rebuilt
binary. Normal Forge handoff, local boot, keyboard behavior, full provisioning,
and daedalus-01 regression remain to be tested.

The source patch disables NII selection in the `snponly` target. The successful
full `ipxe.efi` uses the native Aquantia driver. This workflow preserves the
patch and the entire ignored `src/config/local` directory to retain the tested
recipe; it does not claim that the NII patch is what fixed the native driver.

## Install these scripts first

This is revision 4, adding exact-hash historical fallback for a package URL
that returns HTTP 404/410 during acquisition. Revision 3 added an explicit
timestamp URI for historical indexes.
Revision 2 incorrectly relied on snapshot discovery in an empty private APT
cache; that failed on Athena with "Snapshots not supported". If revision 1, 2 or 3 is
already installed, extract the updated package and run:

```bash
sha256sum -c SHA256SUMS
/usr/bin/python3 update-workflow.py --base /home/nispoe/graystone
```

This guarded updater backs up and replaces only the known earlier artifacts
script and guide. It refuses unexpected local edits. The deployment script is
unchanged. Use `install-workflow.py` below only for a first installation.

Save and extract `graystone-ipxe-workflow.tar.gz` on Athena. For example, if the
download is in `~/Downloads`:

```bash
cd ~/Downloads
tar -xzf graystone-ipxe-workflow.tar.gz
cd graystone-ipxe-workflow
sha256sum -c SHA256SUMS
/usr/bin/python3 install-workflow.py --base /home/nispoe/graystone
```

The installer adds the two scripts and this guide at
`ai-stores/docs/ipxe-native-workflow.md`. It refuses to overwrite a different
existing file. It does not acquire artifacts, change deployed loaders, restart
services, or commit to Git. Existing working-tree changes are retained.

## 1. Capture the tested state on Athena

Run as `nispoe`, using Ubuntu's `/usr/bin/python3` rather than a virtualenv.
Capture reads the installed package database and existing trusted APT indexes;
it does not require Internet access or refresh indexes.

```bash
cd ~/graystone/ai-stores

./scripts/ipxe-artifacts capture \
  --evidence /home/nispoe/graystone/ai-stores/vault/tools/ipxe/snp-test-R66vNn \
  --snapshot /home/nispoe/graystone/ai-stores/vault/tools/ipxe/native/ff6e520-arm64-v1
```

The capture is immutable once sealed. Repeating capture with the same output
path fails instead of overwriting it. A new run should use a new version suffix.

Capture preserves:

- The exact Git commit and tracked patch, including staged changes.
- All local build configuration files, including ignored files.
- Embedded scripts, prior EFI binaries, build logs, source archive and hashes.
- Compiler/linker identification and OS details.
- Exact installed root package versions and recursive `Depends`/`PreDepends`,
  including selected installed alternatives and virtual-package providers.
- Official package URIs, version/architecture/size/SHA256 and trusted origin
  records. Available official Ubuntu InRelease headers are evidence too.
- A copy of the artifact script used to define this capture.

This closure deliberately accepts host `arm64` and architecture-independent
`all` packages. The cross-compiler runs on ARM64 and produces x86-64 code.
The closure assumes an existing Ubuntu 24.04 ARM64 base OS; it is not a complete
operating-system installer image.

If a root build package is missing, capture names it and stops. Install that
package explicitly, then rerun capture. If exact installed package versions are
no longer indexed, revision 2 lists all missing records instead of stopping at
the first one. Recover historical metadata using `snapshot-index`.

### Recover superseded versions using private snapshot indexes

Athena has OpenSSL `3.0.13-0ubuntu3.12`, while today's indexes contain `.15`.
The installed version exists only in dpkg status, with no downloadable source.
Do not upgrade it just to make capture pass. The native Ubuntu Snapshot service
can provide the historical package indexes and canonical download URLs.

Start with an August 31 snapshot. This is a date to search, not a claim that
every installed dependency was available at that instant:

```bash
cd ~/graystone/ai-stores
./scripts/ipxe-artifacts snapshot-index \
  --date 20260831T120000Z \
  --output /home/nispoe/graystone/ai-stores/vault/tools/ipxe/apt-indexes/20260831T120000Z-arm64

./scripts/ipxe-artifacts capture \
  --evidence /home/nispoe/graystone/ai-stores/vault/tools/ipxe/snp-test-R66vNn \
  --snapshot /home/nispoe/graystone/ai-stores/vault/tools/ipxe/native/ff6e520-arm64-v1 \
  --snapshot-index /home/nispoe/graystone/ai-stores/vault/tools/ipxe/apt-indexes/20260831T120000Z-arm64
```

Run these as the ordinary operator, without sudo. `snapshot-index` downloads
metadata only. Its APT configuration, source selection, caches and list files
live beneath the specified output directory. It reads the host's dpkg status
and copies the official Ubuntu archive keyring. It does not edit `/etc/apt`,
refresh `/var/lib/apt/lists`, install packages or run system APT hooks.

Only Ubuntu signatures are trusted. Historical metadata's expiration is ignored
within this private operation; signature checks remain required. Sources use
`https://snapshot.ubuntu.com/ubuntu/<timestamp>/` directly with `Architectures:
arm64`, without a `Snapshot` field or repository-discovery requirement. The
resolver additionally requires `snapshot.ubuntu.com` package URIs.

Capture still traverses the actual installed dependency graph. Historical
indexes supply only the metadata for an exact name/version/architecture match;
they never choose a new version. The resolver runs in a separate process to
isolate libapt's global configuration. Signed indexes used for fallback are
copied into the captured evidence, with their checksums and snapshot date.

If some exact versions remain missing, capture prints the full remaining list.
Create another index directory for a date when those versions were published,
then repeat `--snapshot-index PATH` on the capture command for each date. A
completed index can be reused; it must remain at its original path because the
private source configuration refers to its local keyring. A failed download is
removed and can be retried. Package payloads are fetched later by `acquire`.

## 2. Acquire canonical upstream artifacts while online

```bash
cd ~/graystone/ai-stores

./scripts/ipxe-artifacts acquire \
  --snapshot /home/nispoe/graystone/ai-stores/vault/tools/ipxe/native/ff6e520-arm64-v1

./scripts/ipxe-artifacts verify \
  --snapshot /home/nispoe/graystone/ai-stores/vault/tools/ipxe/native/ff6e520-arm64-v1
```

Acquisition fetches the exact Git commit from the official iPXE repository and
creates a clean source archive. Its uncompressed archive is compared against
the original clean-source evidence. The local patch is kept separate.

Each `.deb` is first fetched directly from its captured official Ubuntu URL, checked
against its upstream SHA256 and size, and checked for matching package control
fields. The resulting native APT repository contains `.deb` files, `Packages`,
`Packages.gz` and `Release`. No installed-machine `.deb` cache is promoted into
canonical content. If that URL returns HTTP 404/410, revision 4 reuses the
original historical index directories recorded in the sealed capture. Their
manifests must match the captured evidence. It selects only the same exact
package/version/architecture with the same SHA256 and size, then downloads from
the official snapshot URI. Both attempted URLs and the actual source are
recorded in acquisition metadata. A copy of the acquisition script is retained
too. The sealed capture does not change and does not need to be rerun.

The historical index directories must still exist at their recorded locations
for this fallback. Keep `vault/tools/ipxe/apt-indexes/` until acquisition is
complete. Different bytes, unindexed versions or further unavailable URLs stop
acquisition. HTTP errors other than 404/410 are reported with the package and
URL rather than treated as a version-availability problem.

Completed acquisitions are verified and reused. Failed acquisition staging
is removed; a retry redownloads that acquisition. An acquisition can contain
hundreds of megabytes or more depending on the installed dependency closure.

The snapshot has separate areas:

| Area | Meaning |
| --- | --- |
| `capture/evidence/` | Historical files; not canonical downloads |
| `capture/recipe/` | Graystone patch, local configuration and embedded scripts |
| `capture/capture.json` | Version, environment, dependency and validation metadata |
| `acquired/upstream/` | Clean source acquired from official iPXE upstream |
| `acquired/apt/` | Native local APT repository of exact official Ubuntu packages |
| `acquired/acquisition.json` | Acquisition provenance, bound to capture checksum |
| `capture/checksums.json`, `acquired/checksums.json` | Full file-inventory and SHA256 verification |

Checksums detect corruption and unexpected changes; they are not signatures.
Keep the snapshot and its manifests under the same trusted backup/access policy
as other AI Stores artifacts. This local repository uses per-command
`trusted=yes` only after verification against the captured official package
hashes. No permanent system APT source or trust key is installed.

## 3. Offline dependency check and build

Both commands require a network namespace with no interfaces other than
loopback. The examples use privileged `unshare --net`, avoiding dependence on
unprivileged user namespaces or changes to AppArmor. They do not disconnect
Athena's host network or stop its provisioning services.

First simulate dependency installation. No packages are changed by this command:

```bash
sudo unshare --net -- /usr/bin/python3 \
  /home/nispoe/graystone/ai-stores/scripts/ipxe-artifacts dependencies \
  --snapshot /home/nispoe/graystone/ai-stores/vault/tools/ipxe/native/ff6e520-arm64-v1
```

On the original capture host the required package versions should already be
installed. On a fresh compatible Ubuntu 24.04 ARM64 host, review the simulation,
then install the captured versions offline with:

```bash
sudo unshare --net -- /usr/bin/python3 \
  /home/nispoe/graystone/ai-stores/scripts/ipxe-artifacts dependencies \
  --snapshot /home/nispoe/graystone/ai-stores/vault/tools/ipxe/native/ff6e520-arm64-v1 \
  --apply
```

Temporary APT sources point only to the local captured repository. Package
removals and unattended downgrades are not allowed. If the host has newer core
packages, investigate the simulation or use a matching clean build environment
instead of downgrading the controller blindly. Strict version checking is
intentional: a different toolchain is a different build recipe.

Build as the ordinary operator inside the isolated network namespace:

```bash
sudo unshare --net -- runuser -u nispoe -- /usr/bin/python3 \
  /home/nispoe/graystone/ai-stores/scripts/ipxe-artifacts build \
  --snapshot /home/nispoe/graystone/ai-stores/vault/tools/ipxe/native/ff6e520-arm64-v1 \
  --output /home/nispoe/graystone/ai-stores/vault/tools/ipxe/builds/ff6e520-arm64-v1 \
  --jobs 4
```

Build verifies both manifests and every captured installed package version,
extracts pristine upstream source, applies the captured patch/configuration,
then builds diagnostic and Forge EFI binaries with the corresponding embedded
scripts. Compiler output is in `diagnostic.log` and `forge.log`; the CLI announces
each variant. Failed builds retain an explicitly incomplete directory for
diagnosis. Successful output includes build metadata and checksums.

The source archive does not contain `.git` metadata. Git discovery is stopped
at the extracted source boundary so iPXE cannot pick up the enclosing ai-stores
repository's version by accident. This workflow preserves
source/configuration/toolchain inputs and sets `SOURCE_DATE_EPOCH`, but does not
assert byte-for-byte identity with the original worktree builds. Each new binary
must pass the hardware checks below before promotion. The built diagnostic still
runs without keyboard input; the keyboard issue remains unresolved.

## 4. Deploy and rollback

Deployment expects the already-established three-line test routing in BOTH
`ai-forge/configs/dnsmasq/provisioning.conf` and
`/etc/dnsmasq.d/provisioning.conf`:

```ini
dhcp-mac=set:daedalus02-snp,d8:5e:d3:0e:b8:3c
dhcp-boot=tag:efi64,tag:!ipxe,tag:daedalus02-snp,snponly.efi
dhcp-boot=tag:efi64,tag:!ipxe,tag:!daedalus02-snp,ipxe.efi
```

If the repository copy lacks these existing test rules or has a different
layout, the script stops before changes. Share that file and the generator so
the integration can be adapted to the actual layout. It does not reconstruct
an unknown dnsmasq configuration. It checks extra matching EFI rules within
the target file; review any additional dnsmasq configuration files as part of
the controller configuration regression.

First set daedalus-02 to normal mode, then check the existing routing:

```bash
cd ~/graystone/ai-forge
./scripts/set-mode daedalus-02 normal

sudo ./scripts/ipxe-loader \
  --state /home/nispoe/graystone/ai-stores/vault/tools/ipxe/deployments \
  status
```

Deploy the freshly rebuilt diagnostic FIRST:

```bash
sudo ./scripts/ipxe-loader \
  --state /home/nispoe/graystone/ai-stores/vault/tools/ipxe/deployments \
  deploy \
  --build /home/nispoe/graystone/ai-stores/vault/tools/ipxe/builds/ff6e520-arm64-v1 \
  --variant diagnostic
```

The script verifies the build, checks the known controller NORMAL response,
backs up the current selected binary and both configurations, writes a unique
`ipxe-aqc13-<sha256-prefix>.efi`, updates only the Aquantia selection line in both
configurations, checks dnsmasq syntax, and restarts dnsmasq. The restart briefly
interrupts DHCP/TFTP service, so run when no other provisioning transfer is
active. The legacy `ipxe.efi` file and legacy selection line are preserved.
Normal mode must remain unarmed for this validation; do not arm concurrently.

The current embedded Forge script intentionally checks that `net0` matches the
Aquantia MAC. If hardware enumeration changes, it stops. The generic Forge
entry script still uses `net0/mac`; multi-interface boot selection is a separate
integration change that this package does not make.

Boot daedalus-02 through onboard UEFI PXE and record DHCP and HTTP results. Once
the new diagnostic passes, deploy the `forge` variant using the same command
with `--variant forge`. Keep normal mode for its first boot handoff test.

Deployment prints its transaction directory. To roll it back:

```bash
sudo ./scripts/ipxe-loader \
  --state /home/nispoe/graystone/ai-stores/vault/tools/ipxe/deployments \
  rollback --transaction /absolute/path/printed/by/deploy
```

Rollback checks backup hashes and refuses to overwrite configurations or
binaries changed since deployment. It restores the previous selection in both
configurations and restarts dnsmasq. Old and new binaries remain available as
evidence. Ordinary deployment failures attempt automatic restoration and
record whether recovery succeeded. If the controller loses power mid-write,
inspect the `prepared` transaction and configuration backups before proceeding;
there is no claim of atomicity across multiple files and a service restart.

The repository configuration update preserves unrelated edits and file
ownership. Re-run `status` after any existing generator/deploy playbook to
detect routing drift. Automatic Ansible integration remains a follow-on to
inspection of the actual generator; the old acquisition task stays in place
for daedalus-01.

## 5. Validation and result recording

| Target/check | Pass evidence |
| --- | --- |
| daedalus-02 diagnostic | Correct onboard MAC, `AQC13`, link up, DHCP `10.10.10.21`, HTTP download success |
| daedalus-02 Forge normal | Recognized as daedalus-02, NORMAL response, observed return to firmware/local boot |
| daedalus-01 regression | Existing legacy loader hash, correct reservation, DHCP, HTTP, Forge recognition and normal boot |
| Keyboard | Explicit typing test; do not infer success from an automatic script |
| Full provisioning | Separate deliberately armed installation and subsequent SSH/Forge validation |

Do not arm either machine merely to test normal PXE handoff. Full provisioning
can erase the registered OS disk and is outside these scripts' automatic actions.
The original NIC firmware has not been flashed by this workflow.

Use `status` to obtain the exact loader hash for the test, save a transcript or
photo on Athena, then record the result immediately (before another deployment):

```bash
sudo ./scripts/ipxe-loader \
  --state /home/nispoe/graystone/ai-stores/vault/tools/ipxe/deployments \
  record-test \
  --machine daedalus-02 \
  --test dhcp \
  --result pass \
  --expected-sha256 ACTUAL_LOADER_SHA256 \
  --evidence /absolute/path/to/test-photo.jpg \
  --notes 'AQC13 on onboard MAC; DHCP assigned 10.10.10.21.'
```

Replace the placeholders with actual observed values; never enter a pass before
the test. Records bind the operator-reported result and evidence hash to the
active loader SHA256. Supported checks are `dhcp`, `http`, `forge-normal`,
`local-boot`, `keyboard`, and `full-provisioning` for both machines.

## Local verification performed for this package

The included 19 automated tests passed in the preparation environment. They
exercise ARM64/all closure selection and installed-version pinning; rejection
of unavailable exact packages, tampering, wrong EFI architecture and ambiguous
routes; preservation of the legacy binary and unrelated configuration edits;
rollback; simulated service-restart failure recovery; and test/hash mismatch.
Revision 2 also tests exact-version metadata recovery, complete missing-package
reporting, and private APT configuration. The snapshot network download and
Ubuntu libapt integration must still be checked on Athena.
Revision 3 additionally exercises APT's real `--print-uris update` operation
against the generated isolated source configuration without making downloads,
verifying direct ARM64 snapshot URLs are selected.
Revision 4 tests recovery from a missing live package URL, rejection of a
different snapshot hash, and distinction between missing packages and server
errors. Actual upstream package availability is checked during acquisition on
Athena, not asserted by these local tests.

Run them from the extracted package with:

```bash
/usr/bin/python3 -m unittest discover -s tests -v
```

Deployment tests use temporary files and mock root/service/controller calls.
They do not restart real services. Actual Ubuntu ARM64 acquisition, offline
dependency installation, compilation, dnsmasq runtime and hardware regression
cannot be validated from the preparation environment; these are staged Athena
checks, not claims of completed testing.

## Git and durable artifact handling

Review and commit only the added workflow files and, after a deliberate
deployment, the intended dnsmasq routing change. Keep existing unrelated edits
out of that commit. Vault evidence, upstream source, packages, build outputs,
and transaction/test records follow the repository's existing vault policy;
back them up through the normal ai-stores process.

The package installs no skills, changes no access controls, sends no messages,
and initiates no OS provisioning. The original hardware-specific test setup is
preserved until an explicit `deploy` command is run.

## Primary technical references

- [iPXE build targets and CROSS toolchain selection](https://ipxe.org/appnote/buildtargets)
- [python-apt package versions, installed dependencies and origin metadata](https://apt-team.pages.debian.net/python-apt/library/apt.package.html)
- [Ubuntu apt-get reference](https://manpages.ubuntu.com/manpages/noble/man8/apt-get.8.html)
- [Official Ubuntu Snapshot source configuration](https://snapshot.ubuntu.com/)

The source acquisition and evidence separation also follow the user-supplied
`ai-stores/docs/provenance-policy.md`.
