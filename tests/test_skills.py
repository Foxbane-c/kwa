"""Qualité des skills : frontmatter valide, pas de résidu, références croisées existantes, routeur filtré."""
import json
import os
import re
import subprocess
import sys
import tempfile
import unittest

PACK = os.path.join(os.path.dirname(__file__), "..")
SKILLS = os.path.join(PACK, "core", "skills")
HOOKS = os.path.join(PACK, "core", "hooks")


def frontmatter(path):
    text = open(path, encoding="utf-8").read()
    m = re.match(r"^---\n(.*?)\n---\n", text, re.S)
    assert m, f"{path} : frontmatter manquant"
    return {k.strip(): v.strip() for k, v in (l.split(":", 1) for l in m.group(1).splitlines() if ":" in l)}, text


class Lint(unittest.TestCase):
    def skills(self):
        return sorted(d for d in os.listdir(SKILLS) if os.path.isfile(os.path.join(SKILLS, d, "SKILL.md")))

    def test_frontmatter_and_names(self):
        for d in self.skills():
            with self.subTest(skill=d):
                fm, text = frontmatter(os.path.join(SKILLS, d, "SKILL.md"))
                self.assertEqual(fm["name"], f"kwa-{d}")
                self.assertGreater(len(fm["description"]), 40, "description trop courte")
                self.assertLessEqual(len(fm["description"]), 700)
                self.assertLessEqual(len(text.splitlines()), 220, "SKILL.md trop long : déplacer le détail en annexe")

    def test_description_survives_yaml_parsing(self):
        """Un « #N » ou un « : » dans une description non quotée tronque ou casse l'en-tête YAML : la skill perd ses déclencheurs."""
        for d in self.skills():
            with self.subTest(skill=d):
                line = open(os.path.join(SKILLS, d, "SKILL.md"), encoding="utf-8").read().split("\n")[2]
                value = line.split(": ", 1)[1]
                if value[:1] not in "\"'":
                    self.assertIsNone(re.search(r"\s#", value), "« #… » est lu comme un commentaire YAML : description tronquée")
                    self.assertNotIn(": ", value, "« : » dans une description non quotée casse le YAML")
                self.assertNotRegex(value, r"(?i)\bvault\b")

    def test_no_residue(self):
        for d in self.skills():
            for dirpath, _, files in os.walk(os.path.join(SKILLS, d)):
                for f in files:
                    p = os.path.join(dirpath, f)
                    text = "\n".join(l for l in open(p, encoding="utf-8").read().splitlines() if not l.startswith("> Inspiré"))
                    with self.subTest(file=os.path.relpath(p, PACK)):
                        self.assertNotRegex(text, r"(?i)superpowers", "mention de superpowers")
                        self.assertNotRegex(text, r"(?i)lorem ipsum|titre de slide|une idée forte")
                        self.assertNotIn("EXTREMELY", text)

    def test_cross_references_exist(self):
        names = {f"kwa-{d}" for d in self.skills()}
        for d in self.skills():
            text = open(os.path.join(SKILLS, d, "SKILL.md"), encoding="utf-8").read()
            for ref in set(re.findall(r"(?<![\w./-])/(kwa-[a-z]+(?:-[a-z]+)*)(?![\w/])", text)):
                with self.subTest(skill=d, ref=ref):
                    self.assertIn(ref, names, f"{d} renvoie vers {ref}, qui n'existe pas")

    def test_manifest_covers_every_skill(self):
        man = json.load(open(os.path.join(PACK, "manifest.json")))["modules"]
        dests = " ".join(s["dest"] for m in man.values() for s in m.get("files", {}).values())
        for d in self.skills():
            if d == "init":  # livrée par le plugin seulement (elle lance la commande kwa que le plugin apporte)
                self.assertTrue(os.path.isfile(os.path.join(PACK, "plugin", "skills", "init", "SKILL.md")))
                continue
            self.assertIn(f".claude/skills/kwa-{d}", dests, f"kwa-{d} n'est dans aucun module")


class Router(unittest.TestCase):
    def run_router(self, installed):
        root = os.path.realpath(tempfile.mkdtemp())
        os.makedirs(os.path.join(root, ".claude", "kwa"))
        open(os.path.join(root, ".claude", "kwa", "router.md"), "w").write(
            open(os.path.join(PACK, "core", "templates", "skills-router.md")).read())
        for s in installed:
            os.makedirs(os.path.join(root, ".claude", "skills", s))
        p = subprocess.run([sys.executable, os.path.join(HOOKS, "skills-router.py")], input=json.dumps({"cwd": root}),
                           capture_output=True, text=True, env={**os.environ, "CLAUDE_PROJECT_DIR": root})
        return json.loads(p.stdout)["hookSpecificOutput"]["additionalContext"] if p.stdout.strip() else ""

    def test_only_installed_skills_are_listed(self):
        out = self.run_router(["kwa-debug", "kwa-commit"])
        self.assertIn("/kwa-debug", out)
        self.assertIn("/kwa-commit", out)
        self.assertNotIn("/kwa-deploy", out)

    def test_silent_when_nothing_installed(self):
        self.assertEqual(self.run_router([]), "")


