---
name: skill-hygiene-audit
description: Audit AI agent skill installations — broken SKILL.md files, duplicate skills shadowing each other across directories, missing or over-long descriptions — and clean them up. Use whenever the user installs or manages skills ("npx skills add", ".claude/skills", ".codex/skills", ".agents/skills"), a skill doesn't trigger or triggers the wrong one, suspects duplicates after installing from multiple sources, asks "which skills do I have", "why doesn't my skill load", "are my skills duplicated", or maintains a skill collection and wants a health check.
---

# Skill hygiene audit

The silent failure mode of agent skills: the same skill installed in two directories — you edit one, the agent loads the other, and the fix "doesn't work". Or a broken one (bad frontmatter, name mismatch with the directory) that never triggers, so the model just... doesn't use it, with no error anywhere. This skill audits that.

Install the CLI:

```bash
pip install skilldoctor
```

## 1. Run the audit

```bash
skilldoctor scan            # project dir + user home; every agent layout it knows
```

```text
scanned 4 skill directories, found 48 skills

DUPLICATES / SHADOWING
  brainstorming
  -> wins   project zcode          C:\proj\.zcode\skills\brainstorming
            user   zcode          C:\Users\me\.zcode\skills\brainstorming
     project-level skills shadow user-level ones in agents that document precedence

BROKEN
  some-skill (C:\Users\me\.claude\skills\some-skill)
     - name 'different-name' != directory 'some-skill'
```

Exit code 1 if anything is wrong — CI-gateable. `skilldoctor check <skill-dir>` validates a single skill directory (its frontmatter, name-vs-directory, description length); `--json` everywhere for scripts.

## 2. Read the conflict reason before deleting anything

- **project shadows user** (winner marked `-> wins`): in agents that document precedence, the project-level copy is what runs. Which copy is the *maintained* one? If you updated the user-level copy and nothing changed, that's why. Fix: keep exactly one copy — the project one for repo-specific skills, the user one for personal skills — and delete the other, after diffing them (`diff -r old new`) so no local edits are lost.
- **same scope, multiple roots** (no winner claimed): agents don't document precedence between, say, `.claude/skills` and `.agents/skills`. Don't guess which one loads — dedupe until only one copy exists, or ask the agent to show which file it reads (`npx skills list`, or the agent's own skill-listing command).
- **a copy is broken:** the *broken* copy might be the one loading (or blocking the load). Fix or remove the broken copy first, then re-scan.

Never delete a skill directory without diffing it against its twin — the two copies often have different local edits, and yours may be the stale one.

## 3. Fix broken SKILL.md files

The checks are deliberately boring and mechanical:

- missing `SKILL.md` or no `---` frontmatter block — the skill is invisible to every agent.
- `name` in frontmatter doesn't match the directory name — some agents key on one, some on the other; they must agree.
- name not kebab-case — rejected or silently unreferenced.
- empty `description` — the skill never triggers, because triggering is description-driven. Write a pushy description: what it does *and* the user phrasings that should summon it.
- description over 1024 chars — some agents reject it outright.

`skilldoctor check <dir>` after every fix; commit the skill only when it reports OK.

## 4. After any install or spring cleaning, re-scan

`npx skills add` writes into the current project by default; `--global` writes to the user directory. Skills gathered from multiple sources drift. The audit is cheap (one command); run it:

- after installing skills from a new marketplace,
- after syncing skills between machines,
- when a skill you know exists doesn't trigger — the model sees only what actually loads, and a broken/duplicate skill is invisible by design.

## 5. Report

```text
hygiene:  48 skills across 4 directories
broken:   13 (frontmatter/name/description problems — each skill gets its fix listed)
dupes:    14 (5 project-over-user shadowing, 9 cross-install-root — dedupe plan with kept-copies)
done:     3 broken fixed in place, 9 stale duplicates removed after diffing, re-scan exit 0
```

## Scope

Audit skill directories on machines the user owns. Read access to skill folders is enough; deleting is the user's call — propose a dedupe plan (which copy to keep and why) instead of removing anything silently.
