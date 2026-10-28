"""Where-used fact acquisition must stay bounded without changing graph facts."""
from collections import defaultdict
import pytest
import managed_execution as managed


def query_server(rows, calls):
    by_material = defaultdict(list)
    for row in rows:
        by_material[row['material_code']].append(row)
    def query(**args):
        calls.append(args)
        condition = args['condition']
        values = condition['value']
        allowed = values if condition['operation'] == 'in' else [values]
        matching = [r for code in allowed for r in by_material.get(code, [])]
        offset = args.get('offset', 0)
        return {'datas': matching[offset:offset + args['limit']]}
    return query


def wide_graph(width=200):
    return ([{'material_code': 'leaf', 'parent_material_code': f'P{i:03d}'} for i in range(width)]
            + [{'material_code': f'P{i:03d}', 'parent_material_code': 'root'} for i in range(width)]
            + [{'material_code': 'root', 'parent_material_code': 'leaf'}])


def test_wide_ancestry_preserves_all_edges_with_a_bounded_query_budget():
    rows = wide_graph()
    calls = []
    actual = managed._load_bom_ancestor_rows(query_server(rows + [rows[0]], calls), 'leaf')
    assert {tuple(sorted(r.items())) for r in actual} == {tuple(sorted(r.items())) for r in rows}
    assert len(actual) == len(rows)
    assert len(calls) <= 4, 'a wide parent frontier must not require one operation per material'
    for call in calls:
        c = call['condition']
        if c['operation'] == 'in':
            assert len(c['value']) <= 100


def test_batched_parent_reads_keep_pagination_and_cycles(monkeypatch):
    monkeypatch.setattr(managed, '_PAGE_SIZE', 2)
    rows = wide_graph(5)
    calls = []
    actual = managed._load_bom_ancestor_rows(query_server(rows, calls), 'leaf')
    assert {tuple(sorted(r.items())) for r in actual} == {tuple(sorted(r.items())) for r in rows}
    assert any(c.get('offset', 0) > 0 for c in calls)
    assert len(calls) <= 7


def test_combined_frontiers_preserve_the_aggregate_safety_limit(monkeypatch):
    monkeypatch.setattr(managed, '_MAX_ROWS_PER_DATASET', 4)
    with pytest.raises(managed.CannotCompute, match='安全上限'):
        managed._load_bom_ancestor_rows(query_server(wide_graph(3), []), 'leaf')


def test_all_real_sample_materials_match_the_complete_bom_business_results():
    from support_bkn_rows import bkn_rows
    rows = bkn_rows()['bom']
    complete = managed.build_snapshot({'bom': rows})
    query = query_server(rows, [])
    def result_or_error(compute):
        try:
            return ('result', compute())
        except managed.CannotCompute as exc:
            return ('cannot_compute', str(exc))
    for code in sorted({r['material_code'] for r in rows if r.get('material_code')}):
        loaded = managed._load_bom_ancestor_rows(query, code)
        for alternatives in (False, True):
            expected = result_or_error(lambda: managed.material_where_used(
                complete, code, include_substitute=alternatives, report_grain='full'))
            actual = result_or_error(lambda: managed.execute_from_bkn_rows(
                'material_where_used', {'bom': loaded},
                {'material_code': code, 'include_substitute': alternatives, 'report_grain': 'full'}))
            assert actual == expected, (code, alternatives)


def test_duplicate_rows_across_materials_do_not_shrink_the_accepted_scope():
    rows = ([{'material_code': 'leaf', 'parent_material_code': 'A'},
             {'material_code': 'leaf', 'parent_material_code': 'B'}]
            + [{'material_code': 'A', 'parent_material_code': 'root'}] * 2501
            + [{'material_code': 'B', 'parent_material_code': 'root'}] * 2500)
    calls = []
    actual = managed._load_bom_ancestor_rows(query_server(rows, calls), 'leaf')
    assert len(actual) == 4
    assert len(calls) < 30


def test_a_single_material_still_obeys_its_original_raw_row_limit():
    rows = ([{'material_code': 'leaf', 'parent_material_code': 'A'},
             {'material_code': 'leaf', 'parent_material_code': 'B'}]
            + [{'material_code': 'A', 'parent_material_code': 'root'}] * 5000)
    with pytest.raises(ValueError):
        managed._load_bom_ancestor_rows(query_server(rows, []), 'leaf')


def test_unrelated_query_errors_are_not_retried():
    calls = []
    def query(**args):
        calls.append(args)
        if len(calls) == 1:
            return {'datas': [{'material_code': 'leaf', 'parent_material_code': 'A'},
                              {'material_code': 'leaf', 'parent_material_code': 'B'}]}
        raise ValueError('invalid query transport configuration')
    with pytest.raises(ValueError, match='invalid query transport configuration'):
        managed._load_bom_ancestor_rows(query, 'leaf')
    assert len(calls) == 2


def test_empty_internal_seed_keeps_the_existing_no_query_behavior():
    calls = []
    assert managed._load_bom_ancestor_rows(query_server([], calls), '') == []
    assert calls == []
