import json,pathlib,re
root=pathlib.Path(__file__).resolve().parents[1]
skill=(root/'SKILL.md').read_text(encoding='utf-8')
assert skill.startswith('---\n')
deps=json.loads((root/'references/dependencies.json').read_text(encoding='utf-8'))
queries=json.loads((root/'queries/queries.json').read_text(encoding='utf-8'))
triggers=json.loads((root/'tests/trigger-cases.json').read_text(encoding='utf-8'))
assert deps['object_types'] and deps['read_only'] is True
assert len(triggers['should_trigger'])>=3 and len(triggers['should_not_trigger'])>=2
for q in queries:
 assert q['cypher'].startswith('MATCH ') and set(re.findall(r'\$([A-Za-z_][A-Za-z0-9_]*)',q['cypher']))==set(q['parameters'])
 assert not re.search(r'\b(CREATE|MERGE|DELETE|SET|REMOVE|DROP|ALTER)\b',q['cypher'],re.I)
for path in ['references/workflows.md','references/dependencies.json','queries/queries.json']:
 assert path in skill and (root/path).is_file()
assert not re.search(r'https?://|(?:\d{1,3}\.){3}\d{1,3}',skill)
print(json.dumps({'status':'ok','objects':len(deps['object_types']),'queries':len(queries),'trigger_cases':sum(map(len,triggers.values()))},ensure_ascii=False))
