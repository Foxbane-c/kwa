/* Workflows animés : six macro-briques compactes sur une ligne. Quand le jeton entre dans une brique, elle s'ouvre et
   montre ses étapes (skills, gardes, agents, vos décisions) ; quand il passe à la suivante, elle se referme. Une boucle
   vers une brique précédente est une flèche sur la ligne des briques. Scénario : src/flows.py, injecté en JSON.
   Lecture, pause, rejouer ; démarre seul quand le schéma devient visible. Mouvement réduit : rien ne part seul, les
   changements sont instantanés. Script classique, sans dépendance. */
(function () {
  'use strict';
  var reduced = window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  var NS = 'http://www.w3.org/2000/svg';
  var MORPH = 650;  // durée d'ouverture ou de fermeture d'une brique (flows.css)

  function h(tag, cls, text) {
    var e = document.createElement(tag);
    if (cls) e.className = cls;
    if (text != null) e.textContent = text;
    return e;
  }
  function each(list, fn) { Array.prototype.forEach.call(list, fn); }

  function mount(root) {
    var script = JSON.parse(root.querySelector('.fl-script').textContent);
    var board = root.querySelector('.fl-board'), token = root.querySelector('.fl-token'), arcs = root.querySelector('.fl-arcs');
    var fill = root.querySelector('.fl-fill'), say = root.querySelector('.fl-say');
    var playBtn = root.querySelector('.fl-play'), restart = root.querySelector('.fl-restart');
    var bricks = Array.prototype.slice.call(root.querySelectorAll('.fl-brick'));
    var byIndex = {};
    each(root.querySelectorAll('.fl-node'), function (n) { byIndex[n.getAttribute('data-i')] = n; });
    var picto = function (kind) { var d = root.querySelector('.fl-legend .fl-' + kind + ' .fl-dot'); return d ? d.innerHTML : ''; };
    var st = { i: 0, playing: false, timer: null, at: null, open: null, run: 0 };
    var T = function (ms) { return reduced ? Math.min(ms, 300) : ms; };
    function later(fn, ms) { var run = st.run; st.timer = setTimeout(function () { if (run === st.run) fn(); }, T(ms)); }

    function brickOf(i) { return byIndex[i].closest('.fl-brick'); }
    function rel(el) {
      var b = board.getBoundingClientRect(), r = el.getBoundingClientRect();
      return { x: r.left - b.left + r.width / 2, y: r.top - b.top + r.height / 2, top: r.top - b.top, bottom: r.bottom - b.top, left: r.left - b.left };
    }
    function progress(brick) {
      var k = bricks.indexOf(brick);
      fill.style.width = ((k + 1) / bricks.length * 100) + '%';
      bricks.forEach(function (b, j) { b.classList.toggle('is-done', j < k); });
    }
    /* ouvrir une brique (et refermer l'autre), puis continuer */
    function open(brick, then) {
      if (st.open === brick) return then();
      token.classList.remove('is-on');
      clearPops();
      if (st.open) st.open.classList.remove('is-open');
      brick.classList.add('is-open');
      st.open = brick;
      progress(brick);
      if (window.innerWidth <= 760 && watching) {  // téléphone : les briques s'empilent, on garde la brique ouverte en vue
        setTimeout(function () { brick.scrollIntoView({ block: 'nearest', behavior: reduced ? 'auto' : 'smooth' }); }, T(MORPH));
      }
      later(then, MORPH);
    }
    function place(i) {
      var n = byIndex[i], c = rel(n.querySelector('.fl-dot')), first = !token.classList.contains('is-on');
      if (first) token.style.transition = 'none';
      token.style.transform = 'translate(' + (c.x - 9) + 'px,' + (c.y - 9) + 'px)';
      if (first) { void token.offsetWidth; token.style.transition = ''; }
      token.classList.add('is-on');
      each(root.querySelectorAll('.fl-node'), function (x) { x.classList.toggle('is-here', x === n); });
      n.classList.add('is-seen');
      st.at = i;
    }
    function goTo(i, then) { open(brickOf(i), function () { place(i); if (then) then(); }); }

    function clearPops() { each(board.querySelectorAll('.fl-pop'), function (p) { p.remove(); }); }
    function pop(node, cls) {
      var p = h('div', 'fl-pop ' + cls), r = rel(node), w = Math.min(280, board.clientWidth - 16);
      p.style.left = Math.max(8, Math.min(r.left, board.clientWidth - w - 8)) + 'px';
      p.style.top = (r.bottom + 8) + 'px';
      board.appendChild(p);
      return p;
    }
    /* flèche de boucle : entre deux étapes de la brique ouverte, ou entre deux briques sur la ligne */
    function arrow(fromEl, toEl, self) {
      var a = rel(fromEl), z = rel(toEl), path = document.createElementNS(NS, 'path'), d;
      if (self) d = 'M' + (a.x + 10) + ' ' + (a.top + 2) + ' C ' + (a.x + 60) + ' ' + (a.top - 44) + ', ' + (a.x - 60) + ' ' + (a.top - 44) + ', ' + (a.x - 10) + ' ' + (a.top + 2);
      else {
        var y = Math.min(a.top, z.top) - 26;
        d = 'M' + a.x + ' ' + a.top + ' C ' + a.x + ' ' + y + ', ' + z.x + ' ' + y + ', ' + z.x + ' ' + z.top;
      }
      path.setAttribute('d', d);
      path.setAttribute('class', 'fl-arc');
      path.setAttribute('marker-end', 'url(#fl-head-' + root.id + ')');
      arcs.appendChild(path);
      var len = path.getTotalLength ? path.getTotalLength() : 300;
      path.style.strokeDasharray = len;
      path.style.strokeDashoffset = reduced ? 0 : len;
      requestAnimationFrame(function () { requestAnimationFrame(function () { path.style.strokeDashoffset = 0; }); });
      later(function () { path.classList.add('is-out'); }, 2200);
      later(function () { path.remove(); }, 2800);
    }
    function loop(ev, then) {
      var from = byIndex[ev.at], to = byIndex[ev.to], same = brickOf(ev.at) === brickOf(ev.to);
      var tag = pop(from, 'fl-pop-loop');
      tag.appendChild(h('b', null, 'Boucle'));
      tag.appendChild(h('span', null, ev.why || ev.say));
      if (same) { arrow(from.querySelector('.fl-dot'), to.querySelector('.fl-dot'), ev.at === ev.to); return later(function () { place(ev.to); then(); }, 1500); }
      arrow(brickOf(ev.at).querySelector('header'), brickOf(ev.to).querySelector('header'), false);
      later(function () { goTo(ev.to, then); }, 1500);
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
      if (ev.t === 'go') return goTo(ev.at, function () { next(1800); });
      if (ev.t === 'guard') return goTo(ev.at, function () {
        var n = byIndex[ev.at];
        n.classList.add('is-deny');
        var p = pop(n, 'fl-pop-deny');
        p.appendChild(h('b', null, 'Refusé par ' + n.querySelector('b').textContent));
        p.appendChild(h('span', null, ev.msg));
        later(function () { n.classList.remove('is-deny'); }, 3200);
        next(3400);
      });
      if (ev.t === 'loop') return goTo(ev.at, function () { loop({ at: ev.at, to: ev.to, say: ev.say }, function () { next(1400); }); });
      if (ev.t === 'ask') return goTo(ev.at, function () { ask(ev); });
      if (ev.t === 'delegate') return goTo(ev.at, function () { delegate(ev); });
      if (ev.t === 'handoff') return goTo(ev.at, function () { handoff(ev); });
      next(800);
    }
    function next(ms) { if (st.playing) later(step, ms); }

    function ask(ev) {
      var p = pop(byIndex[ev.at], 'fl-pop-ask'), row = h('div', 'fl-opts'), done = false;
      p.setAttribute('role', 'dialog');
      p.setAttribute('aria-label', ev.q);
      p.appendChild(h('b', null, ev.q));
      var resolve = function (k) {
        if (done) return;
        done = true;
        var o = ev.opts[k];
        each(row.children, function (b, j) { b.classList.toggle('is-picked', j === k); b.disabled = true; });
        if (k !== ev.pick) {  // choix hors scénario : sa conséquence, puis la question revient
          say.textContent = 'Vous choisissez « ' + o.label + ' » : ' + (o.why || 'on continue.') + ' Puis la question revient.';
          st.i--;
          if (o.to != null) return later(function () { loop({ at: ev.at, to: o.to, why: o.why }, function () { later(step, 1200); }); }, 600);
          return later(step, 2400);
        }
        say.textContent = ev.say;
        later(step, 1100);
      };
      ev.opts.forEach(function (o, k) {
        var b = h('button', 'fl-opt' + (k === 0 ? ' is-main' : ''), o.label);
        b.type = 'button';
        b.addEventListener('click', function () {
          if (!st.playing) { st.playing = true; playBtn.textContent = 'Pause'; playBtn.setAttribute('aria-pressed', 'true'); }
          resolve(k);
        });
        row.appendChild(b);
      });
      p.appendChild(row);
      if (st.playing) later(function () { resolve(ev.pick); }, 2600);
    }

    function delegate(ev) {
      var tray = brickOf(ev.at).querySelector('.fl-tray');
      tray.textContent = '';
      tray.classList.add('is-open');
      ev.agents.forEach(function (a, k) {
        var c = h('div', 'fl-sub'), t = h('span', 'fl-sub-t');
        c.innerHTML = '<span class="fl-dot">' + picto('agent') + '</span>';
        t.appendChild(h('b', null, a.who));
        t.appendChild(h('small', null, a.task));
        c.appendChild(t);
        c.style.animationDelay = (k * 160) + 'ms';
        tray.appendChild(c);
        later(function () { c.classList.add('is-back'); t.lastChild.textContent = 'retour : ' + a.back; }, 1700 + k * 260);
      });
      later(function () { tray.classList.remove('is-open'); }, 3800 + ev.agents.length * 200);
      next(4300 + ev.agents.length * 200);
    }

    function handoff(ev) {
      var card = h('div', 'fl-hand');
      card.innerHTML = '<span class="fl-dot">' + picto('doc') + '</span>';
      card.appendChild(h('span', null, 'vers la session suivante'));
      brickOf(ev.at).querySelector('.fl-body').appendChild(card);
      later(function () { card.classList.add('is-gone'); }, 2400);
      later(function () { card.remove(); }, 3300);
      next(3400);
    }

    function reset() {
      st.run++; clearTimeout(st.timer); st.i = 0; st.at = null; st.open = null;
      clearPops();
      each(arcs.querySelectorAll('.fl-arc'), function (a) { a.remove(); });
      each(root.querySelectorAll('.fl-tray'), function (t) { t.textContent = ''; t.classList.remove('is-open'); });
      each(root.querySelectorAll('.fl-node'), function (x) { x.classList.remove('is-here', 'is-seen', 'is-deny'); });
      bricks.forEach(function (b) { b.classList.remove('is-open', 'is-done'); });
      fill.style.width = '0';
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
    window.addEventListener('resize', function () { if (st.at != null) place(st.at); });
    var watching = false;  // le schéma est à l'écran : seulement alors on fait défiler vers la brique ouverte
    if ('IntersectionObserver' in window) {
      new IntersectionObserver(function (es) { watching = es[0].isIntersecting; }, { threshold: 0.05 }).observe(board);
    }
    if (!reduced && 'IntersectionObserver' in window) {
      var io = new IntersectionObserver(function (es) {
        if (es[0].isIntersecting && !st.playing && st.i === 0) { io.disconnect(); play(); }
      }, { threshold: 0.35 });
      io.observe(board);
    }
  }

  each(document.querySelectorAll('.fl'), mount);
})();
