"""Unit tests for Anna Sentinel AST verifier including alias and breakout hardening."""

import pytest

from anna_sentinel.verifier_ast import audit_source


def test_safe_source() -> None:
    code = "def add(a, b):\n    return a + b\nresult = add(2, 3)"
    res = audit_source(code)
    assert res.is_safe is True
    assert len(res.violations) == 0
    assert res.metrics["elapsed_us"] > 0
    assert res.metrics["nodes_visited"] > 0


def test_dangerous_os_system() -> None:
    code = "import os\nos.system('rm -rf /')"
    res = audit_source(code)
    assert res.is_safe is False
    assert any("os.system()" in v for v in res.violations)


@pytest.mark.parametrize(
    "bypass_code",
    [
        "import os\n",
        "import os as o\no.system('id')\n",
        "import os\nos.execv('/bin/sh', ['sh'])\n",
        "open('/etc/passwd').read()\n",
        "import socket\nsocket.socket()\n",
        "import builtins\nbuiltins.eval('1+1')\n",
        "while True:\n    pass\n",
        "from os import *\n",
        "def f(x):\n    return x.__mro__\n",
        "def g():\n    return ().__class__.__bases__[0].__subclasses__()\n",
        "import io\nio.open('/etc/passwd')\n",
        "import codecs\ncodecs.open('/etc/passwd')\n",
        "import multiprocessing\n",
        "import asyncio\nasyncio.create_subprocess_exec('id')\n",
        "import runpy\n",
        "import tempfile\n",
        "import threading\n",
        "import glob\n",
        "f = eval\nf('1')\n",
        "g = __import__\ng('os')\n",
        "type(()).mro()\n",
    ],
)
def test_blocks_all_documented_bypass_vectors(bypass_code: str) -> None:
    res = audit_source(bypass_code)
    assert res.is_safe is False
    assert len(res.violations) >= 1


def test_syntax_error() -> None:
    code = "def broken(:"
    res = audit_source(code)
    assert res.is_safe is False
    assert any("SyntaxError" in v for v in res.violations)


def test_safe_code_still_passes_after_hardening() -> None:
    assert audit_source("def add(a, b):\n    return a + b\n\nprint(add(1, 2))\n").is_safe is True


def test_documented_limit_antonym_claim_is_supported() -> None:
    """Known limit: word overlap cannot see that 'grew' and 'fell' are opposites."""
    from anna_sentinel.mock_hub import verify_claims_against_source

    res = verify_claims_against_source(["Revenue grew ten percent"], "revenue fell ten percent")
    assert res["claims"][0]["supported"] is True
