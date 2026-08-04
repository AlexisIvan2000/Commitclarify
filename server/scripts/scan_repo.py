import argparse
import asyncio
import json
import logging
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


def parse_arguments() -> argparse.Namespace:
    from core.language import SUPPORTED_LANGUAGES

    parser = argparse.ArgumentParser(
        description="Lance le scan deterministe sur un depot GitHub distant et rend le JSON brut.",
    )
    parser.add_argument("repository", help="owner/repo")
    parser.add_argument("--branch", default="HEAD")
    parser.add_argument("--language", default="fr", choices=SUPPORTED_LANGUAGES)
    parser.add_argument("--token", default=os.getenv("GITHUB_TOKEN"))
    parser.add_argument("--output", type=Path)
    parser.add_argument("--summary", action="store_true")
    parser.add_argument("--verbose", action="store_true")
    return parser.parse_args()


def build_coverage(repo_data: dict) -> dict:
    stats = repo_data["stats"]

    return {
        "sha": repo_data["sha"],
        "tracked_files": stats["tracked"],
        "eligible_files": stats["total_detected"],
        "fetched_files": stats["fetched"],
        "excluded": stats["excluded"],
        "fetch_failures": stats["fetch_failures"],
        "fetched_detail": stats["fetched_detail"],
        "capped_over_limit": stats["capped_over_limit"],
        "tree_truncated": repo_data["truncated"],
    }


def print_summary(scan: dict) -> None:
    coverage = scan["coverage"]
    print(f"scan_version={scan['scan_version']}  langue={scan['language']}")
    print(
        f"couverture: {coverage['fetched_files']}/{coverage['eligible_files']} fichiers analyses "
        f"sur {coverage['tracked_files']} versionnes"
        + ("  [ARBRE TRONQUE PAR GITHUB]" if coverage["tree_truncated"] else "")
        + (
            f"  [{coverage['capped_over_limit']} FICHIERS AU-DELA DU PLAFOND]"
            if coverage["capped_over_limit"] else ""
        )
    )
    if not scan["complete"]:
        print("  couverture incomplete : les axes sans probleme sont marques 'partial'")
    for reason, count in sorted(coverage["excluded"].items()):
        print(f"  ecartes  {reason:26} {count}")
    for reason, count in sorted(coverage["fetch_failures"].items()):
        print(f"  echecs   {reason:26} {count}")
    for reason, count in sorted(coverage["fetched_detail"].items()):
        print(f"  dont     {reason:26} {count}  (inclus dans les fichiers analyses)")
    print(f"findings: {scan['summary']['findings']}  ignores: {scan['summary']['dropped']}")
    print(f"severites: {scan['summary']['by_severity']}\n")

    for axis, result in scan["axes"].items():
        print(f"=== {axis} [{result['status']}] dropped={result['dropped']}")
        for finding in result["findings"]:
            location = finding["file_path"] or "-"
            if finding["line"]:
                location = f"{location}:{finding['line']}"
            context = f" ({finding['context']})" if finding["context"] else ""
            print(f"  [{finding['severity']:8}] {finding['rule']:34} {location}{context}")
            print(f"             {finding['title']}")
            print(f"             id={finding['id']}")
        print()


async def main() -> int:
    from services.github.repo_fetcher import fetch_repo_files
    from services.scan import run_scan

    arguments = parse_arguments()
    logging.basicConfig(
        level=logging.INFO if arguments.verbose else logging.WARNING,
        format="%(levelname)s %(name)s: %(message)s",
    )

    if not arguments.token:
        print("Token GitHub absent : passez --token ou definissez GITHUB_TOKEN.", file=sys.stderr)
        return 2

    if "/" not in arguments.repository:
        print("Le depot doit etre au format owner/repo.", file=sys.stderr)
        return 2

    owner, repo = arguments.repository.split("/", 1)

    from services.github.client import GitHubError

    try:
        repo_data = await fetch_repo_files(owner, repo, arguments.token, arguments.branch)
    except GitHubError as error:
        print(f"HTTP {error.status} sur {error.url}", file=sys.stderr)
        print(str(error), file=sys.stderr)
        return 1
    except ValueError as error:
        print(f"Echec de la recuperation: {error}", file=sys.stderr)
        return 1

    scan = await run_scan(
        repo_data["files"],
        arguments.language,
        tracked_paths=repo_data["tracked_paths"],
        coverage=build_coverage(repo_data),
    )

    payload = json.dumps(scan, indent=2, ensure_ascii=False)

    if arguments.output:
        arguments.output.write_text(payload, encoding="utf-8")
        print(f"Scan ecrit dans {arguments.output}")
    elif not arguments.summary:
        print(payload)

    if arguments.summary:
        print_summary(scan)

    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
