from services.rag.chunker import chunk_files, _get_chunk_config, _get_separators


# Helpers 
def _make_file(path: str, content: str, language: str = "python", sha: str = "abc123") -> dict:
    return {"path": path, "content": content, "language": language, "sha": sha}


PYTHON_CODE = """
class UserService:
    def __init__(self, db):
        self.db = db

    def get_user(self, user_id):
        return self.db.query(User).filter(User.id == user_id).first()

    def create_user(self, data):
        user = User(**data)
        self.db.add(user)
        self.db.commit()
        return user
"""


#  Tests chunk_files 
def test_chunk_files_basic():
    files = [_make_file("src/service.py", PYTHON_CODE)]
    result = chunk_files(files)

    assert "code_chunks" in result
    assert "readme_chunks" in result
    assert "stats" in result
    assert result["stats"]["total_files"] == 1
    assert len(result["code_chunks"]) >= 1
    assert result["stats"]["readme_found"] is False


def test_chunk_files_readme_separated():
    readme = "# Mon Projet\n\nDescription longue du projet qui fait plus de 50 caractères pour passer le filtre."
    files = [
        _make_file("src/main.py", PYTHON_CODE),
        _make_file("README.md", readme, language="markdown"),
    ]
    result = chunk_files(files)

    assert result["stats"]["readme_found"] is True
    assert len(result["readme_chunks"]) >= 1
    assert result["readme_chunks"][0]["metadata"]["file_type"] == "readme"


def test_chunk_files_empty_file_skipped():
    files = [_make_file("empty.py", "   \n  ")]
    result = chunk_files(files)
    assert len(result["code_chunks"]) == 0


def test_chunk_files_short_content_filtered():
    files = [_make_file("tiny.py", "x = 1")]
    result = chunk_files(files)
    assert len(result["code_chunks"]) == 0


def test_chunk_metadata_fields():
    files = [_make_file("src/utils.py", PYTHON_CODE)]
    result = chunk_files(files)
    chunk = result["code_chunks"][0]

    assert "content" in chunk
    assert "metadata" in chunk
    meta = chunk["metadata"]
    assert meta["file_path"] == "src/utils.py"
    assert meta["language"] == "python"
    assert meta["file_type"] == "code"
    assert "chunk_id" in meta
    assert meta["chunk_index"] == 0


#Tests _get_chunk_config
def test_config_extension_gets_config_settings():
    config = _get_chunk_config("config/settings.json")
    assert config["chunk_size"] == 800


def test_doc_extension_gets_doc_settings():
    config = _get_chunk_config("docs/guide.md")
    assert config["chunk_size"] == 1000


def test_code_extension_gets_code_settings():
    config = _get_chunk_config("src/main.py")
    assert config["chunk_size"] == 1500


# Tests _get_separators 
def test_python_separators():
    seps = _get_separators("python")
    assert "\ndef " in seps
    assert "\nclass " in seps

def test_unknown_language_fallback():
    seps = _get_separators("cobol")
    assert "\n\n" in seps
    assert "\ndef " not in seps
