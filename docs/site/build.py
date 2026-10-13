#!/usr/bin/env python3
"""Génère index.html : le gabarit + des données RÉELLES (gardes exécutés, manifeste, détection, tests).
    python3 docs/site/build.py
"""
import json
import os
import re
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
PACK = os.path.realpath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, os.path.join(PACK, "tests"))
from helpers import BASH_GUARDS, HOOKS, RANK, make_repo  # noqa: E402

POLICY = os.path.join(PACK, "examples", "expo-monorepo.policy.json")

import importlib.machinery, importlib.util  # noqa: E402
_loader = importlib.machinery.SourceFileLoader("kwa_cli", os.path.join(PACK, "bin", "kwa"))
_spec = importlib.util.spec_from_loader("kwa_cli", _loader)
kwa = importlib.util.module_from_spec(_spec)
_loader.exec_module(kwa)


PLUGIN_ENV = {"KWA_RUNTIME": "plugin"}  # les exemples des gardes : messages tels que le plugin les affiche


def verdict(guard, tool, tool_input, cwd, env=None):
    # GH=false : le garde ne doit jamais interroger le vrai GitHub, sinon la page dépend de l'état d'un dépôt réel
    e = {**os.environ, "GH": "false", "CLAUDE_PROJECT_DIR": cwd, **(env or {})}
    p = subprocess.run([sys.executable, os.path.join(HOOKS, guard)], input=json.dumps(
        {"tool_name": tool, "tool_input": tool_input, "cwd": cwd}), capture_output=True, text=True, env=e)
    if not p.stdout.strip():
        return "allow", ""
    o = json.loads(p.stdout)["hookSpecificOutput"]
    return o["permissionDecision"], o["permissionDecisionReason"].replace("Kwa — ", "")


def worst(cmd, cwd, env=None):
    best = ("allow", "")
    for g in BASH_GUARDS:
        v = verdict(g, "Bash", {"command": cmd}, cwd, env)
        if RANK[v[0]] > RANK[best[0]]:
            best = v
    return best


def examples():
    feat = make_repo(POLICY, branch="feat/12-filtre")
    main = make_repo(POLICY, branch="main")
    bash_cases = [
        ("Secrets", feat, "cat .env"), ("Secrets", feat, "cat .env.backup"), ("Secrets", feat, "bash -c 'cat .env'"),
        ("Secrets", feat, "env A=1 cat .env"), ("Secrets", feat, "cat .e''nv"), ("Secrets", feat, "gh auth token"),
        ("Secrets", feat, "cat .env.example"),
        ("Git", feat, "git push -u origin feat/12-filtre"), ("Git", feat, "git push --force origin feat/12-filtre"),
        ("Git", feat, "git push --force-with-lease origin feat/12-filtre"), ("Git", main, "git commit -m 'wip'"),
        ("Git", main, "git push origin main"), ("Git", feat, "git push origin HEAD:main"),
        ("Git", feat, "git reset --hard"), ("Git", feat, "gh pr merge 12 --squash"),
        ("Suppression", feat, "rm -rf build"), ("Suppression", feat, "rm -rf /usr/local/x"),
        ("Suppression", feat, "bash -c 'rm -rf /usr/local/x'"), ("Suppression", feat, "rm -rf .git"),
        ("Suppression", feat, "git clean -fd"), ("Suppression", feat, "rm -rf $(pwd)/../x"),
        ("Politique", feat, "npx prisma migrate reset"), ("Politique", feat, "npx prisma db push"),
        ("Politique", feat, "gh workflow run deploy.yml -f target=prod"), ("Politique", feat, "scw container container update abc image=x"),
        ("Politique", feat, "npx eas-cli submit --platform ios --latest"), ("Politique", feat, "grep -rn PROD_RESET_TOKEN docs/"),
        ("Politique", feat, "cat > note.md <<'EOF'\nun `prisma migrate reset` cité en doc\nEOF"),
        ("Politique", feat, "bash <<'EOF'\nnpx prisma migrate reset\nEOF"),
        ("Workflow PR", feat, "gh pr create --title t --body 'rien'"), ("Workflow PR", feat, "gh pr create --title t --body 'Closes #12'"),
    ]
    out = []
    for cat, repo, cmd in bash_cases:
        d, why = worst(cmd, repo, PLUGIN_ENV)
        out.append({"cat": cat, "tool": "Bash", "input": cmd, "branch": "main" if repo == main else "feat/12-filtre", "decision": d, "why": why})
    write_cases = [
        ("Écriture", feat, "src/.env", None, "Edit"), ("Écriture", feat, "packages/db/prisma/migrations/2026_x/migration.sql", None, "Edit"),
        ("Écriture", main, "apps/web/page.tsx", None, "Edit"), ("Écriture", feat, "apps/web/page.tsx", None, "Edit"),
        ("Écriture", feat, "src/pay.ts", "const k = 'sk_live_" + "a" * 24 + "'", "Write"),
        ("Écriture", feat, "src/db.ts", "const url = 'postgres://app:s3cretpw@db.internal/x'", "Write"),
        ("Écriture", feat, ".claude/settings.json", None, "Edit"),
    ]
    for cat, repo, rel, content, tool in write_cases:
        ti = {"file_path": os.path.join(repo, rel), **({"content": content} if content else {"new_string": "x"})}
        d, why = verdict("guard-write.py", tool, ti, repo, PLUGIN_ENV)
        shown = rel if not content else f"{rel} ← {content.replace('a' * 24, '…').replace('s3cretpw', '…')}"
        out.append({"cat": cat, "tool": tool, "input": shown, "branch": "main" if repo == main else "feat/12-filtre", "decision": d, "why": why})
    return out


