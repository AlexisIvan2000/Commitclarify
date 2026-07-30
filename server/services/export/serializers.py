from models.db_models import Analysis

ASPECT_LABELS = {
    "secrets_detection": "Detection de secrets",
    "gitignore_check": "Verification .gitignore",
    "quality_check": "Qualite du code",
    "readme_check": "README vs Code",
}

STATUS_LABELS = {
    "clean": "Aucun probleme",
    "issues_found": "Problemes detectes",
    "unavailable": "Non disponible",
    "error": "Erreur pendant l'analyse",
}


def analysis_to_dict(analysis: Analysis) -> dict:
    return {
        "repo_name": analysis.repo_name,
        "repo_sha": analysis.repo_sha,
        "status": analysis.status,
        "created_at": analysis.created_at.isoformat(),
        "completed_at": analysis.completed_at.isoformat() if analysis.completed_at else None,
        "results": [
            {
                "aspect": r.aspect,
                "status": r.status,
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
