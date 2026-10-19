PRODUCTION_AVAILABLE = [
    "苏州半成品仓",
    "苏州成品仓",
    "苏州电子原料仓",
    "苏州无人机原料仓",
    "苏州装配原料仓",
    "乌鲁木齐成品仓",
    "哈尔滨成品仓",
]

FINISHED_GOODS = [
    "苏州成品仓",
    "乌鲁木齐成品仓",
    "哈尔滨成品仓",
]

PRESETS = {
    "production_available": PRODUCTION_AVAILABLE,
    "finished_goods": FINISHED_GOODS,
    "all": [],
}


def resolve_warehouse_scope(scope: str | list[str] | None) -> list[str]:
    if scope is None:
        return list(PRODUCTION_AVAILABLE)
    if isinstance(scope, list):
        return list(scope)
    key = str(scope).strip()
    if key in PRESETS:
        return list(PRESETS[key])
    raise ValueError(f"unknown warehouse_scope: {scope}")
