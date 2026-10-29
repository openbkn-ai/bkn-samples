"""Build a URL-only offline.v1 supply package for the original official 0.2.0 service.

This deliberately does not change the maintenance branch's default offline.v2 builder.
The data image must already be available in the destination cluster.
"""
import argparse
import hashlib
import json
from pathlib import Path
import platform
import subprocess

import yaml

ROOT = Path(__file__).resolve().parents[2]
LEGACY_COMMIT = '3a0b4ab5a09a42cd43953a38466e762aadfcc0ab'
LEGACY_PATH = 'tools/publication/build_candidate.py'
LEGACY_SHA256 = '9f86e6dcf861470cc91ccf050da168c5569d9c33d5817842c8b7df221141a818'
PLATFORM_CONSTRAINT = '>=0.2.0 <0.2.1'


def read_legacy_source(root):
    return subprocess.check_output(['git', '-C', str(root), 'show', f'{LEGACY_COMMIT}:{LEGACY_PATH}'])


def compatible_source(source):
    if hashlib.sha256(source).hexdigest() != LEGACY_SHA256:
        raise ValueError('legacy builder digest mismatch')
    original = b'"platformVersion": ">=0.2.0 <0.3.0"'
    narrowed = b'"platformVersion": ">=0.2.0 <0.2.1"'
    if source.count(original) != 1:
        raise ValueError('expected exactly one legacy platform constraint')
    return source.replace(original, narrowed)


def load_legacy(root):
    source = compatible_source(read_legacy_source(root))
    namespace = {'__name__': '_reviewed_020_builder', '__file__': str(root / LEGACY_PATH)}
    exec(compile(source, f'{LEGACY_COMMIT}:{LEGACY_PATH}', 'exec'), namespace)
    namespace['ROOT'] = root
    return namespace


def build(sample_dir, version, output, data_image_ref, allow_dirty=False):
    sample_dir = sample_dir.absolute()
    if sample_dir != ROOT / 'samples/supply_ontology_hand':
        raise ValueError('original020 compatibility entry supports Chinese supply sample only')
    untracked = subprocess.check_output(['git', '-C', str(ROOT), 'ls-files', '--others', '--exclude-standard', '--', str(sample_dir)])
    if untracked.strip():
        raise ValueError('stage all new sample files before building; the Git index is the archive allowlist')
    dirty = bool(subprocess.check_output(['git', '-C', str(ROOT), 'status', '--porcelain']).strip())
    if dirty and not allow_dirty:
        raise ValueError('final builds require a clean source commit; --allow-dirty is preliminary only')
    legacy = load_legacy(ROOT)
    target = legacy['build'](sample_dir, version, output, data_image_ref)
    report_path = target / 'build.json'
    report = json.loads(report_path.read_text())
    report['source']['workingTreeChanges'] = dirty
    report['platformConstraint'] = PLATFORM_CONSTRAINT
    report['compatibilityBuilder'] = {
        'protocol': 'samples.openbkn.ai/offline.v1',
        'delivery': 'URL-only; fixed data image must be preavailable',
        'legacyCommit': LEGACY_COMMIT, 'legacyPath': LEGACY_PATH,
        'legacySha256': LEGACY_SHA256,
        'transformedSha256': hashlib.sha256(compatible_source(read_legacy_source(ROOT))).hexdigest(),
        'transformation': 'narrow platformVersion from >=0.2.0 <0.3.0 to >=0.2.0 <0.2.1 only',
        'entryPoint': str(Path(__file__).relative_to(ROOT)),
        'entryPointSha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        'python': platform.python_version(), 'pyyaml': yaml.__version__,
        'preliminary': dirty,
    }
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
    return target


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('sample_dir', type=Path)
    parser.add_argument('--version', required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--data-image-ref', required=True)
    parser.add_argument('--allow-dirty', action='store_true')
    args = parser.parse_args()
    try:
        result = build(args.sample_dir, args.version, args.output, args.data_image_ref, args.allow_dirty)
    except (ValueError, OSError, subprocess.CalledProcessError) as error:
        parser.exit(1, f'Original020 candidate build failed: {error}\n')
    print(f'Original020 offline.v1 candidate: {result}')
    print('Not verified or published; incompatible with the newer offline.v2/shared install contract.')


if __name__ == '__main__':
    main()
