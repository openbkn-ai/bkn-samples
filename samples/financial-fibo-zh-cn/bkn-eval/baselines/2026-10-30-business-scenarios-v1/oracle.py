#!/usr/bin/env python3
"""Independent raw-CSV oracle for the FIBO business-scenario question set.

Reads only the delivered CSV files and model-contract.json of this package. It does not
import or call the sample's functions, skills or earlier answer sets. Business rules
follow docs/PRD (the business-rules section); money uses Decimal with ROUND_HALF_UP.
The file is identical in the zh-CN and en-US packages: their data differ only in
translated text, so the expected values match except for names.

Writes question-set-v1.yaml (no answers) and answer-set-v1.yaml next to this file.
"""
import csv
import json
from collections import Counter, defaultdict
from decimal import Decimal as D, ROUND_HALF_UP
from pathlib import Path

import yaml

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
LANG = 'zh' if ROOT.name.endswith('zh-cn') else 'en'
TODAY = '2027-02-28'
LOC = json.loads((ROOT / 'model-contract.json').read_text(encoding='utf-8'))['localized_values']
BRANCH = {'normal', 'pending_settlement', 'failed_settlement', 'price_exception', 'issuer_breach', 'counterparty_breach', 'future_limit'}
REV = {v: k for k, v in LOC.items() if k not in BRANCH}   # localized enum -> canonical code


def load(name):
    rows = list(csv.DictReader((ROOT / 'data' / (name + '.csv')).open(encoding='utf-8')))
    return [{k: v if k in ('name', 'branch') else REV.get(v, v) for k, v in r.items()} for r in rows]


def index(name, key):
    return {r[key]: r for r in load(name)}


PF, ACC, ENT = index('portfolios', 'portfolio_id'), index('accounts', 'account_id'), index('legal_entities', 'entity_id')
INS, ORD, TR = index('financial_instruments', 'instrument_id'), index('trade_orders', 'order_id'), index('securities_transactions', 'trade_id')
SI, OPEN, POS = index('settlement_instructions', 'instruction_id'), index('opening_positions', 'opening_id'), index('positions', 'position_id')
PX, FX, VAL = index('market_prices', 'price_id'), index('fx_rates', 'fx_id'), index('valuation_snapshots', 'valuation_id')
LIM, IE = index('mandate_limits', 'limit_id'), index('issuer_exposures', 'exposure_id')
EVENTS, CE, LA, CONTRIB = load('settlement_events'), load('counterparty_exposures'), load('limit_assessments'), load('exposure_contributions')


def q2(x):
    return D(x).quantize(D('0.01'), ROUND_HALF_UP)


def num(x):
    x = D(x)
    return int(x) if x == x.to_integral_value() else float(x)


def portfolio_of_account(account_id):
    return ACC[account_id]['portfolio_id']


# ---- settlement (PRD rules 3-4) --------------------------------------------

def settlement(as_of=TODAY, knowledge=TODAY, view='actual'):
    """Per instruction as of a date: settled so far (incremental events), latest event, status, remaining, overdue."""
    done, last = defaultdict(D), {}
    for e in EVENTS:
        if e['event_date'] <= as_of and e['known_date'] <= knowledge and e['view_kind'] == view:
            i = e['instruction_id']
            done[i] += D(e['settled_quantity'])
            key = (e['event_date'], int(e['event_sequence']))
            if i not in last or key > last[i][0]:
                last[i] = (key, e)
    out = {}
    for i, s in SI.items():
        tr = TR[s['trade_id']]
        o = ORD[tr['order_id']]
        if o['view_kind'] != view or tr['trade_date'] > as_of or tr['known_date'] > knowledge:
            continue
        req, got = D(s['required_quantity']), done.get(i, D(0))
        latest = last.get(i, (None, None))[1]
        if got == req:
            status = 'settled'
        elif latest and latest['event_status'] == 'failed':
            status = 'failed'
        else:
            status = 'partial' if got > 0 else 'pending'
        out[i] = dict(instruction=i, trade=tr['trade_id'], portfolio=portfolio_of_account(o['account_id']), counterparty=o['counterparty_id'],
                      instrument=o['instrument_id'], side=o['side'], due=s['due_date'], remaining=req - got, status=status,
                      overdue=req - got > 0 and s['due_date'] < as_of, reason=latest['failure_reason'] if status == 'failed' else None,
                      trade_date=tr['trade_date'], price=D(tr['execution_price']), currency=tr['currency'])
    return out


OPEN_NOW = [x for x in settlement().values() if x['status'] != 'settled']


def fx_rate(currency, as_of, view='actual'):
    rows = [r for r in FX.values() if r['from_currency'] == currency and r['as_of_date'] == as_of and r['view_kind'] == view]
    assert len(rows) == 1, (currency, as_of)
    return D(rows[0]['rate'])


def receivable_lines(pf, cp, as_of=TODAY, knowledge=TODAY):
    return sorted((x for x in settlement(as_of, knowledge).values()
                   if x['portfolio'] == pf and x['counterparty'] == cp and x['side'] == 'sell' and x['remaining'] > 0),
                  key=lambda x: x['instruction'])


def receivable(pf, cp, as_of=TODAY, knowledge=TODAY):
    """Unsettled SELL receivable, not netted against buys: remaining x price x multiplier x FX, summed, then rounded."""
    return q2(sum((x['remaining'] * x['price'] * D(INS[x['instrument']]['price_multiplier']) * fx_rate(x['currency'], as_of)
                   for x in receivable_lines(pf, cp, as_of, knowledge)), D(0)))


