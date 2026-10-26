---
name: demand-fulfillment-requirement-coverage-analysis
description: >
  Use when analyzing shared BOM structure or inventory contention between multiple
  new customer demands on knowledge network supply_ontology_hand.
---

# 需求承接 · 新需求覆盖（S3）

至少两条需求需要共同分析时使用。单产品齐套调用 **要 X 套净需求与齐套**。

## 执行步骤

1. 解析产品为唯一编码。数量全部缺失时只用 **产品 BOM 共用清单** 做结构交集，不给承接结论。结构交集要求至少两个不同产品。
2. 数量部分缺失先补齐，不能当作零。数量完整时确认替代策略、仓范围和需求扣减顺序。
3. 缺省为全仓、仅现有库存；显式范围必须遵守。用户要求在途时还需物料需要日/截止日及业务日期，不能无日期把所有未关闭 PO 加入共享池。
4. 调用 **共用料与多需求争用**，`demands` 使用 `[{"product":"产品编码","qty":数量}]` 对象数组。数组顺序为确定扣减顺序；用户明确优先级时先转换并回显，同级保持输入顺序。
5. 检查逐单先成品、逐层先组件、分支与订单共享池；缺料与分配由函数返回。若能力不可用，单单结果只作对照，不能冒充多单争用结果。
6. 回显每单满足状态、成品分配、剩余制造量、净缺、实际仓范围、扣减顺序及在途前提。篇幅不足注明“展示前 N 项，共 X 项”。
7. 补货建议仅依据当前净缺 `recommended_replenishment_qty`；MOQ、安全库存、其他需求未知时不擅自加量，也不自动创建业务记录。

## 统一业务前提

- 未指定仓范围时默认 `all`；用户明确指定的仓预设或仓名单必须遵守并回显。全仓表示不限制仓库，不能把空列表解释为零仓库。
- 使用 `available_inventory_qty`，预留字段仅展示，不再次扣减；同一物料在多个位置或订单之间共享一个物理库存池。
- 新增客户需求先分配成品，只对剩余数量制造；制造时每层组件先分配现货，只展开该层净缺数量。不把结构叶子缺口直接当成客户需求缺口。
- 主料和替代料的资格限定到 BOM 位置（产品、父件、组号）；实际候选按自己的单耗计算。不得跨位置传播资格或重复使用库存。后单在剩余池上重新选择候选；不默认混合多种候选凑数。
- 纯库存数量分析不计在途；只有明确启用现有 PO 且提供物料需要日期/交期时才分析按期供给。净未收量为 `max(0, qty-actqty)`；已关闭或净未收为零的行不参与。按需要日、业务日期及数量分配，逾期未收货 PO 标为待确认，不直接当成可靠到货。
- 事实不完整、分页未读完、缺失提前期或函数业务口径不匹配时返回无法确认。函数执行成功不等于业务验收通过；不得强行沿用旧数值。
- 从已发布 MCP 元数据确认函数参数，使用实际调用回执；不读取答案集、CSV、实现源码或直连数据库重建函数。能力未支持条件时说明限制，不猜参数。

## 完成门槛

模式、唯一产品、数量、策略和顺序已明确；争用结果来自同一次共享池计算。结构共用不等于实际争用，库存覆盖不等于交期承诺。

参考：`references/business-rules.md`、`references/io-contract.md`、`references/report-spec.md`。

## 确定性覆盖题

当题目明确只使用当前可用库存、禁用替代和采购时，调用对应函数，直接按叶子净缺是否为零给出是/否及缺口；中间组件净缺须继续展开，不能当作最终缺料。多个需求按题目数组顺序共用库存，结构共用数不等于实际短缺数。指定业务日期、需要日与确认供应池的物料题使用按期覆盖字段，不推测未来新采购。完整条件下应给出确定结论。

## Single-demand material assurance

For the stock-only Workshop material-assurance case, use `material_coverage` with an explicit `demand_purpose`: `customer_delivery` allocates finished goods first; `new_production` excludes them. Read the published tool metadata to select its localized name. Return the bounded covered/uncovered quantities, all material gaps, source BOM version and collection provenance. `replenishment_draft` accepts the prior complete coverage result and checks its structure only; it does not re-query facts and returns a proposal only; it does not persist, place purchases or promise delivery. Do not equate a saved-looking draft ID with a stored business record. This path handles one demand; use shared contention for multiple demands.
