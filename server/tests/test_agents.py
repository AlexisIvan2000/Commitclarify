import pytest
from unittest.mock import AsyncMock, patch

from services.ai.security_agent import run_secrets_detection, run_gitignore_check
from services.ai.consistency_agent import run_quality_check, run_readme_check


# Fixtures 
CLEAN_RESPONSE = '{"status": "clean", "issues": [], "recommendations": []}'

ISSUES_RESPONSE = """{
    "status": "issues_found",
    "issues": [{"severity": "high", "title": "Hardcoded API key", "file_path": "config.py", "description": "API key found", "code_hint": "KEY = sk-xxx"}],
    "recommendations": [{"priority": "high", "message": "Use env variables"}]
}"""

MOCK_CHUNKS = [
    {"content": "API_KEY = 'sk-test123'", "metadata": {"file_path": "config.py"}, "similarity": 0.95}
]


# Tests run_secrets_detection
@pytest.mark.asyncio
@patch("services.ai.security_agent.generate", new_callable=AsyncMock, return_value=CLEAN_RESPONSE)
@patch("services.ai.security_agent.retrieve_chunks", return_value=MOCK_CHUNKS)
@patch("services.ai.security_agent.get_embedding", new_callable=AsyncMock, return_value=[0.1] * 768)
async def test_secrets_detection_clean(mock_embed, mock_retrieve, mock_generate):
    result = await run_secrets_detection("test-collection")
    assert result["status"] == "clean"
    assert result["issues"] == []


@pytest.mark.asyncio
@patch("services.ai.security_agent.generate", new_callable=AsyncMock, return_value=ISSUES_RESPONSE)
@patch("services.ai.security_agent.retrieve_chunks", return_value=MOCK_CHUNKS)
@patch("services.ai.security_agent.get_embedding", new_callable=AsyncMock, return_value=[0.1] * 768)
async def test_secrets_detection_issues(mock_embed, mock_retrieve, mock_generate):
    result = await run_secrets_detection("test-collection")
    assert result["status"] == "issues_found"
    assert len(result["issues"]) == 1


#  Tests run_gitignore_check 
@pytest.mark.asyncio
async def test_gitignore_no_file():
    result = await run_gitignore_check("test-collection", has_gitignore=False)
    assert result["status"] == "issues_found"
    assert any("gitignore" in i["title"].lower() for i in result["issues"])

@pytest.mark.asyncio
@patch("services.ai.security_agent.generate", new_callable=AsyncMock, return_value=CLEAN_RESPONSE)
@patch("services.ai.security_agent.retrieve_chunks", return_value=MOCK_CHUNKS)
@patch("services.ai.security_agent.get_embedding", new_callable=AsyncMock, return_value=[0.1] * 768)
async def test_gitignore_with_file(mock_embed, mock_retrieve, mock_generate):
    result = await run_gitignore_check("test-collection", has_gitignore=True)
    assert result["status"] == "clean"


# Tests run_quality_check
@pytest.mark.asyncio
@patch("services.ai.consistency_agent.run_ruff_on_files", new_callable=AsyncMock, return_value=[])
@patch("services.ai.consistency_agent.generate", new_callable=AsyncMock, return_value='{"issues": []}')
@patch("services.ai.consistency_agent.retrieve_chunks", return_value=MOCK_CHUNKS)
@patch("services.ai.consistency_agent.get_embedding", new_callable=AsyncMock, return_value=[0.1] * 768)
async def test_quality_check_clean(mock_embed, mock_retrieve, mock_generate, mock_ruff):
    result = await run_quality_check("test-collection", [])
    assert result["status"] == "clean"


#  Tests run_readme_check 
@pytest.mark.asyncio
async def test_readme_check_no_readme():
    result = await run_readme_check("test-collection", readme_chunks=[])
    assert result["status"] == "unavailable"


@pytest.mark.asyncio
@patch("services.ai.consistency_agent.generate", new_callable=AsyncMock, return_value=CLEAN_RESPONSE)
@patch("services.ai.consistency_agent.retrieve_chunks", return_value=MOCK_CHUNKS)
@patch("services.ai.consistency_agent.get_embedding", new_callable=AsyncMock, return_value=[0.1] * 768)
async def test_readme_check_with_readme(mock_embed, mock_retrieve, mock_generate):
    readme_chunks = [{"content": "# My Project\n\nA cool project with API endpoints."}]
    result = await run_readme_check("test-collection", readme_chunks)
    assert result["status"] == "clean"


#  Tests parse_response fallback
def test_parse_invalid_json():
    from services.ai.llm import parse_response
    result = parse_response("not json at all")
    assert result["status"] == "clean"
    assert "error" in result


def test_parse_with_markdown_fence():
    from services.ai.llm import parse_response
    raw = '```json\n{"status": "clean", "issues": [], "recommendations": []}\n```'
    result = parse_response(raw)
    assert result["status"] == "clean"


# Tests format_chunks

def test_format_chunks():
    from services.ai.llm import format_chunks
    chunks = [
        {"content": "def foo(): pass", "metadata": {"file_path": "main.py"}},
        {"content": "x = 1", "metadata": {"file_path": "config.py"}},
    ]
    result = format_chunks(chunks)
    assert "### main.py" in result
    assert "### config.py" in result
    assert "def foo(): pass" in result
