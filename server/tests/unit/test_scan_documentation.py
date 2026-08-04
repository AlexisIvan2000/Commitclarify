from services.scan.documentation import scan_documentation


def _rules(result):
    return {finding["rule"] for finding in result["findings"]}


def _by_rule(result, rule):
    return [finding for finding in result["findings"] if finding["rule"] == rule]


def test_project_without_markdown_is_unavailable():
    result = scan_documentation([{"path": "app.py", "content": "x = 1"}])

    assert result["status"] == "unavailable"
    assert result["findings"] == []


def test_relative_link_to_a_missing_file_is_reported():
    result = scan_documentation([
        {"path": "README.md", "content": "See [the guide](docs/guide.md).\n"},
    ])

    finding = _by_rule(result, "docs.broken_link")[0]
    assert finding["line"] == 1
    assert finding["evidence"] == "docs/guide.md"


def test_relative_link_to_an_existing_file_is_not_reported():
    result = scan_documentation([
        {"path": "README.md", "content": "See [the guide](docs/guide.md).\n"},
        {"path": "docs/guide.md", "content": "# Guide\n"},
    ])

    assert _by_rule(result, "docs.broken_link") == []


def test_links_are_resolved_relative_to_their_document():
    result = scan_documentation([
        {"path": "docs/index.md", "content": "[next](guide.md)\n"},
        {"path": "docs/guide.md", "content": "# Guide\n"},
    ])

    assert _by_rule(result, "docs.broken_link") == []


def test_external_and_anchor_links_are_ignored():
    content = "[site](https://example.com) [mail](mailto:a@b.c) [top](#intro)\n"
    result = scan_documentation([{"path": "README.md", "content": content}])

    assert _by_rule(result, "docs.broken_link") == []


def test_unfetchable_targets_are_never_reported():
    content = "![logo](assets/logo.png)\n[binary](bin/tool.exe)\n[folder](docs)\n"
    result = scan_documentation([{"path": "README.md", "content": content}])

    assert _by_rule(result, "docs.broken_link") == []


def test_parent_traversal_is_ignored():
    result = scan_documentation([{"path": "README.md", "content": "[up](../other/file.md)\n"}])

    assert _by_rule(result, "docs.broken_link") == []


def test_environment_variable_read_but_never_documented_is_reported():
    result = scan_documentation([
        {"path": "README.md", "content": "# App\n"},
        {"path": "app.py", "content": "import os\n\nSECRET = os.getenv('APP_SECRET')\n"},
    ])

    finding = _by_rule(result, "docs.undocumented_env")[0]
    assert finding["evidence"] == "APP_SECRET"
    assert finding["file_path"] == "app.py"
    assert finding["line"] == 3


def test_variable_declared_in_the_example_file_is_documented():
    result = scan_documentation([
        {"path": "README.md", "content": "# App\n"},
        {"path": ".env.example", "content": "APP_SECRET=\n"},
        {"path": "app.py", "content": "import os\n\nSECRET = os.getenv('APP_SECRET')\n"},
    ])

    assert "docs.undocumented_env" not in _rules(result)


def test_variable_mentioned_in_the_readme_is_documented():
    result = scan_documentation([
        {"path": "README.md", "content": "Set APP_SECRET before starting.\n"},
        {"path": "app.py", "content": "import os\n\nSECRET = os.getenv('APP_SECRET')\n"},
    ])

    assert "docs.undocumented_env" not in _rules(result)


def test_variables_used_only_in_tests_are_never_reported():
    result = scan_documentation([
        {"path": "README.md", "content": "# App\n"},
        {"path": "tests/test_config.py", "content": "import os\nX = os.getenv('FIXTURE_KEY')\n"},
    ])

    assert "docs.undocumented_env" not in _rules(result)
    assert result["metrics"]["env_used"] == 0


def test_platform_variables_are_never_reported():
    result = scan_documentation([
        {"path": "README.md", "content": "# App\n"},
        {"path": "index.js", "content": "const mode = process.env.NODE_ENV;\n"},
    ])

    assert "docs.undocumented_env" not in _rules(result)


def test_declared_but_unused_variable_is_reported():
    result = scan_documentation([
        {"path": "README.md", "content": "# App\n"},
        {"path": ".env.example", "content": "OLD_FLAG=1\n"},
        {"path": "app.py", "content": "x = 1\n"},
    ])

    finding = _by_rule(result, "docs.unused_env")[0]
    assert finding["evidence"] == "OLD_FLAG"
    assert finding["severity"] == "low"


def test_missing_example_file_is_reported_above_the_threshold():
    code = (
        "import os\n"
        "A = os.getenv('ALPHA_KEY')\n"
        "B = os.environ['BETA_KEY']\n"
        "C = os.environ.get('GAMMA_KEY')\n"
    )
    result = scan_documentation([
        {"path": "README.md", "content": "# App\n"},
        {"path": "app.py", "content": code},
    ])

    assert "docs.no_env_example" in _rules(result)
    assert result["metrics"]["env_used"] == 3
    assert result["metrics"]["has_env_example"] is False


def test_vite_variables_are_detected():
    result = scan_documentation([
        {"path": "README.md", "content": "# App\n"},
        {"path": "src/api.js", "content": "const url = import.meta.env.VITE_API_URL;\n"},
    ])

    assert "VITE_API_URL" in {f["evidence"] for f in _by_rule(result, "docs.undocumented_env")}


def test_findings_have_unique_ids():
    result = scan_documentation([
        {"path": "README.md", "content": "[a](docs/a.md)\n[b](docs/b.md)\n"},
        {"path": "app.py", "content": "import os\nX = os.getenv('ONE')\nY = os.getenv('TWO')\n"},
    ])

    ids = [finding["id"] for finding in result["findings"]]
    assert len(ids) == len(set(ids))
    assert len(ids) >= 4
