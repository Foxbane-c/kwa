"""Journal d'activité : un fichier par session, écritures concurrentes, plafond, nettoyage des secrets, purge."""
import json
import os
import subprocess
import sys
import tempfile
import time
import unittest

from helpers import HOOKS
from test_tools import git_repo, sh

sys.path.insert(0, HOOKS)
import _activity  # noqa: E402
import _journal  # noqa: E402

# faux secret assemblé à l'exécution : aucun jeton d'apparence réelle n'est écrit dans ce fichier
FAKE_GH = "gh" + "p_" + "abcdefghijklmnopqrstuvwxyz0123"


def files(repo):
    d = os.path.join(repo, ".claude", "kwa", "local", "activity")
    return sorted(os.listdir(d)) if os.path.isdir(d) else []


class Sessions(unittest.TestCase):
    def setUp(self):
        self.repo = git_repo({"README.md": "x"})
        os.environ.pop("KWA_JOURNAL", None)

    def test_each_session_writes_its_own_file(self):
        _activity.record(self.repo, "sess-A", "skill", name="/kwa:debug")
        _activity.record(self.repo, "sess-B", "tool", tool="Edit", brick="faire", target="src/a.py")
        _activity.record(self.repo, "sess-A", "tool", tool="Bash", brick="prouver", target="python3 -m unittest")
        self.assertEqual(len(files(self.repo)), 2)
        a = _activity.read_session(self.repo, "sess-A")
        self.assertEqual([e["kind"] for e in a], ["skill", "tool"])
        self.assertEqual([e["kind"] for e in _activity.read_session(self.repo, "sess-B")], ["tool"])
        self.assertEqual(a[0]["agent"], "claude")

    def test_a_worktree_writes_in_the_main_repository(self):
        sh("git", "-C", self.repo, "add", "-A")
        sh("git", "-C", self.repo, "commit", "-qm", "init")
        wt = os.path.join(tempfile.mkdtemp(), "wt")
        sh("git", "-C", self.repo, "worktree", "add", "-q", "-b", "feat/x", wt)
        _activity.record(wt, "sess-W", "turn")
        self.assertEqual(len(files(self.repo)), 1)
        self.assertEqual(files(wt), [])

    def test_two_concurrent_writers_never_mix_their_lines(self):
        code = ("import sys; sys.path.insert(0, sys.argv[1]); import _activity\n"
                "for i in range(400): _activity.record(sys.argv[2], 'sess-C', 'tool', tool='Read', brick='cadrer',"
                " target='src/' + sys.argv[3] + str(i) + '.py')")
        procs = [subprocess.Popen([sys.executable, "-c", code, HOOKS, self.repo, w]) for w in ("a", "b")]
        for p in procs:
            self.assertEqual(p.wait(), 0)
        lines = open(os.path.join(self.repo, ".claude", "kwa", "local", "activity", files(self.repo)[0]), encoding="utf-8").read().splitlines()
        self.assertEqual(len(lines), 800)
        for line in lines:
            json.loads(line)   # aucune ligne coupée ni mêlée

    def test_no_secret_and_short_targets(self):
        _activity.record(self.repo, "sess-S", "tool", tool="Bash", target=f"curl -H 'Authorization: token {FAKE_GH}' x")
        _activity.record(self.repo, "sess-S", "tool", tool="Bash", target="echo " + "y" * 500)
        raw = open(os.path.join(self.repo, ".claude", "kwa", "local", "activity", files(self.repo)[0]), encoding="utf-8").read()
        self.assertNotIn(FAKE_GH, raw)
        self.assertLessEqual(max(len(e.get("target", "")) for e in _activity.read_session(self.repo, "sess-S")), _activity.TARGET_CHARS)

    def test_disabled_with_the_journal(self):
        os.environ["KWA_JOURNAL"] = "0"
        try:
            _activity.record(self.repo, "sess-D", "turn")
        finally:
            os.environ.pop("KWA_JOURNAL", None)
        self.assertEqual(files(self.repo), [])


class Cap(unittest.TestCase):
    def setUp(self):
        self.repo = git_repo({"README.md": "x"})
        self.saved = _activity.SESSION_BYTES
        _activity.SESSION_BYTES = 600

    def tearDown(self):
        _activity.SESSION_BYTES = self.saved

    def test_beyond_the_cap_steps_are_kept_and_tools_only_counted(self):
        for i in range(30):
            _activity.record(self.repo, "sess-K", "tool", tool="Read", brick="cadrer", target=f"f{i}.py")
        _activity.record(self.repo, "sess-K", "skill", name="/kwa:tdd")
        events = _activity.read_session(self.repo, "sess-K")
        self.assertLess(len(events), 31)                     # le détail a cessé d'être écrit…
        self.assertEqual(events[-1]["kind"], "skill")        # …pas les étapes
        path = _activity.session_file(self.repo, "sess-K")
        counts = json.load(open(path + ".counts.json"))
        self.assertEqual(counts["cadrer"] + sum(1 for e in events if e["kind"] == "tool"), 30)


class Prune(unittest.TestCase):
    def setUp(self):
        self.repo = git_repo({"README.md": "x"})

    def test_old_sessions_go_and_the_folder_stays_under_its_cap(self):
        for s in ("old", "mid", "new"):
            _activity.record(self.repo, f"sess-{s}", "turn")
        now = time.time()
        old = _activity.session_file(self.repo, "sess-old")
        os.utime(old, (now - 40 * 86400, now - 40 * 86400))
        self.assertEqual(_activity.prune(self.repo, None, now), 1)
        self.assertFalse(os.path.exists(old))
        # la durée se règle dans la politique
        mid = _activity.session_file(self.repo, "sess-mid")
        os.utime(mid, (now - 10 * 86400, now - 10 * 86400))
        self.assertEqual(_activity.prune(self.repo, {"memory": {"activity_days": 7}}, now), 1)
        # plafond global : les plus anciens partent d'abord
        saved = _activity.TOTAL_BYTES
        _activity.TOTAL_BYTES = 1
        try:
            for i in range(3):
                _activity.record(self.repo, f"sess-x{i}", "turn")
                os.utime(_activity.session_file(self.repo, f"sess-x{i}"), (now - 100 + i, now - 100 + i))
            _activity.prune(self.repo, None, now)
        finally:
            _activity.TOTAL_BYTES = saved
        self.assertLessEqual(len(files(self.repo)), 1)

    def test_signals_are_pruned_and_housekeeping_purges_both(self):
        path = _journal.signals_path(self.repo)
        old = {"t": "x", "ts": time.time() - 60 * 86400, "kind": "refus", "key": "k", "text": ""}
        new = {**old, "ts": time.time()}
        with open(path, "w", encoding="utf-8") as f:
            f.write(json.dumps(old) + "\n" + json.dumps(new) + "\n")
        _activity.record(self.repo, "sess-old", "turn")
        stale = _activity.session_file(self.repo, "sess-old")
        os.utime(stale, (time.time() - 40 * 86400,) * 2)
        _journal.housekeeping(self.repo, None)
        self.assertEqual([json.loads(x)["ts"] for x in open(path)], [new["ts"]])
        self.assertFalse(os.path.exists(stale))


if __name__ == "__main__":
    unittest.main()
