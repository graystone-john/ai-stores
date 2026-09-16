#!/usr/bin/env python3
"""Acquire an isolated amd64 CUDA build repository; never install packages."""
import argparse
import datetime
import gzip
import hashlib
import json
import os
import pwd
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import urllib.request

NVIDIA = 'https://developer.download.nvidia.com/compute/cuda/repos/ubuntu2404/x86_64/'
ROOTS = ['build-essential', 'cmake', 'gcc-13', 'g++-13', 'git', 'gzip',
         'libcurl4-openssl-dev', 'cuda-toolkit-12-8=12.8.1-1']


def plan_packages(text):
    result = {}
    for line in text.splitlines():
        if line.startswith('Remv '):
            raise ValueError('Resolver proposed package removal: ' + line)
        if not line.startswith('Inst '):
            continue
        match = re.match(r'^Inst ([^ :]+)(?::amd64)?(?: \[[^\]]+\])? \((\S+)', line)
        if not match:
            raise ValueError('Unrecognized APT install action: ' + line)
        name, version = match.groups()
        if name in result and result[name] != version:
            raise ValueError('Conflicting package versions in plan: ' + name)
        result[name] = version
    return result


def protect_plan(plan, held):
    for name in plan:
        if name in held or re.match(
            r'^(?:linux-(?:generic|image|headers|modules)|cuda-drivers|'
            r'nvidia-(?:driver|dkms|kernel|firmware)|libnvidia-)', name):
            raise ValueError('Resolver proposed changing protected package: ' + name)


def baseline_status(status, holds):
    held = set(holds.split())
    installed = set()
    paragraphs = []
    for paragraph in status.strip().split('\n\n'):
        fields = dict(line.split(': ', 1) for line in paragraph.splitlines()
                      if ': ' in line and not line[0].isspace())
        name = fields.get('Package', '')
        state = fields.get('Status', '')
        if state.endswith(' ok installed'):
            if fields.get('Architecture') not in ('amd64', 'all'):
                raise ValueError('Baseline contains a non-amd64/all installed package: ' + name)
            installed.add(name)
            if name in held:
                paragraph = paragraph.replace('Status: ' + state, 'Status: hold ok installed', 1)
        elif state and not state.endswith(' ok config-files') and state != 'deinstall ok not-installed':
            raise ValueError('Baseline contains an incomplete package state: ' + name + ' ' + state)
        paragraphs.append(paragraph)
    if not installed or not held.issubset(installed):
        raise ValueError('Empty baseline or held package missing from installed baseline')
    return '\n\n'.join(paragraphs) + '\n\n', held


def converge(simulate, roots, held):
    """Find a fixed exact set valid both from empty state and the installed baseline."""
    pins = {}
    for turn in range(1, 9):
        requested = [f'{p}={v}' for p, v in sorted(pins.items())] or roots
        empty = plan_packages(simulate('empty', requested, turn))
        protect_plan(empty, held)
        for name, version in pins.items():
            if empty.get(name) != version:
                raise ValueError('Empty-state solver changed a pinned dependency: ' + name)
        target = plan_packages(simulate('baseline', [f'{p}={v}' for p, v in sorted(empty.items())], turn))
        protect_plan(target, held)
        combined = dict(empty)
        for name, version in target.items():
            if name in combined and combined[name] != version:
                raise ValueError('Baseline solver changed a pinned dependency: ' + name)
            combined[name] = version
        if combined == empty:
            return combined
        pins = combined
    raise ValueError('Dependency solution did not converge in eight rounds')


