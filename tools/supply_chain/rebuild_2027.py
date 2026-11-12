#!/usr/bin/env python3
"""Rebuild the supply-chain sample data for business date 2027-02-25 (kit-schedule edition).

Reads the 0.1.20 / 0.1.15 CSVs from git (``SOURCE_COMMIT``) so a rerun gives the same files, then:

1. shifts every date, datetime and date-bearing document number six months (order is kept);
2. spreads the open demand forecasts over 2027-03..08 (one delivery date per bill) and keeps four
   single-line bills overdue;
3. reconciles the documents: production orders link to the forecasts they serve, every open forecast
   line has a make MRP line, purchase orders arrive lead time after they were placed (closed lines
   on or before the business date, most open lines after it), signed backlog falls due around the
   business date;
4. adds production lines (factories as parent rows), line stoppages and the kit-schedule plan seed.

The Chinese sample is computed; the English sample receives the same changes, with text values
translated through the pairs the two source files already share.

Run from the repository root: ``python3 tools/supply_chain/rebuild_2027.py``.
"""

from __future__ import annotations

import calendar
import csv
import hashlib
import importlib
import io
import json
import re
import subprocess
import sys
from collections import Counter, defaultdict
from datetime import date, datetime, timedelta
from decimal import Decimal as D
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SOURCE_COMMIT = "7572f8c"
BUSINESS_DATE = date(2027, 2, 25)
BD = BUSINESS_DATE.isoformat()
SAMPLES = {"zh": ROOT / "samples" / "supply_ontology_hand", "en": ROOT / "samples" / "supply_ontology_en"}
TABLES = ["customer_entity", "erp_material", "erp_material_bom", "erp_mds_forecast", "erp_mrp_plan_order",
          "erp_production_work_order", "erp_purchase_order", "erp_purchase_request", "erp_real_time_inventory",
          "erp_supplier", "hd_product_view", "sales_order"]
NEW_TABLES = ["production_line", "line_stoppage"]
SEED = "kit_schedule_plan"


# ---------------------------------------------------------------- dates ----

def add_months(day: date, months: int) -> date:
    month = day.month - 1 + months
    year, month = day.year + month // 12, month % 12 + 1
    return date(year, month, min(day.day, calendar.monthrange(year, month)[1]))


DATE = re.compile(r"^(\d{4})-(\d{2})-(\d{2})(.*)$")
NUMBER = re.compile(r"(YCD|JHJY-|MRP-|HDKJ-|KSHA-)(20\d{6})|(CGSQ-|CGDD-)(\d{6})(?=-)")


def shift_value(value: str) -> str:
    match = DATE.match(value)
    if match and len(value) in (10, 19):
        moved = add_months(date(int(match[1]), int(match[2]), int(match[3])), 6)
        return moved.isoformat() + match[4]

    def number(m: re.Match) -> str:
        if m[1]:
            moved = add_months(datetime.strptime(m[2], "%Y%m%d").date(), 6)
            return m[1] + moved.strftime("%Y%m%d")
        moved = add_months(datetime.strptime(m[4], "%y%m%d").date(), 6)
        return m[3] + moved.strftime("%y%m%d")
    return NUMBER.sub(number, value)


def d(value: str) -> date:
    return date.fromisoformat(value[:10])


def plus(day: str | date, days: int) -> str:
    return ((d(day) if isinstance(day, str) else day) + timedelta(days=days)).isoformat()


def stable(*parts: object) -> int:
    return int(hashlib.sha256("|".join(map(str, parts)).encode()).hexdigest()[:8], 16)


def qty(value: D) -> str:
    return f"{value:.6f}"


# ------------------------------------------------------------------ io ----

def read_source(language: str, table: str) -> tuple[list[str], list[dict[str, str]]]:
    path = SAMPLES[language].relative_to(ROOT) / "data" / f"{table}.csv"
    raw = subprocess.check_output(["git", "-C", str(ROOT), "show", f"{SOURCE_COMMIT}:{path.as_posix()}"]).decode("utf-8")
    reader = csv.DictReader(io.StringIO(raw))
    return list(reader.fieldnames or []), list(reader)


