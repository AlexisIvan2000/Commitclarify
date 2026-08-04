import uuid
from collections.abc import Sequence

from sqlalchemy import Row, delete as sql_delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from core.clock import start_of_day, utcnow
from models.db import Analysis, AnalysisLog, AnalysisResult


async def get_owned(
    analysis_id: uuid.UUID,
    user_id: uuid.UUID,
    db: AsyncSession,
    with_results: bool = False,
) -> Analysis | None:
    query = select(Analysis).where(
        Analysis.id == analysis_id,
        Analysis.user_id == user_id,
    )
    if with_results:
        query = query.options(selectinload(Analysis.results))

    result = await db.execute(query)
    return result.scalar_one_or_none()


async def list_for_user(user_id: uuid.UUID, db: AsyncSession) -> Sequence[Analysis]:
    result = await db.execute(
        select(Analysis)
        .where(Analysis.user_id == user_id)
        .order_by(Analysis.created_at.desc())
    )
    return result.scalars().all()


async def list_vector_refs(user_id: uuid.UUID, db: AsyncSession) -> Sequence[Row]:
    result = await db.execute(
        select(Analysis.id, Analysis.repo_name, Analysis.repo_sha).where(
            Analysis.user_id == user_id
        )
    )
    return result.all()


def stage(user_id: uuid.UUID, repo_name: str, language: str, db: AsyncSession) -> Analysis:
    analysis = Analysis(
        user_id=user_id,
        repo_name=repo_name,
        status="pending",
        language=language,
    )
    db.add(analysis)
    return analysis


async def remove(analysis: Analysis, db: AsyncSession) -> None:
    await db.delete(analysis)


async def remove_all_for_user(user_id: uuid.UUID, db: AsyncSession) -> int:
    analyses = await list_for_user(user_id, db)

    for analysis in analyses:
        await db.delete(analysis)

    return len(analyses)


async def replace_results(
    analysis_id: uuid.UUID,
    results: dict[str, dict],
    db: AsyncSession,
) -> None:
    await db.execute(
        sql_delete(AnalysisResult).where(AnalysisResult.analysis_id == analysis_id)
    )

    for aspect, result in results.items():
        db.add(AnalysisResult(
            id=uuid.uuid4(),
            analysis_id=analysis_id,
            aspect=aspect,
            issues=result.get("issues", []),
            recommendations=result.get("recommendations", []),
            status=result.get("status", "clean"),
            created_at=utcnow(),
        ))


async def results_by_aspect(analysis_id: uuid.UUID, db: AsyncSession) -> dict[str, dict]:
    result = await db.execute(
        select(AnalysisResult).where(AnalysisResult.analysis_id == analysis_id)
    )

    return {
        row.aspect: {
            "status": row.status,
            "issues": row.issues or [],
            "recommendations": row.recommendations or [],
        }
        for row in result.scalars().all()
    }


async def count_runs_today(github_id: int, db: AsyncSession) -> int:
    result = await db.execute(
        select(func.count()).select_from(AnalysisLog).where(
            AnalysisLog.github_id == github_id,
            AnalysisLog.created_at >= start_of_day(),
        )
    )
    return result.scalar() or 0


def stage_run(github_id: int, db: AsyncSession) -> None:
    db.add(AnalysisLog(github_id=github_id))
