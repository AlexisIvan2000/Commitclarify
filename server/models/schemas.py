from pydantic import BaseModel
from datetime import datetime
import uuid

class UserResponse(BaseModel):
    id: uuid.UUID
    github_id: int
    login: str
    username : str
    avatar_url: str|None
    email: str|None
    created_at: datetime

    model_config = {"from_attributes" : True}


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"

class RefreshTokenRequest(BaseModel):
    refresh_token: str


# Analysis schemas

class AnalysisResultResponse(BaseModel):
    id: uuid.UUID
    aspect: str
    status: str
    issues: list
    recommendations: list
    created_at: datetime

    model_config = {"from_attributes": True}


class AnalysisResponse(BaseModel):
    id: uuid.UUID
    repo_name: str
    repo_sha: str | None
    status: str
    created_at: datetime
    completed_at: datetime | None

    model_config = {"from_attributes": True}


class AnalysisDetailResponse(AnalysisResponse):
    results: list[AnalysisResultResponse]