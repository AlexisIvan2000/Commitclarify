import asyncio
import logging
import shutil
import tempfile
from contextlib import contextmanager
from pathlib import Path

logger = logging.getLogger(__name__)

MAX_ISSUES_PER_LINTER = 10


def select_files(files: list[dict], extensions: set[str]) -> list[dict]:
    return [
        f for f in files
        if Path(f["path"]).suffix.lower() in extensions
        and f.get("content", "").strip()
    ]


@contextmanager
def materialized_files(files: list[dict], prefix: str):
    tmp_dir = tempfile.mkdtemp(prefix=prefix)
    path_map: dict[str, str] = {}
    try:
        for f in files:
            target = Path(tmp_dir) / f["path"]
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(f["content"], encoding="utf-8")
            path_map[str(target)] = f["path"]
        yield tmp_dir, path_map
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)


async def run_tool(
    tool: str,
    args: list[str],
    cwd: str | None = None,
    expected_codes: tuple[int, ...] = (0, 1),
) -> str | None:
    try:
        proc = await asyncio.create_subprocess_exec(
            *args,
            cwd=cwd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
    except (FileNotFoundError, NotADirectoryError, PermissionError) as exc:
        logger.error("%s: executable introuvable ou non lancable (%s) — analyse ignoree", tool, exc)
        return None

    stdout, stderr = await proc.communicate()

    if proc.returncode not in expected_codes:
        logger.error(
            "%s a echoue (code=%s): %s",
            tool,
            proc.returncode,
            stderr.decode("utf-8", errors="replace").strip()[:500] or "<stderr vide>",
        )
        return None

    if stderr.strip():
        logger.warning("%s stderr: %s", tool, stderr.decode("utf-8", errors="replace").strip()[:300])

    decoded = stdout.decode("utf-8", errors="replace")
    return decoded if decoded.strip() else ""


def extract_line(file_path: str, line_number: int) -> str:
    if not isinstance(line_number, int):
        return ""
    try:
        with open(file_path, encoding="utf-8") as f:
            for i, line in enumerate(f, 1):
                if i == line_number:
                    return line.strip()
    except OSError:
        pass
    return ""
