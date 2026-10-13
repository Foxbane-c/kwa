/* Schéma « Skills qui délèguent » : une ligne de cinq étapes (skill, prompt, agents, rapport, vérification) que
   chaque scénario remplit pas à pas. Lecture automatique ou étape par étape ; en mouvement réduit, étape par étape
   seulement et sans animation. Script classique, sans dépendance. */
(function () {
  'use strict';
  var root = document.getElementById('dg');
  if (!root) return;
  var reduced = window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  var cap = document.getElementById('dg-cap');

  function chip(text, kind, extra) { return { text: text, kind: kind || '', extra: extra || {} }; }
  var S = {
    agents: [
      ['skill', [chip('Le plan : 3 tâches', 'plan')], '/kwa:agents lit le plan validé. Les tâches sont assez indépendantes pour être confiées une à une.'],
      ['prompt', [chip('implementer-prompt.md', 'file', { fill: 'tâche 1 · critères · fichiers · format de retour' })], 'Elle remplit le modèle de prompt pour la tâche 1 : le contexte, les fichiers, les critères de réussite, le format de retour. L\'agent ne verra rien d\'autre.'],
      ['agents', [chip('impl-tâche-1', 'agent', { run: 1 })], 'Un agent neuf implémente la tâche, test d\'abord, dans sa propre fenêtre de contexte.'],
      ['report', [chip('fait · tests verts · 3 fichiers', 'report')], 'Seul un rapport court revient. La lecture des fichiers reste dans la fenêtre de l\'agent, qui est jetée.'],
      ['check', [chip('kwa:relecteur · conformité', 'review', { lock: 1 }), chip('kwa:relecteur · qualité', 'review', { lock: 1 })], 'Deux relectures par un agent neuf, en lecture seule : la conformité à la tâche, puis la qualité. Jamais l\'implémenteur qui se relit.'],
      ['agents', [chip('impl-tâche-2', 'agent', { run: 1 })], 'Tâche suivante : un nouvel agent, le même circuit. Un blocage remonte au lieu d\'être contourné.'],
      ['check', [chip('vérifications du projet', 'proof')], 'À la fin, la session relance elle-même les vérifications du projet. Un rapport d\'agent n\'est pas une preuve.']
    ],
    parallel: [
      ['skill', [chip('3 problèmes indépendants', 'plan')], '/kwa:parallel vérifie d\'abord que les problèmes n\'ont ni fichier ni état en commun.'],
      ['prompt', [chip('agent-prompt.md × 3', 'file', { fill: 'un prompt autonome par problème' })], 'Un prompt complet par problème : erreurs exactes collées, fichiers, contraintes, format de retour.'],
      ['agents', [chip('agent A · tests', 'agent', { run: 1 }), chip('agent B · API', 'agent', { run: 1 }), chip('agent C · doc', 'agent', { run: 1, wt: 1 })], 'Les trois agents partent en même temps. Celui qui touche une zone voisine travaille dans son propre worktree.'],
      ['report', [chip('A · fait', 'report'), chip('C · fait', 'report'), chip('B · bloqué, raison', 'report')], 'Les rapports arrivent dans l\'ordre où les agents finissent. Un blocage est un résultat, pas un échec à cacher.'],
      ['check', [chip('intégration · conflits · vérifications', 'proof')], 'La session intègre, cherche les conflits entre les changements, puis lance les vérifications du projet.']
    ],
    review: [
      ['skill', [chip('le diff de la branche', 'plan')], '/kwa:review rassemble le diff, la demande d\'origine et ses critères.'],
      ['prompt', [chip('reviewer-prompt.md', 'file', { fill: 'la tâche seulement : le rôle est dans l\'agent' })], 'Le prompt ne décrit que la tâche : le rôle, les axes et le format de retour sont dans la définition de l\'agent.'],
      ['agents', [chip('kwa:relecteur', 'review', { run: 1, lock: 1 })], 'Un relecteur neuf, en lecture seule : sous Claude Code ses outils d\'écriture sont retirés, sous Codex il tourne dans un bac à sable en lecture seule.'],
      ['report', [chip('IMPORTANT · fichier:ligne', 'report'), chip('verdict : prêt après corrections', 'report')], 'Il rend des constats classés par gravité et un verdict, pas des corrections.'],
      ['check', [chip('corrections, puis relecture ciblée', 'proof')], 'La session corrige, puis le même relecteur vérifie que chaque point est réglé, sans nouveau défaut.']
    ]
  };

  var st = {}, cur = 'agents', i = -1;
  Array.prototype.forEach.call(root.querySelectorAll('.dg-st'), function (li) { st[li.getAttribute('data-st')] = li; });

  function el(tag, cls, text) { var e = document.createElement(tag); if (cls) e.className = cls; if (text) e.textContent = text; return e; }
  function render(c) {
    var n = el('div', 'dg-chip dg-' + c.kind);
    n.appendChild(el('span', 'dg-t', c.text));
    if (c.extra.fill) n.appendChild(el('small', 'dg-fill', c.extra.fill));
    if (c.extra.lock) n.appendChild(el('em', 'dg-tag', 'lecture seule'));
    if (c.extra.wt) n.appendChild(el('em', 'dg-tag', 'worktree'));
    if (c.extra.run) {
      var bar = el('span', 'dg-run'), fill = el('i');
      bar.appendChild(fill); n.appendChild(bar);
      if (reduced) fill.style.width = '100%';
      else setTimeout(function () { fill.style.transitionDuration = (0.9 + Math.random() * 1.2).toFixed(2) + 's'; fill.style.width = '100%'; }, 60);
    }
    return n;
  }
  function reset() {
    i = -1;
    Object.keys(st).forEach(function (k) { st[k].classList.remove('on', 'done'); st[k].querySelector('.dg-body').textContent = ''; });
    cap.textContent = 'Choisissez une skill, puis lancez la lecture ou avancez pas à pas.';
  }
  function show(k) {  // l'état complet de l'étape k : on repart de zéro et on rejoue jusqu'à elle
    var steps = S[cur];
    Object.keys(st).forEach(function (n) { st[n].classList.remove('on', 'done'); st[n].querySelector('.dg-body').textContent = ''; });
    for (var j = 0; j <= k; j++) {
      var s = steps[j];
      Object.keys(st).forEach(function (n) {
        if (st[n].classList.contains('on')) st[n].classList.add('done');
        st[n].classList.toggle('on', n === s[0]);
      });
      var body = st[s[0]].querySelector('.dg-body');
      s[1].forEach(function (c) { body.appendChild(render(c)); });
    }
    i = k;
    cap.textContent = steps[k][2];
  }
  var player = window.KwaPlayer && KwaPlayer(root, { count: function () { return S[cur].length; }, show: show, reset: reset, interval: 2400 });

  Array.prototype.forEach.call(root.querySelectorAll('[data-dg]'), function (b) {
    b.addEventListener('click', function () {
      cur = b.getAttribute('data-dg');
      Array.prototype.forEach.call(root.querySelectorAll('[data-dg]'), function (o) { o.setAttribute('aria-pressed', String(o === b)); });
      if (player) player.reset();
    });
  });
  reset();
})();