# ---- valuation and exposure (recorded month-end snapshots; PRD rules 5-8) ----

def valuations(pf, as_of=TODAY, view='actual'):
    out = []
    for v in VAL.values():
        p = POS[v['position_id']]
        o = OPEN[p['opening_id']]
        if portfolio_of_account(o['account_id']) == pf and v['as_of_date'] == as_of and v['view_kind'] == view:
            out.append(dict(valuation=v, position=p, instrument=o['instrument_id']))
    return sorted(out, key=lambda r: r['instrument'])


def portfolio_value(pf, as_of=TODAY, view='actual'):
    rows = valuations(pf, as_of, view)
    if any(r['valuation']['valuation_status'] != 'complete' for r in rows):
        return None
    return sum((D(r['valuation']['market_value_base']) for r in rows), D(0))


def assessments(as_of, status=None, measure=None):
    out = []
    for a in LA:
        lim = LIM[a['limit_id']]
        if a['as_of_date'] == as_of and (status is None or a['assessment_status'] == status) and (measure is None or lim['measure'] == measure):
            out.append(dict(a=a, lim=lim, portfolio=lim['portfolio_id'], entity=lim['entity_id']))
    return out


def issuer_amounts(pf, as_of=TODAY):
    """Issuer amount is known only when every valuation of that issuer's holdings is complete (unknown is not zero)."""
    by_issuer = defaultdict(list)
    for r in valuations(pf, as_of):
        by_issuer[INS[r['instrument']]['issuer_id']].append(r)
    return {iss: (sum((D(r['valuation']['market_value_base']) for r in rows), D(0))
                  if all(r['valuation']['valuation_status'] == 'complete' for r in rows) else None)
            for iss, rows in sorted(by_issuer.items())}


# ---- questions ---------------------------------------------------------------------

QUESTIONS = []
ROLE = {'PM': ('投资组合经理', 'Portfolio manager'), 'MO': ('中台运营', 'Middle office'),
        'FA': ('基金会计', 'Fund accountant'), 'RK': ('风控合规', 'Risk and compliance')}
LEVEL = {'basic': ('基础', 'basic'), 'medium': ('中等', 'medium'), 'complex': ('复杂', 'complex')}


def q(qid, scenario, level, role, zh, en, expected, contract_zh, contract_en):
    i = 0 if LANG == 'zh' else 1
    QUESTIONS.append(dict(id=qid, scenario=scenario, difficulty=LEVEL[level][i], role=ROLE[role][i],
                          question=(zh, en)[i], output_contract=(contract_zh, contract_en)[i], expected=expected))


def only(values):
    assert len(values) == 1, values
    return next(iter(values))


def name(entity_id):
    return ENT[entity_id]['name']


def label(code):
    return LOC.get(code, code) if LANG == 'zh' else code


# S01 reference data and portfolios
q('Q-01', 'S01', 'basic', 'PM', '我们现在一共管理多少个投资组合？由多少家资产管理人负责？',
  'How many portfolios do we manage, and how many asset managers run them?',
  dict(portfolios=len(PF), managers=len({p['manager_id'] for p in PF.values()})), '组合数、资产管理人数', 'portfolio count, manager count')
q('Q-02', 'S01', 'basic', 'FA', 'INS-002 这只债券是哪家公司发的？什么时候到期？按什么口径报价？',
  'Who issued bond INS-002, when does it mature, and how is it quoted?',
  dict(issuer_id=INS['INS-002']['issuer_id'], issuer=name(INS['INS-002']['issuer_id']), maturity_date=INS['INS-002']['maturity_date'],
       price_basis=label(INS['INS-002']['price_basis'])), '发行方编号与名称、到期日、报价口径', 'issuer id and name, maturity date, quote basis')
q('Q-03', 'S01', 'basic', 'PM', 'PF-001 是哪家资产管理人在管？基础货币和投资授权是什么？',
  'Which asset manager runs PF-001, and what are its base currency and mandate?',
  dict(manager_id=PF['PF-001']['manager_id'], manager=name(PF['PF-001']['manager_id']), base_currency=PF['PF-001']['base_currency'],
       mandate=label(PF['PF-001']['mandate'])), '管理人编号与名称、基础货币、投资授权', 'manager id and name, base currency, mandate')
holdings = valuations('PF-001')
q('Q-04', 'S01', 'basic', 'PM', 'PF-001 二月底持有几只证券？其中几只是债券？',
  'How many securities does PF-001 hold at the end of February, and how many of them are bonds?',
  dict(securities=len(holdings), bonds=sum(INS[r['instrument']]['asset_class'] == 'bond' for r in holdings)), '证券数、债券数', 'security count, bond count')

# S02 trades and settlement (middle office)
feb = [t for t in TR.values() if t['trade_date'][:7] == '2027-02' and ORD[t['order_id']]['view_kind'] == 'actual']
q('Q-05', 'S02', 'basic', 'MO', '二月份一共成交了多少笔？买入和卖出各多少笔？',
  'How many trades were executed in February, and how many were buys and sells?',
  dict(trades=len(feb), buys=sum(ORD[t['order_id']]['side'] == 'buy' for t in feb), sells=sum(ORD[t['order_id']]['side'] == 'sell' for t in feb)),
  '成交笔数、买入笔数、卖出笔数', 'trade count, buys, sells')
