"""Briques communes des gardes Kwa. Bibliothèque standard uniquement.

Doctrine : ce sont des filets contre la bévue, pas une frontière de sécurité contre
un agent compromis. Ils échouent vers l'humain (« ask »), jamais en silence.
"""
from __future__ import annotations

import json
import os
import re
import shlex
import sys

WRAPPERS = {"env", "nice", "nohup", "sudo", "time", "command", "builtin", "exec", "xargs", "timeout", "doas"}
SHELLS = {"bash", "sh", "zsh", "dash", "ksh"}
SEP_RE = re.compile(r"\|\||&&|[;&|\n]")
SUBST_RE = re.compile(r"\$\(([^()]*)\)|`([^`]*)`")


_LAST: dict = {}  # dernière charge lue : sert au signal de refus (session, commande)


def load_payload() -> dict:
    try:
        data = json.load(sys.stdin)
    except ValueError:
        return {}
    if isinstance(data, dict):
        _LAST.update(data)
    return data


def _log_refusal(reason: str) -> None:
    """Un refus est le signal d'apprentissage le plus fiable : l'erreur que le projet voulait éviter. Jamais bloquant."""
    try:
        import _journal  # module memory : absent ailleurs, sans conséquence

        root = project_dir(_LAST)
        # seulement là où Kwa est installé : un garde lancé hors installation (tests, essai à la main) n'écrit rien
        installed = os.environ.get("KWA_RUNTIME") == "plugin" or any(
            os.path.exists(os.path.join(r, ".claude", "kwa", "state.json")) for r in (root, _journal.main_root(root)))
        if not (_journal.enabled() and installed):
            return
        tool = _LAST.get("tool_input") or {}
        _journal.append_signal(root, "refus", session=_journal._sid(_LAST), key=reason,
                               text=str(tool.get("command") or tool.get("file_path") or ""))
    except Exception:  # noqa: BLE001
        pass


# Ce que Kwa fait confirmer et que Codex sait confirmer lui-même, par ses règles de commandes (.codex/rules/kwa.rules,
# écrit par kwa install). Sous Codex, une demande couverte par une de ces règles laisse passer le hook : c'est Codex
# qui demande. Une demande non couverte devient un refus. (motif, raison, exemple qui doit correspondre)
CODEX_PROMPTS = [
    (["git", "push"], "Kwa : publier une branche demande confirmation.", "git push origin feat/x"),
    (["git", "reset", "--hard"], "Kwa : git reset --hard détruit les modifications non commitées.", "git reset --hard HEAD"),
    (["git", "clean"], "Kwa : git clean supprime des fichiers non suivis.", "git clean -fd"),
    (["git", "branch", ["-d", "-D", "--delete"]], "Kwa : suppression de branche.", "git branch -D feat/x"),
    (["gh", "pr", "merge"], "Kwa : fusionner une PR, c'est publier.", "gh pr merge 12"),
]
PLAIN_RE = re.compile(r"[$`<>*?(){}\[\]\n&|;\\]")


def codex_prompts(policy: dict) -> list[tuple[list, str, str]]:
    """Règles de confirmation pour Codex : les fixes de Kwa, puis les motifs `codex_prompt` des règles bash.ask."""
    out = list(CODEX_PROMPTS)
    for rule in (policy.get("bash") or {}).get("ask", []):
        for pattern in rule.get("codex_prompt", []):
            out.append((pattern, f"Kwa [{rule.get('id', 'politique')}] : {rule.get('reason', 'confirmer')}", ""))
    return out


def codex_covers(command: str, policy: dict) -> bool:
    """Vrai si Codex confirmera lui-même cette commande : une seule commande simple (Codex ne découpe pas les scripts
    avec substitution, redirection ou variable) dont les mots commencent par un motif de codex_prompts."""
    if not command or PLAIN_RE.search(command) or re.match(r"^\s*[A-Za-z_][A-Za-z0-9_]*=", command):
        return False
    try:
        argv = shlex.split(command)
    except ValueError:
        return False
    for pattern, _reason, _example in codex_prompts(policy):
        if len(argv) >= len(pattern) and all(a == p or (isinstance(p, list) and a in p) for a, p in zip(argv, pattern)):
            return True
    return False


def cli(tool: str) -> str:
    """Comment l'agent lance un outil de Kwa (memory, start, hygiene) : `kwa <outil>` quand Kwa vient du plugin,
    le script copié dans le projet sinon."""
    return f"kwa {tool}" if os.environ.get("KWA_RUNTIME") == "plugin" else f"python3 .claude/kwa/bin/kwa-{tool}"


def skill(name: str) -> str:
    """Nom d'une skill tel que l'agent la lance : /kwa:learn (plugin), /kwa-learn (copie) ; $ au lieu de / sous Codex."""
    sigil = "$" if is_codex() else "/"
    return f"{sigil}kwa:{name}" if os.environ.get("KWA_RUNTIME") == "plugin" else f"{sigil}kwa-{name}"


