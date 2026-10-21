"""Public response types, ownership and complete vocabularies; no answer values/counts."""
import json
import re
from pathlib import Path
from labels import ALIAS_ZH
from build import FIELDS_ZH

ROOT = Path(__file__).resolve().parents[2]
NUMBER_PATTERN = r'^[+-]?\d+(?:\.\d+)?(?:[eE][+-]?\d+)?$'
DESCRIPTIONS = {
 'identity_exceptions': ('Count of identity-path exceptions, not the exception list.', '身份链例外数量，不是例外记录列表。'),
 'instruments_checked': ('Count of checked instruments, not instrument records.', '已检查工具数量，不是工具记录列表。'),
 'reconstructed': ('Reconstructed numerical quantity, not a reconciliation boolean.', '重建后的数量值，不是是否勾稽的布尔值。'),
 'maximum_fixing_age': ('Maximum calendar days from selected FX published_date to trade_date.', '所选汇率发布日期至成交日的最大日历天数。'),
 'source': ('BKN object type ID identifying the source category.', '来源类别使用 BKN 对象类编号。'),
 'instrument_name': ('financial_instruments.name of the identified instrument.', '所标识金融工具的名称，来源 financial_instruments.name。'),
 'issuer_name': ('legal_entities.name of financial_instruments.issuer_id.', '金融工具发行方对应法律实体的名称。'),
 'manager_name': ('legal_entities.name of portfolios.manager_id; the manager name.', '投资组合管理人对应法律实体的名称。'),
 'valuation_reason': ('Exact stored valuation_snapshots.reason value; no paraphrase.', '原样返回估值快照中存储的原因值，不作改写。'),
 'scheme': ('Exact identifier record scheme value; a code prefix does not define the scheme.', '原样返回标识记录的标识体系值；编码前缀不能替代标识体系。'),
 'is_synthetic': ('Typed source boolean. Equivalent serializations: boolean true/false, SQL integer 1/0, lowercase string true/false; preserve truth value.', '来源字段的布尔值。等价表示为布尔 true/false、SQL 整数 1/0、或小写字符串 true/false，必须保持真值一致。'),
 'overdue': ('Whether remaining quantity is positive and due_date is before the business date. Boolean true/false, SQL integer 1/0, lowercase string true/false are equivalent; unknown is null.', '剩余数量大于零且约定结算日早于业务日是否成立；布尔 true/false、SQL 整数 1/0、小写字符串 true/false 等价，未知为 null。'),
 'trade_contribution': ('Computed remaining sell quantity × execution_price × price_multiplier × dated USD FX. USD display amount rounded half up to scale 2; aggregate unrounded contributions before rounding the total.', '计算字段：剩余卖出数量×成交价×价格乘数×带日期美元汇率。美元显示金额四舍五入两位；合计先加总未舍入构成，再舍入总额。'),
 'reconstructed_receivable': ('Computed USD aggregate: sum unrounded sell contributions then round half up to scale 2; do not sum rounded display rows.', '重算美元应收合计：先加总未舍入卖出构成，再四舍五入两位，不以已舍入显示行相加。'),
}


def boolean_shape():
 return {'anyOf': [{'type': 'boolean'}, {'type': 'integer', 'enum': [0, 1]}, {'type': 'string', 'enum': ['true', 'false']}, {'type': 'null'}]}


def numeric_shape():
 return {'anyOf': [{'type': 'number'}, {'type': 'string', 'pattern': NUMBER_PATTERN}, {'type': 'null'}]}


def raw_enum(sample, field, tables):
 """Read full declared public BKN vocabulary, never observed answer values."""
 values = set()
 for table in tables:
  path = sample / 'kn/object_types' / (table + '.bkn')
  if not path.exists():
   continue
  for line in path.read_text().splitlines():
   if line.startswith('| ' + field + ' |'):
    match = re.search(r'(?:Allowed values: |允许取值：)([^.|]+)', line)
    if match:
     values.update(x.strip() for x in match[1].split(','))
 return sorted(values)


