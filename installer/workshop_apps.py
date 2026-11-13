"""Workshop apps a sample brings: created on installation, removed on uninstall.

A sample places app specs exported from Workshop (the app's draft) in ``workshop/apps/``, without
``app.id`` and with rule functions named only by ``boxName`` and ``toolName``: toolbox and tool IDs
are new on every installation. Installing resolves those names in the toolboxes this installation
created, writes the IDs in, creates each app on the sample's knowledge network with the spec as its
draft and publishes it, so its pages open from the app workshop. A function that cannot be found
fails the installation before any app is created. The created app IDs are kept in the installation
record; uninstalling deletes them.

On a platform without Workshop (the community edition) there is nothing to create: the sample is
installed without its apps.

Workshop app names are not unique. An app of the same name on the sample's network is the
sample's own app from an earlier installation, so it is replaced, like the apps the record lists.
"""

from __future__ import annotations

import copy

from pathlib import Path
from urllib.parse import quote

import yaml

API_VERSION = "workshop.openbkn.ai/v1"
APPS = "/api/workshop/v1/apps"
DIRECTORY = Path("workshop") / "apps"
MAX_SPEC = 4 * 1024 * 1024


class AppError(Exception):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code
        self.message = message


def files(sample_dir: Path) -> list[Path]:
    folder = sample_dir / DIRECTORY
    return sorted(folder.glob("*.app.yaml")) if folder.is_dir() else []


def load(path: Path) -> dict:
    data = path.read_bytes()
    if len(data) > MAX_SPEC:
        raise AppError("invalid_workshop_app", f"{path.name} is larger than 4 MiB")
    try:
        spec = yaml.safe_load(data.decode("utf-8"))
    except (UnicodeDecodeError, yaml.YAMLError) as error:
        raise AppError("invalid_workshop_app", f"{path.name} is not valid YAML") from error
    return spec


def validate(spec, network_id: str) -> list[str]:
    """Errors in one exported app spec for a sample whose knowledge network is ``network_id``."""
    if not isinstance(spec, dict):
        return ["the app spec must be a mapping"]
    errors = []
    if spec.get("apiVersion") != API_VERSION:
        errors.append(f"apiVersion must be {API_VERSION}")
    app = spec.get("app")
    name = app.get("name") if isinstance(app, dict) else None
    if not isinstance(name, str) or not name.strip() or len(name) > 128:
        errors.append("app.name is required, at most 128 characters")
    description = app.get("description") if isinstance(app, dict) else None
    if description is not None and (not isinstance(description, str) or len(description) > 2000):
        errors.append("app.description must be text of at most 2000 characters")
    network = (spec.get("dependencies") or {}).get("knowledgeNetwork") if isinstance(spec.get("dependencies"), dict) else None
    if not isinstance(network, dict) or network.get("id") != network_id:
        errors.append(f"dependencies.knowledgeNetwork.id must be the sample's knowledge network {network_id}")
    if not isinstance(spec.get("pages"), list) or not spec["pages"]:
        errors.append("pages must list at least one page")
    if isinstance(app, dict) and "id" in app:
        errors.append("app.id must be left out; Workshop assigns it")
    for where, ref in rule_refs(spec):
        if not isinstance(ref, dict) or not all(isinstance(ref.get(k), str) and ref[k].strip() for k in ("boxName", "toolName")):
            errors.append(f"{where}: a rule function is named by boxName and toolName")
        elif "box" in ref or "tool" in ref:
            errors.append(f"{where}: leave out box and tool; the installer fills in this installation's IDs")
    return errors


def rule_refs(spec):
    """``(where, tool)`` for every rule function the spec calls: the Gantt layers' ``ruleTools`` and the
    schedule model's task ``rules``."""
    def walk(node, where):
        if isinstance(node, dict):
            for key, value in node.items():
                if key == "ruleTools" and isinstance(value, list):
                    for index, item in enumerate(value):
                        yield f"{where}.ruleTools[{index}]", item.get("tool") if isinstance(item, dict) else None
                else:
                    yield from walk(value, f"{where}.{key}")
        elif isinstance(node, list):
            for index, item in enumerate(node):
                yield from walk(item, f"{where}[{index}]")
    if not isinstance(spec, dict):
        return
    yield from walk(spec.get("pages"), "pages")
    model = spec.get("scheduleModel")
    for t, task in enumerate(model.get("tasks") or [] if isinstance(model, dict) else []):
        for r, rule in enumerate(task.get("rules") or [] if isinstance(task, dict) else []):
            yield f"scheduleModel.tasks[{t}].rules[{r}]", rule.get("tool") if isinstance(rule, dict) else None


