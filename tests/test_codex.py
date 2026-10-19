"""Codex : les mêmes gardes protègent, avec les charges que Codex envoie réellement.

Codex lance les hooks avec KWA_AGENT=codex et KWA_PROJECT_DIR (voir kwa install --codex), sans CLAUDE_PROJECT_DIR.
Il édite les fichiers par apply_patch (le patch est dans tool_input.command) et ne sait pas demander une
confirmation : une demande doit y devenir un refus, jamais un passage.
"""
import json
import os
import subprocess
import sys
import tempfile
import unittest

from helpers import HOOKS

sys.path.insert(0, HOOKS)
import _kwa  # noqa: E402

SECRET_FILE = ".e" + "nv"
FAKE_TOKEN = "gh" + "p_" + "a1B2" * 9


def repo(branch="main"):
    d = os.path.realpath(tempfile.mkdtemp())
    subprocess.run(["git", "init", "-q", "-b", branch, d], check=True)
    os.makedirs(os.path.join(d, ".claude"))
    with open(os.path.join(d, ".claude", "kwa.policy.json"), "w", encoding="utf-8") as f:
        json.dump({"write": {"no_code_on_main": ["src/"]}}, f)
    return d


def run(hook, payload, root, codex=True):
    env = {k: v for k, v in os.environ.items() if k not in ("CLAUDE_PROJECT_DIR", "KWA_AGENT", "KWA_PROJECT_DIR")}
    if codex:
        env.update(KWA_AGENT="codex", KWA_PROJECT_DIR=root)
    else:
        env["CLAUDE_PROJECT_DIR"] = root
    p = subprocess.run([sys.executable, os.path.join(HOOKS, hook)], input=json.dumps({"cwd": root, **payload}),
                       capture_output=True, encoding="utf-8", env=env, cwd=root)
    assert p.returncode == 0, p.stderr
    if not p.stdout.strip():
        return "allow", ""
    out = json.loads(p.stdout)["hookSpecificOutput"]
    return out["permissionDecision"], out["permissionDecisionReason"]


def patch(*lines):
    return {"tool_name": "apply_patch", "tool_input": {"command": "\n".join(["*** Begin Patch", *lines, "*** End Patch"])}}


class Confirmations(unittest.TestCase):
    """Sous Claude Code, le hook demande. Sous Codex, le hook ne sait pas demander : soit une règle de commandes de
    Codex couvre la commande (Codex demandera), soit le hook refuse. Jamais un passage silencieux."""

    def test_push_is_asked_by_claude_and_left_to_the_codex_rule(self):
        d = repo("feat/x")
        bash = {"tool_name": "Bash", "tool_input": {"command": "git push origin feat/x"}}
        self.assertEqual(run("guard-git.py", bash, d, codex=False)[0], "ask")
        self.assertEqual(run("guard-git.py", bash, d)[0], "allow")
        self.assertTrue(_kwa.codex_covers("git push origin feat/x", {}))

    def test_what_codex_cannot_split_is_refused(self):
        d = repo("feat/x")
        for cmd in ("git push origin $(git branch --show-current)", "cd sub && git push origin feat/x", "FOO=1 git push"):
            decision, reason = run("guard-git.py", {"tool_name": "Bash", "tool_input": {"command": cmd}}, d)
            self.assertEqual(decision, "deny", cmd)
            self.assertIn("Codex", reason)

    def test_project_rules_reach_codex_through_codex_prompt(self):
        policy = {"bash": {"ask": [{"id": "deploy", "reason": "déploiement direct", "any": ["scw container"],
                                    "codex_prompt": [["scw", "container", "container", ["update", "deploy"]]]}]}}
        self.assertTrue(_kwa.codex_covers("scw container container deploy abc", policy))
        self.assertFalse(_kwa.codex_covers("scw container container list", policy))
        d = repo("feat/x")
        with open(os.path.join(d, ".claude", "kwa.policy.json"), "w", encoding="utf-8") as f:
            json.dump(policy, f)
        bash = {"tool_name": "Bash", "tool_input": {"command": "scw container container deploy abc"}}
        self.assertEqual(run("guard-policy.py", bash, d, codex=False)[0], "ask")
        self.assertEqual(run("guard-policy.py", bash, d)[0], "allow")


