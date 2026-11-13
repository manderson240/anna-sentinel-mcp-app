"""Unit tests for Anna Sentinel AST verifier."""

import pytest
from anna_sentinel.verifier_ast import audit_source


def test_safe_source():
    code = "def add(a, b):\n    return a + b\nresult = add(2, 3)"
    res = audit_source(code)
    assert res.is_safe is True
    assert len(res.violations) == 0
    assert res.metrics["elapsed_us"] > 0
    assert res.metrics["nodes_visited"] > 0


def test_dangerous_os_system():
    code = "import os\nos.system('rm -rf /')"
    res = audit_source(code)
    assert res.is_safe is False
    assert any("os.system()" in v for v in res.violations)


def test_dangerous_subprocess():
    code = "import subprocess\nsubprocess.run(['ls', '-la'])"
    res = audit_source(code)
    assert res.is_safe is False
    assert any("subprocess" in v for v in res.violations)


def test_dangerous_eval():
    code = "user_input = '__import__(\"os\")'\neval(user_input)"
    res = audit_source(code)
    assert res.is_safe is False
    assert any("eval()" in v for v in res.violations)


def test_sandbox_breakout_class():
    code = "subclasses = ().__class__.__bases__[0].__subclasses__()"
    res = audit_source(code)
    assert res.is_safe is False
    assert any("__class__" in v or "__subclasses__" in v for v in res.violations)


def test_syntax_error():
    code = "def broken(:"
    res = audit_source(code)
    assert res.is_safe is False
    assert any("SyntaxError" in v for v in res.violations)