def is_codex() -> bool:
    """Les hooks branchés pour Codex sont lancés avec KWA_AGENT=codex (voir kwa install --codex)."""
    return os.environ.get("KWA_AGENT") == "codex"


def decide(decision: str, reason: str) -> None:
    """decision: deny | ask. Sort avec le code 0 après avoir imprimé la décision.
    Les hooks de Codex ne savent pas demander une confirmation : « ask » y passerait. Si une règle de commandes de Codex
    couvre la commande, on laisse Codex demander ; sinon on refuse, en disant pourquoi."""
    if decision == "ask" and is_codex():
        if codex_covers(str((_LAST.get("tool_input") or {}).get("command") or ""), load_policy(_LAST)):
            sys.exit(0)  # Codex demandera lui-même confirmation (règle de .codex/rules/kwa.rules)
        decision = "deny"
        reason = (f"{reason} (Codex ne peut pas demander confirmation pour cette action : refusé par prudence ; "
                  "si c'est voulu, l'utilisateur la lance lui-même)")
    if decision == "deny":
        _log_refusal(reason)
    print(json.dumps({"hookSpecificOutput": {
        "hookEventName": "PreToolUse",
        "permissionDecision": decision,
        "permissionDecisionReason": f"Kwa — {reason}",
    }}, ensure_ascii=False))
    sys.exit(0)


def guarded(main) -> None:
    """Exécute le garde ; une erreur interne ouvre une demande humaine au lieu de laisser passer."""
    try:
        main()
    except SystemExit:
        raise
    except Exception as e:  # noqa: BLE001
        decide("ask", f"le garde a échoué ({type(e).__name__}) ; valider à la main")


def segments(command: str, _depth: int = 0) -> list[list[str]]:
    """Découpe une commande shell en segments de mots, en dépliant bash -c / env / nice / sudo…
    Un guillemet cassé (ex. .e''nv) est recollé par shlex ; un échec de parsing renvoie le mot brut."""
    out: list[list[str]] = []
    if _depth == 0:
        command = strip_heredocs(command)
    if _depth < 4:  # substitutions $(…) et `…` : leur contenu est une commande à part entière
        for m in SUBST_RE.finditer(command):
            out += segments(m.group(1) or m.group(2) or "", _depth + 1)
    for raw in SEP_RE.split(command):
        raw = raw.strip()
        if not raw:
            continue
        try:
            words = shlex.split(raw, posix=True)
        except ValueError:
            words = raw.split()
        if words:
            words[0] = words[0].lstrip("({")
            words[-1] = words[-1].rstrip(")}") or words[-1]
            words = [w for w in words if w]
        # affectations VAR=val en tête, mots de contrôle shell
        while words and (re.match(r"^[A-Za-z_][A-Za-z0-9_]*=", words[0]) or words[0] in {"then", "do", "else", "if", "while", "!"}):
            words = words[1:]
        while words and os.path.basename(words[0]) in WRAPPERS:
            words = words[1:]
            while words and (words[0].startswith("-") or re.match(r"^[A-Za-z_][A-Za-z0-9_]*=", words[0]) or re.match(r"^\d+$", words[0])):
                words = words[1:]
        if not words:
            continue
        if os.path.basename(words[0]) in SHELLS and _depth < 4:
            if "-c" in words and words.index("-c") + 1 < len(words):
                out += segments(words[words.index("-c") + 1], _depth + 1)
                continue
        out.append(words)
    return out


def project_dir(payload: dict) -> str:
    return os.path.realpath(os.environ.get("CLAUDE_PROJECT_DIR") or os.environ.get("KWA_PROJECT_DIR")
                            or payload.get("cwd") or os.getcwd())


PATCH_FILE_RE = re.compile(r"^\*\*\* (Add|Update|Delete) File: (.+)$")
PATCH_MOVE_RE = re.compile(r"^\*\*\* Move to: (.+)$")


def edits(payload: dict) -> list[tuple[str, str, str]]:
    """Fichiers qu'une écriture touche : (chemin absolu, texte ajouté, nature).

    Claude Code envoie file_path et le contenu (Write, Edit, MultiEdit, NotebookEdit). Codex envoie un patch
    apply_patch dans tool_input.command ; on en lit les fichiers (« *** Add File: », « *** Update File: »,
    « *** Delete File: », « *** Move to: ») et les lignes ajoutées. nature : add, update, delete ou write."""
    ti = payload.get("tool_input") or {}
    base = payload.get("cwd") or os.getcwd()
    command = ti.get("command") if isinstance(ti.get("command"), str) else ""
    if payload.get("tool_name") == "apply_patch" or command.lstrip().startswith("*** Begin Patch"):
        out: list[list] = []
        for line in command.splitlines():
            m = PATCH_FILE_RE.match(line)
            if m:
                out.append([os.path.join(base, m.group(2).strip()), [], m.group(1).lower()])
                continue
            m = PATCH_MOVE_RE.match(line)
            if m and out:
                out.append([os.path.join(base, m.group(1).strip()), out[-1][1], "add"])
                continue
            if out and line.startswith("+") and not line.startswith("+++"):
                out[-1][1].append(line[1:])
        return [(p, "\n".join(lines), kind) for p, lines, kind in out]
    path = ti.get("file_path") or ti.get("notebook_path") or ""
    texts = [ti.get("content", ""), ti.get("new_string", ""), ti.get("new_source", "")]
    texts += [e.get("new_string", "") for e in ti.get("edits", []) if isinstance(e, dict)]
    path = os.path.join(base, path) if path and not os.path.isabs(path) else path
    return [(path, "\n".join(t for t in texts if t), "write")] if (path or any(texts)) else []


