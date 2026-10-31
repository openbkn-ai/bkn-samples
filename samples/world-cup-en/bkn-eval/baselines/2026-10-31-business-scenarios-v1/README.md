# Business-scenario test set v1

Written from the scenarios and rules of the [business PRD](../../../docs/PRD.md): 50 questions, 12 basic, 20 medium and 18 complex, asked as a sports editor, team analyst or tournament data steward. Questions use business language and never state fields, ordering or calculation rules. They keep the meaning of the earlier 50 questions, and every reference answer is unchanged.

- `question-set-v1.yaml`: questions, scenarios, difficulty, role and output contract. The evaluated agent sees only this file.
- `answer-set-v1.yaml`: machine-readable expected values. The evaluated agent must not read it.
- `oracle.py` and `reference-queries.json`: load the locked CSV files into SQLite and run the reference SQL per question, never touching the platform. `question-text.yaml` holds this language's wording. Both language packages share the data, `oracle.py` and the reference SQL, so expected values match.

```sh
python3 samples/world-cup-en/bkn-eval/baselines/2026-10-31-business-scenarios-v1/oracle.py
```

## Scenarios and questions

| Scenario | Questions | Basic/medium/complex |
|---|---|---|
| S01 Tournament facts | B-01, B-02, B-03, J-07, A-09 | 4/0/1 |
| S02 Teams and confederations | B-04, J-11, R-04, R-05, R-11 | 1/2/2 |
| S03 Players, squads and awards | B-05, J-01, J-03, R-13, A-05, A-08, A-10 | 1/3/3 |
| S04 Goals and scorers | B-08, J-10, R-01, R-02, R-03, R-09, R-10, A-03, A-06 | 1/4/4 |
| S05 Matches and scores | B-07, J-02, R-07, R-08, A-04, A-14 | 1/3/2 |
| S06 Discipline | B-06, R-14, A-12 | 1/1/1 |
| S07 Managers and referees | J-04, J-05, J-09, R-12 | 1/3/0 |
| S08 Tables and team runs | J-06, A-01, A-02, A-11 | 0/1/3 |
| S09 Shootouts and substitutions | J-08, J-12, A-07 | 0/2/1 |
| S10 Venues and coverage | B-09, B-10, R-06, A-13 | 2/1/1 |
