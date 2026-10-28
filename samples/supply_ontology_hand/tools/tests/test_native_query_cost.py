"""Keep native calculation reads bounded without changing business results."""
import pytest

import managed_execution as managed
from support_bkn_rows import bkn_rows


def matches(row, condition):
    if not condition:
        return True
    operation = condition['operation']
    if operation in {'and', 'or'}:
        values = (matches(row, child) for child in condition['sub_conditions'])
        return all(values) if operation == 'and' else any(values)
    actual = row.get(condition['field'])
    if operation == 'like':
        return actual is not None and condition['value'] in str(actual)
    expected = condition['value']
    if operation == 'in':
        return str(actual) in {str(value) for value in expected}
    assert operation == '=='
    return str(actual) == str(expected)


def reader(datasets):
    returned = []
    reverse = {value: key for key, value in managed._OBJECT_TYPES.items()}

    def query(**request):
        selected = [r for r in datasets[reverse[request['ot_id']]]
                    if matches(r, request.get('condition'))]
        offset = request.get('offset', 0)
        selected = selected[offset:offset + request['limit']]
        properties = request.get('properties')
        if properties:
            selected = [{k: v for k, v in r.items() if k in properties} for r in selected]
        returned.append((request, selected))
        return {'datas': selected}

    return query, returned


def test_material_alternates_avoid_whole_trees_and_keep_full_answer():
    facts = bkn_rows()
    params = {'material_code': '356-000061', 'substitute_enabled': True, 'warehouse_scope': 'all'}
    query, returned = reader(facts)
    loaded = managed.load_bkn_rows('substitute_status', query, params)
    expected = managed.execute_from_bkn_rows('substitute_status', facts, params)
    assert managed.execute_from_bkn_rows('substitute_status', loaded, params) == expected
    key = lambda r: tuple(str(r.get(f) or '').strip() for f in
                          ('bom_material_code', 'parent_material_code', 'alt_group_no'))
    groups = {key(r) for r in facts['bom'] if r.get('material_code') == params['material_code']
              and key(r)[2]}
    bom_reads = [rows for request, rows in returned if request['ot_id'] == managed._OBJECT_TYPES['bom']]
    parents = {k[:2] for k in groups}
    assert all(key(row)[:2] in parents for rows in bom_reads[1:] for row in rows)
    assert sum(map(len, bom_reads)) < 500


def test_alternate_group_filter_keeps_null_parent_and_distinguishes_products():
    def row(product, parent, code):
        return dict(bom_material_code=product, parent_material_code=parent,
                    alt_group_no=7, material_code=code)
    facts = {'bom': [row('P', None, 'M'), row('P', None, 'A'),
                     row('P', 'OTHER', 'BAD'), row('Q', None, 'BAD2')]}
    query, returned = reader(facts)
    assert managed._load_bom_rows_for_material_substitutes(query, 'M') == facts['bom'][:2]
    # Blank parent retains the former whole-root fallback, then exact filtering.
    assert sum(len(rows) for _, rows in returned) == 4


@pytest.mark.parametrize('operation,params', [
    ('substitute_status', {'material_code': '356-000061', 'substitute_enabled': True}),
    ('shared_contention', {'demands': [{'product': 'P61-000351', 'qty': 60},
                                      {'product': 'U00-000151', 'qty': 50}],
                           'substitute_enabled': False, 'report_grain': 'full'}),
])
def test_inventory_projection_preserves_full_calculation(operation, params):
    facts = bkn_rows()
    query, returned = reader(facts)
    loaded = managed.load_bkn_rows(operation, query, params)
    assert managed.execute_from_bkn_rows(operation, loaded, params) == managed.execute_from_bkn_rows(operation, facts, params)
    inventory = [(q, rows) for q, rows in returned if q['ot_id'] == managed._OBJECT_TYPES['inventory']]
    assert inventory
    for request, rows in inventory:
        assert set(request.get('properties', [])) == {'material_code', 'warehouse', 'stock_status', 'available_inventory_qty'}
        assert all(set(row) <= set(request['properties']) for row in rows)


@pytest.mark.parametrize('parent,group', [(' A ', '7'), (' ', '7'), (None, '7'), ('A', ' 7 '), ('A%X', '7'), ('A\\X', '7')])
def test_alternate_members_keep_original_normalized_group_semantics(parent, group):
    row = dict(bom_material_code='P', parent_material_code=parent,
               alt_group_no=group, material_code='M')
    alternative = dict(row, material_code='ALT')
    # Also cover a clean named member whose alternate carries padded values.
    named = dict(row, parent_material_code=str(parent or '').strip(),
                 alt_group_no=str(group).strip())
    facts = {'bom': [named, alternative]}
    query, _ = reader(facts)
    assert managed._load_bom_rows_for_material_substitutes(query, 'M') == facts['bom']
