# 优惠券与售后诊断流程

## 核销率与口径

从coupon_template读取issued_quantity与used_quantity，用其lp_coupon_redeem_rate或calc_coupon_usage_rate计算累计模板核销率=used/issued。累计模板计数不是期间领取cohort核销率；按领取期、核销期分析应从user_coupon分别使用receive_time和use_time，分母和分子采用一致范围。分母0为无定义。

折扣型券discount_value>1按优惠百分比解释，0至1按优惠比例；不要解释为支付折率或“几折”。先读coupon_type、min_order_amt、max_discount、适用范围和有效期，不能仅凭一个比例推算所有订单优惠。JSON源字段为text，布尔标志按实际integer0/1处理，不假定对象字段为JSON/boolean。

## 有效期与订单异常

ecommerce_coupon_validity_anomalies无需参数，定位expire_time早于receive_time的券，包含已核销券。这是时间数据异常，不等于“当前已过期”，也不等于全部订单用券异常。

coupon_abnormal_orders按实际schema接受可选coupon_code、order_no、user_id；限定用户/订单时只传所需过滤，空范围才考虑全量。它检测订单用户与券用户不一致、实际用券晚于到期或早于领取、券关联订单不一致。无必要不传空字符串；不要把“只检查已付款订单”的函数说成所有订单覆盖。coupon_abnormal_count_by_user需要user_id，仅用于汇总，明细仍需追溯前述函数或查询。

诊断前核对完整性、用户权限与检查范围；相同对象多条索引命中不是多张券。发现异常只报告对象身份、规则和时间证据，不自动写入rule-checks、生成事件、修券或通知。现有异常事件可以只读关联，但不以历史事件数替代当前检测数。

## 售后追溯

先用after_sales_cases按订单读售后申请、批准、退货接收、完成时间及三种金额，再用after_sales_lines定位订单行、退货数量和行退款记录。售后行复合身份为(case_id,item_id)。申请金额、批准金额、实退金额分别展示；订单或售后处于退款中不能当作实退完成，完成状态/时间与payment.refund_at事实交叉核对。

源表售后case当前order_id唯一，是本样例的数据约束，不代表所有电商系统永久一单一次售后。售后到支付缺少精确分配键时只能在订单层交叉核对，不能声称某笔支付承担了某条售后行退款。不能以订单退款金额任意分摊成真实行退款；运费退款与商品退款缺少拆分证据时明确不足。

## 输出

列出正常/异常/未知、券或售后复合身份、订单关联、金额阶段和时间证据；将规则异常与数据缺失分开。用户要求退款执行、修改券或批准售后时说明本Skill只诊断并交回相应业务流程，不调用通用CRUD工具。