class Humanize(unittest.TestCase):
    def read(self, *parts):
        return open(os.path.join(PACK, *parts), encoding="utf-8").read()

    def test_never_invents_and_bans_dashes(self):
        text = self.read("core", "skills", "humanize", "SKILL.md")
        self.assertIn("n'inventer aucun fait", text)
        self.assertIn("ne contient pas de tiret cadratin", text)

    def test_own_prose_has_no_dash(self):
        # la skill doit appliquer ce qu'elle enseigne : seule la ligne qui nomme les tirets les cite
        lines = [l for l in self.read("core", "skills", "humanize", "SKILL.md").splitlines() if "\u2014" in l or "\u2013" in l]
        self.assertEqual(len(lines), 1, lines)
        self.assertIn("tiret cadratin", lines[0])

    def test_wired_into_commit_ship_and_router(self):
        for skill in ("commit", "ship"):
            self.assertIn("/kwa-humanize", self.read("core", "skills", skill, "SKILL.md"))
        self.assertIn("/kwa-humanize", self.read("core", "templates", "skills-router.md"))

    def test_module_ships_it(self):
        manifest = json.loads(self.read("manifest.json"))
        dests = [d.get("dest") for m in manifest["modules"].values() for d in (m.get("files") or {}).values()]
        self.assertIn(".claude/skills/kwa-humanize", dests)


class Parcours(unittest.TestCase):
    SITE = os.path.join(PACK, "docs", "site")
    PAGES = ["parcours.html", "parcours-culture.html", "parcours-contexte.html", "parcours-harness.html"]

    def page(self, name):
        return open(os.path.join(self.SITE, name), encoding="utf-8").read()

    def test_harness_page_has_history_and_eight_stages_with_real_output(self):
        text = self.page("parcours-harness.html")
        for n in range(0, 9):
            self.assertIn(f'id="etape-{n}"', text)
        self.assertIn("plugin kwa@kwa non activé pour le projet", text)  # sortie réelle de kwa doctor
        self.assertIn("permissionDecision", text)               # sortie réelle d'un garde

    def test_culture_and_context_stages(self):
        for name, count in (("parcours-culture.html", 6), ("parcours-contexte.html", 6)):
            text = self.page(name)
            for n in range(1, count + 1):
                self.assertIn(f'id="etape-{n}"', text, name)
        self.assertIn("parcours.js", self.page("parcours-culture.html"))
        self.assertTrue(os.path.isfile(os.path.join(self.SITE, "src", "parcours.js")))

    def test_hub_links_the_three_parcours(self):
        text = self.page("parcours.html")
        for target in self.PAGES[1:]:
            self.assertIn(f'href="{target}"', text)

    def test_context_examples_are_valid_and_secret_free(self):
        text = self.page("parcours-contexte.html")
        self.assertIn("${DB_URL}", text)
        self.assertIsNone(re.search(r"sk-[A-Za-z0-9]{8,}", text))

    def test_no_temp_path_or_private_term(self):
        for name in self.PAGES:
            text = self.page(name)
            for bad in ("/var/folders", "/private", "kwa-parcours-", "/Users/"):
                self.assertNotIn(bad, text, name)
            self.assertIsNone(re.search(r"(?i)mycecca|cecca|\\bvault\\b", text), name)

    def test_prose_has_no_em_dash_outside_real_output(self):
        # la prose écrite à la main applique /kwa-humanize ; seules les sorties réelles d'un garde portent « Kwa — »
        for name in ("parcours.html", "parcours-culture.html", "parcours-contexte.html"):
            body = re.search(r"<main.*?</main>", self.page(name), re.S).group(0)
            self.assertNotIn("\u2014", body, name)

    def test_linked_from_home_and_readme(self):
        self.assertIn("parcours.html", open(os.path.join(PACK, "README.md"), encoding="utf-8").read())
        self.assertIn("parcours.html", self.page("index.html"))


