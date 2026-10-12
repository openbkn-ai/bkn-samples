from pathlib import Path

import yaml

from load_sample_data import resolve_load_order

MAP = Path(__file__).resolve().parents[1] / "mapping" / "object_table_map.yaml"


def test_resolve_load_order_matches_map():
    data = yaml.safe_load(MAP.read_text(encoding="utf-8"))
    assert resolve_load_order(data) == data["load_order"]
