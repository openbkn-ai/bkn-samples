"""Verify the independently fetched target-registry multi-platform manifest."""
import json
import re
import sys


def verify_manifest(value):
    if value.get('schemaVersion') != 2 or value.get('mediaType') not in {
        'application/vnd.docker.distribution.manifest.list.v2+json',
        'application/vnd.oci.image.index.v1+json',
    }:
        raise ValueError('target registry must provide a multi-platform manifest')
    platforms = set()
    for item in value.get('manifests', []):
        platform = item.get('platform', {})
        if platform.get('os') != 'linux':
            continue
        if not re.fullmatch(r'sha256:[0-9a-f]{64}', item.get('digest', '')):
            raise ValueError('invalid child manifest digest')
        platforms.add(platform.get('architecture'))
    if not {'amd64', 'arm64'}.issubset(platforms):
        raise ValueError('target registry is missing required linux/amd64 or linux/arm64')


if __name__ == '__main__':
    with open(sys.argv[1]) as stream:
        verify_manifest(json.load(stream))