class ParcoursVisuals(unittest.TestCase):
    """Explications visuelles des parcours : éléments présents, couleurs par parcours, mouvement réduit respecté."""
    SITE = os.path.join(PACK, "docs", "site")

    def test_widgets_do_not_share_a_variable(self):
        # les widgets vivent dans une seule fonction : deux « var » du même nom n'en font qu'une, et l'un casse l'autre
        js = open(os.path.join(PACK, "docs", "site", "src", "parcours.js"), encoding="utf-8").read()
        shared = []  # déclarations au niveau de la fonction ou d'un bloc de widget (indentation 2 ou 4)
        for line in js.splitlines():
            m = re.match(r"^ {2,4}var (.+)$", line)
            if m:
                shared += re.findall(r"(?:^|,\s*)([A-Za-z_$][\w$]*)\s*=(?!=)", m.group(1))
        dup = sorted({n for n in shared if shared.count(n) > 1})
        self.assertEqual(dup, [], dup)

    def read(self, *parts):
        return open(os.path.join(self.SITE, *parts), encoding="utf-8").read()

    def test_token_and_context_widgets_have_their_elements(self):
        page = self.read("parcours-culture.html")
        for needle in ("tk-chips", "tk-probs", "tk-draw", "tk-temp", "tok-input", "ctx-stack", "seg-sum", "Chiffres inventés"):
            self.assertIn(needle, page, needle)
        for seg in ("sys", "rules", "tools", "hist", "files", "res", "sum"):
            self.assertIn(f'id="seg-{seg}"', page, seg)
        for gone in ("ctx-sys", "data-ctx-preset", "data-ctx-play", "Simuler une session"):
            self.assertNotIn(gone, page, "la jauge n'est plus un formulaire : " + gone)

    def test_script_ids_exist_in_the_pages(self):
        js = self.read("src", "parcours.js")
        pages = "".join(self.read(f"parcours-{n}.html") for n in ("culture", "contexte", "harness"))
        idents = set(re.findall(r"\$\('#([a-z-]+)'\)", js))
        self.assertGreater(len(idents), 10)
        for ident in idents:
            self.assertIn(f'id="{ident}"', pages, ident)

    def test_orchestrator_rules_and_skill_loading_are_taught(self):
        contexte = self.read("parcours-contexte.html")
        for needle in ('id="orch"', 'id="skl"', "Les règles", "paths", "etape-10"):
            self.assertIn(needle, contexte, needle)

    def test_everyday_tools_and_agent_flow_are_taught(self):
        contexte = self.read("parcours-contexte.html")
        for needle in ("tools/list", "tools/call", "resources/read", "prompts/get", "mcp-three", "JSON-RPC 2.0"):
            self.assertIn(needle, contexte, needle)
        for needle in ("Context7", "resolve-library-id", "query-docs", "Playwright", "browser_take_screenshot",
                       "browser_run_code_unsafe", "/clear", "/rewind", "etape-8"):
            self.assertIn(needle, contexte, needle)
        harness = self.read("parcours-harness.html")
        for needle in ('id="flow"', "PostToolUse", "stop_hook_active", "etape-9", "Playwright", "Context7"):
            self.assertIn(needle, harness, needle)
        culture = self.read("parcours-culture.html")
        for needle in ('id="loop"', "Injection de prompt", "workflow"):
            self.assertIn(needle, culture, needle)

    def test_stage_numbers_match_the_navigation(self):
        sys.path.insert(0, os.path.join(self.SITE, "src"))
        import parcours_pages
        for page, nav in (("culture", parcours_pages.CULTURE_NAV), ("contexte", parcours_pages.CONTEXTE_NAV), ("harness", parcours_pages.HARNESS_NAV)):
            text = self.read(f"parcours-{page}.html")
            ids = sorted(set(re.findall(r'<section class="pc-stage" id="etape-(\d+)"', text)), key=int)
            self.assertEqual(ids, sorted([n for n, _ in nav], key=int), page)

    def test_each_parcours_has_its_own_accent(self):
        css = self.read("src", "parcours.css")
        for name in ("culture", "contexte", "harness"):
            self.assertIn(f'data-acc="{name}"', self.read(f"parcours-{name}.html"), name)
            self.assertIn(f'[data-acc="{name}"]', css, name)

    def test_motion_is_skipped_when_reduced(self):
        self.assertIn("prefers-reduced-motion", self.read("src", "parcours.css"))
        self.assertIn("prefers-reduced-motion", self.read("src", "parcours.js"))


class Pictos(unittest.TestCase):
    """Pictogrammes des concepts (garde, skill, agent) et mots importants en gras : générés, sans résidu de gabarit."""
    SITE = os.path.join(PACK, "docs", "site")

    def index(self):
        with open(os.path.join(self.SITE, "index.html"), encoding="utf-8") as f:
            return f.read()

    def test_concept_pictos_are_in_the_page(self):
        text = self.index()
        self.assertNotIn("{{pic:", text)
        for name in ("shield", "sword", "agent"):
            self.assertIn(f"p-{name}", text, name)

    def test_credits_markup_is_rendered_not_shown(self):
        with open(os.path.join(PACK, "credits.json"), encoding="utf-8") as f:
            sources = json.load(f)["sources"]
        for src in sources:
            self.assertEqual(src["took"].count("**") % 2, 0, src["id"])
            self.assertIn("**", src["took"], src["id"])
        self.assertIn("<strong>$1</strong>", self.index())


class Workflows(unittest.TestCase):
    """Les cinq workflows de l'accueil ne citent que des skills, hooks et gardes qui existent."""

    def test_every_named_piece_exists(self):
        sys.path.insert(0, os.path.join(PACK, "docs", "site", "src"))
        import workflows
        self.assertEqual(len(workflows.WORKFLOWS), 5)
        skills = set(os.listdir(os.path.join(PACK, "core", "skills")))
        hooks = {f[:-3] for f in os.listdir(os.path.join(PACK, "core", "hooks")) if f.endswith(".py")}
        agents = {"kwa:" + f[:-3] for f in os.listdir(os.path.join(PACK, "core", "agents"))}  # nom sous plugin
        for key, _p, _t, _promise, link, steps in workflows.WORKFLOWS:
            target = link.split("#")[0]
            self.assertTrue(os.path.isfile(os.path.join(PACK, "docs", "site", target)), link)
            for kind, name, _what in steps:
                if kind == "skill":
                    self.assertIn(re.sub(r"^/kwa[-:]", "", name), skills, f"{key}: {name}")
                elif kind == "agent":
                    self.assertIn(name, agents, f"{key}: {name}")
                elif kind in ("hook", "garde") and not name.startswith("refus"):
                    self.assertIn(name, hooks, f"{key}: {name}")

    def test_home_shows_them(self):
        with open(os.path.join(PACK, "docs", "site", "index.html"), encoding="utf-8") as f:
            home = f.read()
        self.assertIn('id="workflows"', home)
        self.assertEqual(home.count('class="wf-panel"'), 5)
        self.assertIn("src/workflows.js", home)


