# skilldoctor

[English](README.md) | [Русский](README.ru.md)

[![CI](https://github.com/juzorei/skilldoctor/actions/workflows/ci.yml/badge.svg)](https://github.com/juzorei/skilldoctor/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/github/license/juzorei/skilldoctor)](LICENSE)
[![PyPI](https://img.shields.io/pypi/v/skilldoctor)](https://pypi.org/project/agent-skilldoctor/)

An agent skill and a CLI that audit AI-agent skill installations: broken SKILL.md files, and duplicate skills shadowing each other across install roots.

Agents discover skills from several directories, each with its own precedence. The same skill installed twice is the classic silent failure: you edit one copy, the agent loads the other — and the fix "doesn't work". A broken skill (bad frontmatter, name mismatch, empty description) never triggers at all, and the model simply doesn't use it, with no error anywhere. `skilldoctor` maps every skill directory it can find and reports both failure classes:

```text
$ skilldoctor scan
scanned 4 skill directories, found 48 skills

DUPLICATES / SHADOWING
  brainstorming
  -> wins  project zcode   C:\proj\.zcode\skills\brainstorming
           user   zcode   C:\Users\me\.zcode\skills\brainstorming
     project-level skills shadow user-level ones in agents that document precedence
```

(A real first run on a live machine found 48 skills, 13 broken, 14 conflicting duplicates — this failure class is everywhere skills are installed from multiple sources.)

## What's in the repo

- **[skills/skill-hygiene-audit](skills/skill-hygiene-audit)** — the cleanup workflow for coding agents: read the conflict reason before deleting (project-over-user shadowing vs undocumented same-scope duplicates), diff copies before removing either, fix broken frontmatter, re-scan after every install. Proposes dedupe plans; never deletes silently.
- **tools/skilldoctor** — the CLI ([README](tools/skilldoctor/README.md)): `scan` (all known layouts, project + user, exit 1 on any problem) and `check` (single-skill validation). Precedence honesty: winners marked only where the agent documents precedence; elsewhere the duplicate is reported without guessing. `--json`, stdlib only.

## Install

```bash
pip install agent-skilldoctor
npx skills add juzorei/skilldoctor
```

## Scope

Audit skill directories on machines you own; deletion is the user's call.

MIT licensed.
