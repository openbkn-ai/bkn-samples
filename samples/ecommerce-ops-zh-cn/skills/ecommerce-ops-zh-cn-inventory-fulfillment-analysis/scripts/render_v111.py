"""Offline rendering of verified business facts; no platform SDK or credentials."""
import argparse,base64,json,sys
from decimal import Decimal,ROUND_HALF_UP
DOMAIN='inventory'
TITLE='库存履约与采购分析'
def money(value):
    if value is None:return '未知'
    return str(Decimal(str(value)).quantize(Decimal('0.01'),rounding=ROUND_HALF_UP))+'元'
def render(facts):
    if not isinstance(facts,dict) or facts.get('domain')!=DOMAIN:raise ValueError('事实不属于当前业务Skill')
    if facts.get('status') not in {'complete','partial'} or facts.get('read_only') is not True:raise ValueError('缺少有效只读业务结果，先调用业务组合函数')
    if not isinstance(facts.get('results'),dict) or not isinstance(facts.get('calls'),list) or not facts['calls']:raise ValueError('事实缺少结果或调用来源')
    results=facts['results'];lines=['# '+TITLE,'','结果状态：'+facts['status']]
    if DOMAIN=='finance':
        financial=results.get('ecommerce_order_financial_analysis',{}).get('entries',[])
        if not financial:lines.append('本次未返回订单财务记录；不能据此判定收入为零。')
        for row in financial:
            lines.append('订单'+str(row['order_id'])+'：应付'+money(row.get('order_payable_amount'))+'，已确认收款'+money(row.get('confirmed_receipts_amount'))+'，已完成退款'+money(row.get('completed_refund_amount'))+'，净收款'+money(row.get('net_receipts_amount'))+'。')
        for row in results.get('ecommerce_user_consumption_analysis',{}).get('entries',[]):
            lines.append('用户'+str(row['user_id'])+'：全历史净收款'+money(row.get('net_receipts_amount'))+'，分析分层='+str(row.get('consumption_segment','未知'))+'。')
        lines.append('口径：申请退款不计实退；订单应付与实际收款分别展示；上述结果不代表银行结算日现金流。')
    elif DOMAIN=='inventory':
        inv=results.get('ecommerce_inventory_availability')
        if not isinstance(inv,dict) or inv.get('complete') is not True:raise ValueError('库存汇总不完整，不能渲染为全量结论')
        lines.append('范围内SKU '+str(inv['sku_count'])+'个；严格低于预警线'+str(inv['below_alert_count'])+'个；达到或低于预警线'+str(inv['at_or_below_alert_count'])+'个。')
        if inv.get('details_truncated'):lines.append('库存明细仅展示前若干条，完整汇总不因此截断。')
        for name,title in [('reservations_to_purchase','预占及补货记录'),('inbound_details','入库记录'),('shipment_line_quantities','订单行发货核对')]:
            if name in results:lines.append(title+'返回'+str(len(results[name].get('entries',[])))+'条；是否完整以结果状态与warnings为准。')
        lines.append('口径：可售=实物-隔离-active实际预占；待补不再次扣减；SKU总量不代表某个仓库或历史余额。')
    elif DOMAIN=='coupon':
        for row in results.get('template_redemption_rates',[]):
            ratio=row['ratio'];value=ratio.get('rate_pct')
            lines.append('模板'+str(row['template_id'])+'累计核销率：'+('无定义（分母为0）' if ratio.get('status')=='undefined' or value is None else str(value)+'%')+'。')
        for name,title in [('after_sales_cases','售后单'),('after_sales_lines','售后明细')]:
            if name in results:lines.append(title+'返回'+str(len(results[name].get('entries',[])))+'条。')
        lines.append('口径：累计核销率不是期间领取cohort核销率；申请、批准、实退分别核对；没有生成事件、修券、退款或通知。')
    if facts['status']=='partial':lines.append('结果为部分数据，不能据此断言全量经营结论。')
    for warning in facts.get('warnings',[]):lines.append('待核实：'+str(warning))
    lines+=['','证据：'+str(len(facts['calls']))+'项底层调用；详见输入facts的calls与results。','本入口仅解释输入事实，不访问平台、不持有调用凭据。']
    return {'status':facts['status'],'domain':DOMAIN,'offline':True,'text':'\n'.join(lines),'source_calls':facts['calls']}
def main():
    parser=argparse.ArgumentParser(description='离线解释业务组合函数返回的数据，不访问平台。')
    group=parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--facts-file');group.add_argument('--facts-base64')
    args=parser.parse_args()
    if args.facts_file:
        with open(args.facts_file,encoding='utf-8') as f:facts=json.load(f)
    else:facts=json.loads(base64.b64decode(args.facts_base64,validate=True).decode('utf-8'))
    print(json.dumps(render(facts),ensure_ascii=False))
if __name__=='__main__':main()