class Beginners(unittest.TestCase):
    """Un débutant trouve par où commencer, comment installer, et ce que veulent dire les mots anglais."""
    SITE = os.path.join(PACK, "docs", "site")

    def read(self, name):
        with open(os.path.join(self.SITE, name), encoding="utf-8") as f:
            return f.read()

    def test_home_says_where_to_start(self):
        home = self.read("index.html")
        self.assertIn("Vous débutez ?", home)
        for target in ("parcours.html", "avant-de-commencer.html", "#demarrer"):
            self.assertIn(f'href="{target}"', home, target)
        self.assertIn("/kwa:init", home)
        self.assertNotIn("export PATH", home, "sous Claude Code, le plugin apporte la commande kwa : pas d'étape PATH")

    def test_install_page_covers_both_agents_and_kwa(self):
        page = self.read("avant-de-commencer.html")
        for needle in ("claude.ai/install.sh", "chatgpt.com/codex/install.sh", "/plugin install kwa@kwa", "/kwa:init",
                       "Python 3", "/hooks"):
            self.assertIn(needle, page, needle)

    def test_glossary_has_every_term_with_its_english_word_and_pages_load_the_tooltips(self):
        sys.path.insert(0, os.path.join(self.SITE, "src"))
        import glossary
        page = self.read("glossaire.html")
        for tid, label, en, _f, _s, _k in glossary.TERMS:
            self.assertIn(f'id="{tid}"', page, tid)
            if en:
                self.assertIn(en.split(",")[0].strip(), page, tid)
        for name in [f for f in os.listdir(self.SITE) if f.endswith(".html") and f != "template.html"]:
            self.assertIn("src/glossary-data.js", self.read(name), name)
        data = self.read(os.path.join("src", "glossary-data.js"))
        self.assertIn('"id": "harness"', data)
        self.assertIn("passage de relais", data)
        self.assertIn("En anglais : guard", data)

    def test_parcours_state_what_the_exercises_need_and_fold_the_theory(self):
        contexte, harness = self.read("parcours-contexte.html"), self.read("parcours-harness.html")
        self.assertIn("Node.js", contexte)
        self.assertIn("avant-de-commencer.html", contexte)
        self.assertIn("jq pour l'exemple de hook", harness)
        self.assertIn("avant-de-commencer.html", harness)
        # la théorie reste là, mais repliée : le tableau MCP/REST et softmax ne passent plus avant la pratique
        self.assertRegex(contexte, r'<details class="pc-reveal"><summary>Pour aller plus loin[^<]*</summary><div><table class="pc-table mcp-vs">')
        self.assertRegex(self.read("parcours-culture.html"), r"Pour aller plus loin[^<]*</summary><div><p>[^<]*<em>softmax</em>")

    def test_first_steps_tutorial_uses_the_demo_repo_and_quotes_real_refusals(self):
        sys.path.insert(0, os.path.join(self.SITE, "src"))
        import firststeps
        page = self.read("premier-pas.html")
        for needle in ("nesyouyou/kwa-demo", "--template</span>", "/kwa:init", '"commands": ["python3 -m unittest"]', "chore/kwa", "/kwa:ship", "/kwa:learn"):
            self.assertIn(needle, page)
        self.assertIn('href="premier-pas.html"', self.read("index.html"))
        hooks = os.path.join(PACK, "core", "hooks")
        # les refus cités sont ceux du code : début du message, puis la suite construite par le garde
        for fragment, guard in ((firststeps.REFUS_WRITE[:60], "guard-write.py"), ("refusé : travailler sur une branche ", "guard-git.py")):
            self.assertIn(fragment, open(os.path.join(hooks, guard), encoding="utf-8").read(), guard)
        self.assertTrue(firststeps.REFUS_COMMIT.startswith("git commit sur main refusé : travailler sur une branche"))

    def test_js_only_pages_point_to_a_static_equivalent(self):
        for name, href in (("skill-map.html", "skills.html"), ("board.html", "index.html#workflows"), ("terminal.html", "index.html#demarrer")):
            self.assertRegex(self.read(name), rf'<noscript>.*href="{re.escape(href)}".*</noscript>', name)


class Panel(unittest.TestCase):
    """Le mod kwa-activity dessine les mêmes workflows que le site, et la page « Le Mod » cite ses vrais libellés."""
    MOD = os.path.join(PACK, "mods", "kwa-activity", "hooks", "workflow.ts")

    def setUp(self):
        sys.path.insert(0, os.path.join(PACK, "docs", "site", "src"))
        import flows, panel
        self.flows, self.panel = flows, panel
        self.ts = open(self.MOD, encoding="utf-8").read()

    def test_the_mod_draws_the_site_workflows_step_by_step(self):
        body = self.ts[self.ts.index("const FLOWS"):self.ts.index("const FLOW_OF")]
        for key, flow in self.flows.FLOWS.items():
            with self.subTest(flow=key):
                block = re.search(key + r": \{ title: '([^']+)', steps: \[(.*?)\] \}", body, re.S)
                self.assertIsNotNone(block, key)
                self.assertEqual(block.group(1), flow["title"])
                mine = re.findall(r"\['(\w+)', '\w+', '([^']+)'\]", block.group(2))
                self.assertEqual(mine, [(b, n) for b, _k, n, _w in flow["steps"]])

    def test_the_page_quotes_labels_the_mod_draws(self):
        for label in self.panel.LABELS:
            with self.subTest(label=label):
                self.assertIn(label, self.ts)