q('Q-06', 'S02', 'basic', 'MO', '到今天为止，还有多少笔结算指令没有交收完？',
  'As of today, how many settlement instructions are not fully settled?',
  dict(instructions=len(OPEN_NOW)), '指令笔数', 'instruction count')
failed = [x for x in OPEN_NOW if x['status'] == 'failed']
q('Q-07', 'S02', 'basic', 'MO', '现在结算失败的指令有多少笔？失败原因各有多少笔？',
  'How many settlement instructions are currently failed, and how many fall under each failure reason?',
  dict(failed=len(failed), reasons={label(k): v for k, v in sorted(Counter(x['reason'] for x in failed).items())}),
  '失败笔数、按原因的笔数', 'failed count, count by reason')
over = [x for x in OPEN_NOW if x['overdue']]
q('Q-08', 'S02', 'medium', 'MO', '没交收完的指令里，有多少笔已经过了应交收日？按失败、部分交收各多少？还没到期的又有多少笔、最早哪天到期？',
  'Of the instructions not fully settled, how many are past their due date, split into failed and partially settled? How many are not yet due, and when is the earliest due date?',
  dict(overdue=len(over), overdue_failed=sum(x['status'] == 'failed' for x in over), overdue_partial=sum(x['status'] == 'partial' for x in over),
       not_due=sum(not x['overdue'] for x in OPEN_NOW), earliest_due=min(x['due'] for x in OPEN_NOW if not x['overdue'])),
  '逾期笔数、其中失败与部分交收、未到期笔数、最早到期日', 'overdue count, of which failed and partial, not-due count, earliest due date')
q('Q-09', 'S02', 'medium', 'MO', '逾期没交收的指令涉及多少家交易对手、多少个组合？',
  'How many counterparties and how many portfolios do the overdue unsettled instructions involve?',
  dict(counterparties=len({x['counterparty'] for x in over}), portfolios=len({x['portfolio'] for x in over})), '交易对手数、组合数', 'counterparty count, portfolio count')
short = sorted({x['portfolio'] for x in failed if x['reason'] == 'insufficient_securities'})
q('Q-10', 'S02', 'medium', 'MO', '因为券不够而交收失败的指令，涉及哪些组合？',
  'Which portfolios have settlements that failed because of insufficient securities?',
  dict(portfolios=short), '完整组合编号清单', 'full list of portfolio ids')
pf19 = sorted((x for x in OPEN_NOW if x['portfolio'] == 'PF-019'), key=lambda x: x['instruction'])
q('Q-11', 'S02', 'medium', 'MO', 'PF-019 还有哪些卖出没交收？各是什么证券、还差多少数量、哪天到期？',
  'Which PF-019 sales are not yet settled? Give the security, remaining quantity and due date for each.',
  dict(instructions=[dict(instruction=x['instruction'], instrument=x['instrument'], remaining=num(x['remaining']), due_date=x['due']) for x in pf19]),
  '完整指令清单（指令、证券、剩余数量、到期日）', 'full list of instructions (instruction, security, remaining quantity, due date)')
pf20 = sorted((x for x in OPEN_NOW if x['portfolio'] == 'PF-020'), key=lambda x: x['instruction'])
q('Q-12', 'S02', 'medium', 'MO', 'PF-020 有哪些卖出只交收了一部分？各还剩多少没交收？',
  'Which PF-020 sales are only partly settled, and how much is still outstanding on each?',
  dict(instructions={x['instruction']: num(x['remaining']) for x in pf20 if x['status'] == 'partial'}), '指令及剩余数量', 'instructions and remaining quantities')

# S03 prices and valuation (fund accountant)
blocked = [v for v in VAL.values() if v['as_of_date'] == TODAY and v['view_kind'] == 'actual' and v['valuation_status'] != 'complete']
q('Q-13', 'S03', 'basic', 'FA', '二月底有多少条持仓估值算不出市值？原因各有多少条？',
  'How many position valuations at the end of February have no market value, and how many fall under each reason?',
  dict(valuations=len(blocked), reasons={label(k): v for k, v in sorted(Counter(v['reason'] for v in blocked).items())}),
  '估值条数、按原因的条数', 'valuation count, count by reason')
eur = [r for r in FX.values() if r['from_currency'] == 'EUR' and r['as_of_date'] == TODAY and r['view_kind'] == 'actual'][0]
q('Q-14', 'S03', 'basic', 'FA', '二月底估值用的欧元兑美元汇率是多少？哪天发布的？',
  'What EUR-to-USD rate is used for the end-of-February valuation, and when was it published?',
  dict(rate=num(eur['rate']), published_date=eur['published_date']), '汇率、发布日期', 'rate, publication date')
px1 = [p for p in PX.values() if p['instrument_id'] == 'INS-001' and p['as_of_date'] == TODAY][0]
q('Q-15', 'S03', 'basic', 'FA', 'INS-001 二月底估值用的价格是多少？哪天的价格？批准了吗？',
  'What price is used to value INS-001 at the end of February, which date is it from, and is it approved?',
  dict(price=num(px1['price']), currency=px1['currency'], price_date=px1['price_date'], approved=px1['approval'] == 'approved'),
  '价格、币种、价格日期、是否已批准', 'price, currency, price date, approved or not')
