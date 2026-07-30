from services.rag.indexer import build_collection_name


# Tests build_collection_name 
def test_basic_name():
    name = build_collection_name("user1234abcd", "owner/my-repo", "abcdef1234567890")
    assert name == "cc-user1234-owner-my-repo-abcdef12"


def test_slash_replaced():
    name = build_collection_name("uid", "alexis/mon-repo", "sha12345")
    assert "/" not in name


def test_underscore_replaced():
    name = build_collection_name("uid", "user/my_repo", "sha12345")
    assert "_" not in name


def test_repo_name_lowercased():
    name = build_collection_name("uid", "User/MyRepo", "sha12345")
    # seul repo_name est lowercased par la fonction
    assert "user-myrepo" in name


def test_truncated_at_63():
    long_repo = "owner/" + "a" * 100
    name = build_collection_name("user1234", long_repo, "sha1234567890")
    assert len(name) <= 63


def test_min_length():
    name = build_collection_name("u", "a/b", "c")
    assert len(name) >= 3
