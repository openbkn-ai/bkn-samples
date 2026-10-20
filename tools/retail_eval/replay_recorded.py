"""Offline audit of saved answers; never calls a model or platform."""
import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def module(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    loaded = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(loaded)
    return loaded


def main():
    for phase in ('first-pass', 'targeted'):
        for lang in ('en-us', 'zh-cn'):
            sample = ROOT / 'samples' / ('retail-gs1-' + lang)
            bank = sample / 'bkn-eval' / 'original' if phase == 'first-pass' else sample / 'bkn-eval'
            grader = module(bank / 'grade.py' if phase == 'first-pass' else Path(__file__).with_name('grade.py'), phase + lang)
            questions = {q['id']: q for q in json.loads((bank / 'questions.json').read_text())}
            expected = json.loads((bank / 'expected-results.json').read_text())
            folder = ROOT / 'docs/retail-gs1-evidence' / phase
            answers = json.loads((folder / (lang + '-answers.json')).read_text())
            score = json.loads((folder / (lang + '-scores.json')).read_text())
            ids = [r['id'] for r in score['results']]
            assert len({a['id'] for a in answers}) == len(answers)
            assert {a['id'] for a in answers} == set(ids)
            by_id = {a['id']: a for a in answers}
            passed = 0
            for result in score['results']:
                qid = result['id']
                observed = grader.grade(by_id[qid]['submission'], expected[qid], questions[qid]['output_contract'])
                assert observed['passed'] == result['passed'], (phase, lang, qid, observed)
                passed += observed['passed']
            assert passed == score['passed']
            print(json.dumps(dict(phase=phase, language=lang, passed=passed, total=len(ids),
                                  method='offline saved-answer audit; no model/platform calls')))


if __name__ == '__main__':
    main()
