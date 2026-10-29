"""skilldoctor CLI: audit agent skill directories for broken, duplicate and shadowed skills."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from . import __version__
from .scan import Diagnosis, scan


def _skill_json(s):
    return {"name": s.name, "agent": s.agent, "scope": s.scope, "path": str(s.path),
            "ok": s.ok, "problems": s.problems}


def _conflict_json(c):
    return {"name": c.name, "reason": c.reason,
            "winner": str(c.winner.path) if c.winner else None,
            "copies": [_skill_json(s) for s in c.copies]}


def diag_json(diag: Diagnosis) -> dict:
    return {
        "dirs_scanned": len(diag.scanned_dirs),
        "skills_total": len(diag.skills),
        "broken": [_skill_json(s) for s in diag.broken],
        "conflicts": [_conflict_json(c) for c in diag.conflicts],
    }


def cmd_scan(args) -> int:
    diag = scan(base_dir=Path(args.directory).resolve() if args.directory else None)
    if args.json:
        print(json.dumps(diag_json(diag), indent=2))
    else:
        print(f"scanned {len(diag.scanned_dirs)} skill directories, found {len(diag.skills)} skills\n")
        if diag.conflicts:
            print("DUPLICATES / SHADOWING")
            for c in diag.conflicts:
                print(f"  {c.name}")
                for s in c.copies:
                    mark = "-> wins " if c.winner is s else "          "
                    print(f"  {mark}{s.scope:<7} {s.agent:<13} {s.path}")
                print(f"     {c.reason}")
            print()
        if diag.broken:
            print("BROKEN")
            for s in diag.broken:
                print(f"  {s.name} ({s.path})")
                for p in s.problems:
                    print(f"     - {p}")
            print()
        if not diag.conflicts and not diag.broken:
            print("clean: no duplicates, no broken skills")
    has_issues = bool(diag.conflicts or diag.broken)
    return 1 if has_issues else 0


def cmd_check(args) -> int:
    """Check one skill directory: frontmatter validity and lint rules."""
    from .scan import MAX_DESCRIPTION, NAME_RE, frontmatter

    path = Path(args.skill_dir)
    skill_md = path / "SKILL.md"
    problems = []
    if not path.is_dir():
        print(f"skilldoctor: error: {path} is not a directory", file=sys.stderr)
        return 2
    if not skill_md.is_file():
        print(json.dumps({"ok": False, "problems": ["missing SKILL.md"]}) if args.json
              else "BROKEN: missing SKILL.md")
        return 1
    fm = frontmatter(skill_md.read_text(encoding="utf-8", errors="replace"))
    if fm is None:
        problems.append("no frontmatter block")
        fm = {}
    name = str(fm.get("name", "")).strip()
    desc = str(fm.get("description", "")).strip()
    if not name:
        problems.append("missing name")
    else:
        if name != path.name:
            problems.append(f"name {name!r} != directory {path.name!r}")
        if not NAME_RE.match(name):
            problems.append(f"name {name!r} is not kebab-case")
    if not desc:
        problems.append("empty description (the skill will never trigger)")
    elif len(desc) > MAX_DESCRIPTION:
        problems.append(f"description {len(desc)} chars (>{MAX_DESCRIPTION}: may be rejected by some agents)")
    if args.json:
        print(json.dumps({"ok": not problems, "problems": problems}, indent=2))
    else:
        print("OK" if not problems else "BROKEN")
        for p in problems:
            print(f"  - {p}")
    return 1 if problems else 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="skilldoctor", description=__doc__)
    parser.add_argument("--version", action="version", version=f"skilldoctor {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("scan", help="scan all known skill directories (project + user) for conflicts")
    p.add_argument("--directory", help="project root to scan (default: cwd)")
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=cmd_scan)

    p = sub.add_parser("check", help="validate one skill directory's SKILL.md")
    p.add_argument("skill_dir")
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=cmd_check)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        return args.func(args)
    except OSError as exc:
        print(f"skilldoctor: error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
