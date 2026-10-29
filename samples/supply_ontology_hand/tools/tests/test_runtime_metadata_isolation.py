"""Published semantic metadata must explain computations without fixed benchmark results."""
import json
from pathlib import Path
import re

from register_native_function_toolbox import _operation_inputs

PACK = Path(__file__).resolve().parents[2]


def test_metric_runtime_assets_do_not_embed_snapshot_answers():
    metrics = json.loads((PACK / 'tools/assets/metrics-create.json').read_text())
    probes = json.loads((PACK / 'tools/assets/metrics-query-examples.json').read_text())
    assert 'csv_snapshot' not in metrics
    for metric in metrics['entries']:
        assert not re.search(r'快照\s*\d', metric.get('comment', ''))
    for case in probes['cases']:
        assert 'expected_value' not in case
        assert '当前锁定 CSV' not in case.get('note', '')


def test_backward_grain_contract_explains_complete_tree_value():
    inputs = {x['name']: x for x in _operation_inputs('backward_plan')}
    assert 'full_tree' in inputs['report_grain']['description']
    assert 'summary' in inputs['report_grain']['description']


def test_demand_mode_contract_routes_business_intent_without_question_ids():
    for operation in ['kitting_net_demand', 'shared_contention']:
        text = next(x['description'] for x in _operation_inputs(operation) if x['name'] == 'demand_mode')
        assert '承接' in text and 'fulfillment' in text
        assert '必须' in text and 'production' in text
        assert not re.search(r'[MFRS]-\d{2}', text)


def test_result_free_probe_still_rejects_missing_metric_data():
    from power_layer import verify_metrics
    def command(args):
        if 'list' in args:
            return json.dumps({'entries': [{'name': 'metric', 'id': 'metric-id'}]})
        return json.dumps({'datas': []})
    report = verify_metrics('network', [{'id': 'probe', 'metric_name': 'metric'}], run_cmd=command)
    assert report['passed'] == []
    assert len(report['failed']) == 1


def test_skill_contracts_describe_types_without_fixed_product_answers():
    for folder in ['demand-fulfillment-capacity-analysis', 'demand-fulfillment-requirement-coverage-analysis', 'production-schedule-backward-planning']:
        text = (PACK / 'skills' / folder / 'references/io-contract.md').read_text()
        assert not re.search(r'"(?:fg_qty|theoretical_build_qty|total_sellable_qty|shared_count|finished_goods_qty)"\s*:\s*\d+', text)
        assert '382-000005' not in text and 'P61-000351' not in text
    backward = (PACK / 'skills/production-schedule-backward-planning/references/io-contract.md').read_text()
    assert '业务日期不晚于交付截止日' in backward


def test_all_skill_references_are_free_of_static_result_examples():
    numeric_result = re.compile(r'"(?:fg_qty|theoretical_build_qty|total_sellable_qty|shared_count|finished_goods_qty|customer_late_days|max_delay_days|unsatisfied_demand_count)"\s*:\s*\d+')
    for path in (PACK / 'skills').rglob('*.md'):
        text = path.read_text()
        assert not numeric_result.search(text), str(path)
        assert '快照 90' not in text and '534' not in text, str(path)
