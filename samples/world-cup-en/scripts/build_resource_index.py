#!/usr/bin/env python3
"""Configure an entity resource index using the current resource API, then build it."""
import argparse
import json
import subprocess


def cli(*args):
    result = subprocess.run(['openbkn', '--json', *args], capture_output=True, text=True)
    if result.returncode:
        raise RuntimeError(result.stderr.strip() or 'Resource index command failed')
    return json.loads(result.stdout)


def index_patch(resource, fulltext_fields, embedding_fields=(), model_id=None, model_name=None):
    schema = resource['schema_definition']
    found = {field['name'] for field in schema}
    if not {'key_id', *fulltext_fields, *embedding_fields}.issubset(found):
        raise ValueError('Index fields are absent from the resource schema')
    for field in schema:
        name = field['name']
        features = field.setdefault('features', [])
        if name in fulltext_fields:
            features[:] = [feature for feature in features if feature.get('feature_type') != 'fulltext']
            features.append({'name': 'fulltext', 'feature_type': 'fulltext', 'ref_property': name, 'config': {'analyzer': 'standard'}})
        if model_id is not None and name in embedding_fields:
            features[:] = [feature for feature in features if feature.get('feature_type') != 'vector']
            features.append({'name': 'vector', 'feature_type': 'vector', 'ref_property': name, 'config': {'embedding_model': str(model_id)}})
    config = dict(resource.get('index_config') or {})
    config.update(primary_key_fields=['key_id'], default_fulltext_analyzer='standard')
    if model_name:
        config['default_embedding_model'] = model_name
    return schema, config


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('resource_id')
    parser.add_argument('--fulltext-fields', required=True)
    parser.add_argument('--embedding-fields', default='')
    parser.add_argument('--embedding-model', default='')
    args = parser.parse_args()
    model_id = None
    if args.embedding_model:
        models = cli('model', 'small', 'list')
        model = next((item for item in models.get('data', models.get('entries', []))
                      if item.get('model_name') == args.embedding_model and item.get('model_type') == 'embedding'), None)
        if not model or not model.get('model_id'):
            raise ValueError('Configured embedding model is unavailable')
        model_id = model['model_id']
    resource = cli('vega', 'resource', 'get', args.resource_id)
    if isinstance(resource, list):
        resource = resource[0]
    schema, config = index_patch(resource, args.fulltext_fields.split(','),
                                 args.embedding_fields.split(',') if args.embedding_fields else [], model_id, args.embedding_model)
    cli('vega', 'resource', 'update', args.resource_id, '--schema-definition', json.dumps(schema), '--index-config', json.dumps(config))
    result = cli('vega', 'resource', 'build', args.resource_id, '--execute-type', 'full')
    print(json.dumps(result))

if __name__ == '__main__':
    main()