class ApplyPatch(unittest.TestCase):
    def test_parser_reads_files_kinds_moves_and_added_lines(self):
        p = patch("*** Add File: src/a.ts", "+export const a = 1;", "*** Update File: docs/b.md", "@@", "-old", "+new",
                  "*** Move to: docs/c.md", "*** Delete File: old.txt")
        got = _kwa.edits({"cwd": "/r", **p})
        self.assertEqual([(os.path.relpath(x, "/r").replace(os.sep, "/"), k) for x, _, k in got],
                         [("src/a.ts", "add"), ("docs/b.md", "update"), ("docs/c.md", "add"), ("old.txt", "delete")])
        self.assertEqual(got[0][1], "export const a = 1;")
        self.assertIn("new", got[1][1])
        self.assertNotIn("old", got[1][1])

    def test_no_code_on_main(self):
        d = repo("main")
        self.assertEqual(run("guard-write.py", patch("*** Add File: src/a.ts", "+x"), d)[0], "deny")
        self.assertEqual(run("guard-write.py", patch("*** Add File: docs/a.md", "+x"), d)[0], "allow")

    def test_code_is_fine_on_a_work_branch(self):
        d = repo("feat/x")
        self.assertEqual(run("guard-write.py", patch("*** Add File: src/a.ts", "+x"), d)[0], "allow")

    def test_secret_in_clear_is_refused(self):
        d = repo("feat/x")
        self.assertEqual(run("guard-write.py", patch("*** Add File: src/c.ts", f"+const t = '{FAKE_TOKEN}';"), d)[0], "deny")

    def test_secret_file_is_refused_even_when_deleted_or_moved_to(self):
        d = repo("feat/x")
        self.assertEqual(run("guard-write.py", patch(f"*** Delete File: {SECRET_FILE}"), d)[0], "deny")
        self.assertEqual(run("guard-write.py", patch("*** Update File: notes.txt", "*** Move to: " + SECRET_FILE), d)[0], "deny")

    def test_guard_configuration_is_refused_not_silently_allowed(self):
        d = repo("feat/x")
        decision, reason = run("guard-write.py", patch("*** Update File: .claude/kwa/hooks/guard-git.py", "+pass"), d)
        self.assertEqual(decision, "deny")
        self.assertIn("Codex", reason)

    def test_claude_payloads_still_work(self):
        d = repo("main")
        write = {"tool_name": "Write", "tool_input": {"file_path": os.path.join(d, "src", "a.ts"), "content": "x"}}
        self.assertEqual(run("guard-write.py", write, d, codex=False)[0], "deny")


class Router(unittest.TestCase):
    def test_skills_are_named_with_a_dollar_under_codex(self):
        d = repo("feat/x")
        os.makedirs(os.path.join(d, ".claude", "kwa"))
        os.makedirs(os.path.join(d, ".claude", "skills", "kwa-commit"))
        with open(os.path.join(d, ".claude", "kwa", "router.md"), "w", encoding="utf-8") as f:
            f.write("Invoque la skill avant d'agir.\n\n| Quand | Skill |\n|---|---|\n| Committer | /kwa-commit |\n")
        env = {k: v for k, v in os.environ.items() if k != "CLAUDE_PROJECT_DIR"}
        env.update(KWA_AGENT="codex", KWA_PROJECT_DIR=d)
        p = subprocess.run([sys.executable, os.path.join(HOOKS, "skills-router.py")], input=json.dumps({"cwd": d}),
                           capture_output=True, encoding="utf-8", env=env)
        ctx = json.loads(p.stdout)["hookSpecificOutput"]["additionalContext"]
        self.assertIn("$kwa-commit", ctx)
        self.assertNotIn("/kwa-commit", ctx)


class ManualSkills(unittest.TestCase):
    def test_every_manual_skill_stays_manual_under_codex(self):
        skills = os.path.join(os.path.dirname(__file__), "..", "core", "skills")
        for name in sorted(os.listdir(skills)):
            text = open(os.path.join(skills, name, "SKILL.md"), encoding="utf-8").read()
            yaml = os.path.join(skills, name, "agents", "openai.yaml")
            if "disable-model-invocation: true" in text:
                self.assertTrue(os.path.isfile(yaml), name)
                self.assertIn("allow_implicit_invocation: false", open(yaml, encoding="utf-8").read(), name)


if __name__ == "__main__":
    unittest.main()
