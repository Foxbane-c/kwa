/* Parcours : explications visuelles (jetons, fenêtre de contexte) et apparition des étapes. Aucun appel à un modèle : ce sont
   des illustrations, présentées comme telles. Script classique, sans dépendance. */
(function () {
  'use strict';
  function $(s, r) { return (r || document).querySelector(s); }
  function fmt(n) { return String(Math.round(n)).replace(/\B(?=(\d{3})+(?!\d))/g, ' '); }
  var reduced = window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  /* apparition des étapes au défilement */
  var stages = document.querySelectorAll('.pc-stage');
  if (stages.length && 'IntersectionObserver' in window && !reduced) {
    document.documentElement.classList.add('pc-js');
    var io = new IntersectionObserver(function (es) { es.forEach(function (e) { if (e.isIntersecting) { e.target.classList.add('is-in'); io.unobserve(e.target); } }); }, { rootMargin: '0px 0px -8% 0px' });
    Array.prototype.forEach.call(stages, function (s) { io.observe(s); });
  }

  /* ---------- jetons : découper, calculer des probabilités, tirer au sort ---------- */
  var cut = function (text) {
    var parts = text.match(/\s*[\p{L}\p{N}'’-]+|\s*[^\s\p{L}\p{N}]/gu) || [], toks = [];
    parts.forEach(function (p) {
      var lead = (p.match(/^\s*/) || [''])[0], core = p.slice(lead.length);
      if (core.length <= 6) { toks.push(lead + core); return; }
      for (var i = 0; i < core.length; i += 5) toks.push((i === 0 ? lead : '') + core.slice(i, i + 5));
    });
    return toks;
  };
  var fakeId = function (t) { var h = 7; for (var i = 0; i < t.length; i++) h = (h * 31 + t.charCodeAt(i)) % 49999; return h + 1; };

  var tk = $('#tk');
  if (tk) {
    var SENT = [
      { text: 'La capitale de la France est', next: [[' Paris', .90], [' une', .03], [' la', .02], [' située', .02], [' Lyon', .004]] },
      { text: 'Il était une fois', next: [[' un', .34], [',', .26], [' dans', .12], [' une', .09], [' deux', .04]] },
      { text: 'Pour limiter les hallucinations, il faut', next: [[' vérifier', .23], [' citer', .17], [' donner', .14], [' demander', .11], [' limiter', .09]] }
    ];
    var tkCur = 0, temp = 1, tChips = $('#tk-chips'), tProbs = $('#tk-probs'), tDraws = $('#tk-draws');
    var dist = function () {
      var next = SENT[tkCur].next, rest = Math.max(0, 1 - next.reduce(function (a, n) { return a + n[1]; }, 0));
      var all = next.concat([['autres jetons', rest]]);
      var w = all.map(function (n) { return Math.pow(Math.max(n[1], 1e-6), 1 / temp); }), tot = w.reduce(function (a, b) { return a + b; }, 0);
      return all.map(function (n, i) { return [n[0], w[i] / tot]; });
    };
    var pct = function (x) { return (x * 100 < 10 ? (x * 100).toFixed(1) : Math.round(x * 100)).toString().replace('.', ',') + ' %'; };
    var drawProbs = function (animate) {
      tProbs.textContent = '';
      dist().forEach(function (d, i) {
        var row = document.createElement('div'); row.className = 'tk-row' + (i === 0 ? ' tk-top' : '');
        row.innerHTML = '<span class="tk-w"></span><span class="tk-bar"><i></i></span><span class="tk-p"></span>';
        row.firstChild.textContent = d[0].replace(/^ /, '·');
        row.lastChild.textContent = pct(d[1]);
        tProbs.appendChild(row);
        var bar = row.querySelector('i');
        if (animate && !reduced) { bar.style.width = '0'; setTimeout(function () { bar.style.width = (d[1] * 100) + '%'; }, 60 + i * 70); }
        else bar.style.width = (d[1] * 100) + '%';
      });
    };
    var drawChips = function (animate) {
      tChips.textContent = '';
      cut(SENT[tkCur].text).forEach(function (t, i) {
        var c = document.createElement('span'); c.className = 'tk-chip';
        c.innerHTML = '<b class="pc-tok pc-t' + (i % 6) + '"></b><small></small>';
        c.firstChild.textContent = t.replace(/ /g, '·'); c.lastChild.textContent = fakeId(t);
        if (animate && !reduced) { c.style.animationDelay = (i * 160) + 'ms'; c.classList.add('tk-in'); }
        tChips.appendChild(c);
      });
    };
    var show = function (animate) {
      drawChips(animate); tDraws.textContent = '';
      var delay = animate && !reduced ? cut(SENT[tkCur].text).length * 160 + 200 : 0;
      setTimeout(function () { drawProbs(animate); }, delay);
    };
    Array.prototype.forEach.call(tk.querySelectorAll('[data-tk-s]'), function (b) {
      b.addEventListener('click', function () {
        tkCur = Number(b.getAttribute('data-tk-s'));
        Array.prototype.forEach.call(tk.querySelectorAll('[data-tk-s]'), function (o) { o.setAttribute('aria-pressed', String(o === b)); });
        show(true);
      });
    });
    $('#tk-temp').addEventListener('input', function (e) { temp = Number(e.target.value); $('#tk-tv').textContent = String(temp.toFixed(1)).replace('.', ','); drawProbs(false); tDraws.textContent = ''; });
    $('#tk-draw').addEventListener('click', function () {
      var d = dist(), counts = {};
      for (var n = 0; n < 20; n++) { var r = Math.random(), acc = 0, k = d[d.length - 1][0]; for (var i = 0; i < d.length; i++) { acc += d[i][1]; if (r <= acc) { k = d[i][0]; break; } } counts[k] = (counts[k] || 0) + 1; }
      tDraws.textContent = '';
      Object.keys(counts).sort(function (a, b) { return counts[b] - counts[a]; }).forEach(function (k, i) {
        var c = document.createElement('span'); c.className = 'pc-tok pc-t' + (i % 6); c.textContent = k.replace(/^ /, '·') + ' × ' + counts[k];
        if (!reduced) { c.style.animation = 'pc-pop .3s both'; c.style.animationDelay = (i * 90) + 'ms'; }
        tDraws.appendChild(c);
      });
    });
    show(false);
    if ('IntersectionObserver' in window && !reduced) {
      var seenT = new IntersectionObserver(function (es) { if (es[0].isIntersecting) { show(true); seenT.disconnect(); } }, { threshold: 0.4 });
      seenT.observe(tk);
    }
  }

  /* estimation sur un texte libre */
  var area = $('#tok-input');
  if (area) {
    var chips = $('#tok-chips'), out = $('#tok-out'), MAX = 400;
    var render = function () {
      var text = area.value, toks = cut(text), chars = text.length, words = (text.trim().match(/\S+/g) || []).length;
      chips.textContent = '';
      toks.slice(0, MAX).forEach(function (t, i) { var c = document.createElement('span'); c.className = 'pc-tok pc-t' + (i % 6); c.textContent = t.replace(/\n/g, '↵'); chips.appendChild(c); });
      if (toks.length > MAX) { var more = document.createElement('span'); more.className = 'pc-tok pc-more'; more.textContent = '… ' + fmt(toks.length - MAX) + ' de plus'; chips.appendChild(more); }
      var lo = Math.min(chars / 4, words * 1.3), hi = Math.max(chars / 4, words * 1.3);
      out.innerHTML = '<div><b>' + fmt(toks.length) + '</b> jetons dans ce découpage illustratif</div><div><b>' + fmt(chars) + '</b> caractères, <b>' + fmt(words) + '</b> mots</div>' +
        '<div>Ordre de grandeur d\'un vrai compte : <b>' + fmt(lo) + ' à ' + fmt(hi) + '</b></div>';
    };
    area.addEventListener('input', render);
    render();
  }

  /* ---------- orchestrateur et sous-agents ---------- */
  var orch = $('#orch');
  if (orch) {
    var main = { sys: $('#pm-sys'), hist: $('#pm-hist'), files: $('#pm-files'), sum: $('#pm-sum') };
    var subs = Array.prototype.slice.call(orch.querySelectorAll('.ps')), downs = orch.querySelectorAll('.po-down'), ups = orch.querySelectorAll('.po-up');
    var cap = $('#po-cap'), val = $('#po-v'), mode = null;
    var setMain = function (v) {
      var tot = 0; ['sys', 'hist', 'files', 'sum'].forEach(function (k) { main[k].style.width = v[k] + '%'; tot += v[k]; });
      $('#po-main').classList.toggle('pc-over', tot > 85);
      val.textContent = 'Fenêtre principale : ' + Math.round(tot) + ' %';
    };
    var setSubs = function (w) { subs.forEach(function (e, i) { e.style.width = (w[i] || 0) + '%'; }); };
    var fly = function (list, on) { Array.prototype.forEach.call(list, function (e, i) { e.classList.toggle('po-go', on); e.style.transitionDelay = on && !reduced ? (i * 70) + 'ms' : '0ms'; }); };
    var SCRIPT = {
      team: [
        function () { fly(downs, false); fly(ups, false); setSubs([0, 0, 0]); setMain({ sys: 10, hist: 4, files: 0, sum: 0 }); return 'L\'agent principal reçoit la demande : « refactorer l\'authentification ». Il a déjà ses consignes et l\'historique.'; },
        function () { fly(downs, true); setMain({ sys: 10, hist: 6, files: 0, sum: 0 }); return 'Il envoie à chacun seulement un brief : la tâche, les critères de réussite, les fichiers utiles. Pas la conversation, pas le reste du code.'; },
        function () { setSubs([72, 86, 58]); return 'Chaque sous-agent lit ce qu\'il lui faut dans sa propre fenêtre. La fenêtre principale ne bouge pas.'; },
        function () { fly(downs, false); fly(ups, true); setSubs([0, 0, 0]); setMain({ sys: 10, hist: 6, files: 0, sum: 6 }); return 'Seul un résumé remonte. Les fenêtres des sous-agents sont jetées avec ce qu\'elles ont lu.'; },
        function () { return 'Résultat : la fenêtre principale reste autour de 22 %, alors que trois sous-agents ont lu des dizaines de fichiers. Contrepartie : un résumé vague donne une suite vague.'; }
      ],
      solo: [
        function () { fly(downs, false); fly(ups, false); setSubs([0, 0, 0]); setMain({ sys: 10, hist: 4, files: 0, sum: 0 }); return 'Le même agent reçoit la même demande, mais travaille seul.'; },
        function () { setMain({ sys: 10, hist: 8, files: 25, sum: 0 }); return 'Il lit les fichiers des routes : tout entre dans la même fenêtre.'; },
        function () { setMain({ sys: 10, hist: 12, files: 55, sum: 0 }); return 'Puis les tests : la fenêtre se remplit, l\'historique grossit.'; },
        function () { setMain({ sys: 10, hist: 15, files: 70, sum: 0 }); return 'Puis la documentation. Rien n\'est jeté.'; },
        function () { return 'Résultat : la fenêtre approche de 95 %. La précision peut baisser avant même la saturation, et une compaction devient nécessaire.'; }
      ]
    };
    var resetOrch = function () { fly(downs, false); fly(ups, false); setSubs([0, 0, 0]); setMain({ sys: 0, hist: 0, files: 0, sum: 0 }); };
    // une étape rejoue celles d'avant : chaque fonction ne pose qu'une partie de l'état
    var oShow = function (i) { var t = ''; for (var k = 0; k <= i; k++) t = SCRIPT[mode][k](); cap.textContent = t; };
    var oPlayer = window.KwaPlayer && KwaPlayer(orch, { count: function () { return mode ? SCRIPT[mode].length : 0; }, show: oShow, reset: resetOrch, interval: 1900 });
    Array.prototype.forEach.call(orch.querySelectorAll('[data-orch]'), function (b) {
      b.addEventListener('click', function () {
        mode = b.getAttribute('data-orch');
        Array.prototype.forEach.call(orch.querySelectorAll('[data-orch]'), function (o) { o.setAttribute('aria-pressed', String(o === b)); });
        if (oPlayer) oPlayer.play();
      });
    });
    if (!mode) { mode = 'team'; orch.querySelector('[data-orch="team"]').setAttribute('aria-pressed', 'true'); if (oPlayer) oPlayer.refresh(); }
    setMain({ sys: 0, hist: 0, files: 0, sum: 0 });
  }

  /* ---------- la boucle d'un agent ---------- */
  var loop = $('#loop');
  if (loop) {
    var LP = [ /* [nœud, tour, au centre, légende] */
      [0, 1, 'lancer les tests d\'abord', 'Le modèle lit la demande « corrige le test qui échoue » et décide : il faut d\'abord lancer les tests.'],
      [1, 1, 'npm test', 'Il appelle un outil : la commande de test.'],
      [2, 1, '1 test rouge', 'Le résultat (un test rouge, avec son message) entre dans le contexte.'],
      [3, 1, 'non : on recommence', 'Est-ce terminé ? Non : le test est rouge. Il refait un tour.'],
      [0, 2, 'lire le fichier en cause', 'Il réfléchit : l\'erreur pointe vers un fichier, il faut le lire.'],
      [1, 2, 'lire, puis modifier', 'Il appelle l\'outil de lecture, puis celui de modification.'],
      [2, 2, 'tous les tests verts', 'Il relance les tests : tout est vert. Le résultat entre dans le contexte.'],
      [3, 2, 'oui : il répond', 'Terminé : le modèle juge que l\'objectif est atteint, la boucle s\'arrête et il répond. C\'est lui qui décide, d\'où l\'importance de lui donner un contrôle qu\'il peut lancer.']
    ];
    var lpRing = loop.querySelector('.lp-ring'), lpDot = loop.querySelector('.lp-dot'), lpMid = loop.querySelector('.lp-mid');
    var lpTurn = loop.querySelector('.lp-turn'), lpSay = loop.querySelector('.lp-say'), lpCap = $('#loop-cap');
    var lpNodes = loop.querySelectorAll('.lp-node'), lpAt = 0, lpRaf = 0;
    var lpStill = window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    var lpPlace = function (q) { /* q : position sur l'anneau en quarts de tour, 0 en haut, sens horaire */
      var t = (q * 90 - 90) * Math.PI / 180;
      lpDot.setAttribute('cx', (50 + 34 * Math.cos(t)).toFixed(2));
      lpDot.setAttribute('cy', (50 + 34 * Math.sin(t)).toFixed(2));
    };
    var lpMove = function (to) { /* toujours dans le sens de la boucle */
      cancelAnimationFrame(lpRaf);
      var from = lpAt, d = ((to - from) % 4 + 4) % 4, t0 = 0;
      lpAt = to;
      if (lpStill || !d || document.hidden) { lpPlace(to); return; }
      var tick = function (now) {
        if (!t0) t0 = now;
        var k = Math.min((now - t0) / (260 * d + 300), 1), e = k < .5 ? 2 * k * k : 1 - Math.pow(-2 * k + 2, 2) / 2;
        lpPlace(from + d * e);
        if (k < 1) lpRaf = requestAnimationFrame(tick);
      };
      lpRaf = requestAnimationFrame(tick);
    };
    var lpShow = function (i) {
      var st = LP[i];
      lpRing.classList.add('run');
      lpRing.classList.toggle('done', i === LP.length - 1);
      Array.prototype.forEach.call(lpNodes, function (n) { n.classList.toggle('on', Number(n.getAttribute('data-n')) === st[0]); });
      lpMove(st[0]);
      lpTurn.textContent = 'Tour ' + st[1];
      lpSay.textContent = st[2];
      lpMid.classList.remove('pop'); void lpMid.offsetWidth; lpMid.classList.add('pop');
      lpCap.textContent = st[3];
    };
    if (window.KwaPlayer) KwaPlayer(loop, { count: LP.length, interval: 2400, show: lpShow,
      reset: function () {
        cancelAnimationFrame(lpRaf); lpAt = 0; lpPlace(0);
        lpRing.classList.remove('run', 'done');
        Array.prototype.forEach.call(lpNodes, function (n) { n.classList.remove('on'); });
        lpTurn.textContent = 'Tour 1'; lpSay.textContent = 'corrige le test qui échoue';
      } });
  }

  /* ---------- le flux d'un développeur ---------- */
  var flow = $('#flow');
  if (flow) {
    var fl = flow.querySelectorAll('.pf-steps li'), fI = -1, fCap = $('#flow-cap');
    var fShow = function () {
      Array.prototype.forEach.call(fl, function (li, i) { li.classList.toggle('on', i === fI); li.classList.toggle('done', i < fI); });
      var who = fl[fI].getAttribute('data-who');
      fCap.textContent = 'Étape ' + (fI + 1) + ' sur ' + fl.length + ' : ' + (who === 'human' ? 'une décision humaine.' : 'automatisé, avec sa preuve.');
    };
    if (window.KwaPlayer) KwaPlayer(flow, { count: fl.length, interval: 2000, show: function (i) { fI = i; fShow(); },
      reset: function () { Array.prototype.forEach.call(fl, function (li) { li.classList.remove('on', 'done'); }); } });
  }

  /* ---------- chargement progressif d'une skill ---------- */
  var skl = $('#skl');
  if (skl) {
    var SK = [
      [{ desc: 3, body: 0, ann: 0 }, 'Au démarrage, seules les descriptions courtes des skills sont dans le contexte : de quoi savoir quand en appeler une.'],
      [{ desc: 3, body: 14, ann: 0 }, 'L\'agent juge que la skill convient : son corps (les étapes) est chargé, et seulement celui-là.'],
      [{ desc: 3, body: 14, ann: 24 }, 'Une étape demande un gabarit : l\'agent lit ce fichier annexe à ce moment-là. Les autres annexes restent sur le disque.']
    ];
    var applySk = function (i) {
      var v = SK[i][0]; $('#sk-desc').style.width = v.desc + '%'; $('#sk-body').style.width = v.body + '%'; $('#sk-ann').style.width = v.ann + '%'; $('#sk-cap').textContent = SK[i][1];
      Array.prototype.forEach.call(skl.querySelectorAll('[data-skl]'), function (b) { b.setAttribute('aria-pressed', String(Number(b.getAttribute('data-skl')) === i)); });
    };
    Array.prototype.forEach.call(skl.querySelectorAll('[data-skl]'), function (b) { b.addEventListener('click', function () { applySk(Number(b.getAttribute('data-skl'))); }); });
    applySk(0);
  }

  /* ---------- fenêtre de contexte : une session qui se remplit, puis se compacte ---------- */
  var gauge = $('#ctx-gauge');
  if (gauge) {
    var F = ['sys', 'rules', 'tools', 'hist', 'files', 'res', 'sum'], WIN = 200000;
    var fill = { sys: 0, rules: 0, tools: 0, hist: 0, files: 0, res: 0, sum: 0 };
    var gtxt = $('#ctx-txt'), gmsg = $('#ctx-msg'), gstack = $('#ctx-stack');
    var FRAMES = [
      [{ sys: 6000, rules: 3000, tools: 12000 }, 1100, 'Au démarrage, les consignes, les instructions et les outils occupent déjà la fenêtre, avant votre premier message.'],
      [{ hist: 14000 }, 1300, 'Vous échangez avec l\'agent : l\'historique grossit.'],
      [{ files: 42000 }, 1500, 'Il lit des fichiers pour comprendre le code : chacun reste dans la fenêtre.'],
      [{ hist: 30000, res: 48000 }, 1500, 'Les résultats des outils (tests, recherches, commandes) s\'accumulent.'],
      [{ hist: 52000, files: 58000, res: 64000 }, 1600, 'La fenêtre est presque pleine : la précision peut baisser avant même qu\'elle déborde.'],
      [{ hist: 3000, files: 7000, res: 2500, sum: 6000 }, 2000, 'Compaction : un agent résume l\'historique et les résultats, la session repart avec un contexte court.']
    ];
    var gpaint = function (note) {
      var tot = 0;
      F.forEach(function (f) { tot += fill[f]; $('#seg-' + f).style.width = (fill[f] / WIN * 100) + '%'; });
      gstack.classList.toggle('pc-over', tot / WIN > 0.9);
      gtxt.textContent = fmt(tot) + ' jetons sur ' + fmt(WIN) + ' (' + Math.round(tot / WIN * 100) + ' %)';
      if (note) gmsg.textContent = note;
    };
    var gtween = function (target, ms, done) {
      var from = {}; F.forEach(function (f) { from[f] = fill[f]; });
      if (reduced || ms <= 0) { F.forEach(function (f) { if (f in target) fill[f] = target[f]; }); gpaint(); if (done) done(); return; }
      var t0 = null;
      (function step(ts) {
        if (!gstate.on) return;
        if (t0 === null) t0 = ts;
        var k = Math.min(1, (ts - t0) / ms), e = 1 - Math.pow(1 - k, 3);
        F.forEach(function (f) { if (f in target) fill[f] = from[f] + (target[f] - from[f]) * e; });
        gpaint();
        if (k < 1) requestAnimationFrame(step); else if (done) done();
      })(performance.now());
    };
    var gstate = { on: false, i: 0, timer: null };
    var gnext = function () {
      if (!gstate.on) return;
      if (gstate.i >= FRAMES.length) {
        gstate.timer = setTimeout(function () { F.forEach(function (f) { fill[f] = 0; }); gpaint(); gmsg.textContent = ''; gstate.i = 0; gstate.timer = setTimeout(gnext, 700); }, 3200);
        return;
      }
      var fr = FRAMES[gstate.i++];
      gmsg.textContent = fr[2];
      gtween(fr[0], fr[1], function () { gstate.timer = setTimeout(gnext, 900); });
    };
    gpaint();
    if (reduced || !('IntersectionObserver' in window)) {
      FRAMES.slice(0, 5).forEach(function (fr) { F.forEach(function (f) { if (f in fr[0]) fill[f] = fr[0][f]; }); });
      gpaint(FRAMES[4][2]);
    } else {
      new IntersectionObserver(function (es) {
        if (es[0].isIntersecting && !gstate.on) { gstate.on = true; gnext(); }
        else if (!es[0].isIntersecting && gstate.on) { gstate.on = false; clearTimeout(gstate.timer); }
      }, { threshold: 0.5 }).observe(gauge);
    }
  }
})();
