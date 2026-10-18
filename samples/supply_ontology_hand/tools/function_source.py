"""Assemble the readable source of one native Function.

The Function Runtime accepts a single Python file per Function.  Each entry in
``functions/`` imports the calculation it runs; this module follows those
imports and copies, as plain source, only the top-level definitions the entry
actually reaches, ordered so every module's definitions follow the modules they
depend on.  The published code is therefore the same code the unit tests
exercise, without a packed archive and without the other operations.
"""

from __future__ import annotations

import ast
from dataclasses import dataclass, field
from pathlib import Path


TOOLS = Path(__file__).resolve().parent
FUNCTIONS = TOOLS / "functions"
# Imports satisfied by the Function Runtime itself rather than copied in.
RUNTIME_MODULES = {"sandbox_sdk"}


@dataclass
class _Module:
    name: str
    path: Path
    tree: ast.Module
    source: str
    # local name -> (module, name) for imports of other sample modules
    internal: dict[str, tuple[str, str]] = field(default_factory=dict)
    external: list[ast.stmt] = field(default_factory=list)
    # top-level definitions in source order: (names bound, statement)
    definitions: list[tuple[tuple[str, ...], ast.stmt]] = field(default_factory=list)


def _module_path(name: str) -> Path:
    parts = name.split(".")
    package = TOOLS.joinpath(*parts)
    return package / "__init__.py" if package.is_dir() else TOOLS.joinpath(*parts[:-1], parts[-1] + ".py")


def _resolve(importer: str, node: ast.ImportFrom) -> str:
    if not node.level:
        return node.module or ""
    package = importer.split(".")
    if not _module_path(importer).name == "__init__.py":
        package = package[:-1]
    package = package[: len(package) - (node.level - 1)]
    return ".".join([*package, node.module] if node.module else package)


def _is_sample_module(name: str) -> bool:
    root = name.split(".")[0]
    return (TOOLS / root).is_dir() or (TOOLS / f"{root}.py").is_file()


def _load(name: str, path: Path) -> _Module:
    source = path.read_text(encoding="utf-8")
    module = _Module(name, path, ast.parse(source), source)
    for index, node in enumerate(module.tree.body):
        if index == 0 and isinstance(node, ast.Expr) and isinstance(node.value, ast.Constant):
            continue  # module docstring
        if isinstance(node, ast.ImportFrom):
            target = _resolve(name, node)
            if target == "__future__" or target.split(".")[0] in RUNTIME_MODULES:
                if target != "__future__":
                    module.external.append(node)
                continue
            if _is_sample_module(target):
                for alias in node.names:
                    if alias.asname:
                        raise ValueError(f"{path.name}: aliased sample import {alias.name}")
                    module.internal[alias.name] = (target, alias.name)
                continue
            module.external.append(node)
        elif isinstance(node, ast.Import):
            if any(_is_sample_module(alias.name) for alias in node.names):
                raise ValueError(f"{path.name}: use 'from ... import' for sample modules")
            module.external.append(node)
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            module.definitions.append(((node.name,), node))
        elif isinstance(node, (ast.Assign, ast.AnnAssign)):
            targets = node.targets if isinstance(node, ast.Assign) else [node.target]
            names = tuple(t.id for t in targets if isinstance(t, ast.Name))
            if len(names) != len(targets):
                raise ValueError(f"{path.name}:{node.lineno}: unsupported assignment target")
            if names != ("__all__",):
                module.definitions.append((names, node))
        else:
            raise ValueError(f"{path.name}:{node.lineno}: unsupported top-level statement")
    return module


def _referenced_names(node: ast.AST) -> set[str]:
    return {item.id for item in ast.walk(node) if isinstance(item, ast.Name)}


