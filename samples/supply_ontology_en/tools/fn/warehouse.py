PRODUCTION_AVAILABLE = [
    'Suzhou Subassemblies',
    'Suzhou Finished Goods',
    'Suzhou Electronics',
    'Suzhou Drone Materials',
    'Suzhou Assembly',
    'Urumqi Finished Goods',
    'Harbin Finished Goods',
]

FINISHED_GOODS = [
    'Suzhou Finished Goods',
    'Urumqi Finished Goods',
    'Harbin Finished Goods',
]

PRESETS = {
    "production_available": PRODUCTION_AVAILABLE,
    "finished_goods": FINISHED_GOODS,
    "all": [],
}


def resolve_warehouse_scope(scope: str | list[str] | None) -> list[str]:
    if scope is None:
        return []
    if isinstance(scope, list):
        return list(scope)
    key = str(scope).strip()
    if key in PRESETS:
        return list(PRESETS[key])
    raise ValueError(f"unknown warehouse_scope: {scope}")
