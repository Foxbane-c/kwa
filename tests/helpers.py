import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

# les tests ne doivent jamais interroger le vrai GitHub ; ceux qui ont besoin d'un faux `gh` fixent GH eux-mêmes
os.environ.setdefault("GH", "false")

HOOKS = os.path.join(os.path.dirname(__file__), "..", "core", "hooks")


def _symlinks_available() -> bool:
    """Windows refuse les liens symboliques hors mode développeur (WinError 1314) : testé une fois."""
    d = tempfile.mkdtemp()
    try:
        os.symlink(os.path.abspath(__file__), os.path.join(d, "lien"))
        return True
    except (OSError, NotImplementedError):
        return False
    finally:
        shutil.rmtree(d, ignore_errors=True)


SYMLINKS = _symlinks_available()


def fake_command(folder: str, name: str, script: str) -> str:
    """Un faux exécutable pour les tests (script sh). Sous Windows, un fichier sans extension ne se lance pas : un
    .cmd à côté le confie au sh de Git. Renvoie le chemin à appeler (le dossier mis dans PATH suffit aussi)."""
    path = os.path.join(folder, name)
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(script)
    os.chmod(path, 0o755)
    if os.name != "nt":
        return path
    git = shutil.which("git")
    sh = shutil.which("sh") or (git and os.path.join(os.path.dirname(os.path.dirname(git)), "bin", "sh.exe"))
    if not sh or not os.path.isfile(sh):
        raise unittest.SkipTest("sh de Git introuvable : pas de faux exécutable possible")
    with open(path + ".cmd", "w", encoding="utf-8") as f:
        f.write(f'@"{sh}" "{path.replace(os.sep, "/")}" %*\n')
    return path + ".cmd"
needs_symlinks = unittest.skipUnless(SYMLINKS, "liens symboliques indisponibles (Windows sans mode développeur)")
BASH_GUARDS = ["guard-secrets.py", "guard-git.py", "guard-delete.py", "guard-policy.py", "guard-github.py"]
RANK = {"allow": 0, "ask": 1, "deny": 2}


def call(hook, tool, tool_input, cwd, env=None):
    e = {**os.environ, "CLAUDE_PROJECT_DIR": cwd, **(env or {})}
    p = subprocess.run([sys.executable, os.path.join(HOOKS, hook)], input=json.dumps(
        {"tool_name": tool, "tool_input": tool_input, "cwd": cwd}), capture_output=True, encoding="utf-8", env=e)
    assert p.returncode == 0, p.stderr
    return json.loads(p.stdout)["hookSpecificOutput"]["permissionDecision"] if p.stdout.strip() else "allow"


def chain(cmd, cwd, env=None, guards=BASH_GUARDS):
    """Décision la plus sévère de la chaîne de gardes Bash (comme Claude Code les enchaîne)."""
    worst = "allow"
    for g in guards:
        d = call(g, "Bash", {"command": cmd}, cwd, env)
        if RANK[d] > RANK[worst]:
            worst = d
    return worst


def make_repo(policy=None, branch="main"):
    d = os.path.realpath(tempfile.mkdtemp())
    subprocess.run(["git", "init", "-q", "-b", branch, d], check=True)
    if policy:
        os.makedirs(os.path.join(d, ".claude"), exist_ok=True)
        shutil.copy(policy, os.path.join(d, ".claude", "kwa.policy.json"))
    return d
