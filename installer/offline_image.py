"""Validate a complete OCI layout without consulting a registry.

Also shipped in the offline package as the node-side preparation tool. Uses only
Python's standard library and the administrator's existing containerd CLI.
"""

import argparse
import hashlib
import json
import re
import shlex
import subprocess
import tarfile
import tempfile
from pathlib import Path

MAX_OFFLINE_ARCHIVE = 1024 * 1024 * 1024
MAX_OFFLINE_CONTENT = 2 * MAX_OFFLINE_ARCHIVE
MAX_OFFLINE_FILE = MAX_OFFLINE_ARCHIVE


def file_sha(path):
    digest = hashlib.sha256()
    with path.open('rb') as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b''):
            digest.update(chunk)
    return 'sha256:' + digest.hexdigest()


def check(condition, message):
    if not condition:
        raise ValueError(message)


def validate_layout(layout, image_ref, architectures, *, require_named=True):
    """Require the pinned manifest and every transitive blob, including layers."""
    check(re.fullmatch(r'[a-z0-9][a-z0-9./:_-]*@sha256:[a-f0-9]{64}', image_ref),
          'offline image needs a fixed digest')
    check(layout.is_dir() and not layout.is_symlink(), 'OCI layout must be a real directory')
    for path in layout.rglob('*'):
        check(not path.is_symlink(), 'OCI symlink is forbidden')
    check(json.loads((layout / 'oci-layout').read_text()) == {'imageLayoutVersion': '1.0.0'},
          'unsupported OCI layout')
    index = json.loads((layout / 'index.json').read_text())
    roots = index.get('manifests', [])
    check(len(roots) == 1 and roots[0]['digest'] == image_ref.split('@')[1],
          'OCI root differs from the pinned data image')
    if require_named:
        check(roots[0].get('annotations', {}).get('org.opencontainers.image.ref.name') == image_ref,
              'OCI root must register the pinned image reference')
    seen, platforms = set(), set()

    def visit(descriptor, depth=0, kind='manifest'):
        check(depth <= 8 and not descriptor.get('urls'), 'external OCI blob reference is forbidden')
        digest = descriptor['digest']
        check(re.fullmatch(r'sha256:[a-f0-9]{64}', digest), 'unsupported OCI digest')
        blob = layout / 'blobs/sha256' / digest[7:]
        check(blob.is_file() and not blob.is_symlink(), 'offline image blob is missing')
        if digest in seen:
            return
        check(blob.stat().st_size == descriptor['size'] and file_sha(blob) == digest,
              'offline image blob digest or size differs')
        seen.add(digest)
        check(len(seen) <= 10000, 'too many OCI blobs')
        if kind == 'layer':
            return
        check(blob.stat().st_size <= 2 * 1024 * 1024, 'OCI metadata exceeds size limit')
        document = json.loads(blob.read_text())
        if kind == 'config':
            if document.get('os') == 'linux' and document.get('architecture') in {'arm64', 'amd64'}:
                platforms.add(document['architecture'])
            return
        if 'manifests' in document:
            for child in document['manifests']:
                visit(child, depth + 1)
        else:
            visit(document['config'], depth + 1, 'config')
            for layer in document['layers']:
                visit(layer, depth + 1, 'layer')

    visit(roots[0])
    check(set(architectures) <= platforms, 'offline image does not contain all declared architectures')
    actual = {p.name for p in (layout / 'blobs/sha256').iterdir()}
    check(actual == {d[7:] for d in seen}, 'unexpected OCI blobs')
    return platforms


def main():
    parser = argparse.ArgumentParser(description='Import the bundled sample image locally; never pulls images.')
    parser.add_argument('--ctr', default='ctr', help='Installed containerd CLI, e.g. "ctr" or "k3s ctr"')
    parser.add_argument('--address', help='Existing containerd socket path')
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    release = json.loads((root / 'offline-release.json').read_text())
    check(release['apiVersion'] == 'samples.openbkn.ai/offline.v2', 'requires a self-contained offline.v2 package')
    layout, image = root / 'runtime/oci', release['dataImageRef']
    validate_layout(layout, image, release['requires']['architectures'])
    command = shlex.split(args.ctr)
    check(command, 'containerd CLI is required')
    if args.address:
        command += ['--address', args.address]
    command += ['--namespace', 'k8s.io']
    with tempfile.TemporaryDirectory(prefix='bkn-offline-image-') as temporary:
        archive = Path(temporary) / 'image.tar'
        with tarfile.open(archive, 'w') as tar:
            for path in sorted(layout.rglob('*')):
                if path.is_file():
                    check(not path.is_symlink(), 'OCI symlink is forbidden')
                    tar.add(path, arcname=path.relative_to(layout).as_posix(), recursive=False)
        with archive.open('rb') as source:
            subprocess.run(command + ['images', 'import', '--all-platforms', '--base-name', image.split('@')[0],
                                      '--digests', '--label', 'io.cri-containerd.image=managed', '-'], stdin=source, check=True)
        # CRI must see the exact pinned identity, not merely an imported blob.
        result = subprocess.run(command + ['images', 'list', '--quiet'], check=True, capture_output=True, text=True)
        check(image in result.stdout.splitlines(), 'import did not register the pinned image reference')
    print('Offline image imported. Repeat on every schedulable node, then import the package in Studio.')


if __name__ == '__main__':
    main()
