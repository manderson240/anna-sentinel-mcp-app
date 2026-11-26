"""Deterministic Python AST verifier for the Anna Sentinel App.

Zero tokens, sub-millisecond traversal, and explicit blocking of dangerous
modules, aliases, builtins, sandbox breakout dunders, and constant true loops.
"""

from __future__ import annotations

import ast
import time
from dataclasses import asdict, dataclass, field
from typing import Any


DANGEROUS_CALLS: frozenset[str] = frozenset(
    {
        "eval",
        "exec",
        "compile",
        "open",
        "__import__",
        "getattr",
        "setattr",
        "delattr",
        "globals",
        "locals",
        "vars",
        "breakpoint",
        "input",
    }
)

DANGEROUS_MODULES: frozenset[str] = frozenset(
    {
        "os",
        "posix",
        "nt",
        "subprocess",
        "importlib",
        "socket",
        "shutil",
        "ctypes",
        "sys",
        "builtins",
        "pty",
        "commands",
        "pickle",
        "marshal",
        "http",
        "urllib",
        "requests",
        "pathlib",
        "io",
        "codecs",
        "tempfile",
        "multiprocessing",
        "threading",
        "asyncio",
        "runpy",
        "code",
        "codeop",
        "glob",
        "fileinput",
        "signal",
        "webbrowser",
        "ftplib",
        "smtplib",
        "telnetlib",
        "xmlrpc",
        "concurrent",
        "sched",
        "imp",
        "zipimport",
        "pkgutil",
        "gc",
        "inspect",
        "operator",
    }
)

DANGEROUS_OS_ATTRS: frozenset[str] = frozenset(
    {
        "system",
        "popen",
        "execv",
        "execl",
        "execve",
        "execvp",
        "spawnv",
        "spawnl",
        "fork",
        "kill",
        "remove",
        "unlink",
        "rmdir",
        "rename",
    }
)

SANDBOX_BREAKOUT_ATTRS: frozenset[str] = frozenset(
    {
        "__class__",
        "__subclasses__",
        "__bases__",
        "__mro__",
        "__globals__",
        "__builtins__",
        "__dict__",
        "__code__",
        "__closure__",
        "__import__",
        "__loader__",
        "__spec__",
        "__reduce__",
        "__reduce_ex__",
        "__getattribute__",
        "mro",
        "__base__",
        "gi_frame",
        "f_globals",
        "f_builtins",
    }
)


@dataclass(slots=True)
class ASTAuditResult:
    """Structured verdict returned by ASTVerifier."""

    is_safe: bool
    violations: list[str] = field(default_factory=list)
    metrics: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def __bool__(self) -> bool:
        return self.is_safe


class ASTVerifier(ast.NodeVisitor):
    """Reusable AST visitor scanning for safety violations."""

    def __init__(self) -> None:
        self.violations: list[str] = []
        self.nodes_visited = 0
        self._aliases: dict[str, str] = {}
        self._call_funcs: set[int] = set()

    def audit_source(self, source: str) -> ASTAuditResult:
        t0 = time.perf_counter()
        self.violations = []
        self.nodes_visited = 0
        self._aliases = {}
        self._call_funcs = set()

        try:
            tree = ast.parse(source)
        except SyntaxError as e:
            elapsed_us = (time.perf_counter() - t0) * 1_000_000
            return ASTAuditResult(
                is_safe=False,
                violations=[f"SyntaxError at line {e.lineno}, col {e.offset}: {e.msg}"],
                metrics={"elapsed_us": round(elapsed_us, 2), "nodes_visited": 0},
            )

        self.visit(tree)
        elapsed_us = (time.perf_counter() - t0) * 1_000_000

        return ASTAuditResult(
            is_safe=len(self.violations) == 0,
            violations=list(self.violations),
            metrics={
                "elapsed_us": round(elapsed_us, 2),
                "nodes_visited": self.nodes_visited,
            },
        )

    def generic_visit(self, node: ast.AST) -> None:
        self.nodes_visited += 1
        super().generic_visit(node)

    def visit_Import(self, node: ast.Import) -> None:
        for alias in node.names:
            root_mod = alias.name.split(".")[0]
            local_name = alias.asname or root_mod
            self._aliases[local_name] = root_mod
            if root_mod in DANGEROUS_MODULES:
                self.violations.append(
                    f"Line {node.lineno}: Forbidden module import '{alias.name}'"
                )
        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        module = (node.module or "").split(".")[0]
        if module in DANGEROUS_MODULES:
            for alias in node.names:
                local_name = alias.asname or alias.name
                self._aliases[local_name] = f"{module}.{alias.name}"
                self.violations.append(
                    f"Line {node.lineno}: Forbidden import 'from {node.module} import {alias.name}'"
                )
        self.generic_visit(node)

    def visit_Call(self, node: ast.Call) -> None:
        self._call_funcs.add(id(node.func))
        if isinstance(node.func, ast.Name):
            if node.func.id in DANGEROUS_CALLS:
                self.violations.append(
                    f"Line {node.lineno}: Forbidden dynamic call '{node.func.id}()'"
                )
            elif node.func.id in self._aliases:
                target = self._aliases[node.func.id]
                root = target.split(".")[0]
                if root in DANGEROUS_MODULES:
                    self.violations.append(
                        f"Line {node.lineno}: Forbidden aliased call '{node.func.id}()' -> '{target}'"
                    )
        elif isinstance(node.func, ast.Attribute) and isinstance(node.func.value, ast.Name):
            base_name = node.func.value.id
            resolved_mod = self._aliases.get(base_name, base_name)
            if resolved_mod in DANGEROUS_MODULES:
                if resolved_mod == "builtins" and node.func.attr in DANGEROUS_CALLS:
                    self.violations.append(
                        f"Line {node.lineno}: Forbidden builtins call '{base_name}.{node.func.attr}()'"
                    )
                elif resolved_mod == "os" and node.func.attr in DANGEROUS_OS_ATTRS:
                    self.violations.append(
                        f"Line {node.lineno}: Forbidden OS execution 'os.{node.func.attr}()'"
                    )
                elif resolved_mod in DANGEROUS_MODULES:
                    self.violations.append(
                        f"Line {node.lineno}: Forbidden call '{base_name}.{node.func.attr}()' on '{resolved_mod}'"
                    )
        self.generic_visit(node)

    def visit_Attribute(self, node: ast.Attribute) -> None:
        if node.attr in SANDBOX_BREAKOUT_ATTRS:
            self.violations.append(
                f"Line {node.lineno}: Forbidden sandbox breakout attribute '{node.attr}'"
            )
        self.generic_visit(node)

    def visit_Name(self, node: ast.Name) -> None:
        if (
            node.id in DANGEROUS_CALLS
            and isinstance(node.ctx, ast.Load)
            and id(node) not in self._call_funcs
        ):
            self.violations.append(
                f"Line {node.lineno}: Forbidden reference to dangerous builtin '{node.id}'"
            )
        if node.id in SANDBOX_BREAKOUT_ATTRS:
            self.violations.append(
                f"Line {node.lineno}: Forbidden sandbox variable '{node.id}'"
            )
        self.generic_visit(node)

    def visit_While(self, node: ast.While) -> None:
        if isinstance(node.test, ast.Constant) and bool(node.test.value) is True:
            self.violations.append(
                f"Line {node.lineno}: Forbidden unbounded constant while loop"
            )
        self.generic_visit(node)


def audit_source(source: str) -> ASTAuditResult:
    """Convenience helper for one-shot AST auditing."""
    return ASTVerifier().audit_source(source)
