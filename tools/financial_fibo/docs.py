# -*- coding: utf-8 -*-
"""Render localized business documentation and full answer tables from fixed artifacts."""
import json
from pathlib import Path
from build import ROOT, NAMES, ANCHORS, BASE, REV, FIELDS_ZH
from labels import ALIAS_ZH

def write(p,s):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(s.strip()+'\n',encoding='utf-8')
def render(sample,zh):
 read=lambda p:json.loads((sample/p).read_text(encoding='utf-8'))
 C=read('model-contract.json');lock=read('dataset.lock');Q=read('bkn-eval/questions.json');A=read('bkn-eval/expected-results.json');S=read('bkn-eval/scenarios.json')
 counts=lock['record_counts'];classes=read('fibo-reference/classes.json');props=read('fibo-reference/properties.json')
 group_names=[s['title'] for s in S]
 if zh:
  intro='''# 金融投资组合运营（FIBO 参考，中文）

以虚构资产管理机构的证券交易后控制为场景，从金融工具、法律实体和组合，追溯到成交、结算、持仓、价格、估值、发行方集中度和未结算应收限额。适用于本地建模、数据关联和业务问答验证。

## 从哪里开始

1. [业务 PRD](docs/PRD.md)：业务角色、关切、P0 决策和业务边界。
2. [本体规范与计算口径](docs/bkn-modeling-spec.md)：20 类对象、29 条关系、3 个分组及所有财务公式。
3. [FIBO 语义映射](docs/fibo-operational-mapping.md)：来源、固定修订、映射方式和明确扩展。
4. [数据设计与业务分支](docs/dataset-scenarios.md)：表记录数、关联方式和共享价格的传播影响。
5. [100 题与完整答案](bkn-eval/answers.md)：10 个验收场景；简单 30 题、中等 40 题、复杂 30 题。

当前观察日为 **2027-02-28**；2026-11 至 2027-02 是实际视图，2027-03-31 为从观察日预测的计划视图。全部事实使用日期。每表至少 50 条，最大表超过 16,000 条；本轮合计 **78,356 条/语言**。中文业务名称、状态、原因、题目和答案均中文表达；业务 ID、币种、字段和官方来源标签保留稳定编码。

## 本地验证

在本目录执行，Python 3.9+，仅标准库；不下载数据或依赖、不需要平台凭据：

```bash
openbkn bkn validate kn
python3 tools/verify.py
python3 bkn-eval/run.py
```

原生 BKN 校验需要预装 OpenBKN CLI。脚本逐一重算 8,000 个持仓、8,000 个估值、5,000 项限额评估，并回放锁定的 100 题答案。仓库根目录额外执行 `python3 tools/financial_fibo/test_financial_fibo.py` 可验证双语等价、负向注入和回归控制。

`data/` 是锁定 CSV，`dataset.lock` 保存摘要与行数；`kn/network.bkn` 是唯一模型入口；`model-contract.json` 记录字段和关系映射；`bkn-eval/` 包含题目、完整结构化答案、只读证据 SQL 与回放器。源码目录的 `verification/` 保存本地验证结果，不随安装包交付。

## 评审记录

[首轮问题、修复与独立复验](docs/expert-review-resolution.zh-CN.md)记录本轮55项控制与完整评审证据。

## 来源与交付边界

来源为 [EDM Council FIBO 官方仓库](https://github.com/edmcouncil/fibo)，固定修订 `2d73435a4419b66b7c9f44cb9763e35fe8ac7890`，MIT 许可。六份原始 RDF、原许可、SHA-256 和具名类/属性清单保存在 [fibo-reference/](fibo-reference/README.md)。本包只使用已声明业务范围对应的来源模块，未声明覆盖整个 FIBO 或其完整导入闭包。

本样例是本地离线候选包，要求 **OpenBKN >=0.2.1 <0.3.0**。[离线安装说明](docs/offline-installation.md)采用 Studio 标准导入、安装流程和共享 MariaDB。包内包含 `sample.yaml`、带类型的数据加载与完整核验脚本、原生 BKN 导入与数据源绑定脚本。未创建官方目录条目或线上发布。SQL 回放用于校验冻结答案，不能代表模型准确率；实际仅题目输入的模型问答记录与评分作为独立验收产物保存。安装2个已记录快照指标、3个原始事实重算函数和1个只读异常调查Skill，详见 docs/business-capability-contract.md。'''
 else:
  intro='''# Financial Portfolio Operations (FIBO reference, EN)

A fictional asset manager’s securities post-trade control sample: instrument, legal entity and portfolio → order and execution → settlement → position → price and valuation → issuer concentration and unsettled-receivable limits.

## Start here

1. [Business PRD](docs/PRD.md): stakeholder concerns, P0 decisions and boundaries.
2. [BKN model and calculation rules](docs/bkn-modeling-spec.md): 20 object types, 29 relations, 3 groups and all financial formulas.
3. [FIBO semantic mapping](docs/fibo-operational-mapping.md): pinned sources, mapping decisions and explicit operational extensions.
4. [Dataset and business branches](docs/dataset-scenarios.md): record counts, relationships and shared-price effects.
5. [100 questions and full answers](bkn-eval/answers.md): 10 acceptance scenarios; 30 easy/basic, 40 intermediate, 30 hard/complex.

The observation date is **2027-02-28**. November 2026 through February 2027 are actual views; 2027-03-31 is a planned view known at the observation date. All business facts use dates. Each table has at least 50 records; the largest exceeds 16,000. There are **78,356 records per language** in this revision. English and Chinese share business keys, numeric facts and semantics; human-facing names, states, reasons, questions and answers are localized.

## Local validation

From this directory, use Python 3.9+ and its standard library. Validation needs no platform credentials or downloaded dependencies:

```bash
openbkn bkn validate kn
python3 tools/verify.py
python3 bkn-eval/run.py
```

Native BKN validation requires an installed OpenBKN CLI. Scripts independently reconstruct 8,000 positions, 8,000 valuations and 5,000 limit assessments, then replay all 100 frozen answers. From the repository root, `python3 tools/financial_fibo/test_financial_fibo.py` runs bilingual-equivalence, negative-injection and regression controls.

`data/` contains locked CSVs; `dataset.lock` binds digests and counts. `kn/network.bkn` is the sole model entry point. `model-contract.json` describes fields and FK relationships. `bkn-eval/` contains questions, complete structured answers, read-only evidence SQL and the replayer. Source-checkout `verification/` holds local evidence; it is not part of the install archive.

## Review evidence

[Initial findings, resolution and independent recheck](docs/expert-review-resolution.zh-CN.md) record the 55 financial/bilingual controls and full review evidence.

## Sources and delivery boundary

Source: [official EDM Council FIBO repository](https://github.com/edmcouncil/fibo), pinned revision `2d73435a4419b66b7c9f44cb9763e35fe8ac7890`, MIT license. Six original RDFs, the original license, SHA-256 digests and named class/property inventories are in [fibo-reference/](fibo-reference/README.md). These are selected business-scope modules, not all FIBO or its transitive import closure.

This is a local offline candidate requiring **OpenBKN >=0.2.1 <0.3.0**. [Offline installation](docs/offline-installation.md) uses the standard Studio import/install flow and the shared MariaDB database. The package includes `sample.yaml`, typed database loading/verification hooks and native BKN resource-binding hooks. No official catalog entry or online release is created. SQL replay validates frozen answers; it does not measure model accuracy. Live question-only model transcripts and scoring are separate acceptance artifacts. Installs 2 recorded-snapshot metrics, 3 atomic reconstruction functions and 1 investigation Skill; see docs/business-capability-contract.md.'''
 intro+='\n\n'+('公开100题保留原难度比例，另有30道复杂能力开发题（bkn-eval/capability-questions.json）。能力契约见 docs/business-capability-contract.md；开发参考结果不属于独立盲测。' if zh else 'The public 100-question split is retained, with 30 additional complex capability development cases in bkn-eval/capability-questions.json. See docs/business-capability-contract.md; development references are not independent holdout evidence.')
 write(sample/'README.md',intro)
 # Calculation contract + generated dictionary.
 calc_zh='''# BKN 本体规范与财务计算口径

## 原生格式与身份

遵循仓库所用原生 BKN 规范：YAML frontmatter 加 Markdown；唯一入口 `kn/network.bkn`；对象、关系、概念分组分别位于对应子目录。结构标题、字段名保持解析器要求，业务显示名中文。对象主键和关系文件名稳定，`id/name` 均不超过 40 字符。对象全部映射本地 CSV 字段；数据源 ID 由将来的平台安装绑定，不在样例中伪造。

规范依据：SDK `skills/create-bkn/references/SPECIFICATION.llm.md` 与 `openbkn bkn validate`。本地原生验证结果保存在 `verification/bkn-validation.json`。

## 统一财务规则

- **视图：**2027-02-28 为当前观察日；此前月末为实际视图，三月为计划。计划于 2027-02-28 已知，计划成交、价格和汇率均非真实未来市场数据。
- **日历：**使用明确虚构的周一至周五工作日及 T+2 工作日示例约定，不模拟地区节假日，不声称适用于真实市场。月末快照可落周末，但价格和汇率定盘来自此前工作日；事件日期与指令内顺序共同确定先后，不使用时点。
- **身份：**法律实体、股票/债券和组合均虚构。`DEMO-ENTITY-*`、`DEMO-SEC-*` 是本地标识，不声称是有效 LEI、ISIN 或监管登记。
- **数量口径：**每组合八项持仓、四家发行方，每家同时发行股票和债券。期初数量来自 `opening_positions`；成交正负由买卖方向决定。交易日持仓 = 期初 + 已知且成交日在截至日前的有符号成交；结算日持仓 = 期初 + 事件日在截至日前的有符号实际结算量。两者差额 = 未结算差量。只允许多头，卖出量不得超过持仓。
- **结算：**每笔成交对应一张指令。事件表的 `settled_quantity` 是本次转移量，不是累计量；每张指令可含确认、部分转移和恢复等多条事件，必须按截至日和已知日先筛选，再按指令累计数量。数量或顺序不可靠时为未知；已全额转移为已结算；否则最新事件失败为失败，再依累计量区分部分与待结算。离线 `settlement_state` 表达当前实际聚合，`settlement_month_end` 表达各成交月末聚合；它们由 `tools/settlement_views.py` 创建，不是额外 BKN 对象或平台函数。实际视图排除计划事件。本样例的实际订单、成交和结算事件按发生日入账，不能提前知道已完成转移。三月正常交易按预期结算，保留部分/失败例外；二月未结算按明确恢复假设处理，不能一律当成永不结算。状态为失败或待结算时转移量为零，部分结算时大于零且小于应结算量。约定日在观察日之后的待结算不等于失败，也不算已逾期。
- **成本与损益：**买入按成交价与单位乘数增加成本；卖出前以剩余成本/剩余数量得到加权平均单位成本。已实现损益 = 卖出数量 ×（成交价 × 单位乘数 − 卖出前平均单位成本）。`realized_pnl` 是本月交易币种已实现损益。成本先按两位小数入账，再按当前汇率折算；未实现损益 = 当前美元市值 − 当前汇率折算的剩余成本。它不包含历史汇兑损益、税费、票息或公司行动。
- **股票与债券：**股票价格按每股，乘数 1；债券数量为面值单位，使用每百元面值全价，乘数 0.01。债券全价已包含应计利息，不重复加息，也不做票息现金流核算。
- **价格质量：**每个估值快照选用相同工具、相同 `as_of_date` 的报价记录，`price_date` 可早于快照。需已批准，价格年龄不超过 3 个日历日，发布日期不得晚于快照。缺失记录、陈旧报价和未批准报价分别处理，不自动回退旧价或将缺失补零。
- **汇率与舍入：**汇率方向是每一单位源币种兑 USD；估值与汇率快照日期一致。交易币种市值 = 交易日数量 × 价格 × 单位乘数，先四舍五入到两位；美元市值 = 上述已舍入市值 × 汇率，再舍入两位。金额使用 Decimal / ROUND_HALF_UP，比例与汇率保留六位。离线 SQL 采用 SQLite 数值类型，按题目指定 0.000001 容差与锁定结果比较；独立财务重算使用 Decimal。
- **发行方集中度：**分子为该组合对某发行方的两项持仓美元市值；分母为同一日期全部八项持仓美元市值。任一持仓估值受阻，该组合所有发行方集中度均无法判定。`exposure_contributions` 记录估值构成，禁止只汇总有价格部分并标记完整。
- **交易对手口径：**`counterparty_exposures` 的兼容技术名称指**未结算卖出应收金额**。按相同组合和交易对手，将截至日尚未结算的卖出数量 × 成交价 × 单位乘数 × 当前汇率求和，再舍入两位。买入应付不进入该金额，不净额抵销，不表示替代成本、PFE、EAD 或监管 CCR。
- **限额：**发行方限额以 0–1 比例表达；交易对手限额以 USD 金额表达。只有在评估日有效、当时已知且已批准的版本可用。观察值严格大于阈值才超限；未知观察值仍为无法判定。超限值为 `max(0,观察值−阈值)`，比例与金额不可混用。

## 对象与记录字典
'''
 calc_en='''# BKN ontology specification and financial rules

## Native format and identity

Use the repository's native BKN format: YAML frontmatter plus Markdown, sole entry point `kn/network.bkn`, and separate object, relation and concept-group directories. Stable primary keys, relation IDs and filenames are retained; all IDs and names fit the 40-character platform limit. Every property maps to a CSV field. Environment-specific resource IDs are left for a future installation binding.

References: SDK `skills/create-bkn/references/SPECIFICATION.llm.md` and `openbkn bkn validate`. Native local evidence is in `verification/bkn-validation.json`.

## Financial rules

- **Views:** 2027-02-28 is the observation date. Earlier month-end snapshots are actual. March is a plan known on 2027-02-28; its trades, prices and FX are fictional forecasts.
- **Calendar:** use an explicitly fictional Monday–Friday and T+2 business-day convention, without jurisdiction holidays or real-market claims. Snapshot dates may fall on weekends; quotes/fixings come from the preceding weekday. Date plus per-instruction event sequence establishes ordering without timestamps.
- **Identity:** entities, instruments and portfolios are fictional. `DEMO-ENTITY-*` and `DEMO-SEC-*` are local identifiers, not valid LEIs, ISINs or regulatory registrations.
- **Quantity bases:** each portfolio has eight positions across four issuers, each with an equity and a bond. Trade-date quantity = opening quantity plus known signed trades executed by the snapshot date. Settlement-date quantity = opening quantity plus signed settlement-event transfers effective by that date. Their difference is the unsettled delta. The sample is long-only and cannot oversell.
- **Settlement:** one instruction per trade. `settled_quantity` is incremental, not cumulative. Instructions can contain acknowledgements, partial transfers and recoveries. Offline `settlement_state` represents current actual aggregation; `settlement_month_end` aggregates at each fill month-end. `tools/settlement_views.py` creates these evidence views, not additional BKN objects or platform functions. Filter by as-of and knowledge date and sum eligible transfers. Invalid quantity or ambiguous ordering is unknown; full transfer is settled; otherwise latest failure takes precedence, followed by partial or pending according to transferred quantity. Actual views exclude planned events. Actual orders, fills and settlement events are booked on their occurrence date in this sample; completed transfers cannot be known in advance. March includes normal projected settlement, partial/failure exceptions and explicit recoveries of February instructions, not universal non-settlement. Failed/pending events transfer zero; partial events transfer a positive amount below required quantity. An instruction due after the observation date is neither overdue nor automatically failed.
- **Cost and P&L:** buys increase cost at execution price times unit factor. Before a sale, weighted-average unit cost is remaining cost divided by quantity. Realized P&L = sold quantity × (execution price × factor − pre-sale average unit cost). `realized_pnl` is the current month's local-currency realized P&L. Remaining cost is booked to two decimal places before FX conversion. Unrealized USD P&L = USD market value − remaining cost translated at current FX. Historical FX P&L, fees, taxes, coupons and corporate actions are excluded.
- **Equities and debt:** equities quote per share, factor 1. Bonds use face units and dirty price per 100 face, factor 0.01. Dirty price already includes accrued interest; no second accrued-interest adjustment or coupon cash ledger is implied.
- **Prices:** select the same instrument and `as_of_date` quote as the valuation snapshot; its `price_date` may be older. The quote must be approved, no more than 3 calendar days old and published by the snapshot date. Missing, stale and unapproved prices block valuation separately. No stale-price fallback or zero-value substitution occurs.
- **FX and rounding:** rates are USD per source-currency unit and share the valuation snapshot date. Local value = trade-date quantity × price × factor, rounded to 2dp. USD value = rounded local value × FX, again rounded to 2dp. Financial reconstruction uses Decimal / ROUND_HALF_UP; ratios and FX have 6dp. Offline SQLite queries compare frozen results with a 0.000001 tolerance; independent financial validation uses Decimal.
- **Issuer concentration:** numerator is the two contributing instrument values for that issuer; denominator is all eight USD position values for the portfolio/date. Any incomplete position blocks every issuer ratio for that portfolio. `exposure_contributions` retains valuation membership; a partial denominator cannot pass as complete.
- **Counterparty measure:** the technical table name `counterparty_exposures` means **unsettled sell receivable**. For the same portfolio/counterparty, sum remaining sell quantity × execution price × unit factor × dated FX and round to 2dp. Buy payables are excluded; no netting is applied. This is not replacement cost, PFE, EAD or regulatory CCR.
- **Limits:** issuer limits are ratios from 0 to 1; receivable limits are USD amounts. Use only an approved version valid on the assessment date and known at the observation date. A strict greater-than comparison breaches; missing observations remain unknown. Excess is `max(0, observed − threshold)` in the measure's own units.

## Object and record dictionary
'''
 d=calc_zh if zh else calc_en
 d+='\n| ObjectType | '+('名称 | 记录数 | 主键 | 关系外键' if zh else 'Name | Records | Primary key | Relationship keys')+' |\n|---|---|---:|---|---|\n'
 for t,v in C['object_types'].items():
  fks=[r['source_property']+' → '+r['target'] for r in C['relations'] if r['source']==t]
  d+=f'| `{t}` | {NAMES[t][1 if zh else 0]} | {counts[t]} | `{v["primary_key"]}` | '+('; '.join(fks) or '—')+' |\n'
 d+='\n'+('## 全部直接关系\n\n每条关系对应具名外键。空的 `price_id` 或评估中的另一种敞口外键表示缺失或不适用，不生成空端点关系。\n' if zh else '## All direct relationships\n\nEach relation maps a named FK. Empty `price_id` and the inapplicable exposure FK on an assessment create no relation.\n')
 d+='\n| ID | Source | Property | Target | Property |\n|---|---|---|---|---|\n'
 for r in C['relations']:d+=f'| `{r["id"]}` | {r["source"]} | {r["source_property"]} | {r["target"]} | {r["target_property"]} |\n'
 d+='\n'+('## 场景能力选择\n\n已物化的带日期业务快照和直接关系支持本地 P0 验证。SQL 只用于验收，不作为平台函数发布；生成器不在运行期执行。安装2个快照指标、3个原始事实重算函数和1个只读调查Skill；能力契约及真实调用验证与SQL回放分开。' if zh else '## Capability choice\n\nDated materialized snapshots and direct relations support the local P0 acceptance. SQL is an offline test oracle, not a published function; generators do not execute at runtime. Two snapshot metrics, three atomic reconstruction functions and one read-only Skill are installed; live capability acceptance remains separate from SQL replay.')
 write(sample/'docs/bkn-modeling-spec.md',d)
 # Source mapping, avoid asserting synthetic identifiers are real LEIs.
 text=('# FIBO 来源与运营语义映射\n\n' if zh else '# FIBO source and operational semantic mapping\n\n')
 text+=('来源为 [FIBO 官方仓库](https://github.com/edmcouncil/fibo)，固定修订' if zh else 'Source: [official FIBO repository](https://github.com/edmcouncil/fibo), pinned revision')+f' `{REV}` (MIT).\n\n'
 text+=('六份原始 RDF、原始许可和摘要均随包保留。来源文件中共识别出 **171 个具名类、71 个具名对象/数据属性**；这些包含复用和废弃声明，只构成来源清单，不能据此声称已实现这些类或 OWL 推理。选用锚点均验证为非废弃且有定义。完整 OWL 导入闭包及 FIBO 全域不在本场景覆盖声明内。\n\n' if zh else 'Six original RDFs, their license and file digests are retained. Their inventories contain **171 named classes and 71 named object/data properties**, including reused and deprecated declarations. These are source inventories, not implementation or inference coverage claims. Selected anchors are checked as nondeprecated and defined. Full OWL import closure and all FIBO domains are outside the declared scenario.\n\n')
 text+='| ObjectType | '+('来源 IRI | 映射说明' if zh else 'Source IRI | Interpretation')+' |\n|---|---|---|\n'
 for t,(mod,cl) in ANCHORS.items():text+=f'| `{t}` | {BASE+mod+"/"+cl} | '+('运营子集；原始英文定义与 IRI 保存在对应 BKN 的 Semantic Provenance。' if zh else 'Operational subset; the original definition and IRI are retained in the BKN Semantic Provenance section.')+' |\n'
 text+='\n'+('## 明确的运营扩展\n\n`legal_entities` 是虚构实体登记表，`legal_entity_identifiers` 使用 `DEMO-ENTITY-*` 本地编码；它们不声称是 FIBO LEIRegisteredEntity 或 ISO 17442 LegalEntityIdentifier 实例。订单、账户、期初持仓、结算指令/事件、汇率观测、估值快照、敞口构成、未结算应收、授权限额及评估是本场景运营扩展。\n\n股票和债券通过 `financial_instruments.asset_class` 分类，其报价单位和乘数明确记录；没有额外建立没有独立业务数据的子类表。组合不是法律实体，持仓不是发行方，交易对手作为法律实体的经纪商角色，而非用机构名称推断风险。\n\n不把匿名限制、外部端点或没有业务映射的 OWL 属性转成兜底关系。29 条关系全部有实际外键，指向可验证的样例记录。' if zh else '## Explicit operational extensions\n\n`legal_entities` is a fictional entity registry; `legal_entity_identifiers` uses local `DEMO-ENTITY-*` codes. They do not assert FIBO LEIRegisteredEntity membership or ISO 17442 LegalEntityIdentifier status. Orders, accounts, opening positions, settlement instructions/events, dated FX, valuation snapshots, contribution records, unsettled receivables, limits and assessments are scenario operational extensions.\n\nEquity/debt are classifications on `financial_instruments.asset_class` with explicit quote basis and multiplier; no empty subtype tables are added. A portfolio is not a legal entity, a position is not an issuer, and a counterparty is an entity in a broker role.\n\nAnonymous restrictions, external endpoints and properties without concrete business mappings do not become catch-all relations. All 29 relations have actual foreign keys and verifiable records.')
 write(sample/'docs/fibo-operational-mapping.md',text)
 # Data design, scenario differences and propagation.
 d=('# 数据设计与业务分支\n\n' if zh else '# Data design and business branches\n\n')
 d+=('200 个组合各有八项持仓，分布于四家发行方的股票/债券。100 个工具和 50 家发行方跨组合复用；另有 50 家经纪商和 50 家管理人。每个持仓具有期初记录，五个月日期错开的订单、成交、多事件结算、数量快照和估值；价格既上涨也下跌，产生正负已实现及未实现损益；每组合每月有四项发行方敞口及一项交易对手应收。不是给同一条业务记录加“批次”后缀扩容。\n\n' if zh else '200 portfolios each have eight positions across four issuers, each issuing an equity and a bond. 100 instruments and 50 issuers are reused across portfolios; there are also 50 brokers and 50 managers. Each position has an opening and five months of staggered orders, fills, multi-event settlement, position snapshots and valuations. Prices rise and fall, producing both positive and negative realized/unrealized P&L. Every portfolio/month has four issuer exposures and one counterparty receivable. Names describe fictional businesses rather than repeated batch labels.\n\n')
 d+=('| 主分支 | 组合 | 数量 | 当前差异 |\n|---|---|---:|---|\n| 正常结算 | PF-(001–018)+50n | 72 | 结算完成；主分支无自身价格例外 |\n| 待结算 | PF-(019–028)+50n | 40 | 20 组尚未到期，20 组部分结算且余额逾期 |\n| 结算失败 | PF-(029–034)+50n | 24 | 证券不足/金额不匹配；保留未结算应收 |\n| 价格例外 | PF-(035–040)+50n | 24 | 两类工具陈旧、两类未批准、两类缺失，跨组合传播 |\n| 发行方超限 | PF-(041–045)+50n | 20 | 对一家发行方集中配置，限额 30% |\n| 交易对手超限 | PF-(046–048)+50n | 12 | 失败卖出应收超过 USD 500 限额 |\n| 未来限额变更 | PF-(049–050)+50n | 8 | 当前 80%；2027-03-15 起 20% |\n\n' if zh else '| Primary branch | Portfolios | Count | Current difference |\n|---|---|---:|---|\n| Normal settlement | PF-(001–018)+50n | 72 | Fully settled; no own primary pricing defect |\n| Pending settlement | PF-(019–028)+50n | 40 | Twenty not yet due; twenty partially settled with overdue balances |\n| Failed settlement | PF-(029–034)+50n | 24 | Insufficient securities / cash mismatch; open receivables retained |\n| Price exception | PF-(035–040)+50n | 24 | Two stale instruments, two unapproved, two missing, with cross-portfolio propagation |\n| Issuer breach | PF-(041–045)+50n | 20 | Concentrated issuer allocation; 30% threshold |\n| Counterparty breach | PF-(046–048)+50n | 12 | Failed sell receivables exceed USD 500 |\n| Future limit change | PF-(049–050)+50n | 8 | 80% currently; 20% from 2027-03-15 |\n\n')
 d+=('表内 n=0、1、2、3，表示200个组合的四组业务配置，数值、名称和交易日期不同。主分支不是互斥风险标签：6项工具的价格缺陷跨组合传播，部分待结算/失败组合同时出现估值例外。不能用主分支替代实际证据判断；完整受影响数量由验收集重算。未来计划采用独立标记的预测价格。\n\n' if zh else 'Here n=0,1,2,3 denotes four groups of portfolio configurations with distinct names, amounts and trade dates. Primary branches are not mutually exclusive: six defective shared instruments propagate across portfolios, including pending/failed segments. Evaluate actual evidence rather than branch labels; acceptance queries derive all impact counts. Forecast prices remain explicitly planned.\n\n')
 d+=('## 全部表规模\n\n| 表 | 记录数 |\n|---|---:|\n' if zh else '## All table sizes\n\n| Table | Records |\n|---|---:|\n')
 for t,n in counts.items():d+=f'| `{t}` | {n} |\n'
 d+=f'| **{"合计" if zh else "Total"}** | **{sum(counts.values())}** |\n\n'
 d+=('## 验收分配\n\n每个场景 10 题：简单 3、中等 4、复杂 3。十个场景合计 100 题：\n\n' if zh else '## Acceptance allocation\n\nEach of ten scenarios has 10 questions: 3 easy/basic, 4 intermediate, 3 hard/complex, for 100 in total:\n\n')
 for s in S:d+=f'- {s["id"]} {s["title"]}\n'
 write(sample/'docs/dataset-scenarios.md',d)
 # Original PRD updated without technical noise.
 p=sample/'docs/PRD.md';s=p.read_text()
 s=s.replace('synthetic LEI-shaped identifiers','clearly synthetic local entity identifiers').replace('带有合成 LEI 形态标识','带有明确本地合成标识')
 s=s.replace('Actual activity runs from','Actual activity runs from')
 s=s if 'The observation date is 2027-02-28;' in s else s.replace('A stated as-of date governs every position, price, exposure, and limit conclusion.', 'The observation date is 2027-02-28; November through February views are actual, while March is a future plan known on that date. A stated as-of date governs every position, price, exposure, and limit conclusion.')
 s=s if '观察日为 2027-02-28：' in s else s.replace('每项持仓、价格、敞口和限额结论都必须标明截至日期。','观察日为 2027-02-28：十一月至二月为实际视图，三月是从该日已知信息出发的未来计划。每项持仓、价格、敞口和限额结论都必须标明截至日期。')
 s=s.replace('counterparty exposure','unsettled counterparty sell receivables').replace('Counterparty exposure','Unsettled counterparty sell receivables')
 s=s.replace('交易对手敞口','交易对手未结算卖出应收')
 write(p,s)
 # Reference README
 write(sample/'fibo-reference/README.md', ('# FIBO 原始来源\n\n六份选定模块的原始 RDF 保存在 `sources/`，`source-lock.json` 固定仓库修订和各文件 SHA-256；`LICENSE-FIBO.txt` 是原 MIT 许可。`classes.json` 是 171 个具名类的来源清单；`properties.json` 是 71 个具名对象/数据属性清单。清单记录来源文件、英文定义、类型和废弃状态。它们用于语义溯源，不作为虚构运营数据的对象实例或全量 FIBO 导入声明。' if zh else '# Original FIBO sources\n\n`sources/` retains six selected original RDF modules. `source-lock.json` pins repository revision and each SHA-256; `LICENSE-FIBO.txt` is the original MIT license. `classes.json` inventories 171 named classes; `properties.json` inventories 71 named object/data properties, with source files, English definitions, kind and deprecation. These support semantic provenance, not operational instances or a full-FIBO import claim.')+f'\n\n[Official source / 官方来源](https://github.com/edmcouncil/fibo/tree/{REV})\n')
 # Readable full answers; structured data remains authoritative.
 title='# 100 题与完整答案' if zh else '# 100 questions and complete answers'
 text=title+'\n\n'+('答案与锁定数据一一对应，包含全部返回行。金额单位以币种列和题意为准，集中度为 0–1 比例。`NULL` 表示缺失/无法判定，不等于零。SQL 证据见 `questions.json`，结构化答案见 `expected-results.json`。\n\n' if zh else 'Answers bind the locked data and contain every returned row. Amount units follow currency columns and question context; concentrations are ratios from 0 to 1. `NULL` means missing/unknown, not zero. SQL evidence is in `questions.json`; structured gold is in `expected-results.json`.\n\n')
 for q in Q:
  rows=A[q['id']]['rows'];text+=f'## {q["id"]} · {q["level"]}\n\n{q["question"]}\n\n{A[q["id"]]["explanation"]}\n\n'
  headers=list(rows[0]);labels=[FIELDS_ZH.get(h,ALIAS_ZH.get(h,h)) if zh else h for h in headers]
  text+='| '+' | '.join(labels)+' |\n|'+'|'.join('---' for _ in headers)+'|\n'
  for row in rows:text+='| '+' | '.join('NULL' if row[h] is None else str(row[h]).replace('|','/') for h in headers)+' |\n'
  text+='\n'
 write(sample/'bkn-eval/answers.md',text)
 write(sample/'bkn-eval/README.md', '# '+('本地验收集' if zh else 'Local acceptance bank')+'\n\n'+('100 道独立题目分布于 10 个业务验收场景。`questions.json` 保留问题、难度、场景 ID、关系路径和只读证据 SQL；`expected-results.json` 固定全部结果行；`answers.md` 供人阅读。逐题结果需保持行顺序、字段和空值语义；数字按显式容差比较。\n\n`run.py` 先检查数据摘要和 BKN 映射，再以独立 Decimal 算法验证金融逻辑，最后在内存 SQLite 回放全部题目。数据库限制为只读查询，不使用生成器或运行中重生成预期答案。实际智能体/MCP问答须针对固定离线包在平台另行执行，原始问答和事后评分与本地回放证据分开保存。' if zh else '100 distinct questions span 10 business acceptance scenarios. `questions.json` includes question, level, scenario ID, relation paths and read-only SQL evidence. `expected-results.json` freezes all rows; `answers.md` is the readable counterpart. Preserve row order, fields and null semantics; numeric comparison uses the explicit tolerance.\n\n`run.py` checks digests and BKN mappings, reconstructs financial facts with independent Decimal logic, then replays queries in in-memory SQLite. The query connection is read-only; evaluation neither imports the generator nor regenerates gold. Actual agent/MCP evaluation requires a separate question-only run with persisted answers, tool traces and post-answer scoring.'))

if __name__=='__main__':
 for z in (False,True):render(ROOT/'samples'/('financial-fibo-zh-cn' if z else 'financial-fibo-en-us'),z)
