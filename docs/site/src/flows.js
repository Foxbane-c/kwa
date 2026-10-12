/* Workflows animés : un jeton parcourt les briques d'un workflow en suivant son scénario (données dans src/flows.py,
   injectées en JSON dans la page). Boucles, décisions (mini-fenêtre), refus de garde, délégation à des sous-agents,
   passage de relais. Lecture, pause, rejouer ; démarre seul quand le schéma devient visible. En mouvement réduit, rien
   ne part tout seul et les déplacements sont instantanés. Script classique, sans dépendance. */
(function () {
  'use strict';
  var reduced = window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  var NS = 'http://www.w3.org/2000/svg';

  function h(tag, cls, text) {
    var e = document.createElement(tag);
    if (cls) e.className = cls;
    if (text != null) e.textContent = text;
    return e;
  }

  function mount(root) {
    var script = JSON.parse(root.querySelector('.fl-script').textContent);
    var board = root.querySelector('.fl-board'), token = root.querySelector('.fl-token'), arcs = root.querySelector('.fl-arcs');
    var say = root.querySelector('.fl-say'), playBtn = root.querySelector('.fl-play'), restart = root.querySelector('.fl-restart');
    var nodes = Array.prototype.slice.call(root.querySelectorAll('.fl-node'));
    var byIndex = {};
    nodes.forEach(function (n) { byIndex[n.getAttribute('data-i')] = n; });
    var picto = function (kind) { var d = root.querySelector('.fl-legend .fl-' + kind + ' .fl-dot'); return d ? d.innerHTML : ''; };

    var st = { i: 0, playing: false, timer: null, waiting: null, at: null, run: 0 };
    var T = function (ms) { return reduced ? Math.min(ms, 400) : ms; };

    function center(node) {
      var b = board.getBoundingClientRect(), r = node.querySelector('.fl-dot').getBoundingClientRect();
      return { x: r.left - b.left + r.width / 2, y: r.top - b.top + r.height / 2 };
    }
    function moveTo(i) {
      var n = byIndex[i];
      if (!n) return;
      var c = center(n), first = !token.classList.contains('is-on');
      if (first) token.style.transition = 'none';  // première apparition : sur l'étape, sans glisser depuis le coin
      token.style.transform = 'translate(' + (c.x - 9) + 'px,' + (c.y - 9) + 'px)';
      if (first) { void token.offsetWidth; token.style.transition = ''; }
      token.classList.add('is-on');
      nodes.forEach(function (x) { x.classList.toggle('is-here', x === n); });
      n.classList.add('is-seen');
      st.at = i;
    }
    function later(fn, ms) { var run = st.run; st.timer = setTimeout(function () { if (run === st.run) fn(); }, T(ms)); }
    function clearPops() { Array.prototype.forEach.call(board.querySelectorAll('.fl-pop'), function (p) { p.remove(); }); }
    function pop(node, cls) {
      var p = h('div', 'fl-pop ' + cls);
      board.appendChild(p);
      var b = board.getBoundingClientRect(), r = node.getBoundingClientRect();
      var left = Math.min(Math.max(8, r.left - b.left), b.width - 288);
      p.style.left = Math.max(8, left) + 'px';
      p.style.top = (r.bottom - b.top + 8) + 'px';
      return p;
    }
    function arc(from, to, label) {
      var a = center(byIndex[from]), z = center(byIndex[to]);
      var path = document.createElementNS(NS, 'path');
      var d;
      if (from === to) d = 'M' + (a.x + 12) + ' ' + (a.y - 6) + ' C ' + (a.x + 60) + ' ' + (a.y - 50) + ', ' + (a.x - 60) + ' ' + (a.y - 50) + ', ' + (a.x - 12) + ' ' + (a.y - 6);
      else {
        var lift = Math.max(40, Math.abs(a.x - z.x) / 4);
        d = 'M' + a.x + ' ' + (a.y - 14) + ' C ' + a.x + ' ' + (Math.min(a.y, z.y) - lift) + ', ' + z.x + ' ' + (Math.min(a.y, z.y) - lift) + ', ' + z.x + ' ' + (z.y - 14);
      }
      path.setAttribute('d', d);
      path.setAttribute('class', 'fl-arc');
      path.setAttribute('marker-end', 'url(#fl-head-' + root.id + ')');
      arcs.appendChild(path);
      var len = path.getTotalLength ? path.getTotalLength() : 300;
      path.style.strokeDasharray = len;
      path.style.strokeDashoffset = reduced ? 0 : len;
      requestAnimationFrame(function () { path.style.strokeDashoffset = 0; });
      var tag = pop(byIndex[from], 'fl-pop-loop');
      tag.appendChild(h('b', null, 'Boucle'));
      tag.appendChild(h('span', null, label));
      later(function () { path.classList.add('is-out'); }, 2600);
      later(function () { path.remove(); }, 3200);
    }

    function step() {
      if (st.i >= script.length) {
        st.playing = false;
        playBtn.textContent = 'Lire'; playBtn.setAttribute('aria-pressed', 'false');
        say.textContent = 'Fin du workflow : de l\'intention floue à la PR fusionnée, puis la leçon rangée. Rejouez pour le revoir.';
        return;
      }
      var ev = script[st.i++];
      clearPops();
      say.textContent = ev.say || '';
      if (ev.t === 'go') { moveTo(ev.at); return next(1700); }
      if (ev.t === 'guard') {
        moveTo(ev.at);
        var n = byIndex[ev.at];
        n.classList.add('is-deny');
        var p = pop(n, 'fl-pop-deny');
        p.appendChild(h('b', null, 'Refusé par ' + n.querySelector('b').textContent));
        p.appendChild(h('span', null, ev.msg));
        later(function () { n.classList.remove('is-deny'); }, 3000);
        return next(3200);
      }
      if (ev.t === 'loop') { moveTo(ev.at); arc(ev.at, ev.to, ev.say); later(function () { moveTo(ev.to); }, 1100); return next(2600); }
      if (ev.t === 'ask') return ask(ev);
      if (ev.t === 'delegate') return delegate(ev);
      if (ev.t === 'handoff') return handoff(ev);
      next(800);
    }
    function next(ms) { if (st.playing) later(step, ms); }

    function ask(ev) {
      moveTo(ev.at);
      var p = pop(byIndex[ev.at], 'fl-pop-ask');
      p.setAttribute('role', 'dialog');
      p.setAttribute('aria-label', ev.q);
      p.appendChild(h('b', null, ev.q));
      var row = h('div', 'fl-opts');
      var done = false;
      var resolve = function (k) {
        if (done) return;
        done = true;
        var o = ev.opts[k];
        Array.prototype.forEach.call(row.children, function (b, j) { b.classList.toggle('is-picked', j === k); b.disabled = true; });
        if (k !== ev.pick) {  // le choix hors scénario : on montre sa conséquence, puis la question revient
          say.textContent = 'Vous choisissez « ' + o.label + ' » : ' + (o.why || 'on continue.') + ' Le scénario reprend ensuite son chemin.';
          if (o.to != null) { arc(ev.at, o.to, o.why); }
          st.i--;
          return later(step, 3000);
        }
        say.textContent = ev.say;
        later(step, 1200);
      };
      ev.opts.forEach(function (o, k) {
        var b = h('button', 'fl-opt' + (k === 0 ? ' is-main' : ''), o.label);
        b.type = 'button';
        b.addEventListener('click', function () { if (!st.playing) { st.playing = true; playBtn.textContent = 'Pause'; playBtn.setAttribute('aria-pressed', 'true'); } resolve(k); });
        row.appendChild(b);
      });
      p.appendChild(row);
      if (st.playing) later(function () { resolve(ev.pick); }, 2400);
    }

    function delegate(ev) {
      moveTo(ev.at);
      var n = byIndex[ev.at], tray = n.closest('.fl-brick').querySelector('.fl-tray');
      tray.textContent = '';
      tray.classList.add('is-open');
      ev.agents.forEach(function (a, k) {
        var c = h('div', 'fl-sub');
        c.innerHTML = '<span class="fl-dot">' + picto('agent') + '</span>';
        var t = h('span', 'fl-sub-t');
        t.appendChild(h('b', null, a.who));
        t.appendChild(h('small', null, a.task));
        c.appendChild(t);
        c.style.animationDelay = (k * 180) + 'ms';
        tray.appendChild(c);
        later(function () { c.classList.add('is-back'); t.lastChild.textContent = 'retour : ' + a.back; }, 1700 + k * 260);
      });
      later(function () { tray.classList.remove('is-open'); }, 3600 + ev.agents.length * 200);
      next(4000 + ev.agents.length * 200);
    }

    function handoff(ev) {
      moveTo(ev.at);
      var n = byIndex[ev.at], card = h('div', 'fl-hand');
      card.innerHTML = '<span class="fl-dot">' + picto('doc') + '</span>';
      card.appendChild(h('span', null, 'Session suivante'));
      n.closest('.fl-brick').appendChild(card);
      later(function () { card.classList.add('is-gone'); }, 2600);
      later(function () { card.remove(); }, 3400);
      next(3400);
    }

    function reset() {
      st.run++; clearTimeout(st.timer); st.i = 0; st.at = null;
      clearPops();
      Array.prototype.forEach.call(arcs.querySelectorAll('.fl-arc'), function (a) { a.remove(); });
      Array.prototype.forEach.call(root.querySelectorAll('.fl-tray'), function (t) { t.textContent = ''; t.classList.remove('is-open'); });
      nodes.forEach(function (x) { x.classList.remove('is-here', 'is-seen', 'is-deny'); });
      token.classList.remove('is-on');
    }
    function play() {
      st.playing = !st.playing;
      playBtn.textContent = st.playing ? 'Pause' : 'Lire';
      playBtn.setAttribute('aria-pressed', String(st.playing));
      if (!st.playing) { st.run++; clearTimeout(st.timer); return; }
      if (st.i >= script.length) reset();
      step();
    }
    var defs = document.createElementNS(NS, 'defs');
    defs.innerHTML = '<marker id="fl-head-' + root.id + '" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path d="M0 0L10 5L0 10z"/></marker>';
    arcs.appendChild(defs);
    playBtn.addEventListener('click', play);
    restart.addEventListener('click', function () { reset(); st.playing = false; play(); });
    window.addEventListener('resize', function () { if (st.at != null) moveTo(st.at); });
    if (!reduced && 'IntersectionObserver' in window) {
      var io = new IntersectionObserver(function (es) {
        if (es[0].isIntersecting && !st.playing && st.i === 0) { io.disconnect(); play(); }
      }, { threshold: 0.35 });
      io.observe(board);
    }
  }

  Array.prototype.forEach.call(document.querySelectorAll('.fl'), mount);
})();