bad_ins = defaultdict(set)
for v in blocked:
    bad_ins[OPEN[POS[v['position_id']]['opening_id']]['instrument_id']].add(v['reason'])
q('Q-16', 'S03', 'medium', 'FA', '二月底哪些证券的价格不能用来估值？分别是什么问题？',
  'Which securities have no usable price for the end-of-February valuation, and what is wrong with each?',
  dict(securities={k: label(sorted(v)[0]) for k, v in sorted(bad_ins.items())}), '证券编号及问题', 'security ids and the issue')
hit = sorted({portfolio_of_account(OPEN[POS[v['position_id']]['opening_id']]['account_id']) for v in blocked})
q('Q-17', 'S03', 'medium', 'FA', '这些价格问题一共影响了多少个组合的二月底估值？',
  'How many portfolios have an end-of-February valuation affected by these price problems?',
  dict(portfolios=len(hit)), '组合数', 'portfolio count')
q('Q-18', 'S03', 'medium', 'PM', 'PF-001 二月底的组合总市值是多少美元？',
  'What is the total market value of PF-001 at the end of February, in USD?',
  dict(market_value_usd=num(portfolio_value('PF-001'))), '美元市值', 'market value in USD')
r2 = [r for r in valuations('PF-001') if r['instrument'] == 'INS-002'][0]
pr2, fx2 = PX[r2['valuation']['price_id']], FX[r2['valuation']['fx_id']]
local2 = q2(D(r2['position']['trade_basis_quantity']) * D(pr2['price']) * D(INS['INS-002']['price_multiplier']))
q('Q-19', 'S03', 'medium', 'FA', 'PF-001 持有的 INS-002 债券二月底市值是怎么算出来的？给出数量、价格、计价乘数、汇率、本币市值和美元市值。',
  'How is the end-of-February market value of the INS-002 bond held by PF-001 calculated? Give the quantity, price, price multiplier, FX rate, local market value and USD market value.',
  dict(quantity=num(r2['position']['trade_basis_quantity']), price=num(pr2['price']), multiplier=num(INS['INS-002']['price_multiplier']),
       fx_rate=num(fx2['rate']), market_value_local=num(local2), market_value_usd=num(q2(local2 * D(fx2['rate'])))),
  '数量、价格、乘数、汇率、本币市值、美元市值', 'quantity, price, multiplier, FX rate, local and USD market value')
complete_values = {pf: portfolio_value(pf) for pf in PF}
top3 = sorted((pf for pf, v in complete_values.items() if v is not None), key=lambda pf: (-complete_values[pf], pf))[:3]
q('Q-20', 'S03', 'medium', 'PM', '二月底估值完整的组合里，美元市值最大的三个是哪几个？各多少？',
  'Among portfolios whose end-of-February valuation is complete, which three have the largest USD market value, and how much each?',
  dict(portfolios={pf: num(complete_values[pf]) for pf in top3}), '组合编号及美元市值，从大到小', 'portfolio ids and USD market values, largest first')
stale69 = [p for p in PX.values() if p['instrument_id'] == 'INS-069' and p['as_of_date'] == TODAY][0]
q('Q-21', 'S03', 'medium', 'FA', 'INS-069 二月底为什么不能用来估值？最近那笔已批准价格是哪天的、多少钱？',
  'Why can INS-069 not be used for the end-of-February valuation? What date and price is its latest approved price?',
  dict(issue=label('stale'), latest_price_date=stale69['price_date'], latest_price=num(stale69['price']), currency=stale69['currency']),
  '原因、最近价格日期、价格、币种', 'issue, latest price date, price, currency')

# S04 positions and P&L
acc1 = sorted(a for a, r in ACC.items() if r['portfolio_id'] == 'PF-001')[0]
pos_by = {(OPEN[p['opening_id']]['account_id'], OPEN[p['opening_id']]['instrument_id'], p['as_of_date'], p['view_kind']): p for p in POS.values()}
jan, febp = pos_by[(acc1, 'INS-001', '2027-01-31', 'actual')], pos_by[(acc1, 'INS-001', TODAY, 'actual')]
buys = [t for t in TR.values() if ORD[t['order_id']]['account_id'] == acc1 and ORD[t['order_id']]['instrument_id'] == 'INS-001' and t['trade_date'][:7] == '2027-02']
q('Q-22', 'S04', 'medium', 'FA', 'PF-001 持有的 INS-001 二月底持仓成本比一月底变了多少？是哪笔交易带来的？',
  'How much did the cost of PF-001\'s INS-001 holding change from end of January to end of February, and which trade caused it?',
  dict(cost_jan=num(jan['cost_amount']), cost_feb=num(febp['cost_amount']), change=num(D(febp['cost_amount']) - D(jan['cost_amount'])),
       trades=[t['trade_id'] for t in buys]), '一月底成本、二月底成本、变化、交易编号', 'January cost, February cost, change, trade ids')
pnl = {(OPEN[p['opening_id']]['instrument_id']): (D(p['realized_pnl']), p['currency']) for p in POS.values()
       if OPEN[p['opening_id']]['account_id'] == acc1 and p['as_of_date'] == TODAY and p['view_kind'] == 'actual' and D(p['realized_pnl']) != 0}
q('Q-23', 'S04', 'medium', 'FA', 'PF-001 二月份哪些持仓有已实现损益？各多少（按本币）？',
  'Which PF-001 holdings have realized P&L in February, and how much each, in local currency?',
  dict(positions={k: dict(realized_pnl=num(v[0]), currency=v[1]) for k, v in sorted(pnl.items())}), '证券及本币已实现损益', 'securities and realized P&L in local currency')
