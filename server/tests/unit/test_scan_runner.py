import pytest

from services.scan import AXES, SCAN_VERSION, findings_index, run_scan, to_issues
from services.scan.report import axis_result, make_finding, to_issue

FILES = [
    {"path": ".gitignore", "content": "*.log\n"},
    {"path": ".env", "content": "OPENAI_KEY=sk-abcdefghijklmnopqrstuvwxyz0123\n"},
    {"path": "README.md", "content": "See [the guide](docs/guide.md).\n"},
    {"path": "app.py", "content": "import os\n\nKEY = os.getenv('APP_SECRET')\n"},
    {"path": "requirements.txt", "content": "fastapi\nrequests\nhttpx\n"},
]


@pytest.mark.asyncio
async def test_scan_returns_every_axis_in_a_stable_order():
    scan = await run_scan(FILES)

    assert list(scan["axes"]) == list(AXES)
    assert scan["language"] == "fr"


@pytest.mark.asyncio
async def test_scan_carries_its_version_so_results_can_be_invalidated():
    scan = await run_scan(FILES)

    assert scan["scan_version"] == SCAN_VERSION
    assert isinstance(SCAN_VERSION, int)


@pytest.mark.asyncio
async def test_coverage_is_reported_when_the_caller_provides_it():
    coverage = {"tracked_files": 120, "fetched_files": 80, "tree_truncated": True}

    scan = await run_scan(FILES, coverage=coverage)

    assert scan["coverage"] == coverage
    assert (await run_scan(FILES))["coverage"] == {}


@pytest.mark.asyncio
async def test_tracked_paths_widen_the_gitignore_axis():
    files = [
        {"path": ".gitignore", "content": "node_modules/\n.env\n__pycache__/\n.venv/\n"},
        {"path": "package.json", "content": "{}"},
        {"path": "src/app.js", "content": "export const x = 1;\n"},
    ]

    without = await run_scan(files)
    with_tree = await run_scan(files, tracked_paths=[
        entry["path"] for entry in files
    ] + ["node_modules/left-pad/index.js"])

    def committed_dependencies(scan):
        return [
            finding for finding in scan["axes"]["gitignore_check"]["findings"]
            if finding["rule"] == "gitignore.tracked_ignored"
        ]

    assert committed_dependencies(without) == []
    assert committed_dependencies(with_tree)[0]["file_path"] == "node_modules/left-pad/index.js"


@pytest.mark.asyncio
async def test_scan_finds_issues_on_each_axis():
    scan = await run_scan(FILES)

    assert set(scan["summary"]["axes_with_issues"]) == set(AXES)
    assert scan["summary"]["findings"] > 0
    assert scan["summary"]["by_severity"]["critical"] > 0


@pytest.mark.asyncio
async def test_every_finding_has_a_unique_identifier():
    scan = await run_scan(FILES)
    index = findings_index(scan)

    assert len(index) == scan["summary"]["findings"]
    assert all(finding["id"] == key for key, finding in index.items())


@pytest.mark.asyncio
async def test_language_switches_the_finding_texts():
    french = await run_scan(FILES, "fr")
    english = await run_scan(FILES, "en")

    def title(scan):
        return next(
            f["title"] for f in scan["axes"]["secrets_detection"]["findings"]
            if f["rule"] == "committed.env"
        )

    assert title(french) != title(english)
    assert english["language"] == "en"


@pytest.mark.asyncio
async def test_findings_convert_to_the_legacy_issue_shape():
    scan = await run_scan(FILES)
    issues = to_issues(scan["axes"]["secrets_detection"])

    assert issues
    for issue in issues:
        assert set(issue) == {
            "severity", "title", "rule", "file_path", "description", "code_hint", "source",
            "occurrences", "locations",
        }
        assert issue["file_path"]
        assert issue["occurrences"] == len(issue["locations"])


@pytest.mark.asyncio
async def test_scan_on_an_empty_repository_does_not_crash():
    scan = await run_scan([])

    assert scan["summary"]["findings"] >= 0
    assert list(scan["axes"]) == list(AXES)


def test_axis_result_truncates_and_counts_what_it_dropped():
    findings = [
        make_finding("axis", "rule", "low", "t", "d", file_path=f"file{index}.py")
        for index in range(5)
    ]

    result = axis_result("axis", findings, limit=2)

    assert len(result["findings"]) == 2
    assert result["dropped"] == 3


def test_axis_result_sorts_the_most_severe_first():
    findings = [
        make_finding("axis", "rule", "low", "t", "d", file_path="a.py"),
        make_finding("axis", "rule", "critical", "t", "d", file_path="b.py"),
        make_finding("axis", "rule", "medium", "t", "d", file_path="c.py"),
    ]

    severities = [f["severity"] for f in axis_result("axis", findings)["findings"]]

    assert severities == ["critical", "medium", "low"]


def test_identifier_ignores_the_line_but_the_finding_keeps_it():
    first = make_finding("axis", "rule", "low", "t", "d", file_path="a.py", line=4, evidence="x = 1")
    second = make_finding("axis", "rule", "low", "t", "d", file_path="a.py", line=90, evidence="x = 1")

    assert first["id"] == second["id"]
    assert (first["line"], second["line"]) == (4, 90)


def test_identifier_separates_two_files_and_two_contents():
    same_content = make_finding("axis", "rule", "low", "t", "d", file_path="b.py", evidence="x = 1")
    other_file = make_finding("axis", "rule", "low", "t", "d", file_path="a.py", evidence="x = 1")
    other_content = make_finding("axis", "rule", "low", "t", "d", file_path="b.py", evidence="y = 2")

    assert len({same_content["id"], other_file["id"], other_content["id"]}) == 3


def test_informational_severity_degrades_to_low_in_the_legacy_shape():
    finding = make_finding("axis", "rule", "info", "t", "d", file_path="a.py")

    assert finding["severity"] == "info"
    assert to_issue(finding)["severity"] == "low"


def test_axis_result_deduplicates_identical_findings():
    finding = make_finding("axis", "rule", "low", "t", "d", file_path="a.py")

    result = axis_result("axis", [finding, dict(finding)])

    assert len(result["findings"]) == 1
    assert result["findings"][0]["occurrences"] == 1
    assert result["dropped"] == 0


def test_same_finding_on_two_lines_merges_into_one_with_both_locations():
    findings = [
        make_finding("axis", "rule", "low", "t", "d", file_path="a.py", line=12, evidence="KEY=x"),
        make_finding("axis", "rule", "low", "t", "d", file_path="a.py", line=87, evidence="KEY=x"),
    ]

    merged = axis_result("axis", findings)["findings"]

    assert len(merged) == 1
    assert merged[0]["occurrences"] == 2
    assert [location["line"] for location in merged[0]["locations"]] == [12, 87]
    assert merged[0]["line"] == 12