def tests_count():
    r = subprocess.run([sys.executable, "-W", "ignore", "-m", "unittest", "discover", "-s", "tests", "-p", "test_*.py"],
                       cwd=PACK, capture_output=True, text=True)
    m = re.search(r"Ran (\d+) tests", r.stderr)
    ok = "OK" in r.stderr.splitlines()[-1] if r.stderr.strip() else False
    return int(m.group(1)) if m else 0, ok


PARCOURS_TAIL = """<div class="pc-check"><h2>Vous avez compris si vous savez</h2><ul>
<li>dire pourquoi un fichier d'instructions ne contraint pas, et nommer ce qui contraint ;</li>
<li>prédire le verdict d'une commande, puis relier un garde à son entrée dans <code>settings.json</code> ;</li>
<li>ajouter une règle de projet et montrer qu'elle change un verdict ;</li>
<li>écrire l'en-tête d'une skill et lire l'échec d'un test ;</li>
<li>dire ce qu'aucun de ces garde-fous ne garantit, et quelle barrière complète.</li></ul>
<p class="kd-note" style="margin-top:18px">Pour les consignes de chaque outil, les documentations officielles font foi : <a href="https://code.claude.com/docs/en/memory">mémoire et instructions</a>, <a href="https://code.claude.com/docs/en/hooks">hooks</a>, <a href="https://code.claude.com/docs/en/settings">réglages</a>. Les commandes et les noms de réglages évoluent avec les versions : vérifiez avant une séance.</p></div>"""


SKILL_NAME = None


def plugin_names(text: str) -> str:
    """Le site parle du plugin : /kwa-commit s'y écrit /kwa:commit (un chemin comme .claude/skills/kwa-commit reste)."""
    global SKILL_NAME
    if SKILL_NAME is None:
        names = sorted(os.listdir(os.path.join(PACK, "core", "skills")), key=len, reverse=True)
        SKILL_NAME = re.compile(r"(?<![\w./-])([/$])kwa-(" + "|".join(map(re.escape, names)) + r")(?![a-z-])")
    text = SKILL_NAME.sub(r"\1kwa:\2", text)
    text = re.sub(r"(?:python3 )?\.claude/kwa/bin/kwa-(memory|start)\b", r"kwa \1", text)
    return re.sub(r"(?<![\w./-])kwa-relecteur(?![a-z.-])", "kwa:relecteur", text)


COPY_PAGES = {"parcours-harness.html"}  # démonte une installation par copie : noms d'origine


