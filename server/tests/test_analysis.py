import uuid
import pytest
import pytest_asyncio
from core.clock import utcnow

from models.db_models import Analysis, AnalysisResult


#  Fixtures 
@pytest_asyncio.fixture
async def sample_analysis(db, test_user) -> Analysis:
    analysis = Analysis(
        id=uuid.uuid4(),
        user_id=test_user.id,
        repo_name="owner/repo",
        status="completed",
        repo_sha="abc12345",
        created_at=utcnow(),
        completed_at=utcnow(),
    )
    db.add(analysis)
    await db.commit()
    await db.refresh(analysis)
    return analysis


@pytest_asyncio.fixture
async def analysis_with_results(db, sample_analysis) -> Analysis:
    for aspect in ["secrets_detection", "quality_check"]:
        db.add(AnalysisResult(
            id=uuid.uuid4(),
            analysis_id=sample_analysis.id,
            aspect=aspect,
            status="clean",
            issues=[],
            recommendations=[],
            created_at=utcnow(),
        ))
    await db.commit()
    return sample_analysis


#  Tests POST /analyze/{repo} 
@pytest.mark.asyncio
async def test_start_analysis(client, auth_headers):
    response = await client.post("/analyze/owner/repo", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert "analysis_id" in data
    uuid.UUID(data["analysis_id"])  # doit être un UUID valide


@pytest.mark.asyncio
async def test_start_analysis_invalid_repo(client, auth_headers):
    response = await client.post("/analyze/invalid-format", headers=auth_headers)
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_start_analysis_no_auth(client):
    response = await client.post("/analyze/owner/repo")
    assert response.status_code in (401, 403)


#  Tests GET /analyze/history
@pytest.mark.asyncio
async def test_list_analyses_empty(client, auth_headers):
    response = await client.get("/analyze/history", headers=auth_headers)
    assert response.status_code == 200
    assert response.json() == []


@pytest.mark.asyncio
async def test_list_analyses_with_data(client, auth_headers, sample_analysis):
    response = await client.get("/analyze/history", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["repo_name"] == "owner/repo"
    assert data[0]["status"] == "completed"


# Tests GET /analyze/{id} 
@pytest.mark.asyncio
async def test_get_analysis_detail(client, auth_headers, analysis_with_results):
    analysis_id = str(analysis_with_results.id)
    response = await client.get(f"/analyze/{analysis_id}", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["repo_name"] == "owner/repo"
    assert len(data["results"]) == 2


@pytest.mark.asyncio
async def test_get_analysis_not_found(client, auth_headers):
    fake_id = str(uuid.uuid4())
    response = await client.get(f"/analyze/{fake_id}", headers=auth_headers)
    assert response.status_code == 404


# Tests DELETE /analyze/{id} 
@pytest.mark.asyncio
async def test_delete_analysis(client, auth_headers, sample_analysis):
    analysis_id = str(sample_analysis.id)
    response = await client.delete(f"/analyze/{analysis_id}", headers=auth_headers)
    assert response.status_code == 200

    # Vérifier que c'est bien supprimé
    response = await client.get(f"/analyze/{analysis_id}", headers=auth_headers)
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_delete_analysis_not_found(client, auth_headers):
    fake_id = str(uuid.uuid4())
    response = await client.delete(f"/analyze/{fake_id}", headers=auth_headers)
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_delete_analysis_no_auth(client, sample_analysis):
    response = await client.delete(f"/analyze/{sample_analysis.id}")
    assert response.status_code in (401, 403)
