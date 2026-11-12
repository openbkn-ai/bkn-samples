"""FIBO, GS1 and energy samples run their native functions as tool actions on OpenBKN 0.2.2."""
import importlib.util
import json
import sys
import types
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SAMPLES = {
    "financial-fibo-en-us": "financial_fibo_en_us", "financial-fibo-zh-cn": "financial_fibo_zh_cn",
    "retail-gs1-en-us": "retail_gs1_en_us", "retail-gs1-zh-cn": "retail_gs1_zh_cn",
    "energy-saref4ener-en-us": "energy_saref4ener_en_us", "energy-saref4ener-zh-cn": "energy_saref4ener_zh_cn",
}


def load(sample):
    tools = ROOT / "samples" / sample / "tools"
    sys.path.insert(0, str(tools))
    try:
        for name in ("ownership_receipt", "register_skills"):
            sys.modules.pop(name, None)
        spec = importlib.util.spec_from_file_location("register_capabilities_" + sample.replace("-", "_"),
                                                      tools / "register_capabilities.py")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module
    finally:
        sys.path.remove(str(tools))


class Platform:
    """Answers the sample's openbkn CLI calls and records them."""

    def __init__(self, module, kn_id, installed=False, actions=None):
        self.module, self.kn_id, self.calls = module, kn_id, []
        self.installed, self.actions = installed, actions
        self.box_name = None

    def __call__(self, *args):
        self.calls.append(list(args))
        if args[:2] == ("toolbox", "list"):
            self.box_name = args[args.index("--keyword") + 1]
            return {"data": [{"box_name": self.box_name, "box_id": "box-1"}] if self.installed else []}
        if args[:2] == ("tool", "list"):
            return {"tools": [{"name": op, "tool_id": "tool-" + op} for op in self.module.OPERATIONS] if self.installed else []}
        if args[:2] == ("tool", "get"):
            op = args[-1].removeprefix("tool-")
            return {"metadata": {"function_content": {"code": self.module.tool_code(op, self.kn_id)}}}
        if args[:2] == ("bkn", "action-type"):
            return {"entries": self.actions or []}
        if args[:2] == ("skill", "list"):
            return {"data": []}
        if args[0] == "call" and args[1].endswith("/tool-box"):
            return {"box_id": "box-1"}
        if args[0] == "call" and args[1].endswith("/tool"):
            body = json.loads(args[args.index("-d") + 1])
            return {"success_ids": ["tool-" + body["function_input"]["name"]]}
        return {}


def patched(module, platform):
    module.cli = platform
    module.remember = lambda *a: None
    module.require_owned = lambda *a: None
    module.read = lambda: {"toolboxes": ["box-1"], "skills": ["skill-1"]}
    module.register_skills = lambda **kw: {"skills": [], "owned": ["skill-1"]}
    return module


class FunctionActionTest(unittest.TestCase):
    def test_install_creates_one_tool_action_per_function_instead_of_mounting(self):
        for sample, kn_id in SAMPLES.items():
            with self.subTest(sample=sample):
                module = load(sample)
                platform = Platform(module, kn_id)
                result = patched(module, platform).run(kn_id, apply=True)
                self.assertFalse(any(c[:3] == ["bkn", "capability", "attach"] for c in platform.calls))
                posts = [c for c in platform.calls if c[0] == "call" and "/action-types" in c[1]]
                self.assertEqual(len(posts), 1)
                self.assertTrue(posts[0][1].endswith(f"/knowledge-networks/{kn_id}/action-types?import_mode=overwrite"))
                actions = json.loads(posts[0][posts[0].index("-d") + 1])["entries"]
                self.assertEqual([a["id"] for a in actions], [f"{kn_id}_{op}" for op in module.OPERATIONS])
                self.assertEqual(result["action_ids"], [a["id"] for a in actions])
                tools = {json.loads(c[c.index("-d") + 1])["function_input"]["name"]: json.loads(c[c.index("-d") + 1])["function_input"]
                         for c in platform.calls if c[0] == "call" and c[1].endswith("/tool")}
                for action, op in zip(actions, module.OPERATIONS):
                    self.assertEqual(action["operation_config"], {"type": "tool"})
                    self.assertEqual(action["object_type_id"], "")
                    self.assertEqual(action["action_source"], {"type": "tool", "box_id": "box-1", "tool_id": "tool-" + op})
                    self.assertTrue(action["name"] and action["comment"])
                    self.assertIn("execute_action", action["comment"])
                    # Every tool input, dates and scope included, is an explicit action input.
                    self.assertEqual([p["name"] for p in action["parameters"]], [i["name"] for i in tools[op]["inputs"]])
                    self.assertTrue(all(p["value_from"] == "input" for p in action["parameters"]))

    def test_verify_requires_an_action_for_every_enabled_function(self):
        for sample, kn_id in SAMPLES.items():
            with self.subTest(sample=sample):
                module = load(sample)
                partial = [{"operation_config": {"type": "tool"}, "action_source": {"type": "tool", "box_id": "box-1", "tool_id": "tool-" + op}}
                           for op in module.OPERATIONS[:-1]]
                with self.assertRaisesRegex(ValueError, "missing function action"):
                    patched(module, Platform(module, kn_id, installed=True, actions=partial)).run(kn_id, apply=False)
                complete = partial + [{"operation_config": {"type": "tool"},
                                       "action_source": {"type": "tool", "box_id": "box-1", "tool_id": "tool-" + module.OPERATIONS[-1]}}]
                result = patched(module, Platform(module, kn_id, installed=True, actions=complete)).run(kn_id, apply=False)
                self.assertEqual(set(result["tool_ids"].values()), {"tool-" + op for op in module.OPERATIONS})

    def test_retail_empty_strings_mean_not_set(self):
        sdk = types.ModuleType("sandbox_sdk"); sdk.tool = lambda f: f
        osdk = types.ModuleType("bkn_osdk"); osdk.kn = None
        config = types.ModuleType("bkn_osdk.config"); config.Context = object
        saved = {k: sys.modules.get(k) for k in ("sandbox_sdk", "bkn_osdk", "bkn_osdk.config")}
        sys.modules.update({"sandbox_sdk": sdk, "bkn_osdk": osdk, "bkn_osdk.config": config})
        try:
            for sample in ("retail-gs1-en-us", "retail-gs1-zh-cn"):
                module = load(sample)
                namespace = {"__name__": "function"}
                exec(compile(module.tool_code("fulfillment_plan", "kn"), "function", "exec"), namespace)
                seen = {}
                namespace["run_request"] = lambda query, kn, contract, op, scope, execute: seen.update(scope) or {}
                namespace["retail_function"](as_of_date="2027-02-28", knowledge_date="2027-02-28", product_ids=["PRD-001"],
                                             location_ids=[], order_ids=[], mode="", horizon_date="")
                self.assertNotIn("mode", seen)
                self.assertNotIn("horizon_date", seen)
                self.assertEqual(seen["product_ids"], ["PRD-001"])
                self.assertEqual(seen["location_ids"], [])
        finally:
            for key, value in saved.items():
                if value is None:
                    sys.modules.pop(key, None)
                else:
                    sys.modules[key] = value


if __name__ == "__main__":
    unittest.main()