def main():
    man = json.load(open(os.path.join(PACK, "manifest.json")))["modules"]
    sys.path.insert(0, os.path.join(HERE, "src"))
    from tree import in_plugin  # noqa: E402  un fichier de module s'affiche où il vit : dans le plugin, ou au projet
    mods = []
    for name, m in man.items():
        mods.append({"name": name, "about": m["about"], "always": bool(m.get("always")),
                     "files": [("plugin/" + in_plugin(s["dest"])) if in_plugin(s["dest"]) else s["dest"] for _, s in kwa.module_files(m)],
                     "seeds": [s["dest"] for _, s in kwa.module_files(m) if s.get("seed")],
                     "hooks": [f"{ev}{' ' + e['matcher'] if e.get('matcher') else ''}" for ev, es in m.get("hooks", {}).items() for e in es],
                     "policy": list(m.get("policy", {}).keys())})
    n_tests, ok = tests_count()
    term = json.load(open(os.path.join(HERE, "src", "terminal-data.json"), encoding="utf-8"))
    detect = term["scenarios"][0]["steps"][0]["output"] if isinstance(term, dict) and "scenarios" in term else ""
    skills = sorted({s["dest"].split("/")[2] for m in man.values() for _, s in kwa.module_files(m)
                     if s["dest"].startswith(".claude/skills/")})
    catalog = []
    for d in sorted(os.listdir(os.path.join(PACK, "core", "skills"))):
        f = os.path.join(PACK, "core", "skills", d, "SKILL.md")
        if os.path.isfile(f):
            m = re.search(r"^description:\s*(.+)$", open(f, encoding="utf-8").read(), re.M)
            catalog.append({"id": d, "description": (m.group(1).strip().strip('"') if m else "")})
    data = {"credits": json.load(open(os.path.join(PACK, "credits.json"))), "catalog": catalog, "version": open(os.path.join(PACK, "VERSION")).read().strip(), "modules": mods, "examples": examples(),
            "tests": n_tests, "tests_ok": ok, "detect": detect, "skills": skills,
            "policy": json.load(open(POLICY)), "guards": sorted(f[:-3] for f in os.listdir(HOOKS) if f.startswith("guard-"))}
    src = os.path.join(HERE, "src")
    term_path = os.path.join(src, "terminal-data.json")
    data["terminal"] = json.load(open(term_path, encoding="utf-8")) if os.path.exists(term_path) else None
    sys.path.insert(0, src)
    import mapdata  # noqa: E402
    data["map"] = mapdata.build(sorted(os.listdir(os.path.join(PACK, "core", "skills"))) and
                                [d for d in sorted(os.listdir(os.path.join(PACK, "core", "skills")))
                                 if os.path.isfile(os.path.join(PACK, "core", "skills", d, "SKILL.md"))], data["credits"], {})
    open(os.path.join(HERE, "data.js"), "w", encoding="utf-8").write("window.KWA=" + json.dumps(data, ensure_ascii=False) + ";")

    def assets(names):
        css = "".join(f'<link rel="stylesheet" href="src/{n}.css">' for n in names if os.path.exists(os.path.join(src, n + ".css")))
        js = "".join(f'<script src="src/{n}.js"></script>' for n in names if os.path.exists(os.path.join(src, n + ".js")))
        return css, js

    tpl = open(os.path.join(HERE, "template.html"), encoding="utf-8").read()
    css, js = assets(["map", "board", "circuit", "terminal"])
    sys.path.insert(0, src)
    import shell, tree, pictos, workflows  # noqa: E402
    files = tree.project_files(man, kwa.module_files, {c["id"]: c["description"] for c in catalog})
    shown = [m for m in man if any(m in f["modules"] for f in files)]
    tpl = pictos.fill_placeholders(tpl).replace("/*PICTOS*/{}", pictos.as_json())
    tpl = tpl.replace("<!--EXTRA_CSS-->", '<link rel="stylesheet" href="src/workflows.css">').replace("<!--EXTRA_JS-->", "").replace("<!--TOPBAR-->", shell.topbar())
    tree_html = tree.section(files, shown, {m: man[m]["about"] for m in shown})

    # pages dédiées : chaque section du gabarit qui n'est pas l'accueil devient sa propre page
    SPLIT = {  # fichier : (id de la section, titre de l'onglet, description)
        "skills.html": ("skills", "Les skills", "Le catalogue des skills de Kwa, classées par famille, avec leur origine."),
        "gardes.html": ("gardes", "Les gardes en action", "Ce que Kwa refuse, demande ou laisse passer, calculé en exécutant les gardes."),
        "memoire.html": ("memoire", "La mémoire", "Comment chaque session enrichit la suivante : capture, journal, filtre, tri, reprise."),
        "methode.html": ("superpowers", "La méthode", "Les principes de discipline de superpowers, réécrits en français et branchés sur la politique du projet."),
        "migrer.html": ("migrer", "Remplacer l'existant", "Remplacer un outillage maison par Kwa : correspondances et détection automatique."),
        "limites.html": ("limites", "Limites et suite", "Les limites de Kwa, sans maquillage, et la feuille de route."),
        "credits.html": ("credits", "Crédits", "Ce que Kwa doit aux autres projets, avec licence et référence."),
    }
    section_re = r'<section class="kw-container kd-section kd-rv" id="%s">.*?</section>\n\n?'
    pieces = {}
    for fname, (sid, _t, _d) in SPLIT.items():
        m = re.search(section_re % sid, tpl, re.S)
        if not m:
            sys.exit(f"gabarit : section {sid} introuvable")
        pieces[fname] = m.group(0).strip()
        tpl = tpl.replace(m.group(0), "", 1)
    index_html = (tpl.replace("<!--SIDEBAR-->", shell.sidebar("index.html")).replace("<!--TREE-->", tree_html)
                  .replace("<!--WORKFLOWS-->", workflows.section()))
    open(os.path.join(HERE, "index.html"), "w", encoding="utf-8").write(index_html)
    main_re = re.compile(r"<main>.*?</main>", re.S)
    for fname, (sid, title, desc) in SPLIT.items():
        sec = re.sub(r'<h2 class="kw-section-title">(.*?)</h2>', r'<h1 class="kw-page-title">\1</h1>', pieces[fname], count=1, flags=re.S)
        page = main_re.sub(lambda _m: '<main class="kd-solo">\n' + sec + "\n</main>", tpl, count=1)
        page = re.sub(r"<title>.*?</title>", f"<title>{title} | Kwa</title>", page, count=1)
        page = re.sub(r'<meta name="description" content=".*?">', f'<meta name="description" content="{desc}">', page, count=1)
        page = page.replace("<!--SIDEBAR-->", shell.sidebar(fname)).replace("<!--TREE-->", "").replace("<!--WORKFLOWS-->", "")
        open(os.path.join(HERE, fname), "w", encoding="utf-8").write(page)

    # pages plein écran : même coquille (barre, thème, logo, pied) autour d'un seul widget
    head = re.search(r"<style>.*?</style>", tpl, re.S).group(0)
    foot = re.search(r"<footer.*?</footer>", tpl, re.S).group(0)
    theme_js = re.search(r"/\* thème : clair par défaut.*?/\* fin du bloc thème \*/\n", tpl, re.S).group(0)
    # les cinq workflows en onglets, puis l'un d'eux déroulé en détail (le script des onglets vient des assets de la page)
    import flows  # noqa: E402
    for key, flow in flows.FLOWS.items():
        errs = flows.check(flow)
        if errs:
            sys.exit(f"workflow {key} : " + "; ".join(errs))
    BOARD_HTML = (re.sub(r'\s*<script src="src/workflows.js"></script>', "", workflows.section())
                  .replace('class="kw-container kd-section kd-rv" id="workflows"', 'class="bd-wf" id="workflows"')
                  .replace('<div class="kd-eyebrow">Les workflows</div><h2 class="kw-section-title">Cinq workflows automatisés</h2>', '')
                  + '<h2 class="kw-section-title bd-detail" id="detail">En détail : développer une fonctionnalité</h2>'
                  '<p class="kd-lead">Le workflow regroupé en briques. Le jeton suit le scénario : les boucles quand une '
                  'condition n\'est pas remplie, vos décisions, les refus des gardes, les sous-agents qui partent et reviennent. '
                  'Vous pouvez cliquer dans les fenêtres de décision.</p>' + flows.player("feature"))
    pages = {
        "skill-map.html": ("Carte des skills", "Carte interactive", "map", '<div id="map" data-deeplink></div>',
                           "DATA.map && KwaMap.mount($('#map'), DATA.map);"),
        "board.html": ("Les workflows", "Fonctionnalité, bug, relecture, livraison, capitalisation", "workflows+flows",
                       BOARD_HTML, ""),
        "terminal.html": ("Le terminal", "Comment on l'utilise", "terminal", '<div id="term-root"></div>', "KwaTerminal.mount($('#term-root'), DATA.terminal);"),
    }
    no_js = {  # ces trois pages n'existent qu'en JavaScript : sans lui, renvoyer vers leur équivalent statique
        "skill-map.html": ('skills.html', "la liste des skills"),
        "board.html": ('index.html#workflows', "les cinq workflows de l'accueil"),  # le déroulé détaillé est en JS
        "terminal.html": ('index.html#demarrer', "les commandes de démarrage"),
    }
    for fname, (href, label) in no_js.items():
        t, e, w, m, j = pages[fname]
        pages[fname] = (t, e, w, m + f'<noscript><p class="kd-note">Cette page est interactive et demande JavaScript. Sans lui, voyez <a href="{href}">{label}</a>.</p></noscript>', j)
    sys.path.insert(0, src)
    import parcours  # noqa: E402
    stages = parcours.collect(PACK, verdict, worst, make_repo, POLICY)[0]
    import parcours_pages  # noqa: E402
    import delegation  # noqa: E402
    import glossary  # noqa: E402
    import beginner  # noqa: E402
    import firststeps  # noqa: E402
    open(os.path.join(HERE, "src", "glossary-data.js"), "w", encoding="utf-8").write(glossary.data_js())
    pages["glossaire.html"] = ("Glossaire", "Les mots du dev agentique, en français", "", glossary.page(), "")
    pages["avant-de-commencer.html"] = ("Avant de commencer", "Installer un agent, puis Kwa", "parcours", beginner.page(), "")
    pages["premier-pas.html"] = ("Premier pas en 30 minutes", "Kwa sur un projet d'exercice", "parcours", firststeps.page(), "")
    pages["delegation.html"] = ("Skills qui délèguent", "Des agents neufs, un prompt rempli", "delegation", delegation.page(), "")
    pages["parcours.html"] = ("Parcours d'apprentissage", "Trois parcours, du modèle au harness", "parcours", parcours_pages.hub(), "")
    pages["parcours-culture.html"] = ("Parcours 1 : Culture IA générative", "Comprendre le modèle", "parcours", parcours_pages.culture(), "")
    pages["parcours-contexte.html"] = ("Parcours 2 : Context engineering", "Donner le bon contexte", "parcours", parcours_pages.contexte(), "")
    pages["parcours-harness.html"] = ("Parcours 3 : Harness", "Encadrer l'agent", "parcours", parcours_pages.harness(parcours.render(stages) + PARCOURS_TAIL), "")
    for fname, (title, eyebrow, widget, mount_html, mount_js) in pages.items():
        wcss, wjs = assets(widget.split('+'))
        html = f"""<!doctype html>
<html lang="fr" data-theme="dark"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<link rel="icon" type="image/svg+xml" href="assets/favicon.svg">
<title>{title} | Kwa</title>
<script>try{{if(localStorage.getItem('kwa-docs-theme')==='light')document.documentElement.dataset.theme='light'}}catch(e){{}}</script>
<link rel="stylesheet" href="style/fonts.css"><link rel="stylesheet" href="style/tokens.css"><link rel="stylesheet" href="style/base.css"><link rel="stylesheet" href="src/shell.css">{wcss}
{head}</head>
<body class="kw">
{shell.topbar()}
<div class="kd-layout">{shell.sidebar(fname, parcours_pages.TOC.get(fname))}<div class="kd-main">
<main class="kw-container pc-wrap" data-acc="{fname.replace('parcours-','').replace('.html','')}" style="padding-top:32px">
  <div class="kd-eyebrow">{eyebrow}</div>
  <h1 class="kw-page-title">{title}</h1>
  {mount_html}
</main>
</div></div>
{foot}
<script src="data.js"></script><script src="src/player.js"></script>{wjs}<script src="src/glossary-data.js"></script><script src="src/shell.js"></script>
<script>
const DATA = window.KWA;
const $ = (s, r=document) => r.querySelector(s);
{theme_js}
$('#ver2').textContent = DATA.version;
{mount_js}
</script></body></html>"""
        open(os.path.join(HERE, fname), "w", encoding="utf-8").write(html)
    for f in [x for x in os.listdir(HERE) if x.endswith(".html") and x != "template.html" and x not in COPY_PAGES] + ["data.js", os.path.join("src", "glossary-data.js")]:
        path = os.path.join(HERE, f)
        text = open(path, encoding="utf-8").read()
        if plugin_names(text) != text:
            open(path, "w", encoding="utf-8").write(plugin_names(text))
    # contrôle de syntaxe des scripts inline des pages générées (une apostrophe oubliée casse toute la page)
    import shutil, tempfile
    if shutil.which("node"):
        for page in ["index.html", "skill-map.html", "board.html", "terminal.html", "parcours.html", "parcours-culture.html", "parcours-contexte.html", "parcours-harness.html", "delegation.html", "glossaire.html", "avant-de-commencer.html", "premier-pas.html"] + list(SPLIT):
            for i, code in enumerate(re.findall(r"<script>(.*?)</script>", open(os.path.join(HERE, page), encoding="utf-8").read(), re.S)):
                with tempfile.NamedTemporaryFile("w", suffix=".js", delete=False, encoding="utf-8") as f:
                    f.write(code)
                r = subprocess.run(["node", "--check", f.name], capture_output=True, text=True)
                os.unlink(f.name)
                if r.returncode != 0:
                    sys.exit(f"erreur de syntaxe JS dans {page} (script {i}) :\n{r.stderr[:400]}")
    d = data["examples"]
    print(f"index.html — {len(mods)} modules, {len(skills)} skills, {len(d)} exemples réels "
          f"({sum(x['decision']=='deny' for x in d)} refus, {sum(x['decision']=='ask' for x in d)} demandes, "
          f"{sum(x['decision']=='allow' for x in d)} passages), {n_tests} tests {'OK' if ok else 'EN ÉCHEC'}")


if __name__ == "__main__":
    main()
