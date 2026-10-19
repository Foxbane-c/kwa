#!/usr/bin/env python3
"""Journal d'activité (module memory) : note ce qui se passe dans la session, une ligne par événement.

Démarrage de session, skill Kwa invoquée, appel d'outil rangé dans sa brique, sous-agent lancé ou revenu, fin de tour.
Les refus des gardes sont notés par les gardes eux-mêmes (_kwa). Rien n'est affiché : la sortie de ce hook entrerait
dans le contexte. Jamais bloquant, sans contenu de fichier ni de prompt. KWA_JOURNAL=0 le coupe.
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _kwa import is_codex, is_copilot, load_payload, load_policy, project_dir  # noqa: E402

AGENT_TOOLS = {"Agent", "Task", "task"}


def agent_name() -> str:
    return "codex" if is_codex() else "copilot" if is_copilot() else "claude"


def main() -> int:
    d = load_payload()
    try:
        import _activity
        import _journal

        if not _journal.enabled():
            return 0
        root = project_dir(d)
        session = _journal._sid(d)
        event = str(d.get("hook_event_name") or "")
        who = agent_name()
        tool = str(d.get("tool_name") or "")
        args = d.get("tool_input") if isinstance(d.get("tool_input"), dict) else {}
        if event == "SessionStart":
            _activity.record(root, session, "session", who, source=d.get("source"),
                             branch=_journal.git(root, "branch", "--show-current"))
        elif event == "Stop":
            _activity.record(root, session, "turn", who)
        elif tool in AGENT_TOOLS:
            # au lancement d'un sous-agent, puis à son retour (un agent en arrière-plan revient aussitôt lancé)
            if event == "PreToolUse":
                _activity.record(root, session, "agent", who, name=args.get("subagent_type") or "agent",
                                 target=args.get("description"))
            elif event == "PostToolUse" and not args.get("run_in_background"):
                _activity.record(root, session, "agent-end", who, name=args.get("subagent_type") or "agent")
        elif event == "PostToolUse" and tool == "Skill":
            _activity.record(root, session, "skill", who, name=args.get("skill") or args.get("command"))
        elif event == "PostToolUse" and tool:
            verify = ((load_policy(d).get("verify") or {}).get("commands")) or []
            brick, target = _activity.classify(tool, args, verify, root)
            _activity.record(root, session, "tool", who, tool=tool, brick=brick, target=target)
    except Exception:  # noqa: BLE001  un journal ne doit jamais gêner la session
        pass
    return 0


if __name__ == "__main__":
    sys.exit(main())