def write_csv(path: Path, header: list[str], rows: list[dict[str, str]]) -> None:
    out = io.StringIO()
    writer = csv.writer(out)
    writer.writerow(header)
    writer.writerows([[row.get(column, "") for column in header] for row in rows])
    path.write_bytes(out.getvalue().encode("utf-8"))


# ------------------------------------------------------------- business ----

LINE_OF_PRODUCT_LINE = {"无人机": "L-SZ-UAV", "无人车": "L-SZ-UGV", "智能播种": "L-SZ-UGV", "监测终端": "L-SZ-ELE",
                        "智能大屏": "L-SZ-ELE", "自动驾驶": "L-UR-AD", "智能定位": "L-UR-NAV"}
# Days to assemble one batch; the source carried 1 day for every product.
PRODUCTION_LEAD = {"无人机": 6, "无人车": 8, "智能播种": 4, "监测终端": 3, "智能大屏": 3, "自动驾驶": 4, "智能定位": 3}
LINES = [
    # code, zh name, en name, kind, parent, factory zh, factory en, max parallel, product lines zh, product lines en
    ("F-SZ", "苏州工厂", "Suzhou Plant", "工厂", "", "苏州工厂", "Suzhou Plant", "", "", ""),
    ("F-UR", "乌鲁木齐工厂", "Urumqi Plant", "工厂", "", "乌鲁木齐工厂", "Urumqi Plant", "", "", ""),
    ("L-SZ-UAV", "无人机总装线", "UAV assembly line", "产线", "F-SZ", "苏州工厂", "Suzhou Plant", "3", "无人机", "Drones"),
    ("L-SZ-UGV", "无人车与播种装配线", "Unmanned vehicle and seeding line", "产线", "F-SZ", "苏州工厂", "Suzhou Plant", "2",
     "无人车、智能播种", "Unmanned Vehicles, Smart Seeding"),
    ("L-SZ-ELE", "电子终端线", "Electronics terminal line", "产线", "F-SZ", "苏州工厂", "Suzhou Plant", "2",
     "监测终端、智能大屏", "Monitoring Devices, Smart Displays"),
    ("L-UR-AD", "自动驾驶总装线", "Autopilot assembly line", "产线", "F-UR", "乌鲁木齐工厂", "Urumqi Plant", "2", "自动驾驶", "Autonomous Driving"),
    ("L-UR-NAV", "车载终端线", "Vehicle terminal line", "产线", "F-UR", "乌鲁木齐工厂", "Urumqi Plant", "3", "智能定位", "Smart Positioning"),
]
STOPPAGES = [
    # id, resource, kind, start, end, zh reason, en reason
    ("ST-2703-01", "L-SZ-UAV", "产线", "2027-03-22 08:00:00", "2027-03-24 20:00:00", "总装工装年度校准", "Annual calibration of assembly fixtures"),
    ("ST-2704-01", "F-SZ", "工厂", "2027-04-09 00:00:00", "2027-04-11 23:59:59", "园区配电改造停电", "Site power distribution upgrade"),
    ("ST-2704-02", "L-UR-AD", "产线", "2027-04-19 08:00:00", "2027-04-21 20:00:00", "产线节拍改造", "Line takt-time retrofit"),
    ("ST-2705-01", "F-UR", "工厂", "2027-05-01 00:00:00", "2027-05-05 23:59:59", "劳动节停产", "Labour Day shutdown"),
    ("ST-2705-02", "L-SZ-ELE", "产线", "2027-05-17 08:00:00", "2027-05-18 20:00:00", "回流焊设备检修", "Reflow oven maintenance"),
]
# Open bills (source numbers): four single-line bills stay overdue; the rest roll over 2027-03..08, near-term first.
_DELIVERY = {
    "YCD2026011200000040": "2027-01-15", "YCD2026010700000039": "2027-01-31",
    "YCD2026020500000045": "2027-02-10", "YCD2026022800000048": "2027-02-20",
    "YCD2026040200000060": "2027-03-10", "YCD2026051400000075": "2027-03-15", "YCD2026040800000069": "2027-03-20",
    "YCD2026040200000061": "2027-03-31",
    "YCD2026030400000052": "2027-04-10", "YCD2026042100000073": "2027-04-15", "YCD2026052800000088": "2027-04-20",
    "YCD2026031600000057": "2027-04-30",
    "YCD2026040200000067": "2027-05-10", "YCD2026040200000062": "2027-05-20", "YCD2026040900000071": "2027-05-31",
    "YCD2026040200000068": "2027-06-10", "YCD2026040200000063": "2027-06-20", "YCD2026060300000090": "2027-06-30",
    "YCD2026040900000070": "2027-07-10", "YCD2026040200000064": "2027-07-20", "YCD2026050700000074": "2027-07-31",
    "YCD2026071700000091": "2027-08-10", "YCD2026040200000065": "2027-08-15", "YCD2026081500000001": "2027-08-20",
    "YCD2026081500000002": "2027-08-25", "YCD2026081500000003": "2027-08-31",
}
# Open production orders that serve near-term demand (source number -> source bill, start offset from the
# business date, days). The rest of the source's open orders were stale and are closed as finished.
_OPEN_WORK = {
    "HDKJ-20260413-003": ("YCD2026051400000075", -9, 12),    # 367-000131
    "HDKJ-20260715-005": ("YCD2026051400000075", -6, 10),    # 367-000130, partly done
    "KSHA-20260717-001": ("YCD2026040200000060", -4, 7),     # U00-000080, partly done
    "KSHA-20260717-003": ("YCD2026040200000060", -2, 5),     # U00-000170
    "HDKJ-20260720-024": ("YCD2026051400000075", -3, 8),     # 367-000097, partly done
    "HDKJ-20260724-002": ("YCD2026052800000088", -1, 9),     # 734-000003
    "HDKJ-20260724-005": ("YCD2026040800000069", -5, 9),     # 734-000001
    "KSHA-20260728-002": ("YCD2026051400000075", -1, 8),     # 367-000130
}
# Kit-schedule history installed with the sample besides the confirmed plans of orders in production
# (those were kitted when they were confirmed and have since drawn their materials). The two confirmed
# U00-000080 plans are not in production yet: both are kitted only by open PO 994-000328 due 2027-03-11,
# so moving that delivery shows confirmed plans turning short.
_SCHEDULED = [
    # source bill, product ('' = whole bill), line, start, finish, confirmed
    ("YCD2026030400000052", "", "L-SZ-UGV", "2027-03-29", "2027-04-05", False),
    ("YCD2026042100000073", "P61-000331", "L-SZ-UGV", "2027-04-12", "2027-04-14", False),
    ("YCD2026031600000057", "382-000005", "L-UR-AD", "2027-03-08", "2027-03-12", False),
    ("YCD2026040200000061", "U00-000159", "L-UR-NAV", "2027-03-15", "2027-03-18", False),
    ("YCD2026040200000061", "U00-000080", "L-UR-NAV", "2027-03-22", "2027-03-26", True),
    ("YCD2026040200000062", "U00-000080", "L-UR-NAV", "2027-04-19", "2027-04-22", True),
]
DELIVERY = {shift_value(k): v for k, v in _DELIVERY.items()}
OPEN_WORK = {shift_value(k): (shift_value(b), o, n) for k, (b, o, n) in _OPEN_WORK.items()}
SCHEDULED = [(shift_value(b), *rest) for b, *rest in _SCHEDULED]

