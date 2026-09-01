from services.rag.embeddings import model_tag
from services.rag.indexer import MAX_COLLECTION_NAME, build_collection_name


def test_basic_name():
    name = build_collection_name("user1234abcd", "owner/my-repo", "abcdef1234567890")
    assert name == f"cc-{model_tag()}-user1234-abcdef12-owner-my-repo"


def test_slash_replaced():
    assert "/" not in build_collection_name("uid", "alexis/mon-repo", "sha12345")


def test_underscore_replaced():
    assert "_" not in build_collection_name("uid", "user/my_repo", "sha12345")


def test_repo_name_lowercased():
    assert "user-myrepo" in build_collection_name("uid", "User/MyRepo", "sha12345")


def test_truncated_at_63():
    long_repo = "owner/" + "a" * 100
    assert len(build_collection_name("user1234", long_repo, "sha1234567890")) <= 63


def test_min_length():
    assert len(build_collection_name("u", "a/b", "c")) >= 3


def test_the_model_is_part_of_the_key():
    name = build_collection_name("user1234", "owner/repo", "abcdef1234")
    assert model_tag() in name


def test_a_long_repo_name_never_eats_the_sha():
    long_repo = "owner/" + "a" * 200
    name = build_collection_name("user1234abcd", long_repo, "abcdef1234567890")

    assert len(name) <= MAX_COLLECTION_NAME
    assert "abcdef12" in name
    assert model_tag() in name


def test_two_commits_of_a_long_repo_do_not_collide():
    long_repo = "owner/" + "a" * 200
    first = build_collection_name("user1234abcd", long_repo, "1111111111")
    second = build_collection_name("user1234abcd", long_repo, "2222222222")

    assert first != second
