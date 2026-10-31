"""Prepare one self-contained archive for online/offline installation and its release manifest; never publish.

The manifest is rebuilt from sample.yaml for every release (names, experience questions, content
packages, knowledge network format), so it follows what the sample ships now. Only the data-dependency
and binding identities are carried over from the latest earlier manifest, keeping bindings whose object
types still exist. The release tag stays sample-<id>-v<version>, which deployed installers require for
the download URL; the release title carries the product version, for example
"[OpenBKN 0.2.1] 世界杯 0.1.7", so a release list shows which product each package targets.
"""
import argparse
import json
import re
import tarfile
from datetime import datetime, timezone
from pathlib import Path

import yaml

from tools.publication.build_candidate import build, require

ROOT = Path(__file__).resolve().parents[2]


def product_version():
    return (ROOT / 'VERSION').read_text(encoding='utf-8').strip()


def release_tag(sample_id, version):
    return f"sample-{sample_id}-v{version}"


def release_title(display_name, version, product=None):
    return f"[OpenBKN {product or product_version()}] {display_name} {version}"


def _network(sample_dir):
    """Knowledge network format, entrypoint and object type IDs, as the installer reads them."""
    kn = sample_dir / 'kn'
    if (kn / 'network.bkn').is_file():
        ids = {m.group(1) for path in (kn / 'object_types').glob('*.bkn')
               if (m := re.search(r'^id:\s*(\S+)\s*$', path.read_text(encoding='utf-8'), re.M))}
        return 'bkn-directory', 'network.bkn', ids
    files = sorted(kn.glob('*.json'))
    require(len(files) == 1, 'a kn-json sample needs exactly one model file under kn/')
    model = json.loads(files[0].read_text(encoding='utf-8'))
    return 'kn-json', files[0].name, {o.get('id') for o in model.get('object_types', [])}


def _version_key(value):
    return tuple(map(int, value.split('.')))


def prepare(sample_dir, version, output):
    document = yaml.safe_load((sample_dir / 'sample.yaml').read_text(encoding='utf-8'))
    meta, spec = document['metadata'], document['spec']
    sample_id = meta['name']
    previous = sorted(sample_dir.glob('releases/*/sample.json'), key=lambda p: _version_key(p.parent.name))
    baseline = json.loads(previous[-1].read_text()) if previous else None
    if previous:
        require(_version_key(version) > _version_key(previous[-1].parent.name),
                'use a new version; existing release artifacts are immutable')
    candidate = build(sample_dir, version, output, shared_database=True)
    report = json.loads((candidate / 'build.json').read_text())
    with tarfile.open(candidate / 'package.tar.gz') as archive:
        descriptor = json.load(archive.extractfile('offline-release.json'))

    old = baseline['spec'] if baseline else {}
    old_network = next(iter(old.get('contents', {}).get('knowledgeNetworks', [])), {})
    network_id = old_network.get('contentId', f'{sample_id}-network')
    old_dependency = next(iter(old.get('delivery', {}).get('dataDependencies', [])), {})
    dependency_id = old_dependency.get('id', f'{sample_id}-data')
    components = spec.get('components', {})
    database = spec['database']
    tag = release_tag(sample_id, version)
    kn_format, entrypoint, object_ids = _network(sample_dir)
    archive = {'id': 'package', 'type': 'archive', 'digest': report['package']['digest'], 'sizeBytes': report['package']['size'],
               'locations': [f'https://github.com/openbkn-ai/bkn-samples/releases/download/{tag}/package.tar.gz']}
    contents = {
        'knowledgeNetworks': [{'artifactId': 'package', 'directory': 'kn', 'format': kn_format, 'entrypoint': entrypoint, 'contentId': network_id}],
        'functionPackages': [{'artifactId': 'package', 'directory': 'tools', 'contentId': f'{sample_id}-functions'}] if components.get('functions') else [],
        'skillPackages': [{'artifactId': 'package', 'directory': 'skills', 'contentId': f'{sample_id}-skills'}] if components.get('skills') else [],
    }
    manifest = {
        'apiVersion': 'samples.openbkn.ai/v1beta1',
        'kind': 'Sample',
        'metadata': {'sampleId': sample_id, 'version': version, 'displayName': meta['displayName'], 'summary': meta['summary'],
                     'authors': (baseline or {}).get('metadata', {}).get('authors', ['OpenBKN']), 'licenseNote': spec['studio']['licenseNote']},
        'spec': {
            'release': {'publishedAt': datetime.now(timezone.utc).isoformat(timespec='seconds').replace('+00:00', 'Z'),
                        'defaultLocale': meta['language'],
                        'releaseNotes': [{**note, 'path': Path(note['path']).name} for note in report['releaseNotes']]},
            'requires': descriptor['requires'],
            'artifacts': [archive],
            'experience': [{'type': 'openbkn.ai/knowledge-network-detail.v1', 'contentId': network_id, 'questions': spec['studio']['questions']}],
            'extensions': {},
            'contents': contents,
            'delivery': {'profile': 'openbkn.ai/sample-install.v1',
                         'dataDependencies': [{'id': dependency_id, 'artifactId': 'package', 'engine': database['engine'],
                                               'databaseName': database['name'], 'expectedTables': database['expectedTables']}],
                         'bindings': [b for b in old.get('delivery', {}).get('bindings', []) if b.get('contentId') == network_id
                                      and b.get('dataDependencyId') == dependency_id and b.get('objectTypeId') in object_ids]},
        },
    }
    (candidate / 'sample.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n')
    return {'sample': sample_id, 'version': version, 'tag': tag, 'title': release_title(meta['displayName'], version),
            'package': str(candidate / 'package.tar.gz'),
            'manifest': str(candidate / 'sample.json'), 'status': 'candidate-not-verified'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('sample_dir', type=Path)
    parser.add_argument('--version', required=True)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    try:
        print(json.dumps(prepare(args.sample_dir.resolve(), args.version, args.output.resolve()), ensure_ascii=False))
    except (ValueError, OSError, KeyError) as error:
        parser.exit(1, f'Release preparation failed: {error}\n')


if __name__ == '__main__':
    main()
