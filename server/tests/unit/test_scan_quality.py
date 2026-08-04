import ast

import pytest

from services.scan.quality import _complexity_of, _pinning_ratio, scan_quality

COMPLEX_FUNCTION = """
def handler(value):
    if value == 1:
        return 1
    elif value == 2:
        return 2
    elif value == 3:
        return 3
    for item in range(10):
        if item:
            pass
    while value:
        value -= 1
    try:
        pass
    except ValueError:
        pass
    except KeyError:
        pass
    return [x for x in range(3) if x]
"""

SIMPLE_FUNCTION = "def add(a, b):\n    return a + b\n"


def _rules(result):
    return {finding["rule"] for finding in result["findings"]}


def _node(source):
    return ast.parse(source).body[0]


def test_complexity_counts_branches_and_boolean_operators():
    assert _complexity_of(_node("def f(a, b):\n    if a and b:\n        return 1\n    return 0\n")) == 3


def test_complexity_ignores_nested_functions():
    source = "def outer():\n    def inner():\n        if 1:\n            pass\n    return inner\n"
    assert _complexity_of(_node(source)) == 1


def test_simple_function_has_complexity_one():
    assert _complexity_of(_node(SIMPLE_FUNCTION)) == 1


@pytest.mark.asyncio
async def test_complex_function_is_reported_with_its_line():
    result = await scan_quality([{"path": "src/handler.py", "content": COMPLEX_FUNCTION}])

    finding = next(f for f in result["findings"] if f["rule"] == "quality.complex_function")
    assert finding["file_path"] == "src/handler.py"
    assert finding["line"] == 2
    assert finding["source"] == "ast"
    assert result["metrics"]["complexity"]["max"] > 10


@pytest.mark.asyncio
async def test_simple_function_is_not_reported_as_complex():
    result = await scan_quality([{"path": "src/math.py", "content": SIMPLE_FUNCTION}])

    assert "quality.complex_function" not in _rules(result)
    assert result["metrics"]["complexity"]["over_threshold"] == 0


@pytest.mark.asyncio
async def test_complexity_is_never_reported_twice_by_ruff_and_the_ast_pass():
    result = await scan_quality([{"path": "src/handler.py", "content": COMPLEX_FUNCTION}])

    assert "C901" not in _rules(result)


@pytest.mark.asyncio
async def test_project_without_tests_is_reported():
    result = await scan_quality([{"path": "src/app.py", "content": SIMPLE_FUNCTION}])

    assert "quality.no_tests" in _rules(result)
    assert result["metrics"]["has_tests"] is False
    assert result["metrics"]["test_files_in_sample"] == 0


@pytest.mark.asyncio
async def test_tests_directory_clears_the_finding():
    result = await scan_quality([
        {"path": "src/app.py", "content": SIMPLE_FUNCTION},
        {"path": "tests/test_app.py", "content": "def test_add():\n    assert True\n"},
    ])

    assert "quality.no_tests" not in _rules(result)
    assert result["metrics"]["test_files_in_sample"] == 1
    assert result["metrics"]["test_ratio_in_sample"] == 1.0


@pytest.mark.asyncio
async def test_missing_ci_is_reported_and_a_workflow_clears_it():
    without = await scan_quality([{"path": "src/app.py", "content": SIMPLE_FUNCTION}])
    with_ci = await scan_quality([
        {"path": "src/app.py", "content": SIMPLE_FUNCTION},
        {"path": ".github/workflows/ci.yml", "content": "name: ci\n"},
    ])

    assert "quality.no_ci" in _rules(without)
    assert "quality.no_ci" not in _rules(with_ci)
    assert with_ci["metrics"]["has_ci"] is True


@pytest.mark.asyncio
async def test_node_project_without_lockfile_is_reported():
    result = await scan_quality([
        {"path": "package.json", "content": '{"name": "app"}'},
        {"path": "src/index.js", "content": "export const x = 1;\n"},
    ])

    assert "quality.no_lockfile" in _rules(result)
    assert result["metrics"]["missing_lockfiles"] == ["node"]


@pytest.mark.asyncio
async def test_lockfile_clears_the_finding():
    result = await scan_quality([
        {"path": "package.json", "content": '{"name": "app"}'},
        {"path": "package-lock.json", "content": "{}"},
        {"path": "src/index.js", "content": "export const x = 1;\n"},
    ])

    assert result["metrics"]["missing_lockfiles"] == []


@pytest.mark.asyncio
async def test_pinned_requirements_soften_the_lockfile_finding_without_hiding_it():
    result = await scan_quality([
        {"path": "requirements.txt", "content": "fastapi==1.0\nrequests==2.0\nhttpx==0.28\n"},
        {"path": "app.py", "content": SIMPLE_FUNCTION},
    ])

    finding = next(f for f in result["findings"] if f["rule"] == "quality.pinned_without_lockfile")
    assert finding["severity"] == "info"
    assert result["metrics"]["missing_lockfiles"] == ["python"]
    assert result["metrics"]["pinned_requirements"] is True
    assert "quality.no_lockfile" not in _rules(result)


