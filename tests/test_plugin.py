"""Plugin Kwa : généré depuis les sources, hooks filtrés par la politique du projet, `kwa init` sans script copié,
migration d'une installation par copie."""
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest

from helpers import make_repo

PACK = os.path.realpath(os.path.join(os.path.dirname(__file__), ".."))
KWA = os.path.join(PACK, "bin", "kwa")
PLUGIN = os.path.join(PACK, "plugin")
RUN = os.path.join(PLUGIN, "core", "hooks", "run.py")


def read(path, mode="r"):
    with open(path, mode, encoding=None if "b" in mode else "utf-8") as f:
        return f.read()


def kwa(*args, env=None):
    return subprocess.run([sys.executable, KWA, *args], capture_output=True, encoding="utf-8", env={**os.environ, **(env or {})})


def hook(name, payload, root, extra=None):
    """Lance un hook comme le plugin le fait ; renvoie la décision, ou "" si le hook n'a rien dit."""
    env = {**os.environ, "CLAUDE_PLUGIN_ROOT": PLUGIN, "CLAUDE_PROJECT_DIR": root, **(extra or {})}
    env.pop("KWA_RUNTIME", None)
    p = subprocess.run([sys.executable, RUN, name], input=json.dumps({"cwd": root, **payload}), capture_output=True,
                       encoding="utf-8", env=env)
    out = p.stdout.strip()
    return json.loads(out)["hookSpecificOutput"].get("permissionDecision", "context") if out else ""


def policy(root, **extra):
    os.makedirs(os.path.join(root, ".claude"), exist_ok=True)
    pol = {"kwa": 1, "protected_branches": ["main"], "write": {"no_code_on_main": ["src/"]}, **extra}
    with open(os.path.join(root, ".claude", "kwa.policy.json"), "w", encoding="utf-8") as f:
        json.dump(pol, f)


def commit_all(root):
    subprocess.run(["git", "-C", root, "add", "-A"], check=True)
    subprocess.run(["git", "-C", root, "-c", "user.name=t", "-c", "user.email=t@t.invalid", "commit", "-qm", "init",
                    "--allow-empty"], check=True)


class Build(unittest.TestCase):
    def test_published_plugin_matches_the_sources(self):
        r = kwa("build-plugin", "--check")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)

    def test_skills_use_plugin_names_and_tools(self):
        for d, _, fs in os.walk(os.path.join(PLUGIN, "skills")):
            for f in fs:
                if not f.endswith(".md"):
                    continue
                text = read(os.path.join(d, f))
                self.assertNotIn(".claude/kwa/bin", text, f)
                self.assertNotIn(".claude/rules/kwa-", text, f)
                self.assertIsNone(re.search(r"[/$]kwa-(commit|ship|tdd|learn|start-dev|review)\b", text), f)
                self.assertIsNone(re.search(r"^name: kwa-", text, re.M), f)
        self.assertIn("/kwa:start-dev", read(os.path.join(PLUGIN, "skills", "tickets", "SKILL.md")))

    def test_every_manifest_hook_runs_through_the_gate(self):
        hooks = json.loads(read(os.path.join(PLUGIN, "hooks.claude.json")))["hooks"]
        commands = [h["command"] for es in hooks.values() for e in es for h in e["hooks"]]
        self.assertTrue(all(c.startswith('python3 "${CLAUDE_PLUGIN_ROOT}/core/hooks/run.py" ') for c in commands))
        names = {c.rsplit(" ", 1)[1] for c in commands}
        man = json.loads(read(os.path.join(PACK, "manifest.json")))["modules"]
        wanted = {re.search(r"hooks/([a-z-]+)\.py", h["command"]).group(1)
                  for m in man.values() for es in m.get("hooks", {}).values() for e in es for h in e["hooks"]}
        self.assertEqual(names, wanted | {"readonly-bash"})
        sys.path.insert(0, os.path.join(PACK, "core", "hooks"))
        import run
        self.assertEqual(set(run.HOOK_MODULE), names)

    def test_reviewer_agent_loses_its_header_hooks(self):
        md = read(os.path.join(PLUGIN, "agents", "reviewer.md"))
        head = md.split("---")[1]
        self.assertIn("name: reviewer", head)
        self.assertNotIn("hooks:", head)
        self.assertIn("disallowedTools: Write, Edit", head)

    def test_both_manifests_and_the_marketplace(self):
        claude = json.loads(read(os.path.join(PLUGIN, ".claude-plugin", "plugin.json")))
        codex = json.loads(read(os.path.join(PLUGIN, ".codex-plugin", "plugin.json")))
        market = json.loads(read(os.path.join(PACK, ".claude-plugin", "marketplace.json")))
        version = read(os.path.join(PACK, "VERSION")).strip()
        self.assertEqual((claude["name"], claude["version"]), ("kwa", version))
        self.assertEqual((codex["name"], codex["skills"]), ("kwa", "./skills/"))
        self.assertEqual(market["plugins"][0]["source"], "./plugin")
        self.assertFalse(os.path.exists(os.path.join(PLUGIN, "hooks", "hooks.json")),
                         "Codex lirait hooks/hooks.json par défaut : les hooks de Claude Code ont leur propre fichier")
        for d, _, fs in os.walk(PLUGIN):
            for f in fs:
                self.assertFalse(os.path.islink(os.path.join(d, f)), "Codex supprime les liens à l'installation")

    @unittest.skipUnless(shutil.which("claude"), "Claude Code absent")
    def test_claude_validates_plugin_and_marketplace(self):
        for target in (PLUGIN, PACK):
            r = subprocess.run(["claude", "plugin", "validate", target], capture_output=True, encoding="utf-8", timeout=120)
            self.assertIn("Validation passed", r.stdout + r.stderr, target)


