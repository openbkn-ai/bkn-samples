#!/usr/bin/env python3
"""Grade independently produced answer rows against the frozen reference."""
from __future__ import annotations
import argparse
import json
import math
from pathlib import Path
import yaml

EVAL = Path(__file__).resolve().parents[1]


def same_value(expected, actual, tolerance):
    if isinstance(expected, (int, float)) and not isinstance(expected, bool):
        try:
            value = float(actual)
        except (TypeError, ValueError):
            return False
        if not math.isfinite(value):
            return False
        return value == expected if isinstance(expected, int) else abs(value - expected) <= tolerance
    return expected == actual


def row_differences(expected, actual, tolerance):
    if not isinstance(actual, list):
        return [{'reason': 'rows must be an array'}]
    differences = []
    if len(expected) != len(actual):
        differences.append({'reason': 'row count differs', 'expected': len(expected), 'actual': len(actual)})
    for index, (left, right) in enumerate(zip(expected, actual)):
        if not isinstance(right, dict):
            differences.append({'row': index, 'reason': 'row must be an object'})
            continue
        for field, value in left.items():
            if field not in right or not same_value(value, right[field], tolerance):
                differences.append({'row': index, 'field': field, 'expected': value, 'actual': right.get(field), 'reason': 'missing field' if field not in right else 'value differs'})
    return differences


def grade(answers):
    questions = yaml.safe_load((EVAL / 'datasets/question-set-v1.yaml').read_text())
    reference = yaml.safe_load((EVAL / 'gold/answer-set-v1.yaml').read_text())
    expected = {case['id']: case['rows'] for case in reference['answers']}
    if not isinstance(answers, list):
        raise ValueError('Answers must be an array of {id, rows} objects')
    actual = {}
    for answer in answers:
        if not isinstance(answer, dict) or answer.get('id') not in expected:
            raise ValueError('Answer contains an unknown or invalid question ID')
        if answer['id'] in actual:
            raise ValueError('Duplicate question ID: ' + answer['id'])
        actual[answer['id']] = answer.get('rows')
    cases = []
    for question in questions['questions']:
        case_id = question['id']
        differences = ([{'reason': 'question not answered'}] if case_id not in actual else
                       row_differences(expected[case_id], actual[case_id], questions['scoring']['numeric_tolerance']))
        cases.append({'id': case_id, 'passed': not differences, 'differences': differences})
    correct = sum(case['passed'] for case in cases)
    return {'baseline_id': reference['baseline_id'], 'correct': correct, 'total': len(cases), 'accuracy': correct / len(cases),
            'categories': {category['id']: {'correct': sum(case['passed'] for case in cases if case['id'].startswith(category['id'] + '-')), 'total': category['question_count']} for category in questions['categories']}, 'cases': cases}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('answers', type=Path)
    args = parser.parse_args()
    report = grade(json.loads(args.answers.read_text()))
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report['correct'] == report['total'] else 1

if __name__ == '__main__':
    raise SystemExit(main())