class Agents(unittest.TestCase):
    """La page « Selon l'agent » montre les refus que les gardes émettent vraiment sous chaque agent."""

    def test_each_agent_gets_the_refusal_it_understands(self):
        sys.path.insert(0, os.path.join(PACK, "docs", "site", "src"))
        import agents_page
        claude, claude_code, _ = agents_page.refusal({})
        copilot, copilot_code, err = agents_page.refusal({"COPILOT_PLUGIN_DATA": tempfile.mkdtemp()})
        self.assertEqual(claude_code, 0)
        self.assertNotIn("permissionDecision", {k for k in json.loads(claude) if k != "hookSpecificOutput"})
        self.assertEqual(copilot_code, 2)
        self.assertEqual(json.loads(copilot)["permissionDecision"], "deny")
        self.assertIn("Kwa — ", err)


class Flows(unittest.TestCase):
    """Workflows animés : chaque pièce nommée existe, chaque événement vise une étape, le scénario est complet."""

    def setUp(self):
        sys.path.insert(0, os.path.join(PACK, "docs", "site", "src"))
        import flows
        self.flows = flows

    def test_every_named_piece_exists(self):
        skills = set(os.listdir(os.path.join(PACK, "core", "skills")))
        hooks = {f[:-3] for f in os.listdir(os.path.join(PACK, "core", "hooks")) if f.endswith(".py")}
        agents = {"kwa:" + f[:-3] for f in os.listdir(os.path.join(PACK, "core", "agents"))}
        for key, flow in self.flows.FLOWS.items():
            for brick, kind, name, _what in flow["steps"]:
                with self.subTest(flow=key, step=name):
                    self.assertIn(brick, {b[0] for b in self.flows.BRICKS})
                    if kind in ("skill", "doc"):
                        self.assertIn(re.sub(r"^/kwa:", "", name), skills)
                    elif kind in ("garde", "hook"):
                        self.assertIn(name, hooks)
                    elif kind == "agent":
                        self.assertIn(name, agents)

    def test_script_is_consistent_and_shows_every_kind_of_event(self):
        for key, flow in self.flows.FLOWS.items():
            self.assertEqual(self.flows.check(flow), [], key)
            kinds = {ev[0] for ev in flow["script"]}
            self.assertTrue({"go", "ask", "loop", "guard"} <= kinds, f"{key} : {kinds}")  # chaque workflow : boucles, décisions, refus

    def test_guard_messages_are_the_real_ones(self):
        hooks = os.path.join(PACK, "core", "hooks")
        for key, flow in self.flows.FLOWS.items():
            for ev in flow["script"]:
                if ev[0] == "guard":
                    guard = flow["steps"][ev[1]][2]
                    src = open(os.path.join(hooks, guard + ".py"), encoding="utf-8").read()
                    start = re.split(r"[`(]", ev[2].replace("Kwa — ", ""))[0][:26].strip()  # la partie fixe du message
                    self.assertIn(start, src, f"{key} : message de {guard} introuvable")


class Shell(unittest.TestCase):
    """Barre latérale de navigation et arborescence : générées, identiques partout, avec de vrais liens."""
    SITE = os.path.join(PACK, "docs", "site")

    def pages(self):
        return [f for f in sorted(os.listdir(self.SITE)) if f.endswith(".html") and f != "template.html"]

    def read(self, name):
        return open(os.path.join(self.SITE, name), encoding="utf-8").read()

    def test_site_speaks_only_of_the_plugin_install(self):
        """L'installation par copie est l'ancienne méthode : le site ne la montre plus (#43). kwa-hygiene reste copié
        dans le projet, pour la CI."""
        legacy = re.compile(r"kwa install|\.claude/kwa/(?:hooks|bin/(?!kwa-hygiene))|\.claude/rules/kwa-|(?<![\w./-])/kwa-(?!demo|activity)[a-z]")  # /kwa-activity : commande du mod
        for name in self.pages():
            text = re.sub(r"<[^>]+>", "", self.read(name))
            self.assertEqual([m.group(0) for m in legacy.finditer(text)], [], name)

    def test_every_page_declares_an_existing_favicon(self):
        for name in self.pages():
            self.assertIn('rel="icon"', self.read(name), name)
        self.assertTrue(os.path.isfile(os.path.join(self.SITE, "assets", "favicon.svg")))

    def test_every_page_has_the_same_sidebar_with_its_own_entry_marked(self):
        self.assertGreaterEqual(len(self.pages()), 8)
        for name in self.pages():
            text = self.read(name)
            self.assertIn('class="kd-side"', text, name)
            self.assertIn('class="kd-top"', text, name)
            current = re.findall(r'<a href="([^"]+)" aria-current="page"', text)
            own = {"skill-map.html": "skills.html"}.get(name, name)  # la carte se range sous Skills
            self.assertEqual(current, [own] if name != "index.html" else ["index.html#top"] if "index.html#top" in current else current, name)
            self.assertIn("src/shell.js", text, name)

    def test_every_sidebar_target_exists(self):
        sys.path.insert(0, os.path.join(self.SITE, "src"))
        import shell

        for page in sorted(set(shell.PAGES)):
            self.assertTrue(os.path.isfile(os.path.join(self.SITE, page)), page)
        home = self.read("index.html")
        for _, _, items in shell.SIDE:
            for _, target in items:
                page, _, frag = target.partition("#")
                if page == "index.html" and frag:
                    self.assertIn(f'id="{frag}"', home, target)

    def test_tree_is_generated_from_the_manifest_and_every_file_is_described(self):
        sys.path.insert(0, os.path.join(self.SITE, "src"))
        import importlib.machinery, importlib.util
        import tree

        loader = importlib.machinery.SourceFileLoader("kwa_cli_t", os.path.join(PACK, "bin", "kwa"))
        spec = importlib.util.spec_from_loader("kwa_cli_t", loader)
        kwa = importlib.util.module_from_spec(spec)
        loader.exec_module(kwa)
        man = json.load(open(os.path.join(PACK, "manifest.json"), encoding="utf-8"))["modules"]
        catalog = {}
        for d in os.listdir(os.path.join(PACK, "core", "skills")):
            f = os.path.join(PACK, "core", "skills", d, "SKILL.md")
            if os.path.isfile(f):
                m = re.search(r"^description:\s*(.+)$", open(f, encoding="utf-8").read(), re.M)
                catalog[d] = m.group(1) if m else ""
        files = tree.project_files(man, kwa.module_files, catalog)
        installed = {spec["dest"] for m in man.values() for _, spec in kwa.module_files(m)}
        self.assertTrue(installed <= {f["dest"] for f in files}, "tout ce que le manifeste installe figure dans l'arborescence")
        for f in files:
            self.assertTrue(f["desc"].strip(), f"{f['dest']} n'a pas de description")
            if f["src"]:
                self.assertTrue(os.path.isfile(os.path.join(PACK, f["src"])), f["src"])
        home = self.read("index.html")
        self.assertIn('id="arborescence"', home)
        self.assertIn(".claude/", home)
        self.assertNotIn('id="principes"', home)

    def test_tree_links_to_the_map_point_at_real_nodes(self):
        data = json.loads(self.read("data.js").split("window.KWA=", 1)[1].rstrip().rstrip(";"))
        nodes = set(data["map"]["nodes"])
        home = self.read("index.html")
        targets = set(re.findall(r"skill-map\.html#view=pack&amp;node=([^\"]+)", home))
        self.assertGreater(len(targets), 20)
        self.assertEqual(sorted(t for t in targets if t not in nodes), [])