# --- corps de heredoc : une DONNÉE (doc, message de commit citant un motif), sauf s'il est exécuté.
HEREDOC_RE = re.compile(r"<<-?[ \t]*[\"']?([A-Za-z_][A-Za-z0-9_]*)[\"']?")
INTERP_RE = re.compile(r"(^|[ \t|;&(])(ba|z|k)?sh([ \t]|$)|python[0-9.]*|node|ruby|perl|eval|xargs")


def strip_heredocs(command: str) -> str:
    """Retire le corps des heredocs non exécutés. `bash <<EOF … EOF` reste inspecté en entier,
    sinon ce serait un contournement trivial."""
    out, delim = [], None
    for line in command.split("\n"):
        if delim is not None:
            if line.strip() == delim:
                delim = None
            continue
        out.append(line)
        m = HEREDOC_RE.search(line)
        if m and not heredoc_is_executed(line, m):
            delim = m.group(1)
    return "\n".join(out)


STAGE_SEP = re.compile(r"\|\||&&|[;&|(`]")
PIPED_INTERP = re.compile(r"\|\s*(?:sudo\s+|env\s+)*(?:(?:ba|z|k)?sh|python[0-9.]*|node|ruby|perl|xargs)\b")


def heredoc_is_executed(line: str, m: "re.Match") -> bool:
    """Le corps est exécuté si la commande qui porte le heredoc est un interpréteur (`python3 - <<EOF`, `bash <<EOF`)
    ou si elle est enchaînée par un tube vers un interpréteur (`cat <<EOF | bash`). Les autres commandes de la même
    ligne (`python3 build.py ; git commit -F - <<EOF`) ne comptent pas : le corps reste une donnée."""
    own = STAGE_SEP.split(line[:m.start()])[-1]
    return bool(INTERP_RE.search(own) or PIPED_INTERP.search(line[m.end():]))


# --- politique projet : .claude/kwa.policy.json, propriété du projet (jamais écrasée par kwa)
def load_policy(payload: dict) -> dict:
    path = os.environ.get("KWA_POLICY") or os.path.join(project_dir(payload), ".claude", "kwa.policy.json")
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}


def glob_match(path: str, pattern: str) -> bool:
    """`**` traverse les dossiers, `*` reste dans un dossier. Le motif est ancré sur la fin ou le chemin relatif."""
    rx, i = "", 0
    while i < len(pattern):
        if pattern.startswith("**/", i):
            rx += "(?:.*/)?"; i += 3
        elif pattern.startswith("**", i):
            rx += ".*"; i += 2
        elif pattern[i] == "*":
            rx += "[^/]*"; i += 1
        elif pattern[i] == "?":
            rx += "[^/]"; i += 1
        else:
            rx += re.escape(pattern[i]); i += 1
    return re.search(rf"(^|/){rx}$", path) is not None


# --- fichiers de secrets (partagé par guard-secrets et guard-write)
SAFE_SUFFIX = re.compile(r"\.(example|sample|template|dist|defaults?)$", re.I)
SECRET_PATH = [
    re.compile(r"(^|/)\.env([._-].*)?$", re.I),
    re.compile(r"(^|/)[^/]+\.env$", re.I),
    re.compile(r"(^|/)\.envrc$", re.I),
    re.compile(r"(^|/)id_(rsa|dsa|ecdsa|ed25519)(\.pub)?$"),
    re.compile(r"(^|/)\.ssh/"),
    re.compile(r"(^|/)\.(netrc|npmrc|pypirc|pgpass|git-credentials)$"),
    re.compile(r"(^|/)\.aws/(credentials|config)$"),
    re.compile(r"(^|/)\.config/(gh/hosts\.yml|scw/config\.yaml|gcloud/)"),
    re.compile(r"(^|/)\.docker/config\.json$"),
    re.compile(r"(^|/)credentials(\.json)?$"),
    re.compile(r"\.(pem|p12|pfx|key|keystore|jks)$", re.I),
    re.compile(r"service[-_]?account[^/]*\.json$", re.I),
]


def is_secret_path(p: str) -> bool:
    p = os.path.expanduser(p.strip().strip("'\""))
    return bool(p) and not SAFE_SUFFIX.search(p) and any(r.search(p) for r in SECRET_PATH)