acc29 = sorted(a for a, r in ACC.items() if r['portfolio_id'] == 'PF-029')[0]
unsettled29 = {OPEN[p['opening_id']]['instrument_id']: num(p['unsettled_delta']) for p in POS.values()
               if OPEN[p['opening_id']]['account_id'] == acc29 and p['as_of_date'] == TODAY and p['view_kind'] == 'actual' and D(p['unsettled_delta']) != 0}
q('Q-24', 'S04', 'complex', 'MO', 'PF-029 的交收失败让二月底哪些持仓的交易口径和已交收口径对不上？各差多少？',
  'Because of PF-029\'s failed settlements, which holdings at the end of February differ between trade-date and settled quantity, and by how much?',
  dict(positions=dict(sorted(unsettled29.items()))), '证券及数量差（交易口径减已交收口径）', 'securities and quantity difference (trade basis minus settled)')

# S05 issuer concentration (risk)
iss41 = [r for r in IE.values() if r['portfolio_id'] == 'PF-041' and r['as_of_date'] == TODAY][0:]
top41 = max(iss41, key=lambda r: D(r['ratio']))
lim41 = [a for a in assessments(TODAY, measure='issuer_ratio') if a['portfolio'] == 'PF-041' and a['entity'] == top41['issuer_id']][0]
q('Q-25', 'S05', 'medium', 'RK', 'PF-041 二月底对哪家发行方最集中？占比多少？限额是多少？',
  'Which issuer is PF-041 most concentrated in at the end of February, at what share, and what is the limit?',
  dict(issuer_id=top41['issuer_id'], issuer=name(top41['issuer_id']), ratio=num(top41['ratio']), limit=num(lim41['lim']['threshold'])),
  '发行方编号与名称、占比、限额', 'issuer id and name, share, limit')
br_iss = sorted(((a['portfolio'], a['entity'], D(a['a']['excess_value'])) for a in assessments(TODAY, 'breach', 'issuer_ratio')))
q('Q-26', 'S05', 'medium', 'RK', '二月底有多少个组合的发行方集中度超限？超得最多的是哪个组合、哪家发行方、超出多少？',
  'How many portfolios breach an issuer concentration limit at the end of February? Which portfolio and issuer exceed it the most, and by how much?',
  dict(portfolios=len({p for p, _, _ in br_iss}), worst_portfolio=max(br_iss, key=lambda x: (x[2], x[0]))[0],
       worst_issuer=max(br_iss, key=lambda x: (x[2], x[0]))[1], excess=num(max(x[2] for x in br_iss))),
  '超限组合数、超出最多的组合与发行方、超出比例', 'breaching portfolio count, worst portfolio and issuer, excess share')
unk = assessments(TODAY, 'unknown', 'issuer_ratio')
q('Q-27', 'S05', 'medium', 'RK', '二月底有多少个组合的发行方集中度判断不了？为什么？',
  'How many portfolios cannot be judged on issuer concentration at the end of February, and why?',
  dict(portfolios=len({a['portfolio'] for a in unk}), all_have_blocked_valuation=sorted({a['portfolio'] for a in unk}) == hit),
  '组合数、是否都因组合内有估值受阻的证券', 'portfolio count, whether all are caused by a blocked valuation in the portfolio')
contrib41 = {}
for c in CONTRIB:
    if c['exposure_id'] == top41['exposure_id']:
        contrib41[OPEN[POS[VAL[c['valuation_id']]['position_id']]['opening_id']]['instrument_id']] = num(c['contribution_amount'])
q('Q-28', 'S05', 'complex', 'RK', 'PF-041 对 ISS-041 超限，是由哪些持仓构成的？各多少美元？组合总额是多少？',
  'PF-041 breaches its ISS-041 limit. Which holdings make up that exposure, how much is each in USD, and what is the portfolio total?',
  dict(holdings=dict(sorted(contrib41.items())), exposure_usd=num(top41['exposure_amount']), portfolio_total_usd=num(top41['denominator_amount']),
       ratio=num(top41['ratio'])), '持仓证券及美元金额、发行方合计、组合总额、占比', 'securities and USD amounts, issuer total, portfolio total, share')
known35 = issuer_amounts('PF-035')
bad35 = [r for r in valuations('PF-035') if r['valuation']['valuation_status'] != 'complete'][0]
q('Q-29', 'S05', 'complex', 'RK', 'PF-035 二月底的发行方集中度为什么判断不了？哪些发行方的美元金额仍然能确认、各多少？',
  'Why can PF-035\'s issuer concentration not be judged at the end of February? Which issuers\' USD amounts can still be confirmed, and how much each?',
  dict(blocked_security=bad35['instrument'], reason=label(bad35['valuation']['reason']), unknown_issuer=INS[bad35['instrument']]['issuer_id'],
       known_issuers={k: num(v) for k, v in known35.items() if v is not None}), '受阻证券、原因、金额未知的发行方、可确认的发行方金额',
  'blocked security, reason, issuer with unknown amount, confirmed issuer amounts')

