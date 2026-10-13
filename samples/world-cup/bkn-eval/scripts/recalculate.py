#!/usr/bin/env python3
"""Recalculate deterministic reference results directly from locked CSV files."""
from __future__ import annotations
import argparse
import csv
import hashlib
import json
import re
import sqlite3
from pathlib import Path
import yaml

SAMPLE = Path(__file__).resolve().parents[2]
EVAL = SAMPLE / 'bkn-eval'
ANSWER = EVAL / 'gold' / 'answer-set-v1.yaml'


def calculate() -> dict:
    lock = yaml.safe_load((SAMPLE / 'dataset.lock').read_text())
    connection = sqlite3.connect(':memory:')
    connection.row_factory = sqlite3.Row
    connection.create_function('CONCAT', -1, lambda *parts: None if None in parts else ''.join(map(str, parts)))
    row_counts = {}
    unmodeled_fields = {}
    known_missing = {
        'matches': {'tournament_name', 'stage_name', 'group_name', 'home_team_name', 'away_team_name', 'stadium_name', 'city_name', 'country_name', 'result', 'match_name'},
        'team_appearances': {'tournament_name', 'stage_name', 'group_name', 'team_name', 'opponent_name', 'stadium_name', 'city_name', 'country_name', 'result', 'match_name'},
    }
    for entry in lock['files']:
        path = SAMPLE / 'data' / entry['path']
        if hashlib.sha256(path.read_bytes()).hexdigest() != entry['sha256']:
            raise ValueError(f'Locked CSV checksum mismatch: {entry["path"]}')
        with path.open(newline='', encoding='utf-8-sig') as stream:
            reader = csv.DictReader(stream)
            headers = reader.fieldnames
            rows = list(reader)
        schema = (SAMPLE / 'kn' / 'object_types' / f'{path.stem}.bkn').read_text()
        types = dict(re.findall(r'^\| (\w+) \| [^|]+ \| (string|integer|float|double|number|boolean) \|', schema, re.M))
        missing = set(headers) - set(types)
        if set(types) - set(headers) or missing - known_missing.get(path.stem, set()):
            raise ValueError(f'Unexpected CSV/model field mismatch: {path.stem}')
        if missing:
            unmodeled_fields[path.stem] = sorted(missing)
        # Reference SQL runs only against local frozen CSVs. Missing display
        # columns are strings; agents must obtain equivalent labels via declared objects.
        for field in missing:
            types[field] = 'string'
        numeric = {key for key, kind in types.items() if kind in {'integer', 'float', 'double', 'number'}}
        columns = ','.join(f'"{key}" {"NUMERIC" if key in numeric else "TEXT"}' for key in headers)
        connection.execute(f'CREATE TABLE "{path.stem}" ({columns})')
        # Preserve source strings and missing-value markers; SQLite numeric affinity
        # converts numeric strings only. This oracle never imports runtime functions.
        connection.executemany(f'INSERT INTO "{path.stem}" VALUES ({",".join("?" for _ in headers)})', [[row[key] for key in headers] for row in rows])
        row_counts[path.stem] = len(rows)
    cases_path = EVAL / 'gold' / 'cases.json'
    cases = json.loads(cases_path.read_text())
    questions_path = EVAL / 'datasets' / 'question-set-v1.yaml'
    questions = {item['id']: item for item in yaml.safe_load(questions_path.read_text())['questions']}
    if set(questions) != {case['id'] for case in cases}:
        raise ValueError('Question and reference IDs differ')
    answers = []
    for case in cases:
        question = questions[case['id']]
        for key in ('question', 'output_fields', 'row_order'):
            if case[key] != question[key]:
                raise ValueError(f'{case["id"]}: question/reference contract mismatch: {key}')
        if set(case['tables']) != set(question['required_objects']):
            raise ValueError(f'{case["id"]}: required objects differ')
        try:
            rows = [dict(row) for row in connection.execute(case['sql'])]
        except sqlite3.Error as error:
            raise ValueError(f'{case["id"]}: {error}') from error
        if not rows:
            raise ValueError(f'{case["id"]}: unexpectedly empty reference result')
        if list(rows[0]) != question['output_fields']:
            raise ValueError(f'{case["id"]}: reference columns differ from the question')
        answers.append({'id': case['id'], 'rows': rows})
    connection.close()
    return {'schema_version': '1.0', 'baseline_id': 'worldcup-cn-fjelstul-v1',
            'source_commit': lock['source']['commit'],
            'dataset_lock_sha256': hashlib.sha256((SAMPLE / 'dataset.lock').read_bytes()).hexdigest(),
            'question_set_sha256': hashlib.sha256(questions_path.read_bytes()).hexdigest(),
            'case_specification_sha256': hashlib.sha256(cases_path.read_bytes()).hexdigest(),
            'row_counts': row_counts, 'unmodeled_csv_fields': unmodeled_fields, 'answers': answers}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true', help='Compare recalculated answers with the committed reference.')
    args = parser.parse_args()
    result = calculate()
    if args.check:
        if not ANSWER.exists() or yaml.safe_load(ANSWER.read_text()) != result:
            raise SystemExit('Reference answers differ; review and recalculate the baseline.')
        print(f'Validated {len(result["answers"])} reference answers against {sum(result["row_counts"].values())} locked CSV rows.')
    else:
        ANSWER.write_text(yaml.safe_dump(result, allow_unicode=True, sort_keys=False))
        print(f'Wrote {len(result["answers"])} reference answers.')

if __name__ == '__main__':
    main()
