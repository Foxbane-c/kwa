"""L'agent relecteur : en lecture seule sous Claude Code (outils et hook) comme sous Codex (bac à sable)."""
import json
import os
import subprocess
import sys
import tempfile
import unittest

from helpers import HOOKS

PACK = os.path.join(os.path.dirname(__file__), "..")
KWA = os.path.join(PACK, "bin", "kwa")


def readonly(cmd, root, policy=None):
    if policy is not None:
        os.makedirs(os.path.join(root, ".claude"), exist_ok=True)
        with open(os.path.join(root, ".claude", "kwa.policy.json"), "w") as f:
            json.dump(policy, f)
    env = {**os.environ, "CLAUDE_PROJECT_DIR": root}
    p = subprocess.run([sys.executable, os.path.join(HOOKS, "readonly-bash.py")],
                       input=json.dumps({"tool_name": "Bash", "tool_input": {"command": cmd}, "cwd": root}),
                       capture_output=True, text=True, env=env)
    assert p.returncode == 0, p.stderr
    return json.loads(p.stdout)["hookSpecificOutput"]["permissionDecision"] if p.stdout.strip() else "allow"


class ReadOnlyShell(unittest.TestCase):
    def setUp(self):
        self.root = os.path.realpath(tempfile.mkdtemp())

    def test_reading_is_allowed(self):
        for cmd in ("git diff --stat main..HEAD", "git log --oneline -5", "git show HEAD:src/a.ts",
                    "git status --short", "git branch --show-current", "grep -rn todo src | head -20",
                    "gh pr view 12 --json body", "find src -name '*.ts'", "sed -n 1,40p src/a.ts", "cat a.ts 2>/dev/null"):
            self.assertEqual(readonly(cmd, self.root), "allow", cmd)

    def test_anything_that_writes_is_refused(self):
        for cmd in ("git commit -m x", "git checkout main", "git stash", "git reset --hard", "git branch -D x",
                    "sed -i s/a/b/ f.ts", "echo x > f.ts", "cat a >> b", "ls | tee out.txt", "rm -rf build",
                    "find . -name '*.tmp' -delete", "gh pr merge 12", "npm install", "python3 -c 'open(\"f\",\"w\")'"):
            self.assertEqual(readonly(cmd, self.root), "deny", cmd)

    def test_the_project_checks_can_run(self):
        policy = {"verify": {"commands": ["pnpm test:int", "npx tsc --noEmit"]}}
        self.assertEqual(readonly("pnpm test:int", self.root, policy), "allow")
        self.assertEqual(readonly("npx tsc --noEmit", self.root, policy), "allow")
        self.assertEqual(readonly("pnpm add left-pad", self.root, policy), "deny")


class Installed(unittest.TestCase):
    def test_agent_is_installed_for_both_tools_and_read_only_in_each(self):
        d = os.path.realpath(tempfile.mkdtemp())
        subprocess.run(["git", "init", "-q", d], check=True)
        r = subprocess.run([sys.executable, KWA, "install", d, "--modules", "core,craft"], capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stderr)
        claude = open(os.path.join(d, ".claude/agents/kwa-relecteur.md"), encoding="utf-8").read()
        self.assertIn("disallowedTools: Write, Edit", claude)
        self.assertIn("readonly-bash.py", claude)
        self.assertTrue(os.path.isfile(os.path.join(d, ".claude/kwa/hooks/readonly-bash.py")))
        codex = open(os.path.join(d, ".codex/agents/kwa-relecteur.toml"), encoding="utf-8").read()
        self.assertIn('name = "kwa-relecteur"', codex)
        self.assertIn('sandbox_mode = "read-only"', codex)
        self.assertIn("developer_instructions = '''", codex)
        # la seconde installation ne réécrit rien
        r = subprocess.run([sys.executable, KWA, "install", d, "--modules", "core,craft"], capture_output=True, text=True)
        self.assertNotIn(".codex/agents/kwa-relecteur.toml", r.stdout)

    def test_skills_send_reviews_to_the_reviewer_agent(self):
        for rel in ("core/skills/review/SKILL.md", "core/skills/agents/SKILL.md",
                    "core/skills/agents/spec-reviewer-prompt.md", "core/skills/agents/quality-reviewer-prompt.md"):
            self.assertIn("kwa-relecteur", open(os.path.join(PACK, rel), encoding="utf-8").read(), rel)


class DelegationPage(unittest.TestCase):
    def test_page_explains_the_three_delegating_skills_with_its_diagram(self):
        site = os.path.join(PACK, "docs", "site")
        page = open(os.path.join(site, "delegation.html"), encoding="utf-8").read()
        for needle in ("/kwa-agents", "/kwa-parallel", "/kwa-review", "kwa-relecteur", 'id="dg"', "src/delegation.js",
                       "implementer-prompt.md", "agent-prompt.md", "reviewer-prompt.md"):
            self.assertIn(needle, page, needle)
        js = open(os.path.join(site, "src", "delegation.js"), encoding="utf-8").read()
        for st in ("skill", "prompt", "agents", "report", "check"):
            self.assertIn(f'data-st="{st}"', page, st)
        self.assertIn("prefers-reduced-motion", js)


if __name__ == "__main__":
    unittest.main()
