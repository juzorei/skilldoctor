"""skilldoctor: find broken, duplicate and shadowed agent skills across install directories.

Agents discover skills from several directories, each with its own precedence.
The same skill name installed twice is the classic silent failure: the editor
changes one copy, the agent loads the other. skilldoctor maps every skill
directory it can find and reports the conflicts.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

NAME_RE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
MAX_DESCRIPTION = 1024

# Discovery layouts, by agent. Precedence order documented per agent; where an
# agent's docs don't specify precedence between dirs, we report duplicates
# without claiming which one wins (`winner` is None).
KNOWN_DIRS = {
    "claude-code": {"project": [".claude/skills"], "user": ["~/.claude/skills"]},
    "codex": {"project": [".codex/skills"], "user": ["~/.codex/skills"]},
    "agents-generic": {"project": [".agents/skills"], "user": ["~/.agents/skills"]},
    "zcode": {"project": [".zcode/skills"], "user": ["~/.zcode/skills"]},
    "cursor": {"project": [".cursor/skills"], "user": []},
}


@dataclass
class SkillMeta:
    name: str
    path: Path
    description: str = ""
    problems: list[str] = field(default_factory=list)
    agent: str = ""
    scope: str = ""          # project | user

    @property
    def ok(self) -> bool:
        return not self.problems


def frontmatter(text: str) -> dict | None:
    text = text.replace("\r\n", "\n")
    if not text.startswith("---"):
        return None
    end = text.find("\n---", 3)
    if end < 0:
        return None
    block = text[3:end].strip("\n")
    fields: dict[str, str] = {}
    for line in block.splitlines():
        key, sep, value = line.partition(":")
        if sep and not line.startswith((" ", "\t")):
            fields[key.strip()] = value.strip()
    return fields


def parse_skill(path: Path, agent: str, scope: str) -> SkillMeta:
    meta = SkillMeta(name=path.name, path=path, agent=agent, scope=scope)
    skill_md = path / "SKILL.md"
    if not skill_md.is_file():
        meta.problems.append("missing SKILL.md")
        return meta
    text = skill_md.read_text(encoding="utf-8", errors="replace")
    fm = frontmatter(text)
    if fm is None:
        meta.problems.append("SKILL.md has no frontmatter block")
        return meta
    declared = str(fm.get("name", "")).strip()
    desc = str(fm.get("description", "")).strip()
    if not declared:
        meta.problems.append("frontmatter has no name")
    else:
        if declared != path.name:
            meta.problems.append(f"name {declared!r} != directory {path.name!r}")
        if not NAME_RE.match(declared):
            meta.problems.append(f"name {declared!r} is not kebab-case")
    if not desc:
        meta.problems.append("empty description (never triggers)")
    elif len(desc) > MAX_DESCRIPTION:
        meta.problems.append(f"description {len(desc)} chars (>{MAX_DESCRIPTION}: may be rejected)")
    meta.description = desc
    meta.name = declared or path.name
    return meta


def candidates(roots_for: dict[str, dict[str, list[str]]] | None = None,
               base_dir: Path | None = None) -> list[tuple[str, str, Path]]:
    """Yield (agent, scope, directory) for every configured layout."""
    layouts = roots_for or KNOWN_DIRS
    base = base_dir or Path.cwd()
    home = Path.home()
    out = []
    for agent, scopes in layouts.items():
        for scope, dirs in scopes.items():
            for d in dirs:
                expanded = Path(d)
                if str(expanded).startswith("~"):
                    expanded = home / str(expanded)[2:]
                if not expanded.is_absolute():
                    expanded = base / expanded
                out.append((agent, scope, expanded))
    return out


@dataclass
class Diagnosis:
    @dataclass
    class Conflict:
        name: str
        copies: list[SkillMeta]
        winner: SkillMeta | None = None
        reason: str = ""

    skills: list[SkillMeta] = field(default_factory=list)
    conflicts: list[Conflict] = field(default_factory=list)
    scanned_dirs: list[Path] = field(default_factory=list)

    @property
    def broken(self) -> list[SkillMeta]:
        return [s for s in self.skills if not s.ok]


def scan(roots_for: dict | None = None, base_dir: Path | None = None) -> Diagnosis:
    diag = Diagnosis()
    # project scope beats user scope across agents that document precedence;
    # within the same scope, agent-specific dirs win over the generic .agents
    order = {"project": 0, "user": 1}
    by_name: dict[str, list[SkillMeta]] = {}
    rank: dict[int, int] = {}
    seen_dirs = set()
    for agent, scope, d in candidates(roots_for, base_dir):
        if not d.is_dir():
            continue
        real = d.resolve()
        if real in seen_dirs:
            continue
        seen_dirs.add(real)
        diag.scanned_dirs.append(d)
        for child in sorted(p for p in d.iterdir() if p.is_dir()):
            skill = parse_skill(child, agent, scope)
            diag.skills.append(skill)
            by_name.setdefault(skill.name, []).append(skill)
    for name, copies in by_name.items():
        if len(copies) < 2:
            continue
        # winner: project scope first; then non-generic agent; then earlier layout
        def rank_of(s: SkillMeta, i: int):
            return (order.get(s.scope, 2), 1 if s.agent == "agents-generic" else 0, i)
        winner = None
        if all(s.ok for s in copies):
            candidate_scopes = {s.scope for s in copies}
            if len(candidate_scopes) > 1:
                winner = min(copies, key=lambda s: order.get(s.scope, 1))
                reason = "project-level skills shadow user-level ones in agents that document precedence"
            else:
                reason = "same skill in multiple install roots; which one wins is agent-specific — dedupe to be safe"
        else:
            reason = "at least one copy is broken; the working copy may still be shadowed"
        diag.conflicts.append(Diagnosis.Conflict(name, copies, winner, reason))
    return diag