class OwnStyle(unittest.TestCase):
    """Le site porte sa propre feuille de style : plus de trace d'une charte graphique empruntée."""

    def test_no_borrowed_prefixes_or_fonts(self):
        files = subprocess.run(["git", "ls-files"], cwd=PACK, capture_output=True, text=True).stdout.split("\n")
        hits = []
        for f in files:
            path = os.path.join(PACK, f)
            if not f or not os.path.isfile(path) or f.endswith((".woff2", ".ttf", ".png", ".jpg")) or f.startswith("tests/"):
                continue
            text = open(path, encoding="utf-8", errors="ignore").read()
            if re.search(r"nkds|nkui|Manrope", text):
                hits.append(f)
        self.assertEqual(hits, [])

    def test_titles_are_plain(self):
        text = open(os.path.join(PACK, "docs", "site", "template.html"), encoding="utf-8").read()
        for m in re.finditer(r"<h[12] class=\"kw-(?:section-)?title\"[^>]*>(.*?)</h[12]>", text, re.S):
            self.assertNotRegex(m.group(1), r"<strong>|<br", "un titre est du texte simple : pas de mot en gras ni de retour forcé")
            self.assertFalse(m.group(1).rstrip().endswith("."), "pas de point final décoratif")


class Neutral(unittest.TestCase):
    def test_no_organisation_name_in_tracked_files(self):
        # le dépôt est personnel pour l'instant : aucun nom d'organisation, y compris dans les pages générées
        files = subprocess.run(["git", "ls-files"], cwd=PACK, capture_output=True, text=True).stdout.split("\n")
        needle = "naka" + "ma"
        hits = []
        for f in files:
            path = os.path.join(PACK, f)
            if not f or not os.path.isfile(path) or f.endswith((".woff2", ".ttf", ".png", ".jpg", ".svg")):
                continue
            if needle in open(path, encoding="utf-8", errors="ignore").read().lower() or needle in f.lower():
                hits.append(f)
        self.assertEqual(hits, [])


class ThemeIcon(unittest.TestCase):
    def test_every_page_uses_an_icon_button_without_visible_label(self):
        site = os.path.join(PACK, "docs", "site")
        pages = [f for f in os.listdir(site) if f.endswith(".html") and f != "template.html"]
        self.assertGreaterEqual(len(pages), 7)
        for name in pages:
            text = open(os.path.join(site, name), encoding="utf-8").read()
            button = re.search(r'<button[^>]*id="theme".*?</button>', text, re.S)
            self.assertIsNotNone(button, name)
            html = button.group(0)
            self.assertIn("i-sun", html, name)
            self.assertIn("i-moon", html, name)
            self.assertIn("aria-label", html, name)
            self.assertNotRegex(re.sub(r"<[^>]+>", "", html).strip(), r"\S", f"{name} : le bouton ne porte aucun texte visible")
            self.assertNotIn("Thème sombre</button>", text, name)


