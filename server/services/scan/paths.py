import re
from pathlib import PurePosixPath

TEST_DIR_NAMES = {"tests", "test", "__tests__", "spec", "specs", "testing"}

TEST_FILE_PATTERN = re.compile(
    r"(^|/)test_[^/]+\.py$"
    r"|_test\.(py|go|js|ts|rb)$"
    r"|\.(test|spec)\.(js|jsx|mjs|cjs|ts|tsx)$"
    r"|Test\.java$"
    r"|_spec\.rb$",
    re.IGNORECASE,
)

CI_FILE_PATTERN = re.compile(
    r"^\.github/workflows/[^/]+\.ya?ml$"
    r"|^\.gitlab-ci\.yml$"
    r"|^\.travis\.yml$"
    r"|^Jenkinsfile$"
    r"|^azure-pipelines\.ya?ml$"
    r"|^\.circleci/config\.ya?ml$"
    r"|^\.drone\.yml$"
    r"|^bitbucket-pipelines\.yml$",
)


def is_test_path(path: str) -> bool:
    parts = PurePosixPath(path).parts[:-1]
    return bool(set(parts) & TEST_DIR_NAMES) or bool(TEST_FILE_PATTERN.search(path))


def is_ci_path(path: str) -> bool:
    return bool(CI_FILE_PATTERN.match(path))