class EnglishIdentifiers(unittest.TestCase):
    """Skills, agents, hooks, règles, modules : des identifiants en anglais (les textes restent en français)."""

    FRENCH = re.compile(r"relecteur|remise|livr|capitalis|cadr|preuve|garde[-_]|regle|règle")

    def test_names_are_english(self):
        names = list(json.loads(read(os.path.join(PACK, "manifest.json")))["modules"])
        for d in ("core/skills", "core/agents", "core/hooks", "core/rules", "core/bin", "plugin/agents", "plugin/skills"):
            names += [os.path.splitext(n)[0] for n in os.listdir(os.path.join(PACK, d))]
        bad = sorted(n for n in names if self.FRENCH.search(n))
        self.assertEqual(bad, [])


class Gate(unittest.TestCase):
    EDIT = {"tool_name": "Edit", "tool_input": {"file_path": "src/a.py"}}

    def setUp(self):
        self.root = make_repo()
        self.EDIT = {"tool_name": "Edit", "tool_input": {"file_path": os.path.join(self.root, "src", "a.py")}}

    def test_silent_without_a_kwa_policy(self):
        self.assertEqual(hook("guard-write", self.EDIT, self.root), "")

    def test_guards_with_a_policy(self):
        policy(self.root)
        self.assertEqual(hook("guard-write", self.EDIT, self.root), "deny")

    def test_module_off_means_hook_off(self):
        policy(self.root, modules=["core"])
        self.assertEqual(hook("guard-write", self.EDIT, self.root), "deny")
        self.assertEqual(hook("guard-github", {"tool_name": "Bash", "tool_input": {"command": "gh pr create"}}, self.root), "")
        policy(self.root, modules=["core", "issue-flow"])
        self.assertEqual(hook("guard-github", {"tool_name": "Bash", "tool_input": {"command": "gh pr create"}}, self.root), "deny")

    def test_rules_reach_the_agent_without_craft(self):
        policy(self.root, modules=["core", "issue-flow"])
        env = {**os.environ, "CLAUDE_PLUGIN_ROOT": PLUGIN, "CLAUDE_PROJECT_DIR": self.root}
        p = subprocess.run([sys.executable, RUN, "skills-router"], input="{}", capture_output=True, encoding="utf-8", env=env)
        ctx = json.loads(p.stdout)["hookSpecificOutput"]["additionalContext"]
        self.assertIn("Discipline git", ctx)
        self.assertNotIn("/kwa:tdd", ctx)
        self.assertNotIn(".claude/kwa/bin", ctx, "les règles injectées nomment les outils du plugin")
        self.assertIn("kwa start", ctx)

    def test_copy_install_keeps_its_own_hooks(self):
        policy(self.root)
        os.makedirs(os.path.join(self.root, ".claude", "kwa", "hooks", "__pycache__"))
        self.assertEqual(hook("guard-write", self.EDIT, self.root), "deny", "un dossier resté vide ne coupe pas le plugin")
        with open(os.path.join(self.root, ".claude", "kwa", "state.json"), "w", encoding="utf-8") as f:
            f.write("{}")
        self.assertEqual(hook("guard-write", self.EDIT, self.root), "")

    def test_read_only_only_for_the_reviewer(self):
        policy(self.root)
        rm = {"tool_name": "Bash", "tool_input": {"command": "rm -rf src"}}
        self.assertEqual(hook("readonly-bash", rm, self.root), "")
        self.assertEqual(hook("readonly-bash", {**rm, "agent_type": "kwa:reviewer"}, self.root), "deny")

    def test_worktree_without_committed_policy_uses_the_main_one(self):
        commit_all(self.root)
        wt = self.root + "-wt"
        subprocess.run(["git", "-C", self.root, "worktree", "add", "-q", "-b", "fix/x", wt], check=True)
        policy(self.root)  # la politique n'existe que dans le dépôt principal
        secret = os.path.join(wt, "." + "e" + "nv")
        self.assertFalse(os.path.exists(os.path.join(wt, ".claude", "kwa.policy.json")))
        self.assertEqual(hook("guard-secrets", {"tool_name": "Read", "tool_input": {"file_path": secret}}, wt), "deny")

    def test_router_lists_plugin_skill_names_and_rules(self):
        policy(self.root, modules=["core", "craft", "issue-flow"])
        env = {**os.environ, "CLAUDE_PLUGIN_ROOT": PLUGIN, "CLAUDE_PROJECT_DIR": self.root}
        p = subprocess.run([sys.executable, RUN, "skills-router"], input="{}", capture_output=True, encoding="utf-8", env=env)
        ctx = json.loads(p.stdout)["hookSpecificOutput"]["additionalContext"]
        self.assertIn("/kwa:tdd", ctx)
        self.assertIn("/kwa:start-dev", ctx)
        self.assertNotIn("/kwa-tdd", ctx)
        self.assertNotIn("/kwa:learn", ctx, "module memory inactif : sa skill n'est pas proposée")
        self.assertIn("Discipline git", ctx)