def main() -> int:
    source = {lang: {t: read_source(lang, t) for t in TABLES} for lang in SAMPLES}
    for t in TABLES:
        assert [r[next(iter(r))] for r in source["zh"][t][1]] == [r[next(iter(r))] for r in source["en"][t][1]], t
    headers = {t: source["zh"][t][0] for t in TABLES}
    zh = {t: [{k: shift_value(v or "") for k, v in row.items()} for row in source["zh"][t][1]] for t in TABLES}
    log: list[str] = []

    material = {r["material_code"]: r for r in zh["erp_material"]}
    products = {r["material_code"]: r for r in zh["hd_product_view"]}
    for code, row in products.items():
        row["line_code"] = LINE_OF_PRODUCT_LINE[row["huid_productline_name"]]
        material[code]["product_fixedleadtime"] = f"{PRODUCTION_LEAD[row['huid_productline_name']]:.2f}"
    headers["hd_product_view"] = [*headers["hd_product_view"], "line_code"]
    lead_of = lambda code: PRODUCTION_LEAD[products[code]["huid_productline_name"]]

    # ---- forecasts -----------------------------------------------------
    forecasts = zh["erp_mds_forecast"]
    # Three lines the source appended for function tests get regular IDs and a regular planner.
    next_id = max(int(r["id"]) for r in forecasts if r["id"].isdigit())
    for row in forecasts:
        if not row["id"].isdigit():
            next_id += 1
            row["id"] = f"{next_id:010d}"
            row["creator_name"] = row["auditor_name"] = "朱杰倩"
    assert len({r["id"] for r in forecasts}) == len(forecasts)
    open_bills = sorted({r["billno"] for r in forecasts if r["closestatus_title"] == "正常"})
    assert set(open_bills) == set(DELIVERY), sorted(set(open_bills) ^ set(DELIVERY))
    for row in forecasts:
        if row["closestatus_title"] != "正常":
            assert row["enddate"] < BD
            continue
        # startdate is the delivery date (预测交货日期); enddate closes the demand window at month end.
        due = DELIVERY[row["billno"]]
        row["startdate"] = due
        row["enddate"] = date(d(due).year, d(due).month, calendar.monthrange(d(due).year, d(due).month)[1]).isoformat()
        assert row["bizdate"] <= BD and row["auditdate"][:10] <= BD
    bill_rows = defaultdict(list)
    for row in forecasts:
        bill_rows[row["billno"]].append(row)

    # ---- production orders ---------------------------------------------
    work = zh["erp_production_work_order"]
    by_number = {r["billno"]: r for r in work}
    assert set(OPEN_WORK) <= set(by_number), set(OPEN_WORK) - set(by_number)
    used_numbers = set(by_number)
    for row in work:
        if row["taskstatus_title"] == "完工":
            continue
        if row["billno"] not in OPEN_WORK:
            # Stale orders from the source extract: finished long ago.
            row["taskstatus_title"], row["pickstatus_title"] = "完工", "全部领料"
            row["xkquainwaqty"] = row["qty"]
            log.append(f"work order {row['billno']} closed as finished")
            continue
        bill, offset, days = OPEN_WORK[row["billno"]]
        line = next(r for r in bill_rows[bill] if r["material_number"] == row["material_number"])
        if D(row["qty"]) > D(line["qty"]):
            row["qty"] = qty(D(line["qty"]))
        begin = plus(BD, offset)
        end = plus(begin, days)
        assert end < line["startdate"], (row["billno"], end, line["startdate"])
        number = f"{row['billno'][:5]}{d(begin):%Y%m%d}-{row['billno'][-3:]}"
        while number in used_numbers:
            number = number[:-3] + f"{int(number[-3:]) + 1:03d}"
        used_numbers.add(number)
        old_time = row["planbegintime"][11:]
        row.update(billno=number, billdate=begin, auditdate=f"{begin} {old_time}", planbegintime=f"{begin} {old_time}",
                   planendtime=f"{end} 23:59:59", sourcebilltype="mds_forecast", sourcebillnumber=bill)
        row["taskstatus_title"] = "未开工" if offset > 0 else row["taskstatus_title"]
        if offset > 0:
            row["xkquainwaqty"], row["pickstatus_title"] = qty(D(0)), row["pickstatus_title"]
    # Every closed forecast line was produced: link it to a finished order of its product. Where the
    # source has too few orders for a product, an unlinked finished order of that period is re-labelled.
    finished = sorted((r for r in work if r["taskstatus_title"] == "完工"), key=lambda r: r["planendtime"])
    taken: set[str] = set()
    closed = sorted((r for r in forecasts if r["closestatus_title"] != "正常"), key=lambda r: (r["enddate"], r["id"]))

    def link(w, line):
        taken.add(w["entry_id"])
        w["sourcebilltype"], w["sourcebillnumber"] = "mds_forecast", line["billno"]

    def in_window(w, line):
        return plus(line["bizdate"], -45) <= w["planendtime"][:10] <= line["enddate"]
    unmatched = []
    for line in closed:
        same = [w for w in finished if w["material_number"] == line["material_number"] and w["entry_id"] not in taken
                and w["planendtime"][:10] <= line["enddate"]]
        if same:
            link(min(same, key=lambda w: (not in_window(w, line), -int(w["planendtime"][:10].replace("-", "")))), line)
        else:
            unmatched.append(line)
    relabelled = 0
    for line in unmatched:
        pool = [w for w in finished if w["entry_id"] not in taken and w["sourcebilltype"] == "" and in_window(w, line)]
        if not pool:
            pool = [w for w in finished if w["entry_id"] not in taken and w["sourcebilltype"] == ""
                    and w["planendtime"][:10] <= line["enddate"]][-1:]
        w = max(pool, key=lambda w: w["planendtime"])
        w.update(material_number=line["material_number"], material_name=line["material_name"],
                 qty=f"{D(line['qty']):.4f}", xkquainwaqty=f"{D(line['qty']):.4f}")
        link(w, line)
        relabelled += 1
    for line in closed:
        for w in finished:
            if w["material_number"] == line["material_number"] and w["entry_id"] not in taken and in_window(w, line):
                link(w, line)
    unmatched = [f"{relabelled} finished orders re-labelled to cover closed forecast lines"]
    log.append(f"closed forecast lines without a finished order: {unmatched}")

    # ---- MRP -----------------------------------------------------------
    mrp = zh["erp_mrp_plan_order"]
    referenced = {r["srcbillnumber"] for r in zh["erp_purchase_request"]} | {r["sourcebillnumber"] for r in work}
    started = {(w["sourcebillnumber"], w["material_number"]): w for w in work
               if w["sourcebilltype"] == "mds_forecast" and w["taskstatus_title"] != "完工"}
    have = {(r["rootdemandbillno"], r["materialplanid_number"]): r for r in mrp}
    spare = [r for r in mrp if r["billno"] not in referenced and (r["rootdemandbillno"] == "" or r["rootdemandbillno"] in open_bills)
             and (r["rootdemandbillno"], r["materialplanid_number"]) not in {(b, p) for b, p in have if p in products}]
    spare.sort(key=lambda r: (r["rootdemandbillno"] != "", r["materialattr_title"] != "自制", r["billno"]))
    make_lines = 0
    for line in sorted((r for r in forecasts if r["closestatus_title"] == "正常"), key=lambda r: (r["startdate"], r["id"])):
        key = (line["billno"], line["material_number"])
        row = have.get(key)
        if row is None:
            row = spare.pop(0)
            have[key] = row
        make_lines += 1
        due = line["startdate"]
        finish = plus(due, -1)
        start = plus(finish, -lead_of(line["material_number"]))
        released = key in started
        row.update(materialplanid_number=line["material_number"], materialplanid_name=line["material_name"],
                   materialattr_title="自制", dropbilltype_name="汇报生产", rootdemandbillno=line["billno"],
                   adviseorderqty=f"{D(line['qty']):.4f}", bizorderqty=f"{D(line['qty']):.4f}",
                   orderdate=start, advisestartdate=start, startdate=start, adviseenddate=finish, enddate=finish,
                   availabledate=finish, dropstatus_title="已投放" if released else "未投放",
                   closestatus_title="投放关闭" if released else "正常",
                   bizdropqty=f"{D(line['qty']):.4f}" if released else "0.0000",
                   droptime=f"{plus(started[key]['planbegintime'][:10], -1)} 09:00:00" if released else "")
        if row["createtime"][:10] > BD:
            row["createtime"] = f"{line['bizdate']} 20:00:00"
    product_start = {key: r["startdate"] for key, r in have.items() if key[1] in products and key[0] in open_bills}
    bill_start = defaultdict(lambda: "9999-12-31")
    for (bill, _), start in product_start.items():
        bill_start[bill] = min(bill_start[bill], start)
    moved_material = 0
    for row in mrp:
        bill = row["rootdemandbillno"]
        if bill in open_bills and row["materialplanid_number"] not in products and row["availabledate"] >= bill_start[bill]:
            ready = plus(bill_start[bill], -1)
            row.update(availabledate=ready, enddate=ready, adviseenddate=ready if row["adviseenddate"] else "")
            for key in ("startdate", "advisestartdate", "orderdate"):
                if row[key] and row[key] > ready:
                    row[key] = ready
            moved_material += 1
    log.append(f"MRP make lines for open forecasts: {make_lines}; material lines pulled before production: {moved_material}")

    # ---- purchase orders -----------------------------------------------
    po = zh["erp_purchase_order"]
    def is_open(r):
        return r["rowclosestatus_title"] == "正常" and r["rowterminatestatus_title"] == "正常" and D(r["qty"]) > D(r["actqty"])

    def lead(code):
        value = D(material.get(code, {}).get("purchase_fixedleadtime") or 0)
        return int(value) if value > 0 else 15
    headers_po = defaultdict(list)
    for r in po:
        headers_po[r["billno"]].append(r)
    renamed = {}
    for number, lines in headers_po.items():
        if not any(is_open(r) for r in lines):
            continue
        longest = max(lead(r["material_number"]) for r in lines if is_open(r))
        placed = plus(BD, -(stable("po", number) % int(longest * 1.25 + 1)))
        placed = max(placed, lines[0]["biztime"][:10])
        if placed > BD:
            placed = BD
        new_number = re.sub(r"CGDD-\d{6}", "CGDD-" + d(placed).strftime("%y%m%d"), number)
        renamed[number] = new_number
        for r in lines:
            jitter = (stable("deliver", r["entry_id"]) % 7) - 3
            due = plus(placed, max(1, lead(r["material_number"]) + jitter))
            if not is_open(r):
                due = min(due, BD)
            r.update(billno=new_number, biztime=placed, createtime=f"{placed} {r['createtime'][11:]}",
                     auditdate=f"{placed} {r['auditdate'][11:]}", deliverdate=due)
    assert len(set(renamed.values())) == len(renamed)
    for r in po:
        if r["rowclosestatus_title"] == "已关闭":
            r["deliverdate"] = min(r["deliverdate"], BD)
            if r["rowterminatestatus_title"] == "正常":
                r["actqty"] = r["invqty"] = r["qty"]
    open_po = [r for r in po if is_open(r)]
    log.append(f"open PO lines {len(open_po)}, overdue {sum(r['deliverdate'] < BD for r in open_po)}, "
               f"closed after business date {sum(r['deliverdate'] > BD for r in po if not is_open(r) and r['rowclosestatus_title'] == '已关闭')}")
    pr_by_entry = {r["entry_id"]: r for r in zh["erp_purchase_request"]}
    early = 0
    for r in po:
        pr = pr_by_entry.get(r["srcbillentryid"])
        if pr and pr["biztime"][:10] > r["biztime"][:10]:
            early += 1
    log.append(f"PO lines placed before their request: {early}")
    joined = defaultdict(D)
    for r in po:
        if r["srcbillentryid"] in pr_by_entry and r["rowterminatestatus_title"] == "正常":
            joined[r["srcbillentryid"]] += D(r["qty"])
    for entry, total in joined.items():
        pr_by_entry[entry]["joinqty"] = f"{total:.4f}"

    # ---- sales orders --------------------------------------------------
    sales = zh["sales_order"]
    backlog = sorted((r for r in sales if int(r["signing_quantity"]) > int(r["shipping_quantity"] or 0)),
                     key=lambda r: (r["promised_delivery_date"], r["sales_order_id"]))
    for rank, r in enumerate(backlog):
        lead_days = (d(r["promised_delivery_date"]) - d(r["signing_date"])).days
        promised = plus(BD, -45 + rank * 120 // max(1, len(backlog)))
        signed = min(plus(promised, -lead_days), plus(BD, -1 - stable("sign", r["sales_order_id"]) % 5))
        r.update(promised_delivery_date=promised, signing_date=signed)
        if r["shipping_date"]:
            r["shipping_date"] = min(max(r["shipping_date"], signed), BD)
    log.append(f"backlog orders {len(backlog)}, overdue {sum(r['promised_delivery_date'] < BD for r in backlog)}")

    # ---- new tables (zh) -----------------------------------------------
    new_rows = {
        "production_line": ([dict(line_code=c, line_name=n, line_kind=k, parent_code=p, factory_name=f, max_parallel=m, product_lines=pl)
                             for c, n, _en, k, p, f, _fe, m, pl, _ple in LINES]),
        "line_stoppage": ([dict(stoppage_id=i, resource_code=r, resource_kind=k, start_time=s, end_time=e, reason=z)
                           for i, r, k, s, e, z, _en in STOPPAGES]),
    }
    new_headers = {t: list(rows[0]) for t, rows in new_rows.items()}

    # ---- checks --------------------------------------------------------
    assert all(r["planendtime"][:10] < BD for r in work if r["taskstatus_title"] == "完工")
    assert all(r["deliverdate"] <= BD for r in po if r["rowclosestatus_title"] == "已关闭")
    assert all(int(r["shipping_quantity"] or 0) <= int(r["signing_quantity"]) for r in sales)
    for t, key in (("erp_mrp_plan_order", "billno"), ("erp_production_work_order", "entry_id"),
                   ("erp_purchase_order", "entry_id"), ("sales_order", "sales_order_id")):
        assert len({r[key] for r in zh[t]}) == len(zh[t]), t

    # ---- English -------------------------------------------------------
    en = translate(source, zh, headers)
    lines_en = [dict(line_code=c, line_name=en_name, line_kind="Plant" if k == "工厂" else "Line", parent_code=p,
                     factory_name=fe, max_parallel=m, product_lines=ple)
                for c, _n, en_name, k, p, _f, fe, m, _pl, ple in LINES]
    stops_en = [dict(stoppage_id=i, resource_code=r, resource_kind="Plant" if k == "工厂" else "Line", start_time=s, end_time=e, reason=reason)
                for i, r, k, s, e, _z, reason in STOPPAGES]
    en_new = {"production_line": lines_en, "line_stoppage": stops_en}

    # ---- write ---------------------------------------------------------
    for lang, tables, extra in (("zh", zh, new_rows), ("en", en, en_new)):
        data_dir = SAMPLES[lang] / "data"
        for t in TABLES:
            write_csv(data_dir / f"{t}.csv", headers[t], tables[t])
        for t, rows in extra.items():
            write_csv(data_dir / f"{t}.csv", new_headers[t], rows)
        seed = kit_plan_seed(lang, data_dir)
        write_csv(data_dir / f"{SEED}.csv", list(seed[0]), seed)
        counts = {t: len(tables[t]) for t in TABLES} | {t: len(rows) for t, rows in extra.items()}
        (SAMPLES[lang] / "db" / "row_counts.json").write_text(json.dumps(dict(sorted(counts.items())), indent=2) + "\n", encoding="utf-8")
        update_lock(SAMPLES[lang], sorted([*TABLES, *extra, SEED]))
    print("\n".join(log))
    return 0


def translate(source, zh, headers):
    """Apply the Chinese changes to the English rows; changed text goes through the pairs the sources share."""
    cjk = re.compile(r"[\u4e00-\u9fff]")
    pairs: dict[str, dict[str, str]] = defaultdict(dict)
    for t in TABLES:
        for zrow, erow in zip(source["zh"][t][1], source["en"][t][1]):
            for k in zrow:
                pairs[f"{t}.{k}"].setdefault(zrow[k] or "", erow[k] or "")
                pairs["*"].setdefault(zrow[k] or "", erow[k] or "")
    out = {}
    for t in TABLES:
        rows = []
        for zold, eold, znew in zip(source["zh"][t][1], source["en"][t][1], zh[t]):
            row = {}
            for k in headers[t]:
                z1 = znew[k]
                if k not in zold:
                    row[k] = z1
                elif z1 == shift_value(zold[k] or ""):
                    row[k] = shift_value(eold[k] or "")
                elif not cjk.search(z1):
                    row[k] = z1
                else:
                    row[k] = pairs[f"{t}.{k}"].get(z1) or pairs["*"][z1]
                if cjk.search(row[k] or "") and shift_value(eold[k] or "") != row[k]:
                    raise SystemExit(f"untranslated value in {t}.{k}: {row[k]}")
            rows.append(row)
        out[t] = rows
    return out


def kit_plan_seed(lang: str, data_dir: Path) -> list[dict[str, str]]:
    """Kit-schedule history: confirmed plans for orders in production, scheduled plans for the next bills."""
    tools = SAMPLES[lang] / "tools"
    sys.path.insert(0, str(tools))
    for name in [m for m in sys.modules if m == "fn" or m.startswith("fn.")]:
        del sys.modules[name]
    kitplan = importlib.import_module("fn.kitplan")
    sys.path.remove(str(tools))
    read = lambda t: list(csv.DictReader((data_dir / f"{t}.csv").open(encoding="utf-8")))
    rows = {"bom": read("erp_material_bom"), "inventory": read("erp_real_time_inventory"),
            "purchase_order": read("erp_purchase_order"), "sales_order": read("sales_order")}
    names = {r["material_code"]: r["material_name"] for r in read("erp_material")}
    forecasts = read("erp_mds_forecast")
    products = {r["material_code"]: r for r in read("hd_product_view")}
    work = read("erp_production_work_order")
    zh = lang == "zh"
    status = {"confirmed": "已确认" if zh else "Confirmed", "scheduled": "已排" if zh else "Scheduled"}
    planner, scenario = ("朱杰倩", "初始排产") if zh else ("Owen Brooks", "Initial schedule")
    plans = []
    started = sorted((w for w in work if w["sourcebilltype"] == "mds_forecast"
                      and w["taskstatus_title"] not in ("完工", "Complete")), key=lambda w: w["planbegintime"])
    seen = set()
    for w in started:
        key = (w["sourcebillnumber"], w["material_number"])
        group = [x for x in started if (x["sourcebillnumber"], x["material_number"]) == key]
        if key in seen:
            continue
        seen.add(key)
        begin = min(x["planbegintime"] for x in group)[:10]
        end = max(x["planendtime"] for x in group)[:10]
        plans.append((key[0], key[1], products[key[1]]["line_code"], begin, end, status["confirmed"], True))
    for bill, product, line, begin, end, confirmed in SCHEDULED:
        plans.append((bill, product, line, begin, end, status["confirmed" if confirmed else "scheduled"], False))
    seed = []
    for bill, product, line, begin, end, plan_status, in_production in plans:
        lines = [r for r in forecasts if r["billno"] == bill and (not product or r["material_number"] == product)]
        demands = [{"product": r["material_number"], "qty": r["qty"]} for r in lines]
        if in_production:
            kit = {"kit_status": kitplan.KIT_COVERED, "kit_date": begin, "key_material": "", "shortage_note": ""}
        else:
            kit = kitplan.kit_check(rows, demands, begin, business_date=BD, names=names)
        number = f"KP-{bill[3:]}-{product or 'ALL'}-01"
        seed.append(dict(
            plan_id=number, bill_no=bill, product_code=product, line_code=line,
            planned_start=f"{begin}T08:00:00+08:00", planned_finish=f"{end}T20:00:00+08:00",
            quantity=f"{sum(D(r['qty']) for r in lines):f}".rstrip("0").rstrip(".") if product else "",
            kit_date=kit["kit_date"], kit_status=kit["kit_status"], key_material=kit["key_material"],
            shortage_note=kit["shortage_note"], plan_status=plan_status, reschedule_count="0", previous_finish="",
            source_scenario=scenario, planner=planner, planned_at=f"{plus(BD, -3 - len(seed) % 5)}T{9 + len(seed) % 8:02d}:30:00+08:00"))
    return seed


def update_lock(sample: Path, tables: list[str]) -> None:
    path = sample / "dataset.lock"
    lock = json.loads(path.read_text(encoding="utf-8"))
    files = []
    for t in tables:
        p = sample / "data" / f"{t}.csv"
        files.append({"path": f"data/{t}.csv", "rows": sum(1 for _ in csv.DictReader(p.open(encoding="utf-8"))),
                      "sha256": hashlib.sha256(p.read_bytes()).hexdigest()})
    lock.update(business_date=BD, files=files,
                preserved="IDs and quantities of the 0.1.20 fixture; dates and date-bearing numbers moved six months; "
                          "open demand, production orders, MRP make lines, purchase arrivals and signed backlog "
                          "re-dated around the business date by tools/supply_chain/rebuild_2027.py")
    path.write_text(json.dumps(lock, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    raise SystemExit(main())
