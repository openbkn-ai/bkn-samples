# 库存履约与采购流程

## 库存与预警

1. 确认SKU范围、是否限商品online且SKU active、分析时点。当前函数计算当前源表事实，不提供历史as_of余额；历史问题需要流水及完整期初证据，不能把当前数改名为历史数。
2. 调用ecommerce_inventory_availability：sku_ids最多1000个；空列表明确表示全部；online_only为布尔值；detail_limit为0至1000。先说明空列表可能全量扫描，默认返回20条明细但汇总是完整范围；用户未要求全量时尽量限定SKU。
3. 校验complete=true。物理量physical_quantity取SKU源表stock_quantity；held_quantity汇总隔离；reserved_quantity仅汇总active记录的实际预占；available_quantity=physical-held-reserved。backorder_quantity是待补量，不能再次扣减。负可售量应保留并作为异常，不自动改为0。
4. below_alert_count使用严格<；at_or_below_alert_count使用<=。品牌分组应与总计一致。details_truncated只表示明细被限制，不能据此将完整汇总说成部分，也不能据明细列表长度替代sku_count。

## 缺货与补货

用reservations_to_purchase模板沿预占→采购明细→采购单追溯SKU、待补量、采购量、已收量及预计到货。补货需求与已建采购计划分别报告；预计日期为空是未知，不是逾期。待补采购关系不存在时明确“未关联采购”，不能用相同SKU的任意采购替代。

用inbound_details核对采购行的实际入库与仓库。一个采购行可能多次入库，按入库身份去重后汇总；不要同时把采购行received_qty和入库quantity相加。解释采购预计日期与实际入库日期差异，不假设采购单actual_date等于每条入库发生日。

## 分批发货

用shipment_line_quantities从订单行出发OPTIONAL MATCH发货明细，保留未发货订单行。订单行原数量取根行，不随发货次数重复相加；按发货明细完整身份(shipment_id,item_id)统计发货量。不能把发货记录数当作订单数，也不把已发货当作已签收。缺失匹配与索引同步差异需要交叉核对，不直接判丢单。

## 粒度边界

当前可售函数为SKU汇总，不能直接连到单一仓库。逐仓分析应从流水、预占、隔离、入库等warehouse_id事实进入，并验证覆盖范围；不能任意分配SKU总余额。隔离源表无解除状态，不推断完整隔离/释放历史。库存流水reference_id需结合reference_type确认，不能都连订单。所有建议均为只读建议，不执行补货、出入库或状态修改。