class Init(unittest.TestCase):
    def setUp(self):
        self.t = make_repo()
        os.makedirs(os.path.join(self.t, "src"))

    def files(self):
        return sorted(os.path.relpath(os.path.join(d, f), self.t) for d, _, fs in os.walk(self.t) if "/.git" not in d + "/"
                      for f in fs)

    def test_init_writes_configuration_only(self):
        r = kwa("init", self.t)
        self.assertEqual(r.returncode, 0, r.stderr)
        files = self.files()
        self.assertFalse([f for f in files if f.endswith(".py") or "/kwa/hooks" in f or "/skills/" in f], files)
        settings = json.loads(read(os.path.join(self.t, ".claude", "settings.json")))
        self.assertTrue(settings["enabledPlugins"]["kwa@kwa"])
        self.assertEqual(settings["extraKnownMarketplaces"]["kwa"]["source"], {"source": "github", "repo": "nesyouyou/kwa"})
        self.assertIn("core", json.loads(read(os.path.join(self.t, ".claude", "kwa.policy.json")))["modules"])
        agents = read(os.path.join(self.t, "AGENTS.md"))
        self.assertIn("/kwa:commit", agents)
        self.assertNotIn(".claude/kwa/hooks", agents)
        codex = read(os.path.join(self.t, ".codex", "hooks.json"))
        self.assertIn("kwa hook guard-git", codex)
        self.assertNotIn(".claude/kwa/hooks", codex)
        self.assertEqual(kwa("doctor", self.t).returncode, 0)

    def test_init_twice_changes_nothing(self):
        kwa("init", self.t)
        before = {f: read(os.path.join(self.t, f), "rb") for f in self.files() if ".bak-" not in f}
        kwa("init", self.t)
        after = {f: read(os.path.join(self.t, f), "rb") for f in self.files() if ".bak-" not in f}
        self.assertEqual(before, after)

    def test_init_migrates_a_copy_install(self):
        self.assertEqual(kwa("install", self.t).returncode, 0)
        skill = os.path.join(self.t, ".claude", "skills", "kwa-commit", "SKILL.md")
        with open(skill, "a", encoding="utf-8") as f:
            f.write("retouche locale\n")
        r = kwa("init", self.t)
        self.assertIn("installation par copie retirée", r.stdout)
        left = [f for f in self.files() if "backup" not in f and ".bak-" not in f]
        self.assertFalse([f for f in left if f.startswith((".claude/kwa/hooks", ".claude/skills", ".claude/rules",
                                                           ".agents/"))], left)
        saved = [f for f in self.files() if f.startswith(".claude/kwa/backup/") and f.endswith("kwa-commit/SKILL.md")]
        self.assertTrue(saved and "retouche locale" in read(os.path.join(self.t, saved[0])))
        settings = json.loads(read(os.path.join(self.t, ".claude", "settings.json")))
        self.assertNotIn("hooks", settings, "la clé hooks vidée par la migration disparaît")
        self.assertEqual(kwa("doctor", self.t).returncode, 0)

    def test_rerun_keeps_the_chosen_modules(self):
        kwa("install", self.t, "--with", "client-handover")
        kwa("init", self.t)
        first = json.loads(read(os.path.join(self.t, ".claude", "kwa.policy.json")))["modules"]
        kwa("init", self.t)
        self.assertEqual(json.loads(read(os.path.join(self.t, ".claude", "kwa.policy.json")))["modules"], first)
        self.assertIn("client-handover", first)
        self.assertTrue(os.access(os.path.join(self.t, ".claude", "kwa", "bin", "kwa-hygiene"), os.X_OK),
                        "la CI de remise lance kwa-hygiene : il reste un fichier du projet")

    def test_init_unplugs_copy_hooks_left_in_settings(self):
        kwa("install", self.t)
        settings = read(os.path.join(self.t, ".claude", "settings.json"))
        kwa("init", self.t)
        with open(os.path.join(self.t, ".claude", "settings.json"), "w", encoding="utf-8") as f:  # réglages restaurés après migration
            f.write(settings)
        kwa("init", self.t)
        self.assertNotIn(".claude/kwa/hooks", read(os.path.join(self.t, ".claude", "settings.json")))

    def test_copy_install_leaves_no_python_cache_nor_codex_hooks(self):
        kwa("install", self.t)
        os.makedirs(os.path.join(self.t, ".claude", "kwa", "hooks", "__pycache__"))
        with open(os.path.join(self.t, ".claude", "kwa", "hooks", "__pycache__", "_kwa.cpython-312.pyc"), "w", encoding="utf-8") as f:
            f.write("x")
        kwa("init", self.t, "--no-codex")
        self.assertFalse(os.path.exists(os.path.join(self.t, ".claude", "kwa", "hooks")))
        self.assertNotIn(".claude/kwa/hooks", read(os.path.join(self.t, ".codex", "hooks.json")))

    def test_init_migrates_the_old_kata_name(self):
        kwa("install", self.t)
        claude = os.path.join(self.t, ".claude")
        os.rename(os.path.join(claude, "kwa"), os.path.join(claude, "kata"))  # une installation sous l'ancien nom
        with open(os.path.join(claude, "kata", "state.json"), encoding="utf-8") as f:
            state = json.load(f)
        state["files"] = {k.replace(".claude/kwa/", ".claude/kata/"): v for k, v in state["files"].items()}
        with open(os.path.join(claude, "kata", "state.json"), "w", encoding="utf-8") as f:
            json.dump(state, f)
        settings = read(os.path.join(claude, "settings.json")).replace(".claude/kwa/hooks/", ".claude/kata/hooks/")
        with open(os.path.join(claude, "settings.json"), "w", encoding="utf-8") as f:
            f.write(settings)
        pol = json.loads(read(os.path.join(claude, "kwa.policy.json")))
        pol["bash"]["deny"].append({"id": "proj-x", "pattern": "^make prod", "reason": "x"})
        os.remove(os.path.join(claude, "kwa.policy.json"))
        with open(os.path.join(claude, "kata.policy.json"), "w", encoding="utf-8") as f:
            json.dump({"kata": 1, **{k: v for k, v in pol.items() if k != "kwa"}}, f)
        r = kwa("init", self.t)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertNotIn(".claude/kata/", read(os.path.join(claude, "settings.json")))
        self.assertFalse(os.path.exists(os.path.join(claude, "kata", "hooks")))
        self.assertIn("proj-x", read(os.path.join(claude, "kwa.policy.json")), "les règles du projet sont reprises")
        self.assertEqual(kwa("doctor", self.t).returncode, 0, kwa("doctor", self.t).stdout)

    def test_the_kwa_shipped_in_the_plugin_can_init(self):
        r = subprocess.run([sys.executable, os.path.join(PLUGIN, "bin", "kwa"), "init", self.t], capture_output=True, encoding="utf-8")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertTrue(os.path.exists(os.path.join(self.t, ".codex", "agents", "kwa-reviewer.toml")))

    def test_init_removes_the_renamed_codex_agent(self):
        old = os.path.join(self.t, ".codex", "agents", "kwa-relecteur.toml")
        os.makedirs(os.path.dirname(old))
        with open(old, "w", encoding="utf-8") as f:
            f.write("# Géré par Kwa (kwa install) : généré depuis .claude/agents/kwa-relecteur.md, ne pas éditer.\n")
        kwa("init", self.t)
        self.assertFalse(os.path.exists(old))
        self.assertTrue(os.path.exists(os.path.join(self.t, ".codex", "agents", "kwa-reviewer.toml")))

    def test_kwa_hook_and_tools_pass_through(self):
        kwa("init", self.t)
        p = subprocess.run([sys.executable, KWA, "hook", "guard-write"], input=json.dumps(
            {"tool_name": "Edit", "tool_input": {"file_path": os.path.join(self.t, "src", "a.py")}, "cwd": self.t}),
            capture_output=True, encoding="utf-8", env={**os.environ, "KWA_PROJECT_DIR": self.t, "CLAUDE_PROJECT_DIR": ""})
        self.assertIn('"deny"', p.stdout)
        self.assertIn("/kwa:start-dev", p.stdout)
        r = kwa("memory", "--help")
        self.assertIn("kwa-memory", r.stdout + r.stderr)


if __name__ == "__main__":
    unittest.main()
