import uuid

import pytest

from core.clock import utcnow
from core.language import DEFAULT_LANGUAGE, SUPPORTED_LANGUAGES, TEXTS, normalize, text
from models.db_models import Analysis, AnalysisResult
from services.ai.security_agent import _scan_committed_secret_files, run_gitignore_check
from services.export.pdf import generate_pdf
from services.export.serializers import analysis_to_dict, aspect_label, status_label


@pytest.mark.parametrize("value,expected", [
    ("fr", "fr"),
    ("en", "en"),
    ("EN", "en"),
    ("en-US", "en"),
    ("fr_FR", "fr"),
    ("  En  ", "en"),
    ("de", "fr"),
    ("", "fr"),
    (None, "fr"),
])
def test_normalize_language(value, expected):
    assert normalize(value) == expected


def test_every_key_is_translated_in_every_language():
    for key, entry in TEXTS.items():
        for language in SUPPORTED_LANGUAGES:
            assert entry.get(language), f"{key} manque en {language}"


def test_unknown_key_returns_the_key():
    assert text("cle.inexistante", "en") == "cle.inexistante"


def test_placeholders_are_filled():
    assert "42" in text("recommendation.ruff", "en", count=42)
    assert "42" in text("recommendation.ruff", "fr", count=42)


def test_committed_secret_title_differs_between_languages():
    files = [{"path": ".env", "content": "SECRET=abc"}]

    fr = _scan_committed_secret_files(files, "fr")[0]
    en = _scan_committed_secret_files(files, "en")[0]

    assert fr["title"] != en["title"]
    assert ".env" in fr["title"] and ".env" in en["title"]
    assert fr["rule"] == en["rule"] == "committed.env"
    assert fr["severity"] == en["severity"] == "critical"


def test_ssh_key_title_carries_the_filename():
    issue = _scan_committed_secret_files([{"path": "deploy/id_rsa", "content": "x"}], "en")[0]
    assert "id_rsa" in issue["title"]


@pytest.mark.asyncio
async def test_missing_gitignore_is_reported_in_english():
    result = await run_gitignore_check("collection", has_gitignore=False, language="en")
    issue = result["issues"][0]

    assert issue["title"] == "No .gitignore file found"
    assert issue["rule"] == "gitignore.missing"
    assert "gitignore" in result["recommendations"][0]["message"].lower()


def test_export_labels_follow_the_language():
    assert aspect_label("quality_check", "fr") == "Qualite du code"
    assert aspect_label("quality_check", "en") == "Code quality"
    assert status_label("clean", "en") == "No issue"
    assert aspect_label("aspect_inconnu", "en") == "aspect_inconnu"


def _analysis(language: str) -> Analysis:
    analysis = Analysis(
        id=uuid.uuid4(),
        user_id=uuid.uuid4(),
        repo_name="owner/repo",
        status="completed",
        language=language,
        created_at=utcnow(),
        completed_at=utcnow(),
    )
    analysis.results = [
        AnalysisResult(
            id=uuid.uuid4(),
            analysis_id=analysis.id,
            aspect="quality_check",
            status="issues_found",
            issues=[{"title": "x", "severity": "low"}],
            recommendations=[],
            created_at=utcnow(),
        )
    ]
    return analysis


def test_json_export_carries_language_and_labels():
    data = analysis_to_dict(_analysis("en"))

    assert data["language"] == "en"
    assert data["results"][0]["aspect_label"] == "Code quality"
    assert data["results"][0]["status_label"] == "Issues found"


def test_json_export_falls_back_to_default_language():
    analysis = _analysis("fr")
    analysis.language = None

    assert analysis_to_dict(analysis)["language"] == DEFAULT_LANGUAGE


def test_pdf_is_generated_in_both_languages():
    for language in SUPPORTED_LANGUAGES:
        pdf = generate_pdf(_analysis(language))
        assert pdf.startswith(b"%PDF")
        assert len(pdf) > 1000


@pytest.mark.asyncio
async def test_start_analysis_stores_the_requested_language(client, auth_headers, db):
    response = await client.post("/analyze/owner/repo?language=en", headers=auth_headers)

    assert response.status_code == 200
    assert response.json()["language"] == "en"

    from sqlalchemy import select
    stored = await db.execute(select(Analysis).where(Analysis.repo_name == "owner/repo"))
    assert stored.scalar_one().language == "en"


@pytest.mark.asyncio
async def test_start_analysis_falls_back_on_unsupported_language(client, auth_headers):
    response = await client.post("/analyze/owner/repo?language=klingon", headers=auth_headers)

    assert response.status_code == 200
    assert response.json()["language"] == DEFAULT_LANGUAGE


@pytest.mark.asyncio
async def test_conflict_carries_a_stable_code(client, auth_headers, db, test_user):
    analysis = Analysis(
        id=uuid.uuid4(),
        user_id=test_user.id,
        repo_name="owner/repo",
        status="completed",
        created_at=utcnow(),
    )
    db.add(analysis)
    await db.commit()

    response = await client.get(f"/analyze/{analysis.id}/stream", headers=auth_headers)

    assert response.status_code == 409
    assert response.json()["code"] == "analysis_finished"
