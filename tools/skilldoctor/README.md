# skilldoctor

Audit AI agent skill installations: broken SKILL.md files, duplicate skills shadowing each other across install roots.

The silent failure mode of agent skills: the same skill installed in two directories — you edit one, the agent loads the other, and the fix "doesn't work". Or a broken one (bad frontmatter, name mismatch) that never triggers, so the model just doesn't use it — with no error anywhere.

```text
$ skilldoctor scan
scanned 4 skill directories, found 48 skills

DUPLICATES / SHADOWING
  brainstorming
  -> wins  project zcode   C:\proj\.zcode\skills\brainstorming
           user   zcode   C:\Users\me\.zcode\skills\brainstorming
     project-level skills shadow user-level ones in agents that document precedence

BROKEN
  some-skill (C:\Users\me\.claude\skills\some-skill)
     - name 'different-name' != directory 'some-skill'
```

- `skilldoctor scan` — every layout it knows (project + user): `.claude/skills`, `.codex/skills`, `.agents/skills`, `.zcode/skills`, `.cursor/skills`. Exit 1 if anything is wrong: CI-gateable. Conflicts come with a reason and, where the agent documents precedence, the marked winner.
- `skilldoctor check <skill-dir>` — validate one skill: frontmatter present, name matches the directory, kebab-case, description present and under 1024 chars.

The checks are deliberately mechanical — every one of them corresponds to a real "skill silently doesn't load" failure. `--json` everywhere. Python 3.11+, stdlib only.

Precedence honesty: where an agent documents `project over user`, the winner is marked. Where precedence between roots is undocumented (`.claude` vs `.agents`), skilldoctor reports the duplicate and refuses to guess — that guess is how edits get lost.

Install: `pip install skilldoctor` — or from this repo:
`pip install "git+https://github.com/juzorei/skilldoctor#subdirectory=tools/skilldoctor"`

The companion agent skill lives in [skills/skill-hygiene-audit](../skills/skill-hygiene-audit): how to read the report, dedupe without losing local edits (diff before delete), fix the broken copies, and re-scan after every install. Skills: `npx skills add juzorei/skilldoctor`.
