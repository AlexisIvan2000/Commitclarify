from core.language import normalize, text
from models.db_models import Analysis


def _labelled(prefix: str, value: str, language: str | None) -> str:
    key = f"{prefix}.{value}"
    label = text(key, language)
    return value if label == key else label


def aspect_label(aspect: str, language: str | None = None) -> str:
    return _labelled("aspect", aspect, language)


def status_label(status: str, language: str | None = None) -> str:
    return _labelled("result", status, language)


def analysis_to_dict(analysis: Analysis) -> dict:
    language = normalize(getattr(analysis, "language", None))

    return {
        "repo_name": analysis.repo_name,
        "repo_sha": analysis.repo_sha,
        "status": analysis.status,
        "language": language,
        "created_at": analysis.created_at.isoformat(),
        "completed_at": analysis.completed_at.isoformat() if analysis.completed_at else None,
        "results": [
            {
                "aspect": r.aspect,
                "aspect_label": aspect_label(r.aspect, language),
                "status": r.status,
                "status_label": status_label(r.status, language),
                "issues": r.issues,
                "recommendations": r.recommendations,
            }
            for r in analysis.results
        ],
    }


def export_filename(analysis: Analysis, extension: str) -> str:
    safe_repo = analysis.repo_name.replace("/", "_")
    stamp = analysis.created_at.strftime("%Y%m%d")
    return f"commitclarify_{safe_repo}_{stamp}.{extension}"
