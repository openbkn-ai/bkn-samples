"""Prepare online/offline content archives and a candidate release manifest; never publish."""
import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

from tools.publication.build_candidate import build, require


def prepare(sample_dir, version, output):
    previous = list(sample_dir.glob('releases/*/sample.json'))
    require(previous, 'a reviewed release manifest is required as the publication baseline')
    baseline = max(previous, key=lambda p: tuple(map(int, p.parent.name.split('.'))))
    require(tuple(map(int, version.split('.'))) > tuple(map(int, baseline.parent.name.split('.'))),
            'use a new version; existing release artifacts are immutable')
    online = build(sample_dir, version, output / 'online')
    offline = build(sample_dir, version, output / 'offline', shared_database=True)
    manifest = json.loads(baseline.read_text())
    manifest['metadata']['version'] = version
    spec = manifest['spec']
    spec['release']['publishedAt'] = datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')
    report = json.loads((online / 'build.json').read_text())
    spec['release']['releaseNotes'] = [{**note, 'path': Path(note['path']).name} for note in report['releaseNotes']]
    if 'database.shared' not in spec['requires']['capabilities']:
        spec['requires']['capabilities'].append('database.shared')
    archive = next(a for a in spec['artifacts'] if a['type'] == 'archive')
    archive['digest'] = report['package']['digest']
    archive['locations'] = ['https://github.com/openbkn-ai/bkn-samples/releases/download/'
                            f"sample-{manifest['metadata']['sampleId']}-v{version}/package.tar.gz"]
    spec['artifacts'] = [archive]
    require(len(spec['delivery']['dataDependencies']) == 1, 'one database dependency is required')
    spec['delivery']['dataDependencies'][0]['artifactId'] = archive['id']
    (online / 'sample.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n')
    return {'sample': manifest['metadata']['sampleId'], 'version': version,
            'online': str(online / 'package.tar.gz'), 'offline': str(offline / 'offline-package.tar.gz'),
            'manifest': str(online / 'sample.json'), 'status': 'candidate-not-verified'}


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