# S06 counterparty receivables
br_cp = assessments(TODAY, 'breach', 'receivable_amount')
q('Q-30', 'S06', 'basic', 'RK', '二月底有多少个组合的交易对手未结算卖出应收超限？',
  'How many portfolios breach a counterparty unsettled-sale receivable limit at the end of February?',
  dict(portfolios=len({a['portfolio'] for a in br_cp})), '组合数', 'portfolio count')
cp_total = defaultdict(D)
for c in CE:
    if c['as_of_date'] == TODAY and c['view_kind'] == 'actual':
        cp_total[c['counterparty_id']] += D(c['unsettled_receivable'])
cp_top = max(cp_total, key=lambda k: (cp_total[k], k))
q('Q-31', 'S06', 'medium', 'RK', '二月底哪家交易对手欠我们的未结算卖出款最多？合计多少美元？',
  'Which counterparty owes us the most on unsettled sales at the end of February, and how much in total in USD?',
  dict(counterparty_id=cp_top, counterparty=name(cp_top), receivable_usd=num(cp_total[cp_top])), '交易对手编号与名称、美元金额', 'counterparty id and name, USD amount')
l46 = [a for a in br_cp if a['portfolio'] == 'PF-046'][0]
lines46 = receivable_lines('PF-046', 'CP-046')
q('Q-32', 'S06', 'complex', 'RK', 'PF-046 对 CP-046 的未结算卖出应收超限了，是哪些卖出没交收造成的？各剩多少数量？合计多少美元、超出多少？',
  'PF-046\'s unsettled-sale receivable from CP-046 is over its limit. Which unsettled sales cause it, how much quantity remains on each, and what are the USD total and the excess?',
  dict(instructions={x['instruction']: num(x['remaining']) for x in lines46}, receivable_usd=num(receivable('PF-046', 'CP-046')),
       limit_usd=num(l46['lim']['threshold']), excess_usd=num(l46['a']['excess_value'])),
  '指令及剩余数量、应收合计、限额、超出金额', 'instructions and remaining quantities, receivable total, limit, excess')
q('Q-33', 'S06', 'complex', 'RK', 'PF-046 对 CP-046 的应收里，有没有用它同期的买入来抵减？如果那几笔失败的卖出今天全部交收完，还会超限吗？',
  'Is PF-046\'s receivable from CP-046 reduced by its purchases from the same counterparty? If the failed sales all settled today, would it still breach?',
  dict(netted_with_buys=False, breach_if_settled=False), '是否抵减、交收后是否仍超限', 'netted or not, breach after settlement or not')

# S07 limits and plans
future = sorted((l for l in LIM.values() if l['effective_from_date'] > '2026-11-01'), key=lambda l: l['limit_id'])
q('Q-34', 'S07', 'basic', 'RK', '有多少条限额是还没生效、之后才开始生效的？涉及多少个组合？',
  'How many limits only take effect later, and how many portfolios do they cover?',
  dict(limits=len(future), portfolios=len({l['portfolio_id'] for l in future})), '限额条数、组合数', 'limit count, portfolio count')
f49 = sorted((l for l in future if l['portfolio_id'] == 'PF-049'), key=lambda l: l['entity_id'])
old49 = [l for l in LIM.values() if l['portfolio_id'] == 'PF-049' and l['entity_id'] == f49[0]['entity_id'] and l['effective_from_date'] <= TODAY][0]
q('Q-35', 'S07', 'medium', 'RK', 'PF-049 的发行方限额接下来会怎么变？什么时候生效？今天用的还是哪个限额？',
  'How will PF-049\'s issuer limits change, from when, and which limit applies today?',
  dict(new_limit=num(f49[0]['threshold']), effective_from=f49[0]['effective_from_date'], issuers=[l['entity_id'] for l in f49], current_limit=num(old49['threshold'])),
  '新限额、生效日、涉及发行方、当前限额', 'new limit, effective date, issuers, current limit')
mar_br = {a['portfolio'] for a in assessments('2027-03-31', 'breach')}
feb_br = {a['portfolio'] for a in assessments(TODAY, 'breach')}
q('Q-36', 'S07', 'complex', 'PM', '按三月计划，哪些组合会出现超限而二月实际并没有超限？',
  'Under the March plan, which portfolios will breach a limit that they do not breach in February actuals?',
  dict(portfolios=sorted(mar_br - feb_br)), '完整组合编号清单', 'full list of portfolio ids')
mar50 = sorted((a for a in assessments('2027-03-31', 'breach') if a['portfolio'] == 'PF-050'), key=lambda a: a['entity'])
feb50 = {a['entity']: a for a in assessments(TODAY) if a['portfolio'] == 'PF-050'}
q('Q-37', 'S07', 'complex', 'PM', 'PF-050 三月计划里哪些发行方会超限？各超出多少？它们二月实际的占比和适用限额是多少？',
  'Which issuers will PF-050 breach under the March plan, and by how much? What are their February actual shares and the limits applying then?',
  dict(march={a['entity']: dict(share=num(a['a']['observed_value']), limit=num(a['lim']['threshold']), excess=num(a['a']['excess_value'])) for a in mar50},
       february={a['entity']: dict(share=num(feb50[a['entity']]['a']['observed_value']), limit=num(feb50[a['entity']]['lim']['threshold'])) for a in mar50}),
  '各发行方三月占比、限额、超出；二月占比与限额', 'per issuer: March share, limit, excess; February share and limit')