class _Graph:
    def __init__(self) -> None:
        self.modules: dict[str, _Module] = {}

    def module(self, name: str) -> _Module:
        if name not in self.modules:
            self.modules[name] = _load(name, _module_path(name))
        return self.modules[name]

    def definition(self, module_name: str, name: str) -> tuple[str, str]:
        """Follow re-exports (such as ``fn/__init__``) to the defining module."""
        module = self.module(module_name)
        if any(name in names for names, _ in module.definitions):
            return module_name, name
        if name in module.internal:
            return self.definition(*module.internal[name])
        raise ValueError(f"{module.path.name} does not define {name}")

    def symbols_used_by(self, module_name: str, node: ast.AST) -> set[tuple[str, str]]:
        module = self.module(module_name)
        own = {name for names, _ in module.definitions for name in names}
        used = set()
        for name in _referenced_names(node):
            if name in own:
                used.add((module_name, name))
            elif name in module.internal:
                used.add(self.definition(*module.internal[name]))
        return used


def _entry_path(operation: str) -> Path:
    path = FUNCTIONS / f"{operation}.py"
    if not path.is_file():
        raise KeyError(f"unknown operation: {operation}")
    return path


def build_function_code(operation: str) -> str:
    """Return the complete, readable source published for one operation."""
    graph = _Graph()
    entry_name = f"functions.{operation}"
    entry = graph.module(entry_name)

    # Every symbol reachable from the entry's own definitions.
    needed: set[tuple[str, str]] = set()
    pending = [symbol for _, node in entry.definitions for symbol in graph.symbols_used_by(entry_name, node)]
    while pending:
        symbol = pending.pop()
        if symbol in needed:
            continue
        needed.add(symbol)
        module = graph.module(symbol[0])
        for names, node in module.definitions:
            if symbol[1] in names:
                pending.extend(graph.symbols_used_by(symbol[0], node))

    published: dict[str, tuple[str, str]] = {}
    for symbol in needed:
        if symbol[1] in published and published[symbol[1]] != symbol:
            raise ValueError(f"{symbol[1]} is defined in both {published[symbol[1]][0]} and {symbol[0]}")
        published[symbol[1]] = symbol

    # Modules ordered so dependencies come first; definitions keep source order.
    ordered: list[str] = []

    def visit(name: str, trail: tuple[str, ...] = ()) -> None:
        if name in ordered:
            return
        if name in trail:
            raise ValueError("circular import: " + " -> ".join((*trail, name)))
        module = graph.module(name)
        for target in sorted({graph.definition(*ref)[0] for ref in module.internal.values()}):
            if any(symbol[0] == target for symbol in needed):
                visit(target, (*trail, name))
        ordered.append(name)

    for module_name in sorted({symbol[0] for symbol in needed}):
        visit(module_name)

    imports: dict[str | None, list[str]] = {}  # module (None: plain import) -> names
    sections: list[str] = []
    for module_name in [*ordered, entry_name]:
        module = graph.module(module_name)
        chosen = [
            node for names, node in module.definitions
            if module_name == entry_name or any((module_name, name) in needed for name in names)
        ]
        if not chosen:
            continue
        for node in module.external:
            key = node.module if isinstance(node, ast.ImportFrom) else None
            names = imports.setdefault(key, [])
            names.extend(alias.name for alias in node.names if alias.name not in names)
        header = f"# ---- {module.path.relative_to(TOOLS).as_posix()} ----"
        sections.append(f"{header}\n\n{_definition_source(module, chosen)}")

    doc = ast.get_docstring(entry.tree)
    head = f'"""{doc}"""\n\n' if doc else ""
    lines = [f"import {name}" for name in imports.pop(None, [])]
    lines += [f"from {module} import {', '.join(names)}" for module, names in imports.items()]
    # No ``from __future__`` here: the runtime prepends its own imports to this
    # code, so a future import would no longer be the first statement.
    return head + "\n".join(lines) + "\n\n\n" + "\n\n\n".join(sections) + "\n"


def _definition_source(module: _Module, nodes: list[ast.stmt]) -> str:
    """Copy each definition verbatim, including its decorators."""
    lines = module.source.splitlines()
    pieces = []
    for node in nodes:
        start = min([node.lineno, *(d.lineno for d in getattr(node, "decorator_list", []))])
        pieces.append("\n".join(lines[start - 1 : node.end_lineno]))
    return "\n\n\n".join(pieces)


__all__ = ["build_function_code"]
