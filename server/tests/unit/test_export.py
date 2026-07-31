import uuid

from core.clock import utcnow
from models.db_models import Analysis, AnalysisResult
from services.export.pdf import generate_pdf
from services.export.serializers import analysis_to_dict, export_filename

LONG_TEXT = (
    "Une recommandation volontairement tres longue pour verifier que le retour a la ligne "
    "fonctionne et que le contenu ne sort pas de la page ni ne se fait tronquer en silence. " * 4
)


def _analysis(results) -> Analysis:
    analysis = Analysis(
        id=uuid.uuid4(),
        user_id=uuid.uuid4(),
        repo_name="owner/mon-repo",
        repo_sha="abcdef1234567890",
        status="completed",
        created_at=utcnow(),
        completed_at=utcnow(),
    )
    analysis.results = results
    return analysis


def _result(aspect, issues=None, recommendations=None) -> AnalysisResult:
    return AnalysisResult(
        id=uuid.uuid4(),
        analysis_id=uuid.uuid4(),
        aspect=aspect,
        status="issues_found" if issues else "clean",
        issues=issues or [],
        recommendations=recommendations or [],
        created_at=utcnow(),
    )


def test_pdf_is_generated():
    analysis = _analysis([
        _result("secrets_detection", issues=[{
            "severity": "critical",
            "title": "Fichier .env commite dans le depot",
            "file_path": ".env",
            "description": "...",
            "code_hint": "OPENAI_API_KEY=sk-xxxx",
        }]),
        _result("quality_check", recommendations=[{"priority": "medium", "message": LONG_TEXT}]),
        _result("readme_check"),
    ])

    pdf = generate_pdf(analysis)

    assert pdf.startswith(b"%PDF")
    assert pdf.rstrip().endswith(b"%%EOF")
    assert len(pdf) > 1000


def test_pdf_handles_empty_results():
    pdf = generate_pdf(_analysis([]))
    assert pdf.startswith(b"%PDF")


def test_pdf_handles_malformed_issue():
    analysis = _analysis([_result("quality_check", issues=[{"message": "sans titre ni severite"}])])
    assert generate_pdf(analysis).startswith(b"%PDF")


def test_pdf_paginates_on_many_issues():
    issues = [
        {
            "severity": "medium",
            "title": f"Probleme numero {i}",
            "file_path": f"src/module_{i}.py",
            "description": "...",
            "code_hint": f"ligne {i}",
        }
        for i in range(80)
    ]
    pdf = generate_pdf(_analysis([_result("quality_check", issues=issues)]))
    assert pdf.count(b"/Type /Page") > 1


def test_json_export_shape():
    analysis = _analysis([_result("gitignore_check", issues=[{"title": "x"}])])
    data = analysis_to_dict(analysis)

    assert data["repo_name"] == "owner/mon-repo"
    assert data["repo_sha"] == "abcdef1234567890"
    assert data["results"][0]["aspect"] == "gitignore_check"
    assert data["results"][0]["issues"] == [{"title": "x"}]


def test_export_filename_is_filesystem_safe():
    analysis = _analysis([])
    name = export_filename(analysis, "pdf")

    assert "/" not in name
    assert name.startswith("commitclarify_owner_mon-repo_")
    assert name.endswith(".pdf")
