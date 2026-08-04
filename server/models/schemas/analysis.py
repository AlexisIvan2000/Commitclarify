import uuid
from datetime import datetime

from pydantic import BaseModel


class AnalysisResultResponse(BaseModel):
    id: uuid.UUID
    aspect: str
    status: str
    issues: list
    recommendations: list
    metrics: dict | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class AnalysisResponse(BaseModel):
    id: uuid.UUID
    repo_name: str
    repo_sha: str | None
    status: str
    language: str
    scan_version: int | None = None
    coverage: dict | None = None
    created_at: datetime
    completed_at: datetime | None

    model_config = {"from_attributes": True}


class AnalysisDetailResponse(AnalysisResponse):
    results: list[AnalysisResultResponse]


class QuotaResponse(BaseModel):
    used: int
    limit: int
    remaining: int
