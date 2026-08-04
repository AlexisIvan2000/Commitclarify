from services.scan.gitignore import scan_gitignore


def _rules(result):
    return {finding["rule"] for finding in result["findings"]}


def _by_rule(result, rule):
    return [finding for finding in result["findings"] if finding["rule"] == rule]


def test_an_empty_gitignore_is_not_reported_as_missing():
    result = scan_gitignore([
        {"path": ".gitignore", "content": ""},
        {"path": "app.py", "content": "x = 1"},
    ])

    assert "gitignore.missing" not in _rules(result)
    assert result["metrics"]["gitignore_files"] == 1
    assert result["metrics"]["rules"] == 0
    assert _by_rule(result, "gitignore.rule_missing")


def test_missing_gitignore_is_the_only_finding():
    result = scan_gitignore([{"path": "app.py", "content": "x = 1"}])

    assert _rules(result) == {"gitignore.missing"}
    assert result["metrics"]["gitignore_files"] == 0


def test_tracked_sensitive_file_without_rule_is_critical():
    result = scan_gitignore([
        {"path": ".gitignore", "content": "*.log\n"},
        {"path": ".env", "content": "TOKEN=abc"},
    ])

    finding = _by_rule(result, "gitignore.unprotected")[0]
    assert finding["severity"] == "critical"
    assert finding["file_path"] == ".env"


def test_tracked_file_covered_by_a_rule_is_reported_as_already_committed():
    result = scan_gitignore([
        {"path": ".gitignore", "content": ".env\n"},
        {"path": ".env", "content": "TOKEN=abc"},
    ])

    assert "gitignore.unprotected" not in _rules(result)
    finding = _by_rule(result, "gitignore.tracked_ignored")[0]
    assert finding["severity"] == "high"
    assert finding["file_path"] == ".env"


def test_negation_keeps_the_example_file_out_of_the_findings():
    result = scan_gitignore([
        {"path": ".gitignore", "content": ".env*\n!.env.example\n"},
        {"path": ".env.example", "content": "TOKEN=your_key"},
    ])

    assert _by_rule(result, "gitignore.tracked_ignored") == []


def test_negation_order_matters_like_in_git():
    reversed_rules = scan_gitignore([
        {"path": ".gitignore", "content": "!.env.example\n.env.*\n"},
        {"path": ".env.example", "content": "TOKEN=your_key"},
    ])

    assert _by_rule(reversed_rules, "gitignore.tracked_ignored")


def test_negation_under_an_excluded_directory_stays_excluded():
    result = scan_gitignore([
        {"path": ".gitignore", "content": "build/\n!build/keep.md\n"},
        {"path": "build/keep.md", "content": "# keep"},
    ])

    assert _by_rule(result, "gitignore.tracked_ignored")


def test_nested_gitignore_only_applies_below_its_directory():
    files = [
        {"path": ".gitignore", "content": "*.log\n"},
        {"path": "backend/.gitignore", "content": "config.json\n"},
        {"path": "backend/config.json", "content": "{}"},
        {"path": "frontend/config.json", "content": "{}"},
    ]

    tracked = [finding["file_path"] for finding in _by_rule(scan_gitignore(files), "gitignore.tracked_ignored")]

    assert "backend/config.json" in tracked
    assert "frontend/config.json" not in tracked


def test_node_project_without_node_modules_rule_is_reported():
    result = scan_gitignore([
        {"path": ".gitignore", "content": ".env\n"},
        {"path": "package.json", "content": "{}"},
        {"path": "src/app.js", "content": "var x = 1;"},
    ])

    missing = {finding["evidence"] for finding in _by_rule(result, "gitignore.rule_missing")}
    assert "node_modules" in missing


def test_rule_findings_have_distinct_ids():
    result = scan_gitignore([
        {"path": ".gitignore", "content": "*.log\n"},
        {"path": "package.json", "content": "{}"},
        {"path": "main.py", "content": "x = 1"},
    ])

    ids = [finding["id"] for finding in result["findings"]]
    assert len(ids) == len(set(ids))
    assert len(_by_rule(result, "gitignore.rule_missing")) >= 3


def test_standard_rules_are_checked_against_each_gitignore_directory():
    result = scan_gitignore([
        {"path": "server/.gitignore", "content": ".env\n__pycache__/\n.venv/\n"},
        {"path": "server/app.py", "content": "x = 1"},
    ])

    assert _by_rule(result, "gitignore.rule_missing") == []


def test_a_rule_missing_from_every_gitignore_is_still_reported():
    result = scan_gitignore([
        {"path": "server/.gitignore", "content": "__pycache__/\n.venv/\n"},
        {"path": "server/app.py", "content": "x = 1"},
    ])

    assert {f["evidence"] for f in _by_rule(result, "gitignore.rule_missing")} == {".env"}


def test_complete_gitignore_reports_nothing():
    result = scan_gitignore([
        {"path": ".gitignore", "content": ".env\n__pycache__/\n.venv/\n"},
        {"path": "main.py", "content": "x = 1"},
    ])

    assert result["status"] == "clean"


def test_tracked_paths_can_be_wider_than_the_fetched_files():
    result = scan_gitignore(
        [{"path": ".gitignore", "content": "*.log\n"}],
        tracked_paths=["node_modules/left-pad/index.js"],
    )

    assert _by_rule(result, "gitignore.tracked_ignored") == []
    assert result["metrics"]["gitignore_files"] == 1