def functions(api, toolboxes) -> dict:
    """``{(toolbox name, tool name): (toolbox ID, tool ID)}`` for the toolboxes this installation created."""
    found = {}
    for box_id in toolboxes:
        box = api("GET", "/api/agent-operator-integration/v1/tool-box/" + quote(str(box_id), safe=""))
        if not isinstance(box, dict):
            continue
        for tool in box.get("tools") or []:
            if isinstance(tool, dict) and tool.get("tool_id") and tool.get("name"):
                found[(box.get("box_name"), tool["name"])] = (box.get("box_id") or box_id, tool["tool_id"])
    return found


def resolve(spec: dict, catalog: dict) -> dict:
    """A copy of ``spec`` whose rule functions carry this installation's toolbox and tool IDs."""
    resolved = copy.deepcopy(spec)
    missing = []
    for _where, ref in rule_refs(resolved):
        ids = catalog.get((ref["boxName"], ref["toolName"]))
        if ids is None:
            missing.append(f"{ref['boxName']} / {ref['toolName']}")
        else:
            ref["box"], ref["tool"] = ids
    if missing:
        raise AppError("workshop_function_missing",
                       f"The app {spec['app']['name']} calls functions this installation does not have: "
                       + ", ".join(sorted(set(missing))))
    return resolved


def specs(sample_dir: Path, network_id: str) -> list[dict]:
    loaded = []
    names = set()
    for path in files(sample_dir):
        spec = load(path)
        errors = validate(spec, network_id)
        if errors:
            raise AppError("invalid_workshop_app", f"{path.name}: {'; '.join(errors)}")
        if spec["app"]["name"] in names:
            raise AppError("invalid_workshop_app", f"{path.name}: another app of the sample has the same name")
        names.add(spec["app"]["name"])
        loaded.append(spec)
    return loaded


def _entries(found) -> list[dict]:
    if found is None:
        return []
    if not isinstance(found, dict) or not isinstance(found.get("entries"), list):
        raise AppError("workshop_unavailable", "Workshop app list has an unexpected shape")
    return [item for item in found["entries"] if isinstance(item, dict)]


def _same_name(api, network_id: str, name: str) -> list[str]:
    ids, cursor = [], ""
    for _ in range(50):
        query = f"?kn_id={quote(network_id, safe='')}&name={quote(name, safe='')}&limit=200"
        found = api("GET", APPS + query + (f"&cursor={quote(cursor, safe='')}" if cursor else ""))
        ids += [item["id"] for item in _entries(found)
                if item.get("name") == name and (item.get("kn") or {}).get("id") == network_id and item.get("id")]
        cursor = (found or {}).get("next_cursor") or ""
        if not cursor:
            return ids
    raise AppError("workshop_unavailable", "Workshop app list does not end")


def available(api) -> bool:
    """Whether the platform has Workshop: it is part of the professional edition, and below it every
    Workshop route answers 404."""
    return api("GET", APPS + "?limit=1") is not None


def remove(api, app_id: str) -> None:
    """Deletes one app; an app already absent counts as removed."""
    path = APPS + "/" + quote(app_id, safe="")
    if api("GET", path) is None:
        return
    api("DELETE", path)


def install(api, spec_list: list[dict], network: dict, recorded: list[dict], remember=lambda apps: None,
            toolboxes=()) -> list[dict]:
    """Replaces the sample's apps with ``spec_list``; returns ``[{id, name}]`` for the record.

    ``recorded`` are the apps a previous attempt or installation created. ``network`` is
    ``{id, name}`` of the sample's knowledge network. ``remember`` receives the list after every
    change, so an interrupted attempt still leaves a receipt of what it created. ``toolboxes`` are the
    IDs of the toolboxes this installation created; rule functions are resolved in them first.
    """
    catalog = functions(api, toolboxes) if any(True for spec in spec_list for _ in rule_refs(spec)) else {}
    spec_list = [resolve(spec, catalog) for spec in spec_list]
    left = [item for item in recorded if isinstance(item, dict) and item.get("id")]
    for item in list(left):
        remove(api, str(item["id"]))
        left.remove(item)
        remember(list(left))
    created = []
    for spec in spec_list:
        name = spec["app"]["name"]
        for app_id in _same_name(api, network["id"], name):
            remove(api, app_id)
        draft = {**spec, "dependencies": {**spec["dependencies"], "knowledgeNetwork": dict(network)}}
        app = api("POST", APPS, {"name": name, "description": spec["app"].get("description") or "",
                                 "tags": [], "references": [], "kn": dict(network), "draft": draft})
        if not isinstance(app, dict) or not app.get("id"):
            raise AppError("workshop_unavailable", f"Workshop did not create the app {name}")
        created.append({"id": app["id"], "name": name})
        remember(list(created))
        api("POST", f"{APPS}/{quote(app['id'], safe='')}/publish",
            {"revision": app.get("draft_revision") or 1, "note": "Installed with the sample"})
    return created
