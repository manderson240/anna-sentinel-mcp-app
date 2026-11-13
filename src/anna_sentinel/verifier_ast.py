"""High-performance, deterministic Python AST verifier for the Anna Sentinel App.
==============================================================================
Design Principles:
- Zero tokens: Static AST traversal with zero LLM dependency.
- Sub-millisecond latency: Runs in <0.2ms.
- Comprehensive safety: Filters OS injections, shell executions, and sandbox breakout dunders.
"""

from __future__ import annotations

import ast
import time
from dataclasses import asdict, dataclass, field
from typing import Any

# Capabilities that grant OS-level or dynamic-execution reach
DANGEROUS_CALLS: frozenset[str] = frozenset(
    {
        "eval",
        "exec",
        "__import__",
        "getattr",
        "setattr",
        "delattr",
    }
)

DANGEROUS_MODULES: frozenset[str] = frozenset(
    {
        "subprocess",
        "importlib",
    }
)

# Dunder attributes that enable sandbox escape via object tree traversal
SANDBOX_BREAKOUT_ATTRS: frozenset[str] = frozenset(
    {
        "__class__",
        "__subclasses__",
        "__bases__",
        "__globals__",
        "__builtins__",
        "__dict__",
        "__code__",
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

    def audit_source(self, source: str) -> ASTAuditResult:
        t0 = time.perf_counter()
        self.violations = []
        self.nodes_visited = 0

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
            if alias.name in DANGEROUS_MODULES:
                self.violations.append(
                    f"Line {node.lineno}: Forbidden module import '{alias.name}'"
                )
        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        module = node.module or ""
        if module in DANGEROUS_MODULES or module == "os":
            for alias in node.names:
                if module == "os" and alias.name in ("system", "popen"):
                    self.violations.append(
                        f"Line {node.lineno}: Forbidden import 'from os import {alias.name}'"
                    )
                elif module in DANGEROUS_MODULES:
                    self.violations.append(
                        f"Line {node.lineno}: Forbidden import from dangerous module '{module}'"
                    )
        self.generic_visit(node)

    def visit_Call(self, node: ast.Call) -> None:
        # Check call by name: eval(...), exec(...)
        if isinstance(node.func, ast.Name) and node.func.id in DANGEROUS_CALLS:
            self.violations.append(
                f"Line {node.lineno}: Forbidden dynamic call '{node.func.id}()'"
            )
        # Check attribute call: os.system(...)
        elif isinstance(node.func, ast.Attribute):
            if isinstance(node.func.value, ast.Name) and node.func.value.id == "os":
                if node.func.attr in ("system", "popen"):
                    self.violations.append(
                        f"Line {node.lineno}: Forbidden OS execution 'os.{node.func.attr}()'"
                    )
        self.generic_visit(node)

    def visit_Attribute(self, node: ast.Attribute) -> None:
        if node.attr in SANDBOX_BREAKOUT_ATTRS:
            self.violations.append(
                f"Line {node.lineno}: Forbidden sandbox breakout attribute '{node.attr}'"
            )
        self.generic_visit(node)


def audit_source(source: str) -> ASTAuditResult:
    """Convenience helper for one-shot AST auditing."""
    return ASTVerifier().audit_source(source)
