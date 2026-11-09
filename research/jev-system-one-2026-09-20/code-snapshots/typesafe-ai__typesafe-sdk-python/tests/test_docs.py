"""Execute Markdown and Python docstring examples against the configured API."""

import doctest
import importlib
from pathlib import Path

import pytest
from sybil import Document
from sybil.document import PythonDocStringDocument
from sybil.evaluators.python import PythonEvaluator
from sybil.parsers.markdown import CodeBlockParser, PythonCodeBlockParser

import typesafe_sdk

ROOT = Path(__file__).resolve().parents[1]
MARKDOWN_FILES = [ROOT / "README.md", *sorted((ROOT / "docs").rglob("*.md"))]
SOURCE_FILES = sorted((ROOT / "src" / "typesafe_sdk").rglob("*.py"))


def code_parsers() -> tuple[PythonCodeBlockParser, CodeBlockParser]:
    """Parse both ```python and ```py fenced blocks with the same Python evaluator."""
    return PythonCodeBlockParser(), CodeBlockParser("py", PythonEvaluator())


@pytest.mark.integration
@pytest.mark.usefixtures("live_api_key")
@pytest.mark.parametrize("path", MARKDOWN_FILES, ids=lambda path: str(path.relative_to(ROOT)))
def test_markdown(path: Path) -> None:
    document = Document.parse(str(path), *code_parsers())
    for example in document.examples():
        example.evaluate()


@pytest.mark.parametrize("path", SOURCE_FILES, ids=lambda path: str(path.relative_to(ROOT)))
@pytest.mark.integration
@pytest.mark.usefixtures("live_api_key")
def test_python_doctests(path: Path) -> None:
    document = PythonDocStringDocument.parse(str(path), *code_parsers())
    # Docstring examples are shown on the documented symbol's own page, so they may reference public
    # names (like the client) without importing them; standalone Markdown pages still import everything.
    document.namespace.update({export: getattr(typesafe_sdk, export) for export in typesafe_sdk.__all__})
    for example in document.examples():
        example.evaluate()
    parts = path.relative_to(ROOT / "src").with_suffix("").parts
    name = ".".join(parts[:-1] if parts[-1] == "__init__" else parts)
    result = doctest.testmod(importlib.import_module(name))
    assert result.failed == 0
