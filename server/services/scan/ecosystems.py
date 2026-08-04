from pathlib import PurePosixPath

MANIFESTS = {
    "node": {"package.json", "deno.json"},
    "python": {"requirements.txt", "pyproject.toml", "Pipfile", "setup.py", "setup.cfg"},
    "go": {"go.mod"},
    "rust": {"Cargo.toml"},
    "php": {"composer.json"},
    "ruby": {"Gemfile"},
    "java": {"pom.xml", "build.gradle"},
    "dart": {"pubspec.yaml"},
}

SOURCE_EXTENSIONS = {
    "node": {".js", ".jsx", ".mjs", ".cjs", ".ts", ".tsx", ".vue", ".svelte", ".astro"},
    "python": {".py", ".pyw", ".pyi"},
    "go": {".go"},
    "rust": {".rs"},
    "php": {".php", ".phtml"},
    "ruby": {".rb", ".rake"},
    "java": {".java", ".kt", ".kts", ".scala", ".groovy"},
    "dart": {".dart"},
}

LOCKFILES = {
    "node": {"package-lock.json", "yarn.lock", "pnpm-lock.yaml", "deno.lock"},
    "python": {"poetry.lock", "Pipfile.lock", "uv.lock", "pdm.lock"},
    "go": {"go.sum"},
    "rust": {"Cargo.lock"},
    "php": {"composer.lock"},
    "ruby": {"Gemfile.lock"},
    "dart": {"pubspec.lock"},
}

DEPENDENCY_SAMPLES = {
    "node": ("node_modules/package/index.js",),
    "python": ("__pycache__/module.cpython-313.pyc", ".venv/bin/activate"),
    "rust": ("target/debug/app",),
    "php": ("vendor/autoload.php",),
    "dart": (".dart_tool/package_config.json",),
}


def detect(paths: list[str]) -> set[str]:
    names = {PurePosixPath(path).name for path in paths}
    suffixes = {PurePosixPath(path).suffix.lower() for path in paths}

    found = set()
    for ecosystem, manifests in MANIFESTS.items():
        if names & manifests:
            found.add(ecosystem)
    for ecosystem, extensions in SOURCE_EXTENSIONS.items():
        if suffixes & extensions:
            found.add(ecosystem)

    return found


def missing_lockfiles(paths: list[str], ecosystems: set[str]) -> list[str]:
    names = {PurePosixPath(path).name for path in paths}

    return sorted(
        ecosystem
        for ecosystem in ecosystems
        if ecosystem in LOCKFILES and not names & LOCKFILES[ecosystem]
    )
