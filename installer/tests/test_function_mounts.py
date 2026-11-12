"""FIBO, GS1 and energy mount their read-only calculation functions on the knowledge network."""
import importlib.util
import json
import sys
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

    def __init__(self, module, kn_id, installed=False, bindings=()):
        self.module, self.kn_id, self.calls = module, kn_id, []
        self.installed, self.bindings = installed, list(bindings)

    def __call__(self, *args):
        self.calls.append(list(args))
        if args[:2] == ("toolbox", "list"):
            name = args[args.index("--keyword") + 1]
            return {"data": [{"box_name": name, "box_id": "box-1"}] if self.installed else []}
        if args[:2] == ("tool", "list"):
            return {"tools": [{"name": op, "tool_id": "tool-" + op} for op in self.module.OPERATIONS] if self.installed else []}
        if args[:2] == ("tool", "get"):
            op = args[-1].removeprefix("tool-")
            return {"metadata": {"function_content": {"code": self.module.tool_code(op, self.kn_id)}}}
        if args[0] == "call" and "/capabilities" in args[1]:
            return {"entries": self.bindings}
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


def binding(op, binding_id="binding-1", box="box-1"):
    return {"id": binding_id, "capability_type": "function", "box_id": box, "capability_id": "tool-" + op}


class FunctionMountTest(unittest.TestCase):
    def test_install_mounts_every_function_and_creates_no_action(self):
        for sample, kn_id in SAMPLES.items():
            with self.subTest(sample=sample):
                module = load(sample)
                platform = Platform(module, kn_id)
                patched(module, platform).run(kn_id, apply=True)
                attach = [c for c in platform.calls if c[:3] == ["bkn", "capability", "attach"]]
                self.assertEqual(attach, [["bkn", "capability", "attach", kn_id, "--box", "box-1", "--tool",
                                           ",".join("tool-" + op for op in module.OPERATIONS)]])
                self.assertFalse(any(c[0] == "call" and "/action-types" in c[1] for c in platform.calls))

    def test_verify_requires_each_function_to_be_mounted(self):
        for sample, kn_id in SAMPLES.items():
            with self.subTest(sample=sample):
                module = load(sample)
                ops = module.OPERATIONS
                # Entries derived from actions have no binding id; execute_tool rejects them as unmounted.
                derived = [binding(op, binding_id="") for op in ops]
                partial = [binding(op) for op in ops[:-1]]
                other_box = [binding(op, box="box-2") for op in ops]
                for bindings in (derived, partial, other_box):
                    with self.assertRaisesRegex(ValueError, "not mounted"):
                        patched(module, Platform(module, kn_id, installed=True, bindings=bindings)).run(kn_id, apply=False)
                result = patched(module, Platform(module, kn_id, installed=True, bindings=[binding(op) for op in ops])).run(kn_id, apply=False)
                self.assertEqual(set(result["tool_ids"].values()), {"tool-" + op for op in ops})


if __name__ == "__main__":
    unittest.main()
