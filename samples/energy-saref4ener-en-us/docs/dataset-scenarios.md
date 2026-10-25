# Business differences and anomaly index

The dataset covers50customer sites,150devices with unique meters and25response dates. Four fully overlapping events share devices on each date, exposing priority and site-limit decisions.60events are historical;40March2027events are future plans with no actual readings, receipts or posted settlements. Business names/status/reasons/units are localized; IDs and codes are stable across languages.

Anomalies are specific business facts, alongside clean events, failed/declined receipts, missing evidence, revisions, conflicts and zero commitments.

| Type | Exact records/scope |
|---|---|
| missing constraint cap | {"source_ids": ["CON-076"], "response_date": "2027-02-10", "device_id": "DEV-061"} |
| latest invalid forecast | {"source_ids": ["FOR-04-046", "FOR-04-046-R2"], "device_id": "DEV-046", "response_date": "2026-11-25"} |
| same revision baseline conflict | {"source_ids": ["BAS-06-076", "BAS-06-076-CONFLICT"], "device_id": "DEV-076", "response_date": "2026-12-09"} |
| missing reading | {"source_ids": ["REA-08-106"], "device_id": "DEV-106", "response_date": "2026-12-23"} |
| identical reading retry | {"source_ids": ["REA-09-136", "REA-09-136-RETRY"], "device_id": "DEV-136", "response_date": "2026-12-30"} |
| late reading correction | {"source_ids": ["REA-10-136", "REA-10-136-R2"], "device_id": "DEV-136", "response_date": "2027-01-06", "known_date": "2027-01-18"} |
| post cutoff baseline restatement | {"source_ids": ["BAS-15-061", "BAS-15-061-R2"], "device_id": "DEV-061", "response_date": "2027-02-24", "known_date": "2027-03-03"} |
| missing execution receipt | {"event_id": "EVT-033", "allocation_id": "ALL-0283"} |
| overreserved block | {"event_ids": ["EVT-057", "EVT-058", "EVT-059", "EVT-060"], "allocation_id": "ALL-0499", "device_id": "DEV-061", "response_date": "2027-02-24"} |
| future offer withdrawal | {"source_ids": ["OFF-2161", "OFF-2161-R2"], "event_id": "EVT-073", "known_date": "2027-03-05"} |
| shared meter prorata | {"response_date": "2026-11-04", "block_code": "peak_a", "shared_devices": [{"device_id": "DEV-016", "meter_id": "MTR-016", "reading_id": "REA-01-016", "allocation_ids": ["ALL-0004", "ALL-0010"], "event_ids": ["EVT-001", "EVT-002"], "total_committed_kwh": "12.250000", "observed_reduction_kwh": "9.800000"}, {"device_id": "DEV-017", "meter_id": "MTR-017", "reading_id": "REA-01-017", "allocation_ids": ["ALL-0005", "ALL-0011"], "event_ids": ["EVT-001", "EVT-002"], "total_committed_kwh": "12.250000", "observed_reduction_kwh": "9.800000"}, {"device_id": "DEV-018", "meter_id": "MTR-018", "reading_id": "REA-01-018", "allocation_ids": ["ALL-0006", "ALL-0012"], "event_ids": ["EVT-001", "EVT-002"], "total_committed_kwh": "12.250000", "observed_reduction_kwh": "9.800000"}]} |
| inclusive threshold half cent | {"event_id": "EVT-001", "committed_kwh": "37.500000", "verified_kwh": "30.000000", "delivery_ratio": "0.800000", "minimum_ratio": "0.800000", "reward_cny_kwh": "1.200500", "unrounded_revenue_cny": "36.015000000000", "rounded_revenue_cny": "36.02"} |
| load increase no response | {"device_id": "DEV-046", "reading_id": "REA-01-046", "response_date": "2026-11-04"} |
| recorded capacity drift | {"snapshot_id": "CAP-017", "event_id": "EVT-017", "difference_kw": "7.000000"} |
| posted revenue drift | {"event_id": "EVT-025", "settlement_id": "SET-025", "snapshot_id": "SSP-025", "difference_cny": "5.00"} |
| recorded capacity drift | {"snapshot_id": "CAP-065", "event_id": "EVT-065", "difference_kw": "7.000000"} |
| recorded capacity drift | {"snapshot_id": "CAP-091", "event_id": "EVT-091", "difference_kw": "7.000000"} |
| same day posted ledger conflict | {"event_id": "EVT-041", "source_ids": ["SET-041", "SET-041-CONFLICT"], "posted_date": "2027-01-15", "effect": "Reconciliation unknown; measured delivery and recomputed revenue remain independently known."} |

See dataset-scenarios.json for full counts, IDs and construction rules. Source values are comparison fixtures, not official market settlement or proof of model accuracy.