def sha(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def run(argv, *, env=None, cwd=None):
    result = subprocess.run(list(map(str, argv)), env=env, cwd=cwd,
                            text=True, stdout=subprocess.PIPE,
                            stderr=subprocess.STDOUT)
    if result.returncode:
        raise RuntimeError(f"Command failed: {argv[0]}\n{result.stdout}")
    return result.stdout


def write_json(path, value):
    path.write_text(json.dumps(value, indent=2) + '\n')


def apt_environment(base, sources):
    """Empty dpkg state and no host APT configuration/preferences/hooks."""
    base.mkdir(parents=True, exist_ok=True)
    for name in ['lists/partial', 'archives/partial', 'conf.d', 'sourceparts',
                 'preferences.d', 'trusted.d', 'log']:
        (base / name).mkdir(parents=True, exist_ok=True)
    for name in ['status', 'extended_states', 'preferences', 'empty.conf']:
        (base / name).write_text('')
    (base / 'sources.list').write_text(sources)
    settings = {
        'Dir::Etc::main': str(base / 'empty.conf'),
        'Dir::Etc::parts': str(base / 'conf.d'),
        'Dir::Etc::sourcelist': str(base / 'sources.list'),
        'Dir::Etc::sourceparts': str(base / 'sourceparts'),
        'Dir::Etc::preferences': str(base / 'preferences'),
        'Dir::Etc::preferencesparts': str(base / 'preferences.d'),
        'Dir::Etc::trusted': str(base / 'unused.gpg'),
        'Dir::Etc::trustedparts': str(base / 'trusted.d'),
        'Dir::State::status': str(base / 'status'),
        'Dir::State::extended_states': str(base / 'extended_states'),
        'Dir::State::lists': str(base / 'lists'),
        'Dir::Cache::archives': str(base / 'archives'),
        'Dir::Cache::pkgcache': str(base / 'pkgcache.bin'),
        'Dir::Cache::srcpkgcache': str(base / 'srcpkgcache.bin'),
        'Dir::Log': str(base / 'log'),
        'APT::Architecture': 'amd64',
        'APT::Sandbox::User': pwd.getpwuid(os.geteuid()).pw_name,
        'APT::Install-Recommends': 'false',
        'APT::Install-Suggests': 'false',
        'Acquire::Languages': 'none',
        'APT::Get::List-Cleanup': 'false',
        'Acquire::Retries': '3',
    }
    config = '#clear APT::Architectures;\nAPT::Architectures { "amd64"; };\n'
    config += ''.join(f'{key} {json.dumps(value)};\n' for key, value in settings.items())
    (base / 'apt.conf').write_text(config)
    env = dict(os.environ, APT_CONFIG=str(base / 'apt.conf'), LC_ALL='C')
    return env


def package_identity(path):
    fields = run(['dpkg-deb', '-f', path, 'Package', 'Version', 'Architecture'])
    result = dict(line.split(': ', 1) for line in fields.splitlines())
    if result['Architecture'] not in ('amd64', 'all'):
        raise ValueError(f'Wrong architecture: {path}')
    return result['Package'], result['Version'], result['Architecture']


def verify(directory):
    record = json.loads((directory / 'capture.json').read_text())
    for relative, expected in record['files'].items():
        path = directory / relative
        if not path.resolve().is_relative_to(directory.resolve()):
            raise ValueError('Manifest path outside capture')
        if not path.is_file() or path.is_symlink() or sha(path) != expected:
            raise ValueError(f'Missing or changed captured file: {relative}')
    print(f"Verified {len(record['packages'])} packages and captured repository metadata.")


def acquire(args):
    if os.geteuid() == 0:
        raise ValueError('Run as your normal ai-stores owner, without sudo.')
    for tool in ['apt-get', 'apt-cache', 'dpkg-deb', 'dpkg-scanpackages',
                 'apt-ftparchive', 'gpg']:
        if not shutil.which(tool):
            raise ValueError(f'Required acquisition tool missing: {tool}')
    if not re.fullmatch(r'\d{8}T\d{6}Z', args.snapshot):
        raise ValueError('Snapshot must be YYYYMMDDTHHMMSSZ')
    datetime.datetime.strptime(args.snapshot, '%Y%m%dT%H%M%SZ')
    store = args.stores_root.expanduser().resolve()
    if not (store / 'modules').is_dir() or not (store / 'vault').is_dir():
        raise ValueError('Expected an existing ai-stores repository')
    if not args.baseline_status or not args.baseline_holds:
        raise ValueError('Acquisition requires --baseline-status and --baseline-holds')
    baseline, held = baseline_status(args.baseline_status.expanduser().read_text(),
                                     args.baseline_holds.expanduser().read_text())
    previous = args.reuse_capture.expanduser().resolve() if args.reuse_capture else None
    previous_record = None
    if previous:
        if not previous.is_relative_to(store / 'vault/graystone/llama.cpp/dependencies/cuda12.8-sm120'):
            raise ValueError('Reuse capture must be inside the sm120 dependency store')
        previous_record = json.loads((previous / 'capture.json').read_text())
    stamp = datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S.%fZ')
    out = store / 'vault/graystone/llama.cpp/dependencies/cuda12.8-sm120' / stamp
    # Each acquisition is immutable and separate, including failed attempts.
    out.mkdir(parents=True)
    print(f'Acquisition directory: {out}', flush=True)
    print('Resolving against empty amd64 state and the recorded target baseline.', flush=True)
    (out / 'baseline.dpkg-status').write_text(baseline)
    (out / 'baseline.holds').write_text('\n'.join(sorted(held)) + '\n')
    keys = out / 'keys'
    keys.mkdir()
    ubuntu_key = Path('/usr/share/keyrings/ubuntu-archive-keyring.gpg')
    if not ubuntu_key.is_file():
        raise ValueError(f'Missing Ubuntu signing keyring: {ubuntu_key}')
    shutil.copy2(ubuntu_key, keys / ubuntu_key.name)
    # Bootstrap trust from NVIDIA's HTTPS repository, then verify APT signatures.
    with urllib.request.urlopen(NVIDIA + '3bf863cc.pub', timeout=60) as response:
        (keys / 'nvidia.asc').write_bytes(response.read())
    run(['gpg', '--batch', '--yes', '--dearmor', '--output', keys / 'nvidia.gpg', keys / 'nvidia.asc'])
    (keys / 'nvidia-fingerprints.txt').write_text(run([
        'gpg', '--batch', '--show-keys', '--with-colons', keys / 'nvidia.gpg']))
    snapshot_url = f'https://snapshot.ubuntu.com/ubuntu/{args.snapshot}/'
    sources = ''.join(
        f'deb [arch=amd64 check-valid-until=no signed-by={keys / ubuntu_key.name}] '
        f'{snapshot_url} {suite} main restricted universe multiverse\n'
        for suite in ['noble', 'noble-updates', 'noble-security'])
    sources += f'deb [arch=amd64 signed-by={keys / "nvidia.gpg"}] {NVIDIA} /\n'
    env = apt_environment(out / 'upstream', sources)
    (out / 'roots.txt').write_text('\n'.join(ROOTS) + '\n')
    (out / 'update.log').write_text(run(['apt-get', '-o', 'APT::Update::Error-Mode=any', 'update'], env=env))
    install = ['apt-get', '--no-install-recommends', '--no-remove']
    target_env = apt_environment(out / 'baseline-upstream', sources)
    (out / 'baseline-upstream/status').write_text(baseline)
    # Use the same authenticated indexes for both simulations, without refreshing them.
    for path in (out / 'upstream/lists').iterdir():
        if path.is_file() and path.name != 'lock':
            shutil.copy2(path, out / 'baseline-upstream/lists' / path.name)

    def simulate(kind, requested, turn):
        command = install + ['-o', 'Debug::pkgProblemResolver=yes', '--simulate', 'install'] + requested
        result = subprocess.run(command, env=env if kind == 'empty' else target_env,
                                text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        (out / f'resolve-{turn}-{kind}.log').write_text(result.stdout)
        if result.returncode:
            raise ValueError(f'{kind} dependency resolution failed; see {out / f"resolve-{turn}-{kind}.log"}\n' + result.stdout[-12000:])
        return result.stdout

    roots = ROOTS
    if previous_record:
        roots = [f"{p['package']}={p['version']}" for p in previous_record['packages']]
    solution = converge(simulate, roots, held)
    selected = sorted(solution)
    pins = [f'{p}={solution[p]}' for p in selected]
    if not solution:
        raise ValueError('APT returned an empty dependency solution')
    print(f'Both upstream simulations passed: {len(solution)} pinned packages.', flush=True)
    if previous_record:
        reused = 0
        for package in previous_record['packages']:
            if solution.get(package['package']) != package['version']:
                continue
            source = previous / package['file']
            if not source.resolve().is_relative_to(previous) or source.is_symlink() or sha(source) != package['sha256']:
                raise ValueError('Missing or changed reusable package: ' + str(source))
            shutil.copy2(source, out / 'upstream/archives' / source.name)
            reused += 1
        print(f'Reused {reused} verified packages; downloading remaining dependencies.', flush=True)
    (out / 'download-uris.txt').write_text(run(
        install + ['--print-uris', '--yes', 'install'] + pins, env=env))
    print(f'Downloading dependency solution ({len(selected)} packages); this may take several minutes.', flush=True)
    # apt validates downloaded content against the authenticated upstream indexes.
    (out / 'download.log').write_text(run(
        install + ['--download-only', '--yes', 'install'] + pins, env=env))
    repo = out / 'apt'
    pool = repo / 'pool/main'
    pool.mkdir(parents=True)
    packages = []
    for deb in sorted((out / 'upstream/archives').glob('*.deb')):
        name, version, arch = package_identity(deb)
        # Verify SHA256 explicitly against the signed-index-derived APT record too.
        metadata = run(['apt-cache', 'show', f'{name}={version}'], env=env)
        paragraphs = metadata.strip().split('\n\n')
        digests = set()
        for paragraph in paragraphs:
            if f'Architecture: {arch}' in paragraph.splitlines():
                digests.update(re.findall(r'^SHA256: ([0-9a-f]{64})$', paragraph, re.M))
        digest = sha(deb)
        if digests != {digest}:
            raise ValueError(f'Package SHA256 differs from upstream metadata: {deb.name}')
        destination = pool / deb.name
        # Move rather than duplicate several GB of toolkit packages.
        deb.rename(destination)
        packages.append({'package': name, 'version': version, 'architecture': arch,
                         'file': str(destination.relative_to(out)), 'sha256': digest})
    if len(packages) != len(selected):
        raise ValueError(f'Expected {len(selected)} packages, downloaded {len(packages)}')
    manifest = ''.join(f"{p['package']}\t{p['version']}\n" for p in sorted(packages, key=lambda p:p['package']))
    (out / 'amd64-closure.tsv').write_text('# Package\tVersion\n' + manifest)
    dist = repo / 'dists/noble/main/binary-amd64'
    dist.mkdir(parents=True)
    # Keep diagnostics out of the Packages file (dpkg-scanpackages uses stderr).
    proc = subprocess.run(['dpkg-scanpackages', '--multiversion', 'pool/main', '/dev/null'],
                          cwd=repo, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
    (out / 'index.log').write_text(proc.stderr)
    (dist / 'Packages').write_text(proc.stdout)
    (dist / 'Packages.gz').write_bytes(gzip.compress(proc.stdout.encode(), mtime=0))
    release = run(['apt-ftparchive', '-o', 'APT::FTPArchive::Release::Origin=Graystone AI Stores',
                   '-o', 'APT::FTPArchive::Release::Suite=noble',
                   '-o', 'APT::FTPArchive::Release::Codename=noble',
                   '-o', 'APT::FTPArchive::Release::Architectures=amd64',
                   '-o', 'APT::FTPArchive::Release::Components=main',
                   'release', 'dists/noble'], cwd=repo)
    (repo / 'dists/noble/Release').write_text(release)
    # Independent empty-state solver, with only the newly captured local repository.
    local_env = apt_environment(out / 'offline-check', f'deb [arch=amd64 trusted=yes] {repo.as_uri()} noble main\n')
    run(['apt-get', '-o', 'APT::Update::Error-Mode=any', 'update'], env=local_env)
    pins = [f"{p['package']}={p['version']}" for p in packages]
    (out / 'offline-solve.log').write_text(run(install + ['--simulate', 'install'] + pins, env=local_env))
    baseline_local_env = apt_environment(out / 'offline-baseline-check', f'deb [arch=amd64 trusted=yes] {repo.as_uri()} noble main\n')
    (out / 'offline-baseline-check/status').write_text(baseline)
    run(['apt-get', '-o', 'APT::Update::Error-Mode=any', 'update'], env=baseline_local_env)
    baseline_plan = run(install + ['--simulate', 'install'] + pins, env=baseline_local_env)
    protect_plan(plan_packages(baseline_plan), held)
    (out / 'offline-baseline-solve.log').write_text(baseline_plan)
    shutil.copy2(Path(__file__), out / 'acquire-sm120-dependencies.py')
    record = {
        'schema_version': 2, 'captured_at': stamp, 'ubuntu_snapshot': args.snapshot,
        'baseline_status_sha256': sha(out / 'baseline.dpkg-status'),
        'baseline_holds': sorted(held),
        'reused_capture': str(previous.relative_to(store)) if previous else None,
        'nvidia_repository': NVIDIA, 'roots': ROOTS, 'packages': packages,
        'validation': {'upstream_signatures': 'APT verified', 'package_sha256': 'passed',
                       'local_repository_dependency_solve': 'passed',
                       'local_repository_baseline_solve': 'passed',
                       'protected_packages_unchanged': 'passed',
                       'target_install_build_capture_and_inference': 'pending'},
        'notes': ['Build dependencies validated from empty state and the recorded baseline; not a minimal runtime closure.',
                  'NVIDIA trust key bootstrapped from its official HTTPS repository.',
                  'NVIDIA dependencies are locked to the resolved versions in amd64-closure.tsv.',
                  'Existing driver, sm86 repository and Forge profiles have not been modified.'],
        'files': {},
    }
    for path in sorted(out.rglob('*')):
        if path.is_file() and not path.is_symlink() and path.name not in ('lock', 'pkgcache.bin', 'srcpkgcache.bin'):
            record['files'][str(path.relative_to(out))] = sha(path)
    write_json(out / 'capture.json', record)
    verify(out)
    if args.result_file:
        result_path = args.result_file.expanduser().absolute()
        if result_path.is_symlink():
            raise ValueError('Refusing result-file symlink')
        result_path.parent.mkdir(parents=True, exist_ok=True)
        fd, temporary = tempfile.mkstemp(dir=result_path.parent, prefix='.acquisition-result-')
        try:
            with os.fdopen(fd, 'w') as stream:
                json.dump({'capture': str(out), 'baseline_compatible': True}, stream)
                stream.write('\n')
                stream.flush()
                os.fsync(stream.fileno())
            os.chmod(temporary, 0o644)
            os.replace(temporary, result_path)
        finally:
            if os.path.exists(temporary):
                os.unlink(temporary)
    print(f'CAPTURE={out}')
    print(f'MANIFEST={out / "amd64-closure.tsv"}')
    print(f'REPOSITORY={repo}')
    print('BASELINE_COMPATIBILITY=PASS (simulation; full clean regression remains pending)')
    print('Acquisition and local dependency resolution complete. Target build/capture remain pending.')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--stores-root', type=Path)
    parser.add_argument('--snapshot', default='20260907T000000Z')
    parser.add_argument('--baseline-status', type=Path)
    parser.add_argument('--baseline-holds', type=Path)
    parser.add_argument('--reuse-capture', type=Path, help='Retain prior exact versions and reuse verified DEBs')
    parser.add_argument('--result-file', type=Path, help='Write the successful capture path as JSON for the next scripted stage')
    parser.add_argument('--verify', type=Path, help='Verify a completed capture without network access')
    args = parser.parse_args()
    if args.verify:
        verify(args.verify.expanduser().resolve())
    elif args.stores_root:
        acquire(args)
    else:
        parser.error('provide --stores-root or --verify')


if __name__ == '__main__':
    try:
        main()
    except (OSError, ValueError, RuntimeError, subprocess.CalledProcessError) as error:
        sys.exit(f'ERROR: {error}')
