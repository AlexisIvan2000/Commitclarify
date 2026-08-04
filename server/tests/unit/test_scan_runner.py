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


CLEAN_FILES = [
    {"path": ".gitignore", "content": ".env\n__pycache__/\n.venv/\n"},
    {"path": "README.md", "content": "# App\n"},
    {"path": "app.py", "content": "def add(a, b):\n    return a + b\n"},
    {"path": "tests/test_app.py", "content": "def test_add():\n    assert True\n"},
    {"path": ".github/workflows/ci.yml", "content": "name: ci\n"},
    {"path": "requirements.txt", "content": "fastapi==1.0\nrequests==2.0\nhttpx==0.28\n"},
    {"path": "poetry.lock", "content": "# lock\n"},
]


@pytest.mark.asyncio
@pytest.mark.parametrize("gap", [
    {"tree_truncated": True},
    {"capped_over_limit": 1200},
    {"fetch_failures": {"fetch_http_error": 3}},
])
async def test_incomplete_coverage_turns_clean_axes_into_partial(gap):
    complete = await run_scan(CLEAN_FILES, coverage={"tree_truncated": False})
    partial = await run_scan(CLEAN_FILES, coverage=gap)

    assert complete["complete"] is True
    assert partial["complete"] is False

    for axis, result in partial["axes"].items():
        assert result["status"] != "clean", f"{axis} affirme 'clean' sur une couverture partielle"
        if complete["axes"][axis]["status"] == "clean":
            assert result["status"] == "partial"


@pytest.mark.asyncio
async def test_deliberate_exclusions_do_not_make_a_scan_partial():
    scan = await run_scan(CLEAN_FILES, coverage={
        "excluded": {"excluded_by_extension": 40},
        "tree_truncated": False,
        "capped_over_limit": 0,
        "fetch_failures": {},
    })

    assert scan["complete"] is True


@pytest.mark.asyncio
async def test_completeness_is_the_only_field_describing_coverage():
    scan = await run_scan(CLEAN_FILES, coverage={"tree_truncated": False})
    metrics = [result["metrics"] for result in scan["axes"].values()]

    assert "complete" in scan
    assert all("sample_covers_repository" not in entry for entry in metrics)


@pytest.mark.asyncio
async def test_axes_with_issues_keep_their_status_when_coverage_is_partial():
    scan = await run_scan(FILES, coverage={"tree_truncated": True})

    assert scan["axes"]["secrets_detection"]["status"] == "issues_found"


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
            "id", "severity", "title", "rule", "file_path", "description", "code_hint",
            "source", "context", "occurrences", "locations",
        }
        assert issue["file_path"]
        assert issue["occurrences"] == len(issue["locations"])


@pytest.mark.asyncio
async def test_the_persisted_issue_carries_the_identifier_the_verdicts_key_on():
    scan = await run_scan(FILES)
    issues = to_issues(scan["axes"]["secrets_detection"])

    assert all(issue["id"] for issue in issues)
    assert {issue["id"] for issue in issues} == {
        finding["id"] for finding in scan["axes"]["secrets_detection"]["findings"]
    }


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


ADDED_FILE = {
    "path": "settings.py",
    "content": "DB = 'postgresql://user:motdepasse@db.example.com/app'\n",
}


@pytest.mark.asyncio
async def test_only_the_delta_needs_a_new_verdict_between_two_commits():
    before = findings_index(await run_scan(FILES))
    after = findings_index(await run_scan(FILES + [ADDED_FILE]))

    assert set(before) <= set(after), "un finding inchange a perdu son identifiant"

    delta = set(after) - set(before)

    assert delta
    assert all("settings.py" in identifier for identifier in delta)


@pytest.mark.asyncio
async def test_removing_a_file_only_removes_its_own_findings():
    full = findings_index(await run_scan(FILES + [ADDED_FILE]))
    reduced = findings_index(await run_scan(FILES))

    disappeared = set(full) - set(reduced)

    assert all("settings.py" in identifier for identifier in disappeared)


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