class SplitPages(unittest.TestCase):
    """L'accueil est court ; chaque grand sujet a sa page, atteignable depuis la barre latérale."""
    SITE = os.path.join(PACK, "docs", "site")
    PAGES = {"skills.html": "skills", "gardes.html": "gardes", "memoire.html": "memoire", "methode.html": "superpowers",
             "migrer.html": "migrer", "limites.html": "limites", "credits.html": "credits"}

    def read(self, name):
        with open(os.path.join(self.SITE, name), encoding="utf-8") as f:
            return f.read()

    def test_home_keeps_only_the_short_story(self):
        home = self.read("index.html")
        for sid in ("pourquoi", "arborescence", "demarrer"):
            self.assertIn(f'id="{sid}"', home, sid)
        for sid in list(self.PAGES.values()) + ["carte", "board", "terminal"]:
            self.assertNotIn(f'<section class="kw-container kd-section kd-rv" id="{sid}">', home, sid)

    def test_each_topic_has_its_own_page_with_a_title_and_its_sidebar_entry(self):
        for fname, sid in self.PAGES.items():
            text = self.read(fname)
            self.assertEqual(text.count("<h1"), 1, fname)
            self.assertIn(f'id="{sid}"', text, fname)
            self.assertIn(f'href="{fname}" aria-current="page"', text, fname)

    def test_home_buttons_lead_to_dedicated_pages(self):
        home = self.read("index.html")
        for target in ("skill-map.html", "board.html", "terminal.html"):
            self.assertIn(f'href="{target}"', home, target)


class WorkflowsPage(unittest.TestCase):
    SITE = os.path.join(PACK, "docs", "site")

    def read(self, *p):
        return open(os.path.join(self.SITE, *p), encoding="utf-8").read()

    def test_workflows_page_mounts_the_animated_player(self):
        text = self.read("board.html")
        self.assertIn("src/flows.js", text)
        self.assertIn('class="fl-script"', text)
        self.assertNotIn("KwaCircuit.mount", text)
        sys.path.insert(0, os.path.join(PACK, "docs", "site", "src"))
        import flows
        for name in flows.FLOWS:
            self.assertIn(f'data-flow-tab="{name}"', text, name)
        self.assertNotIn("src/flows.js", self.read("index.html"), "l'accueil ne charge pas les widgets des pages dédiées")

    def test_home_workflows_come_from_the_animated_ones(self):
        """Une seule source : les étapes de l'accueil sont celles de la page Les workflows (#46)."""
        sys.path.insert(0, os.path.join(PACK, "docs", "site", "src"))
        import flows
        import workflows
        for key, _p, title, _promise, _link, steps in workflows.WORKFLOWS:
            self.assertEqual(title, flows.FLOWS[key]["title"], key)
            self.assertEqual(steps, [s[1:] for s in flows.FLOWS[key]["steps"]], key)

    def test_review_jargon_is_in_the_glossary(self):
        """Les termes signalés par la relecture critique (#47) ont leur entrée, et le marqueur animé n'est pas un « jeton »."""
        sys.path.insert(0, os.path.join(PACK, "docs", "site", "src"))
        import glossary
        ids = {t[0] for t in glossary.TERMS}
        for term in ("regle", "preuve", "plugin", "marketplace", "superpowers", "conventional-commits", "pre-vol", "seed", "opt-in", "sous-agent"):
            self.assertIn(term, ids)
        self.assertNotIn("Le jeton suit", self.read("board.html"))

    def test_site_follows_the_lexicon(self):
        """Un seul mot par idée (#54) : le mot écarté n'apparaît, hors code, que sur les pages qui l'expliquent."""
        sys.path.insert(0, os.path.join(PACK, "docs", "site", "src"))
        import glossary
        for name in [f for f in os.listdir(self.SITE) if f.endswith(".html") and f != "template.html"]:
            text = re.sub(r"<(script|style|code|pre)\b.*?</\1>", " ", self.read(name), flags=re.S)
            text = re.sub(r"<[^>]+>", " ", text)
            for kept, banned, allowed in glossary.LEXICON:
                m = None if name in allowed else re.search(rf"(?i)(?<![\w/:.-]){re.escape(banned)}s?(?![\w/.-])", text)
                self.assertIsNone(m, f"{name} : « {m and text[max(0, m.start() - 40):m.end() + 40]} » ; écrire « {kept} »")

    def test_every_skill_has_one_family(self):
        sys.path.insert(0, os.path.join(PACK, "docs", "site", "src"))
        import mapdata
        placed = [s for ids in mapdata.FAMILIES.values() for s in ids]
        self.assertEqual(sorted(placed), sorted(set(placed)), "une skill dans deux familles")
        self.assertEqual(set(placed), set(os.listdir(os.path.join(PACK, "plugin", "skills"))))
        self.assertEqual(set(mapdata.FAMILIES), set(mapdata.FAMILY_RULE))

    def test_no_dead_widget_is_left(self):
        src = os.path.join(self.SITE, "src")
        pages = "".join(self.read(f) for f in os.listdir(self.SITE) if f.endswith(".html") and f != "template.html")
        for f in os.listdir(src):
            if f.endswith((".js", ".css")) and f != "glossary-data.js":
                self.assertIn(f"src/{f}", pages, f"{f} n'est chargé par aucune page")


