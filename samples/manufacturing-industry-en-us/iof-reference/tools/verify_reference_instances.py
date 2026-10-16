#!/usr/bin/env python3
"""Verify the complete IOF reference-instance coverage and direct links."""
import csv
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def rows(object_id):
    with (ROOT / 'data' / f'{object_id}.csv').open(encoding='utf-8', newline='') as handle:
        return list(csv.DictReader(handle))


objects = list((ROOT / 'kn' / 'object_types').glob('*.bkn'))
assert len(objects) == 112
assert len(list((ROOT / 'data').glob('*.csv'))) == 112
for object_type in objects:
    document = object_type.read_text()
    object_id = re.search(r'^id: ([a-z0-9_]+)$', document, re.M).group(1)
    expected_iri = re.search(r'Source IRI: `([^`]+)`', document).group(1)
    expected_label = re.search(r'Source label: (.+?)\. Source IRI:', document).group(1)
    expected_definition = re.search(r'Source definition: (.+?)\n\n', document, re.S).group(1)
    for row in rows(object_id):
        assert row['source_iri'] == expected_iri and row['source_iri']
        assert row['source_label'] == expected_label
        assert row['source_definition'] == expected_definition
        assert row['is_synthetic_reference_instance'] == 'true'
for relation in (ROOT / 'kn' / 'relation_types').glob('*.bkn'):
    document = relation.read_text()
    source, target = re.search(r'\| ([a-z0-9_]+) \| ([a-z0-9_]+) \| direct \|', document).groups()
    mapping = document.split('### Mapping Rules', 1)[1]
    source_field, target_field = re.search(r'\| ([a-z0-9_]+) \| ([a-z0-9_]+) \|\s*$', mapping, re.M).groups()
    target_ids = {row[target_field] for row in rows(target)}
    values = [row[source_field] for row in rows(source) if row[source_field]]
    assert values and all(value in target_ids for value in values)
print('Validated 112 IOF reference-instance tables, source provenance, and 7 direct IOF relation links.')