cp_mar = {a['portfolio'] for a in assessments('2027-03-31', 'breach', 'receivable_amount')}
cp_feb = {a['portfolio'] for a in assessments(TODAY, 'breach', 'receivable_amount')}
q('Q-38', 'S07', 'complex', 'RK', '二月实际对手应收超限的组合，到三月计划里还有哪些仍然超限？',
  'Of the portfolios over a counterparty receivable limit in February actuals, which are still over it under the March plan?',
  dict(portfolios=sorted(cp_mar & cp_feb)), '完整组合编号清单', 'full list of portfolio ids')
mv50 = {d: portfolio_value('PF-050', d, v) for d, v in ((TODAY, 'actual'), ('2027-03-31', 'planned'))}
q('Q-39', 'S07', 'medium', 'PM', '按三月计划，PF-050 月底市值会是多少美元？比二月实际多多少？',
  'Under the March plan, what will PF-050\'s month-end market value be in USD, and how much higher is it than February actual?',
  dict(march_plan_usd=num(mv50['2027-03-31']), february_actual_usd=num(mv50[TODAY]), change=num(mv50['2027-03-31'] - mv50[TODAY])),
  '三月计划市值、二月实际市值、变化', 'March plan value, February actual value, change')

# S08 as-of reconstruction and trace
s15 = settlement('2027-02-15', '2027-02-15')
pf29 = sorted((x for x in s15.values() if x['portfolio'] == 'PF-029' and x['status'] != 'settled'), key=lambda x: x['instruction'])
q('Q-40', 'S08', 'complex', 'MO', '站在 2 月 15 日、只用当天已经知道的信息，PF-029 有哪些指令没交收完？哪些已经逾期、哪些已经失败？',
  'Standing on February 15 and using only what was known that day, which PF-029 instructions were not fully settled? Which were overdue and which had failed?',
  dict(instructions={x['instruction']: dict(status=label(x['status']), overdue=x['overdue']) for x in pf29}), '指令及状态、是否逾期', 'instructions with status and overdue flag')
s20 = settlement('2027-02-20', '2027-02-20')
pf20b = {x['instruction']: x for x in s20.values() if x['portfolio'] == 'PF-020' and x['status'] != 'settled'}
q('Q-41', 'S08', 'complex', 'MO', '2 月 20 日那天看，PF-020 还有哪些卖出没交收完、各剩多少？到今天又多交收了多少？',
  'As seen on February 20, which PF-020 sales were not fully settled and how much remained on each? How much more has settled since then?',
  dict(feb20={k: num(v['remaining']) for k, v in sorted(pf20b.items())},
       settled_since={k: num(v['remaining'] - (next((x['remaining'] for x in OPEN_NOW if x['instruction'] == k), D(0)))) for k, v in sorted(pf20b.items())}),
  '2 月 20 日各指令剩余数量、此后新交收数量', 'remaining per instruction on Feb 20, quantity settled since')
s15all = Counter((x['status'], x['overdue']) for x in s15.values() if x['status'] != 'settled')
q('Q-42', 'S08', 'complex', 'MO', '如果按 2 月 15 日当天掌握的信息，全公司有多少笔指令没交收完？其中多少笔已经失败？',
  'Based on what was known on February 15, how many instructions across the company were not fully settled, and how many had failed?',
  dict(instructions=sum(s15all.values()), failed=sum(v for (st, _), v in s15all.items() if st == 'failed')), '未完成笔数、失败笔数', 'unsettled count, failed count')
r29 = receivable('PF-029', 'CP-029', '2027-02-15', '2027-02-15')
q('Q-43', 'S08', 'complex', 'RK', '按 2 月 15 日掌握的信息，PF-029 对 CP-029 的未结算卖出应收是多少美元？今天又是多少？',
  'Based on what was known on February 15, what was PF-029\'s unsettled-sale receivable from CP-029 in USD, and what is it today?',
  dict(feb15_usd=num(r29), today_usd=num(receivable('PF-029', 'CP-029'))), '2 月 15 日应收、今天应收', 'receivable on Feb 15, receivable today')
trace = [x for x in failed if x['portfolio'] == 'PF-029']
iss29 = sorted({INS[x['instrument']]['issuer_id'] for x in trace})
q('Q-44', 'S08', 'complex', 'RK', 'PF-029 交收失败的卖出涉及哪些发行方的证券？这些失败加起来让对 CP-029 的应收是多少美元？',
  'Which issuers\' securities are in PF-029\'s failed sales, and what receivable from CP-029 do these failures add up to in USD?',
  dict(issuers=iss29, receivable_usd=num(receivable('PF-029', 'CP-029'))), '发行方清单、应收金额', 'issuer list, receivable amount')
pf35_unknown = name(INS[bad35['instrument']]['issuer_id'])
q('Q-45', 'S08', 'complex', 'FA', 'PF-035 估值受阻的那只证券属于哪家发行方？如果这只证券有了合格价格，组合里还有别的估值缺口吗？',
  'Which issuer does PF-035\'s blocked security belong to? If it got an eligible price, would any other valuation gap remain in the portfolio?',
  dict(security=bad35['instrument'], issuer_id=INS[bad35['instrument']]['issuer_id'], issuer=pf35_unknown,
       other_gaps=sum(1 for r in valuations('PF-035') if r['valuation']['valuation_status'] != 'complete') - 1), '证券、发行方、其余缺口数', 'security, issuer, remaining gaps')