@pytest.mark.asyncio
async def test_unpinned_requirements_keep_the_full_lockfile_finding():
    result = await scan_quality([
        {"path": "requirements.txt", "content": "fastapi\nrequests\nhttpx\n"},
        {"path": "app.py", "content": SIMPLE_FUNCTION},
    ])

    finding = next(f for f in result["findings"] if f["rule"] == "quality.no_lockfile")
    assert finding["severity"] == "medium"
    assert result["metrics"]["pinned_requirements"] is False


def test_pinning_ratio_ignores_comments_and_flags():
    pinned, total = _pinning_ratio("# comment\n-r base.txt\nfastapi==1.0\nrequests\n\n")
    assert (pinned, total) == (1, 2)


@pytest.mark.asyncio
async def test_unpinned_requirements_are_reported():
    result = await scan_quality([
        {"path": "requirements.txt", "content": "fastapi\nrequests\nhttpx\n"},
        {"path": "app.py", "content": SIMPLE_FUNCTION},
    ])

    assert "quality.unpinned_dependencies" in _rules(result)


@pytest.mark.asyncio
async def test_pinned_requirements_are_not_reported():
    result = await scan_quality([
        {"path": "requirements.txt", "content": "fastapi==1.0\nrequests==2.0\nhttpx==0.28\n"},
        {"path": "app.py", "content": SIMPLE_FUNCTION},
    ])

    assert "quality.unpinned_dependencies" not in _rules(result)


@pytest.mark.asyncio
async def test_linter_issues_become_findings_with_unique_ids():
    dirty = "import os\nimport json\n\n\ndef handler():\n    try:\n        pass\n    except:\n        pass\n"
    result = await scan_quality([{"path": "src/dirty.py", "content": dirty}])

    ruff_findings = [f for f in result["findings"] if f["source"] == "ruff"]
    ids = [finding["id"] for finding in result["findings"]]

    assert len(ruff_findings) >= 2
    assert len(ids) == len(set(ids))
    assert result["metrics"]["linter_issues"] >= 2


@pytest.mark.asyncio
async def test_absence_rules_look_at_the_whole_repository_not_the_sample():
    sample = [{"path": "src/index.js", "content": "export const x = 1;\n"}]
    tracked = [
        "src/index.js",
        "package.json",
        "yarn.lock",
        "src/index.test.js",
        ".github/workflows/ci.yml",
    ]

    result = await scan_quality(sample, tracked_paths=tracked)

    assert result["metrics"]["missing_lockfiles"] == []
    assert result["metrics"]["has_ci"] is True
    assert result["metrics"]["has_tests"] is True
    assert _rules(result).isdisjoint({"quality.no_lockfile", "quality.no_ci", "quality.no_tests"})


@pytest.mark.asyncio
async def test_the_same_sample_without_the_tree_produces_the_false_positives():
    sample = [{"path": "src/index.js", "content": "export const x = 1;\n"}]

    result = await scan_quality(sample)

    assert {"quality.no_lockfile", "quality.no_ci", "quality.no_tests"} <= _rules(result)


@pytest.mark.asyncio
async def test_the_sample_counts_are_labelled_as_such():
    result = await scan_quality(
        [{"path": "a.py", "content": SIMPLE_FUNCTION}],
        tracked_paths=["a.py", "b.py", "tests/test_a.py"],
    )

    assert result["metrics"]["source_files_in_sample"] == 1
    assert "source_files" not in result["metrics"]
    assert "test_ratio" not in result["metrics"]
    assert "sample_covers_repository" not in result["metrics"]


@pytest.mark.asyncio
async def test_complexity_is_null_when_no_python_was_analyzed():
    result = await scan_quality([{"path": "src/app.js", "content": "export const x = 1;\n"}])
    complexity = result["metrics"]["complexity"]

    assert complexity["max"] is None
    assert complexity["average"] is None
    assert complexity["over_threshold"] is None
    assert complexity["analyzed_languages"] == []
    assert complexity["unanalyzed_languages"] == ["node"]


@pytest.mark.asyncio
async def test_complexity_is_zero_only_when_python_was_actually_analyzed():
    result = await scan_quality([{"path": "a.py", "content": SIMPLE_FUNCTION}])
    complexity = result["metrics"]["complexity"]

    assert complexity["analyzed_languages"] == ["python"]
    assert complexity["over_threshold"] == 0
    assert complexity["max"] == 1


@pytest.mark.asyncio
async def test_complexity_identifier_survives_a_line_shift():
    def identifier(result):
        return next(f["id"] for f in result["findings"] if f["rule"] == "quality.complex_function")

    before = await scan_quality([{"path": "handler.py", "content": COMPLEX_FUNCTION}])
    after = await scan_quality([{"path": "handler.py", "content": "x = 1\n" + COMPLEX_FUNCTION}])

    assert identifier(before) == identifier(after)


@pytest.mark.asyncio
async def test_empty_input_does_not_crash():
    result = await scan_quality([])

    assert result["status"] == "clean"
    assert result["metrics"]["source_files_in_sample"] == 0
