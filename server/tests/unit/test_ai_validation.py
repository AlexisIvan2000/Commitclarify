import json

import pytest

from services.ai import prompts
from services.ai.validation import (
    apply_verdicts,
    parse_verdicts,
    reject_invented_paths,
)

ALLOWED = {"secrets_detection:committed.env:.env:abc123", "secrets_detection:secret.openai_key:app.py:def456"}

KNOWN = next(iter(sorted(ALLOWED)))


def _response(verdicts: list[dict]) -> str:
    return json.dumps({"verdicts": verdicts})


def test_a_well_formed_response_is_accepted():
    raw = _response([{"finding_id": KNOWN, "verdict": "confirmed", "reason": "cle reelle"}])

    verdicts = parse_verdicts(raw, ALLOWED)

    assert verdicts == [{"finding_id": KNOWN, "verdict": "confirmed", "reason": "cle reelle"}]


def test_an_invented_identifier_rejects_the_whole_response():
    raw = _response([
        {"finding_id": KNOWN, "verdict": "confirmed", "reason": "ok"},
        {"finding_id": "secrets_detection:invente:nulle.part:000", "verdict": "confirmed", "reason": "x"},
    ])

    assert parse_verdicts(raw, ALLOWED) is None


def test_an_unknown_verdict_rejects_the_whole_response():
    raw = _response([{"finding_id": KNOWN, "verdict": "probablement", "reason": "x"}])

    assert parse_verdicts(raw, ALLOWED) is None


def test_malformed_json_is_rejected():
    assert parse_verdicts("pas du json", ALLOWED) is None
    assert parse_verdicts("", ALLOWED) is None
    assert parse_verdicts('{"autre": []}', ALLOWED) is None


def test_markdown_fences_are_tolerated():
    raw = "```json\n" + _response([{"finding_id": KNOWN, "verdict": "uncertain", "reason": ""}]) + "\n```"

    assert parse_verdicts(raw, ALLOWED)[0]["verdict"] == "uncertain"


@pytest.mark.parametrize("verdict", ["confirmed", "false_positive", "uncertain"])
def test_the_three_verdicts_are_all_accepted(verdict):
    raw = _response([{"finding_id": KNOWN, "verdict": verdict, "reason": "x"}])

    assert parse_verdicts(raw, ALLOWED)[0]["verdict"] == verdict


def test_a_verdict_only_depends_on_a_finding_identifier():
    raw = _response([{"finding_id": KNOWN, "verdict": "confirmed", "reason": "x"}])

    verdict = parse_verdicts(raw, ALLOWED)[0]

    assert set(verdict) == {"finding_id", "verdict", "reason"}


def test_a_false_positive_is_demoted_but_never_dropped():
    issues = [{"id": KNOWN, "severity": "critical", "title": "cle"}]
    verdicts = [{"finding_id": KNOWN, "verdict": "false_positive", "reason": "fixture"}]

    triaged = apply_verdicts(issues, verdicts)

    assert len(triaged) == 1
    assert triaged[0]["severity"] == "info"
    assert triaged[0]["original_severity"] == "critical"
    assert triaged[0]["verdict_reason"] == "fixture"


def test_an_untriaged_issue_passes_through_unchanged():
    issues = [{"id": "autre", "severity": "high", "title": "x"}]

    assert apply_verdicts(issues, []) == issues


def test_a_confirmed_issue_keeps_its_severity():
    issues = [{"id": KNOWN, "severity": "critical", "title": "cle"}]
    verdicts = [{"finding_id": KNOWN, "verdict": "confirmed", "reason": "reelle"}]

    assert apply_verdicts(issues, verdicts)[0]["severity"] == "critical"


def test_an_issue_on_an_invented_path_is_rejected():
    issues = [
        {"file_path": "src/app.py", "rule": "vrai"},
        {"file_path": "src/nexiste_pas.py", "rule": "invente"},
    ]

    kept, rejected = reject_invented_paths(issues, {"src/app.py"})

    assert [issue["rule"] for issue in kept] == ["vrai"]
    assert rejected == 1


def test_the_triage_prompt_lists_only_the_supplied_identifiers():
    findings = [
        {
            "id": KNOWN,
            "rule": "committed.env",
            "severity": "critical",
            "file_path": ".env",
            "title": "Fichier .env commite",
            "code_hint": "TOKEN=x",
            "context": None,
            "locations": [{"line": None, "evidence": ".env"}],
        },
    ]

    prompt = prompts.secrets_triage(findings, "fr")

    assert KNOWN in prompt
    assert "finding_id" in prompt
    assert "confirmed" in prompt and "false_positive" in prompt and "uncertain" in prompt


def test_the_test_context_reaches_the_prompt():
    findings = [{
        "id": KNOWN,
        "rule": "secret.aws_key",
        "severity": "critical",
        "file_path": "tests/test_agents.py",
        "title": "Cle AWS exposee",
        "code_hint": "AKIAIOSFODNN7EXAMPLE",
        "context": "test",
        "locations": [{"line": 53, "evidence": "AKIA..."}],
    }]

    prompt = prompts.secrets_triage(findings, "fr")

    assert "context=test" in prompt
    assert "lignes=53" in prompt