q('Q-46', 'S08', 'complex', 'RK', 'PF-041 对 ISS-041 的集中度从十一月到二月每个月底各是多少？哪个月开始超限？',
  'What was PF-041\'s concentration in ISS-041 at each month end from November to February, and from which month was it over the limit?',
  dict(shares={a['a']['as_of_date']: num(a['a']['observed_value']) for a in sorted((x for d in ('2026-11-30', '2026-12-31', '2027-01-31', TODAY) for x in assessments(d)
                                                                                     if x['portfolio'] == 'PF-041' and x['entity'] == 'ISS-041'), key=lambda x: x['a']['as_of_date'])},
       first_breach=min(a['a']['as_of_date'] for d in ('2026-11-30', '2026-12-31', '2027-01-31', TODAY) for a in assessments(d, 'breach') if a['portfolio'] == 'PF-041')),
  '各月底占比、开始超限的月份', 'share at each month end, first breaching month')

# month-end reconciliation (S04, complex)
def cohort(pf, month):
    out = defaultdict(lambda: dict(signed_gross=D(0), open_sell_notional=D(0)))
    status = settlement()
    for t in TR.values():
        o = ORD[t['order_id']]
        if portfolio_of_account(o['account_id']) != pf or t['trade_date'][:7] != month or o['view_kind'] != 'actual':
            continue
        g = D(t['gross_amount'])
        out[t['currency']]['signed_gross'] += g if o['side'] == 'buy' else -g
        if o['side'] == 'sell':
            rem = sum((x['remaining'] for x in status.values() if x['trade'] == t['trade_id']), D(0))
            out[t['currency']]['open_sell_notional'] += rem * D(t['execution_price']) * D(INS[o['instrument_id']]['price_multiplier'])
    return {c: dict(signed_gross=num(v['signed_gross']), open_sell_notional=num(q2(v['open_sell_notional']))) for c, v in sorted(out.items())}
q('Q-47', 'S04', 'complex', 'FA', '二月月结时，PF-046 二月份的成交按币种，买卖相抵后的成交总额各是多少？还有多少卖出名义金额没交收？',
  'For month-end close, what is PF-046\'s February traded amount by currency with buys positive and sells negative, and how much sale notional is still unsettled?',
  dict(currencies=cohort('PF-046', '2027-02')), '各币种带符号成交总额、未交收卖出名义金额（本币）', 'per currency: signed traded amount and unsettled sale notional (local currency)')
q('Q-48', 'S06', 'medium', 'RK', 'PF-019 对 CP-019 现在的未结算卖出应收是多少美元？这些卖出都还没到期吗？',
  'What is PF-019\'s unsettled-sale receivable from CP-019 now in USD, and are all of those sales still not due?',
  dict(receivable_usd=num(receivable('PF-019', 'CP-019')), all_not_due=all(not x['overdue'] for x in receivable_lines('PF-019', 'CP-019'))),
  '应收金额、是否全部未到期', 'receivable amount, all not yet due or not')
q('Q-49', 'S03', 'complex', 'FA', 'PF-020 二月底哪只证券估值受阻？原因是什么？组合里其他证券的美元市值合计是多少？',
  'Which PF-020 security has a blocked valuation at the end of February, why, and what is the total USD market value of its other securities?',
  dict(security=[r['instrument'] for r in valuations('PF-020') if r['valuation']['valuation_status'] != 'complete'][0],
       reason=label([r['valuation']['reason'] for r in valuations('PF-020') if r['valuation']['valuation_status'] != 'complete'][0]),
       others_usd=num(sum((D(r['valuation']['market_value_base']) for r in valuations('PF-020') if r['valuation']['valuation_status'] == 'complete'), D(0)))),
  '证券、原因、其余证券美元市值合计', 'security, reason, USD total of the other securities')
q('Q-50', 'S07', 'complex', 'RK', '2 月 28 日才批准的新限额里，有没有今天就该按新限额评估的？PF-049 今天的集中度按适用限额判断是什么结论？',
  'Among the new limits approved on February 28, should any already be applied today? What is PF-049\'s concentration verdict today under the applicable limits?',
  dict(apply_today=False, pf049_today=label(only({a['a']['assessment_status'] for a in assessments(TODAY, measure='issuer_ratio') if a['portfolio'] == 'PF-049'}))),
  '是否今天适用、PF-049 今天结论', 'applies today or not, PF-049 verdict today')


def main():
    assert len(QUESTIONS) == 50 and len({x['id'] for x in QUESTIONS}) == 50
    meta = dict(schema_version='1.0', set_id='fibo-business-scenarios-v1', business_date=TODAY, prd='docs/PRD.md')
    dump = lambda data: yaml.safe_dump(data, allow_unicode=True, sort_keys=False, width=200)
    questions = [{k: v for k, v in x.items() if k != 'expected'} for x in QUESTIONS]
    answers = [dict(id=x['id'], question=x['question'], expected=x['expected']) for x in QUESTIONS]
    (HERE / 'question-set-v1.yaml').write_text(dump(dict(meta, audience='evaluated_agent', answer_set_access='forbidden', questions=questions)), encoding='utf-8')
    (HERE / 'answer-set-v1.yaml').write_text(dump(dict(meta, generation_method='independent raw CSV Decimal oracle (oracle.py)', answers=answers)), encoding='utf-8')
    print(len(QUESTIONS), Counter(x['difficulty'] for x in QUESTIONS), Counter(x['role'] for x in QUESTIONS))


if __name__ == '__main__':
    main()
