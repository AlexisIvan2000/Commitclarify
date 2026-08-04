from services.scan.secrets import scan_secrets

REAL_KEY = "sk-abcdefghijklmnopqrstuvwxyz0123"


def _rules(result):
    return {finding["rule"] for finding in result["findings"]}


def test_committed_env_file_is_critical():
    result = scan_secrets([{"path": ".env", "content": "TOKEN=abc"}])

    finding = next(f for f in result["findings"] if f["source"] == "filename")
    assert finding["rule"] == "committed.env"
    assert finding["severity"] == "critical"
    assert finding["file_path"] == ".env"
    assert result["status"] == "issues_found"


def test_env_example_is_never_flagged():
    result = scan_secrets([{"path": ".env.example", "content": "TOKEN=your_key_here"}])

    assert result["status"] == "clean"
    assert result["findings"] == []


def test_regex_match_carries_the_line_number():
    content = f"import os\n\nAPI_KEY = '{REAL_KEY}'\n"
    result = scan_secrets([{"path": "src/config.py", "content": content}])

    finding = next(f for f in result["findings"] if f["source"] == "regex")
    assert finding["rule"] == "secret.openai_key"
    assert finding["line"] == 3
    assert REAL_KEY in finding["evidence"]


def test_secrets_in_test_files_are_reported_and_tagged():
    result = scan_secrets([{"path": "tests/test_config.py", "content": f"KEY = '{REAL_KEY}'"}])

    finding = result["findings"][0]
    assert finding["rule"] == "secret.openai_key"
    assert finding["severity"] == "critical"
    assert finding["context"] == "test"


def test_findings_outside_tests_carry_no_context():
    result = scan_secrets([{"path": "src/config.py", "content": f"KEY = '{REAL_KEY}'"}])

    assert result["findings"][0]["context"] is None


def test_obvious_fixtures_are_still_filtered_by_their_value():
    result = scan_secrets([{
        "path": "tests/test_config.py",
        "content": f"FAKE_KEY = '{REAL_KEY}'  # fake",
    }])

    assert result["status"] == "clean"


def test_placeholder_lines_are_skipped():
    result = scan_secrets([{"path": "app.py", "content": f"KEY = '{REAL_KEY}'  # changeme"}])

    assert result["status"] == "clean"


def test_connection_string_is_detected():
    content = "DB = 'postgresql://user:password@db.example.com/app'\n"
    result = scan_secrets([{"path": "settings.py", "content": content}])

    assert "secret.connection_string" in _rules(result)


def test_private_key_in_pem_file_is_reported_twice_with_distinct_ids():
    result = scan_secrets([{
        "path": "keys/server.pem",
        "content": "-----BEGIN RSA PRIVATE KEY-----\nAAAA\n",
    }])

    ids = [finding["id"] for finding in result["findings"]]
    assert len(ids) == len(set(ids))
    assert {"committed.pem", "secret.private_key"} <= _rules(result)


def test_clean_project_reports_no_finding():
    result = scan_secrets([{"path": "app.py", "content": "import os\nKEY = os.getenv('KEY')\n"}])

    assert result["status"] == "clean"
    assert result["dropped"] == 0


def test_empty_input_does_not_crash():
    assert scan_secrets([])["status"] == "clean"


def test_the_same_key_twice_in_a_file_keeps_both_lines():
    content = f"API_KEY = '{REAL_KEY}'\nimport os\n\nBACKUP = '{REAL_KEY}'\n"
    result = scan_secrets([{"path": "src/config.py", "content": content}])

    assert len(result["findings"]) == 1

    finding = result["findings"][0]
    assert finding["occurrences"] == 2
    assert [location["line"] for location in finding["locations"]] == [1, 4]


def test_identifier_survives_a_line_shift():
    line = f"API_KEY = '{REAL_KEY}'\n"
    before = scan_secrets([{"path": "src/config.py", "content": line}])
    after = scan_secrets([{"path": "src/config.py", "content": f"import os\n\n{line}"}])

    assert before["findings"][0]["line"] == 1
    assert after["findings"][0]["line"] == 3
    assert before["findings"][0]["id"] == after["findings"][0]["id"]


def test_identifier_changes_when_the_detected_content_changes():
    first = scan_secrets([{"path": "src/config.py", "content": f"A = '{REAL_KEY}'"}])
    second = scan_secrets([{"path": "src/config.py", "content": f"B = '{REAL_KEY}x'"}])

    assert first["findings"][0]["id"] != second["findings"][0]["id"]