def response_contract(fields, rows, sample, zh, tables=(), native=None):
 props = {}
 for field in fields:
  values = [r.get(field) for r in rows if r.get(field) is not None]
  description = DESCRIPTIONS.get(field, (field.replace('_', ' '), FIELDS_ZH.get(field, ALIAS_ZH.get(field, field))))[int(zh)]
  if field in ('is_synthetic', 'overdue'):
   shape = boolean_shape()
  elif native and field == 'event_ids':
   shape = {'type': 'array', 'items': {'type': 'string'}}
  elif values and all(isinstance(v, (int, float)) and not isinstance(v, bool) for v in values):
   shape = numeric_shape()
  elif native and field in native.get('numeric', ()):
   shape = numeric_shape()
  elif values and all(isinstance(v, bool) for v in values):
   shape = {'type': ['boolean', 'null']}
  else:
   shape = {'type': ['string', 'null']}
  enums = native.get('enums', {}).get(field, []) if native else raw_enum(sample, field, tables)
  if field == 'due_state':
   # This SQL classification is binary on the filtered known-date records.
   enums = ['已逾期', '未到期'] if zh else ['overdue', 'not_due']
   description = ('计算分类：约定结算日早于业务日为已逾期，其余为未到期；范围为累计结算量小于应结算量的指令。' if zh else 'Computed classification: overdue if due_date precedes the business date, otherwise not_due; scoped to cumulative settled quantity below required quantity.')
  if enums:
   shape = {'type': ['string', 'null'], 'enum': [*enums, None]}
  props[field] = {**shape, 'description': description}
  owner = {'instrument_name': 'financial_instruments.name', 'issuer_name': 'legal_entities.name via financial_instruments.issuer_id', 'manager_name': 'legal_entities.name via portfolios.manager_id', 'valuation_reason': 'valuation_snapshots.reason'}.get(field)
  if owner:
   props[field]['x-owner'] = owner
  if field in ('trade_contribution', 'reconstructed_receivable'):
   props[field].update({'x-owner': 'computed_usd_receivable', 'x-currency': 'USD', 'x-scale': 2, 'x-rounding': 'ROUND_HALF_UP', 'x-aggregation': 'sum_unrounded_then_round'})
  if native and field in native.get('enums', {}):
   props[field]['description'] += (' 原生函数稳定机器码；两种语言均使用此完整词汇。' if zh else ' Native function canonical machine vocabulary, identical in both languages.')
 row_shape = {'type': 'object', 'properties': {'rows': {'type': 'array', 'items': {'type': 'object', 'properties': props, 'required': fields}}}, 'required': ['rows']}
 # Per-column schemas also constrain compact serialization; it cannot bypass enums/types.
 item_schemas = [props[f] for f in fields]
 compact = {'type': 'object', 'description': ('等价紧凑格式：columns 必须按所示顺序列出全部字段，data 包含全部请求行，各列遵循相同字段契约。' if zh else 'Compact equivalent: columns must list all fields in the stated order; data contains all requested rows and obeys the same per-field contracts.'), 'properties': {'columns': {'const': fields}, 'data': {'type': 'array', 'items': {'type': 'array', 'prefixItems': item_schemas, 'items': False, 'minItems': len(fields)}}}, 'required': ['columns', 'data']}
 return {'$schema': 'https://json-schema.org/draft/2020-12/schema', 'anyOf': [row_shape, compact]}


def capability_contract(fields, rows, sample, zh, scenario):
 enums = {'side': ['buy', 'sell'], 'view_kind': ['actual', 'planned']}
 if scenario == 'C01':
  enums['status_code'] = ['settled', 'pending', 'partial', 'failed', 'unknown']
 elif scenario == 'C02':
  enums.update(actual_status=['complete', 'blocked'], planned_status=['complete', 'blocked'])
 elif scenario == 'C03':
  enums.update(status_code=['within', 'breach', 'unknown'], selection_status=['valid', 'missing', 'ambiguous', 'invalid'], measure=['issuer_ratio', 'receivable_amount'])
 numeric = ['required_quantity', 'settled_quantity', 'remaining_quantity', 'actual_value', 'planned_value', 'value_change', 'actual_settled_quantity', 'planned_settled_quantity', 'observed_value', 'threshold', 'excess_value', 'recorded_value', 'recorded_difference']
 return response_contract(fields, rows, sample, zh, native={'enums': enums, 'numeric': numeric})


def main():
 for lang in ('en-us', 'zh-cn'):
  sample = ROOT / 'samples' / ('financial-fibo-' + lang)
  b = sample / 'bkn-eval'
  gold = json.loads((b / 'expected-results.json').read_text())
  questions = {q['id']: q for q in json.loads((b / 'questions.json').read_text())}
  out = {}
  for qid, entry in gold.items():
   rows = entry['rows']
   fields = sorted(set().union(*(r.keys() for r in rows))) if rows else []
   out[qid] = response_contract(fields, rows, sample, lang == 'zh-cn', questions[qid]['evidence_tables'])
  (b / 'response-contracts.json').write_text(json.dumps(out, ensure_ascii=False, indent=2) + '\n')
 print('Prepared public response types, semantic owners and complete declared vocabularies; no financial expected values or record counts.')


if __name__ == '__main__':
 main()
