---
name: demand-fulfillment-requirement-coverage-analysis
description: >
  Use when checking whether multiple new product demands can be accepted together
  on knowledge network supply_ontology_hand, including shared-BOM structure,
  kitting net demand, and shared-material contention.
---

# 需求承接 · 新需求覆盖（S3）

这是一个**业务场景导航 Skill**。仅当至少两个产品需求需要一起分析时使用；单产品齐套直接调用 **要 X 套净需求与齐套**。

> 数量全部缺失时只做 BOM 结构交，不给满足/不满足结论；数量全部明确时才做争用。
> **理论可产、合计可售、齐套净需求、共用料争用是不同口径。**本 Skill 只回答结构共用或多需求争用。

## Skill Card

| 字段 | 值 |
|------|-----|
| `bkn_scope` | `supply_ontology_hand` |
| `trigger` | 多单互抢、新需求能否一起接、共用料够不够 |
| `calculation` | 无数量：`bom_shared_list`；数量完整：`shared_contention` |
| `优先指标` | 库存可用量（用于解释争用的库存基础） |
| `优先函数` | **共用料与多需求争用**；结构分析用 **产品 BOM 共用清单**；单单核对用 **要 X 套净需求与齐套** |
| `open_parameters` | `demands[]`（产品 + 数量? + 优先级?）、`substitute_enabled`、`warehouse_scope?` |

不要调用：S1（无截止日）；把结构交当成争用；把成品可售当作多需求争用；自动创建采购申请或采购订单。
在途只计未关闭 PO，**只在数量完整的争用模式中进入共享池**。

## Agent 执行步骤

1. 解析每个产品为唯一编码；名称歧义先澄清。
2. 数量全部缺失时，只调用 **产品 BOM 共用清单** 并说明不能判断承接。
3. 数量部分缺失时先追问；不得把缺失数量当作 0。
4. 数量完整时，确认替代料策略与扣减顺序后调用 **共用料与多需求争用**。`demands` 只使用对象数组：`[{"product":"382-000005","qty":50},{"product":"P61-000351","qty":60}]`；数组顺序即扣减顺序。
5. 函数未覆盖或不可用时，如实记录 `unavailable`；可补充单单齐套函数结果，但不得把它表述为多需求争用结论。
6. 需要向采购提出补货建议时，只能使用函数缺料项的 `recommended_replenishment_qty`。该值等于当前需求快照的净缺；MOQ、安全库存或其他需求未明确时，不得把计划采购量直接写成建议量。

## 模式选择与业务边界

- 至少两个产品且数量全部缺失 → `bom_shared_list`；只报告结构交集，明确“这不是争用，也不是满足结论”
- 数量全部明确 → `shared_contention`；共享可用与未关闭 PO 在途按传入顺序扣减
- 数量部分缺失 → 先追问：补齐全部数量，或明确改做纯结构分析；不得把缺失数量猜成 0，也不得混合计算
- 显式优先级先转换为确定的 `deduction_order`，同优先级保持用户传入顺序；调用前回显，禁止静默改序
- 替代组 MAX；未确认替代 → 不能算
- 无截止日时不调用 S1；单产品问题改走单产品函数或 S2

## 计算调用

每个产品输入先解析为唯一编码。结构模式调用 **产品 BOM 共用清单**；争用模式调用 **共用料与多需求争用**。函数自行读取 BKN 数据，Skill 不读取源码、不重建运行时、不在本地改写算法。

## 输入

- `knowledge_network_id`：默认 `supply_ontology_hand`
- `demands[]`：至少 2 条；每个产品允许编码或名称，名称命中多个编码时必须追问
- 调用函数时每项固定为 `{ "product": "产品编码", "qty": 数量 }`；不得传入 `产品:数量` 等字符串，也不得猜测分隔符或尝试其他格式
- 数量必须全部明确或全部缺失；部分缺失时先澄清模式
- `substitute_enabled`：未给出先问
- `warehouse_scope`：争用模式默认 `production_available`
- 扣减顺序 = 规范化后的数组顺序；若用户给出优先级，则高优先先扣、同级保持传入顺序

## 编排

1. `resolve_input` — 解析至少两个唯一产品编码，确认结构/争用模式、替代策略和扣减顺序
2. `select_capability` — 结构问题直调共用料函数；数量完整时调争用函数
3. `analyze` — 只解释函数返回的结构、缺口和扣减顺序；需要补货建议时回显 `recommended_replenishment_qty` 与其适用前提
4. `render_report` — 生成结构交或争用报告；若篇幅只展示部分缺料，必须写明“展示前 N 项，共 X 项”

## 完成门槛

1. 至少 2 个产品均已解析为唯一编码
2. 数量全部缺失时不得输出满足/不满足；部分缺失时不得执行函数
3. `substitute_enabled` 已确认
4. 争用模式回显函数返回的 `deduction_order`、仓名单，并说明在途仅计未关闭 PO
5. 报告阶段不再拉数或重算
6. 只输出分析与建议，不自动创建采购申请或采购订单

## 输出

见 `references/io-contract.md` 与 `references/report-spec.md`。

## 参考

- `references/business-rules.md`
- `references/io-contract.md`
- `references/report-spec.md`
