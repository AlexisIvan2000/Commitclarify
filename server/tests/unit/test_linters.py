import pytest

from services.ai.linters import run_eslint_on_files, run_ruff_on_files
from services.ai.linters.eslint import find_eslint

DIRTY_PYTHON = """import os
import json


def handler(a, b, items=[]):
    try:
        unused = 1
    except:
        pass
    return a
"""

DIRTY_JS = """var x = 1;
if (x == 1) {
}
function dead() {
  return 1;
  console.log("jamais atteint");
}
"""

DIRTY_JSX = """export const Widget = () => {
  var label = "hi";
  if (label == "hi") { return <span>{label}</span>; }
  return null;
};
"""

FILES = [
    {"path": "src/handler.py", "content": DIRTY_PYTHON},
    {"path": "src/legacy.js", "content": DIRTY_JS},
    {"path": "src/Widget.jsx", "content": DIRTY_JSX},
    {"path": "docs/README.md", "content": "# doc"},
]


@pytest.mark.asyncio
async def test_ruff_reports_real_issues():
    issues = await run_ruff_on_files(FILES)

    assert issues, "Ruff doit remonter des issues sur du code volontairement sale"
    assert all(i["source"] == "ruff" for i in issues)
    assert {i["file_path"] for i in issues} == {"src/handler.py"}

    titles = " ".join(i["title"] for i in issues)
    assert "Import inutilise" in titles
    assert "Bare except" in titles


@pytest.mark.asyncio
async def test_ruff_ignores_projects_without_python():
    assert await run_ruff_on_files([{"path": "a.js", "content": "var x = 1;"}]) == []


@pytest.mark.asyncio
async def test_ruff_selected_rules_are_all_valid():
    issues = await run_ruff_on_files([{"path": "x.py", "content": "import os\n"}])
    assert issues, "un code invalide fait echouer ruff silencieusement (regle inexistante ?)"


@pytest.mark.asyncio
@pytest.mark.skipif(find_eslint() is None, reason="ESLint absent (npm install manquant)")
async def test_eslint_reports_real_issues():
    issues = await run_eslint_on_files(FILES)

    assert issues, "ESLint doit remonter des issues sur du JS volontairement sale"
    assert all(i["source"] == "eslint" for i in issues)
    assert {i["file_path"] for i in issues} <= {"src/legacy.js", "src/Widget.jsx"}

    titles = " ".join(i["title"] for i in issues)
    assert "let/const" in titles
    assert "Egalite stricte" in titles


@pytest.mark.asyncio
@pytest.mark.skipif(find_eslint() is None, reason="ESLint absent (npm install manquant)")
async def test_eslint_parses_jsx():
    issues = await run_eslint_on_files([{"path": "Widget.jsx", "content": DIRTY_JSX}])
    assert issues, "le JSX doit etre parsable par la config ESLint generee"


@pytest.mark.asyncio
async def test_eslint_ignores_projects_without_js():
    assert await run_eslint_on_files([{"path": "a.py", "content": "x = 1"}]) == []


@pytest.mark.asyncio
async def test_linters_never_crash_on_empty_input():
    assert await run_ruff_on_files([]) == []
    assert await run_eslint_on_files([]) == []
