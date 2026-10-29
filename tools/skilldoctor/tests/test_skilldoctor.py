import json

import pytest

from skilldoctor.cli import main
from skilldoctor.scan import KNOWN_DIRS, candidates, parse_skill, scan


def make_skill(dir_path, name=None, description="does something", fm_name=None, extra=""):
    d = dir_path / (name or "test-skill") if name else dir_path / "test-skill"
    d.mkdir(parents=True)
    fm_name = fm_name if fm_name is not None else d.name
    body = f"---\nname: {fm_name}\ndescription: {description}\n---\n\n# {d.name}\n{extra}\n"
    (d / "SKILL.md").write_text(body, encoding="utf-8")
    return d


def pointed_roots(tmp_path):
    """Point every agent layout at fixtures under tmp_path to keep tests hermetic."""
    return {
        "claude-code": {"project": [str(tmp_path / "proj" / ".claude" / "skills")],
                        "user": [str(tmp_path / "user" / ".claude" / "skills")]},
        "agents-generic": {"project": [str(tmp_path / "proj" / ".agents" / "skills")],
                           "user": [str(tmp_path / "user" / ".agents" / "skills")]},
    }


def test_detects_project_shadowing_user(tmp_path):
    roots = pointed_roots(tmp_path)
    make_skill(tmp_path / "proj" / ".claude" / "skills", "my-skill")
    make_skill(tmp_path / "user" / ".claude" / "skills", "my-skill")
    diag = scan(roots_for=roots, base_dir=tmp_path)
    assert len(diag.conflicts) == 1
    conflict = diag.conflicts[0]
    assert conflict.winner is not None and conflict.winner.scope == "project"
    assert "shadow" in conflict.reason


def test_same_scope_duplicate_flagged_without_false_winner(tmp_path):
    roots = pointed_roots(tmp_path)
    make_skill(tmp_path / "user" / ".claude" / "skills", "dup")
    make_skill(tmp_path / "user" / ".agents" / "skills", "dup")
    diag = scan(roots_for=roots, base_dir=tmp_path)
    assert len(diag.conflicts) == 1
    assert diag.conflicts[0].winner is None
    assert "agent-specific" in diag.conflicts[0].reason


def test_no_conflict_when_clean(tmp_path):
    roots = pointed_roots(tmp_path)
    make_skill(tmp_path / "proj" / ".claude" / "skills", "alpha")
    make_skill(tmp_path / "user" / ".claude" / "skills", "beta")
    diag = scan(roots_for=roots, base_dir=tmp_path)
    assert not diag.conflicts and not diag.broken
    assert len(diag.skills) == 2


def test_broken_skill_problems(tmp_path):
    d = tmp_path / "broken"
    d.mkdir()
    (d / "SKILL.md").write_text("no frontmatter here\n", encoding="utf-8")
    meta = parse_skill(d, "claude-code", "project")
    assert not meta.ok and any("frontmatter" in p for p in meta.problems)

    d2 = tmp_path / "wrong-name"
    d2.mkdir()
    (d2 / "SKILL.md").write_text(
        "---\nname: different-name\ndescription: x\n---\n", encoding="utf-8")
    meta2 = parse_skill(d2, "claude-code", "project")
    assert any("!=" in p for p in meta2.problems)

    d3 = tmp_path / "kebab"
    d3.mkdir()
    (d3 / "SKILL.md").write_text("---\nname: BadName\ndescription: x\n---\n", encoding="utf-8")
    meta3 = parse_skill(d3, "claude-code", "project")
    assert any("kebab" in p for p in meta3.problems)


def test_missing_skillmd_is_broken(tmp_path):
    d = tmp_path / "empty"
    d.mkdir()
    meta = parse_skill(d, "claude-code", "user")
    assert meta.problems == ["missing SKILL.md"]


@pytest.mark.parametrize("long_desc", [False, True])
def test_description_length_rule(tmp_path, long_desc):
    d = tmp_path / ("long" if long_desc else "short")
    d.mkdir()
    desc = "x" * 1200 if long_desc else "short description"
    (d / "SKILL.md").write_text(
        f"---\nname: {d.name}\ndescription: {desc}\n---\n", encoding="utf-8")
    meta = parse_skill(d, "claude-code", "project")
    assert (any("1024" in p for p in meta.problems)) == long_desc


def test_same_real_dir_scanned_once(tmp_path):
    # two layouts pointing at the same resolved directory must not double-count
    target = str(tmp_path / "shared")
    roots = {"a": {"project": [target]}, "b": {"project": [target]}}
    make_skill(tmp_path / "shared", "solo")
    diag = scan(roots_for=roots, base_dir=tmp_path)
    assert len(diag.skills) == 1 and not diag.conflicts


def test_cli_scan_exit_codes(tmp_path, monkeypatch, capsys):
    import skilldoctor.scan as scanmod

    roots = pointed_roots(tmp_path)
    make_skill(tmp_path / "proj" / ".claude" / "skills", "s")
    make_skill(tmp_path / "user" / ".claude" / "skills", "s")
    monkeypatch.setattr(scanmod, "KNOWN_DIRS", roots)
    assert main(["scan", "--directory", str(tmp_path), "--json"]) == 1
    out = json.loads(capsys.readouterr().out)
    assert out["skills_total"] == 2 and out["conflicts"]

    # a clean world: no skills anywhere -> exit 0
    empty_roots = {"claude-code": {"project": [str(tmp_path / "nothing" / "here")]}}
    monkeypatch.setattr(scanmod, "KNOWN_DIRS", empty_roots)
    assert main(["scan", "--directory", str(tmp_path), "--json"]) == 0
    assert json.loads(capsys.readouterr().out)["skills_total"] == 0


def test_cli_check(tmp_path, capsys):
    ok = make_skill(tmp_path, "good-skill")
    assert main(["check", str(ok)]) == 0
    assert "OK" in capsys.readouterr().out
    assert main(["check", str(ok), "--json"]) == 0

    bad = tmp_path / "odd_name"
    bad.mkdir()
    (bad / "SKILL.md").write_text("---\nname: mismatch\n---\n", encoding="utf-8")
    assert main(["check", str(bad)]) == 1
    out = capsys.readouterr().out
    assert "mismatch" in out and "description" in out
    assert main(["check", str(tmp_path / "missing-dir")]) == 2