class Bricks(unittest.TestCase):
    """Page « Les briques » : chaque fiche est complète et ses exemples sont justes."""
    SITE = os.path.join(PACK, "docs", "site")

    def setUp(self):
        sys.path.insert(0, os.path.join(self.SITE, "src"))
        import bricks
        self.b = bricks

    def test_every_brick_has_its_facts_an_example_and_a_real_kwa_file(self):
        ids = [x[0] for x in self.b.BRICKS]
        self.assertEqual(len(ids), len(set(ids)))
        for bid, _pic, _name, _line, _nature, why, when, when_not, who, where, cost, files, real in self.b.BRICKS:
            for field in (why, when, when_not, who, where, cost):
                self.assertTrue(field.strip(), bid)
            self.assertTrue(files, bid)
            target = os.path.join(self.SITE, real[0].split("#")[0]) if ".html" in real[0] else os.path.join(PACK, real[0])
            self.assertTrue(os.path.exists(target), f"{bid} : {real[0]}")
            self.assertIn(bid, self.b.CHECK, f"{bid} : pas de « Vérifier que ça marche »")
        self.assertEqual({to for _n, to, _w in self.b.NEEDS} - set(ids), set())

    def test_mcp_examples_use_the_variable_dbhub_reads(self):
        """@bytebase/dbhub lit DSN (ou --dsn), pas DATABASE_URL : sinon le serveur démarre sans base."""
        sys.path.insert(0, os.path.join(self.SITE, "src"))
        import parcours_pages
        for servers in (self.b.MCP_JSON["mcpServers"], parcours_pages.MCP_EX["mcpServers"]):
            for name, cfg in servers.items():
                if "@bytebase/dbhub" in cfg.get("args", []):
                    self.assertIn("DSN", cfg.get("env", {}), name)

    def test_examples_are_valid_files(self):
        for bid, *_rest, files, _real in self.b.BRICKS:
            for path, content in files:
                if path.endswith(".json"):
                    json.loads(content)
                if path.endswith(".md") and content.startswith("---"):
                    head = content.split("---")[1]
                    self.assertIn("name:" if "/rules/" not in path else "paths:", head, path)
                if path.endswith(".py"):
                    compile(content, path, "exec")

    def test_the_python_hook_example_really_denies_a_commit_on_main(self):
        with tempfile.TemporaryDirectory() as tmp:
            subprocess.run(["git", "init", "-q", "-b", "main", tmp], check=True)
            hook = os.path.join(tmp, "hook.py")
            open(hook, "w").write(self.b.HOOK_PY)
            run = lambda cmd: subprocess.run([sys.executable, hook], input=json.dumps(
                {"hook_event_name": "PreToolUse", "tool_name": "Bash", "tool_input": {"command": cmd}, "cwd": tmp}),
                capture_output=True, text=True)
            for cmd in ("git commit -m wip", "cd . && git commit -m wip", "git -C . commit -m wip", "git -c x=y commit"):
                out = json.loads(run(cmd).stdout)["hookSpecificOutput"]
                self.assertEqual(out["permissionDecision"], "deny", cmd)
                self.assertIn("main", out["permissionDecisionReason"], cmd)
            self.assertEqual(run("git status").stdout, "")
            subprocess.run(["git", "-C", tmp, "switch", "-q", "-c", "feat/x"], check=True)
            self.assertEqual(run("git commit -m wip").stdout, "", "sur une branche de travail, le commit passe")

    def test_page_is_built_and_linked(self):
        text = open(os.path.join(self.SITE, "briques.html"), encoding="utf-8").read()
        self.assertEqual(text.count('class="br-card"'), len(self.b.BRICKS))
        self.assertIn('href="briques.html" aria-current="page"', text)
        self.assertIn("src/bricks.js", text)


class BorderStyle(unittest.TestCase):
    """Choix de style : un trait épais d'un seul côté est permis sur un rectangle, jamais sur un coin arrondi."""

    def test_no_thick_one_sided_border_on_rounded_box(self):
        site = os.path.join(PACK, "docs", "site")
        files = [os.path.join(site, "template.html")] + [os.path.join(site, "src", f) for f in os.listdir(os.path.join(site, "src")) if f.endswith(".css")]
        bad = []
        for path in files:
            text = open(path, encoding="utf-8").read()
            for rule in re.findall(r"[^{}]+\{[^{}]*\}", text):
                one_side = re.search(r"border-(?:left|right|top|bottom)\s*:\s*([2-9]|\d{2,})px", rule)
                radius = re.search(r"border-radius\s*:\s*([1-9]\d*)px", rule)
                if one_side and radius and int(radius.group(1)) >= 6:
                    bad.append(os.path.basename(path) + " : " + rule.strip()[:90])
        self.assertEqual(bad, [])


class MotionRespect(unittest.TestCase):
    """Toute animation du site doit se couper quand la personne demande de réduire les animations."""

    def test_reduced_motion_is_honoured_wherever_there_is_animation(self):
        site = os.path.join(PACK, "docs", "site")
        for rel in ("src/flows.css", "src/parcours.css", "src/map.css", "src/shell.css"):
            text = open(os.path.join(site, rel), encoding="utf-8").read()
            if "@keyframes" in text or "transition:" in text:
                self.assertIn("prefers-reduced-motion", text, rel)
        for rel in ("src/flows.js", "src/player.js"):
            self.assertIn("prefers-reduced-motion", open(os.path.join(site, rel), encoding="utf-8").read(), rel)
        tpl = open(os.path.join(site, "template.html"), encoding="utf-8").read()
        self.assertIn("prefers-reduced-motion: reduce", tpl)
        self.assertIn("startViewTransition", tpl)


if __name__ == "__main__":
    unittest.main()
