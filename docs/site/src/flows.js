/* Workflows animés : six macro-briques compactes sur une ligne. Quand le jeton entre dans une brique, elle s'ouvre et
   montre ses étapes (skills, gardes, agents, vos décisions) ; quand il passe à la suivante, elle se referme. Une boucle
   vers une brique précédente est une flèche entre briques. Scénario : src/flows.py, injecté en JSON.
   Deux façons de lire : la lecture automatique (démarre seule quand le schéma devient visible), ou pas à pas avec
   Précédent / Suivant et les flèches du clavier. Revenir en arrière rejoue instantanément tout ce qui précède, puis
   anime le pas demandé. Mouvement réduit : rien ne part seul, les changements sont instantanés.
   Script classique, sans dépendance. */
(function () {
  'use strict';
  var reduced = window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  var NS = 'http://www.w3.org/2000/svg';
  var MORPH = 650;  // durée d'ouverture ou de fermeture d'une brique (flows.css)
  var REVEAL = 450;  // apparition du contenu d'une brique ouverte, après sa morphose
  var PAUSE = { go: 1800, guard: 3400, loop: 1400, ask: 1100, delegate: 1000, handoff: 1200 };  // lecture auto : temps de lecture après un pas

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
    var fill = root.querySelector('.fl-fill'), say = root.querySelector('.fl-say'), count = root.querySelector('.kp-count');
    var playBtn = root.querySelector('[data-p="play"]'), prevBtn = root.querySelector('[data-p="prev"]'), nextBtn = root.querySelector('[data-p="next"]');
    var restart = root.querySelector('[data-p="restart"]');
    var bricks = Array.prototype.slice.call(root.querySelectorAll('.fl-brick'));
    var byIndex = {};
    each(root.querySelectorAll('.fl-node'), function (n) { byIndex[n.getAttribute('data-i')] = n; });
    var picto = function (kind) { var d = root.querySelector('.fl-legend .fl-' + kind + ' .fl-dot'); return d ? d.innerHTML : ''; };
    var intro = say.textContent;
    // i : nombre de pas déjà joués ; fast : on reconstruit un état sans animer ; run : invalide les minuteries d'un état périmé
    var st = { i: 0, playing: false, fast: false, timers: [], at: null, open: null, run: 0 };
    var watching = false;

    function later(fn, ms) {
      if (st.fast) return fn();
      var run = st.run;
      st.timers.push(setTimeout(function () { if (run === st.run) fn(); }, reduced ? Math.min(ms, 250) : ms));
    }
    function stopTimers() { st.run++; st.timers.forEach(clearTimeout); st.timers = []; }

    function brickOf(i) { return byIndex[i].closest('.fl-brick'); }
    function rel(el) {
      var b = board.getBoundingClientRect(), r = el.getBoundingClientRect();
      return { x: r.left - b.left + r.width / 2, top: r.top - b.top, bottom: r.bottom - b.top, left: r.left - b.left, y: r.top - b.top + r.height / 2 };
    }
    function progress(brick) {
      var k = bricks.indexOf(brick);
      fill.style.width = ((k + 1) / bricks.length * 100) + '%';
      bricks.forEach(function (b, j) { b.classList.toggle('is-done', j < k); });
    }
    function open(brick, then) {
      if (st.open === brick) return then();
      token.classList.remove('is-on');
      clearPops();
      if (st.open) st.open.classList.remove('is-open');
      brick.classList.add('is-open');
      st.open = brick;
      progress(brick);
      if (!st.fast && window.innerWidth <= 760 && watching) {  // téléphone : on garde la brique ouverte en vue
        later(function () { brick.scrollIntoView({ block: 'nearest', behavior: reduced ? 'auto' : 'smooth' }); }, MORPH);
      }
      later(then, MORPH + REVEAL);  // le jeton arrive une fois le contenu apparu (flows.css : fondu en cascade)
    }
    function place(i) {
      if (st.fast) { st.at = i; byIndex[i].classList.add('is-seen'); return; }
      var n = byIndex[i], c = rel(n.querySelector('.fl-dot')), first = !token.classList.contains('is-on');
      if (first) token.style.transition = 'none';
      token.style.transform = 'translate(' + (c.x - 9) + 'px,' + (c.y - 9) + 'px)';
      if (first) { void token.offsetWidth; token.style.transition = ''; }
      token.classList.add('is-on');
      each(root.querySelectorAll('.fl-node'), function (x) { x.classList.toggle('is-here', x === n); });
      n.classList.add('is-seen');
      st.at = i;
    }
    function goTo(i, then) { open(brickOf(i), function () { place(i); then(); }); }

    function clearPops() { each(board.querySelectorAll('.fl-pop'), function (p) { p.remove(); }); }
    function pop(node, cls) {
      var p = h('div', 'fl-pop ' + cls), r = rel(node), w = Math.min(280, board.clientWidth - 16);
      p.style.left = Math.max(8, Math.min(r.left, board.clientWidth - w - 8)) + 'px';
      p.style.top = (r.bottom + 8) + 'px';
      board.appendChild(p);
      return p;
    }
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
      later(function () { path.classList.add('is-out'); }, 2600);
      later(function () { path.remove(); }, 3200);
    }
    function loop(ev, done) {
      var from = byIndex[ev.at], same = brickOf(ev.at) === brickOf(ev.to);
      if (st.fast) return goTo(ev.to, done);
      clearPops();
      var tag = pop(from, 'fl-pop-loop');
      tag.appendChild(h('b', null, 'Boucle'));
      tag.appendChild(h('span', null, ev.why || ev.say));
      if (same) { arrow(from.querySelector('.fl-dot'), byIndex[ev.to].querySelector('.fl-dot'), ev.at === ev.to); return later(function () { place(ev.to); done(); }, 1500); }
      arrow(brickOf(ev.at).querySelector('header'), brickOf(ev.to).querySelector('header'), false);
      later(function () { goTo(ev.to, done); }, 1500);
    }

    /* un pas du scénario ; done() quand son animation est finie */
    function run(ev, done) {
      if (!st.fast) { clearPops(); say.textContent = ev.t === 'ask' ? ev.q : (ev.say || ''); }  // une décision : la question d'abord, sa suite après
      if (ev.t === 'go') return goTo(ev.at, done);
      if (ev.t === 'guard') return goTo(ev.at, function () {
        if (st.fast) return done();
        var n = byIndex[ev.at];
        n.classList.add('is-deny');
        var p = pop(n, 'fl-pop-deny');
        p.appendChild(h('b', null, 'Refusé par ' + n.querySelector('b').textContent));
        p.appendChild(h('span', null, ev.msg));
        later(function () { n.classList.remove('is-deny'); }, 1000);
        done();
      });
      if (ev.t === 'loop') return goTo(ev.at, function () { loop({ at: ev.at, to: ev.to, say: ev.say }, done); });
      if (ev.t === 'ask') return goTo(ev.at, function () { ask(ev, done); });
      if (ev.t === 'delegate') return goTo(ev.at, function () { delegate(ev, done); });
      if (ev.t === 'handoff') return goTo(ev.at, function () { handoff(ev, done); });
      done();
    }

    function ask(ev, done) {
      if (st.fast) return done();
      var p = pop(byIndex[ev.at], 'fl-pop-ask'), row = h('div', 'fl-opts'), settled = false;
      p.setAttribute('role', 'dialog');
      p.setAttribute('aria-label', ev.q);
      p.appendChild(h('b', null, ev.q));
      var resolve = function (k) {
        if (settled) return;
        settled = true;
        st.pending = null;
        var o = ev.opts[k];
        each(row.children, function (b, j) { b.classList.toggle('is-picked', j === k); b.disabled = true; });
        if (k !== ev.pick) {  // choix hors scénario : sa conséquence, puis la question revient
          say.textContent = 'Vous choisissez « ' + o.label + ' » : ' + (o.why || 'on continue.') + ' Puis la question revient.';
          var again = function () { run(ev, done); };
          if (o.to != null) return later(function () { loop({ at: ev.at, to: o.to, why: o.why }, function () { later(again, 1400); }); }, 600);
          return later(again, 2200);
        }
        say.textContent = ev.say;
        if (o.to != null) return later(function () { loop({ at: ev.at, to: o.to, why: o.why }, done); }, 500);  // le scénario lui-même revient en arrière
        done();
      };
      st.pending = function () { resolve(ev.pick); };  // « Suivant » répond comme le scénario
      sync();  // « Suivant » redevient actif pendant que la question attend
      ev.opts.forEach(function (o, k) {
        var b = h('button', 'fl-opt' + (k === 0 ? ' is-main' : ''), o.label);
        b.type = 'button';
        b.addEventListener('click', function () { resolve(k); });
        row.appendChild(b);
      });
      p.appendChild(row);
      if (st.playing) later(function () { resolve(ev.pick); }, 2600);
    }

    function delegate(ev, done) {
      var tray = brickOf(ev.at).querySelector('.fl-tray');
      if (st.fast) { tray.textContent = ''; tray.classList.remove('is-open'); return done(); }
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
      later(done, 2400 + ev.agents.length * 260);
    }

    function handoff(ev, done) {
      if (st.fast) return done();
      var card = h('div', 'fl-hand');
      card.innerHTML = '<span class="fl-dot">' + picto('doc') + '</span>';
      card.appendChild(h('span', null, 'vers la session suivante'));
      brickOf(ev.at).querySelector('.fl-body').appendChild(card);
      later(function () { card.classList.add('is-gone'); }, 2200);
      later(done, 2200);
    }

    /* état visible : boutons et compteur */
    function sync() {
      count.textContent = st.i + ' / ' + script.length;
      prevBtn.disabled = st.i <= 1;
      nextBtn.disabled = st.i >= script.length && !st.pending;
      playBtn.setAttribute('aria-pressed', String(st.playing));
      playBtn.setAttribute('aria-label', st.playing ? 'Mettre en pause' : (st.i >= script.length ? 'Rejouer depuis le début' : 'Lancer la lecture'));
    }
    function finished() {
      st.playing = false;
      say.textContent = 'Fin du workflow. ' + (root.getAttribute('data-end') || '');
      sync();
    }
    /* joue le pas suivant (animé) ; en lecture automatique, enchaîne */
    function forward() {
      if (st.i >= script.length) return finished();
      var ev = script[st.i++];
      sync();
      var token0 = st.run;
      run(ev, function () {
        if (token0 !== st.run) return;
        sync();
        if (st.playing) later(st.i >= script.length ? finished : forward, PAUSE[ev.t] || 1200);
        else if (st.i >= script.length) finished();
      });
    }
    function reset() {
      stopTimers();
      st.i = 0; st.at = null; st.open = null; st.pending = null;
      clearPops();
      each(arcs.querySelectorAll('.fl-arc'), function (a) { a.remove(); });
      each(root.querySelectorAll('.fl-tray'), function (t) { t.textContent = ''; t.classList.remove('is-open'); });
      each(root.querySelectorAll('.fl-node'), function (x) { x.classList.remove('is-here', 'is-seen', 'is-deny'); });
      each(root.querySelectorAll('.fl-hand'), function (x) { x.remove(); });
      bricks.forEach(function (b) { b.classList.remove('is-open', 'is-done'); });
      fill.style.width = '0';
      token.classList.remove('is-on');
      say.textContent = intro;
    }
    /* aller au pas k (1 à n) : tout ce qui précède est rejoué sans animation, puis le pas k est animé */
    function seek(k) {
      k = Math.max(1, Math.min(script.length, k));
      reset();
      root.classList.add('fl-instant');
      st.fast = true;
      for (var j = 0; j < k - 1; j++) run(script[j], function () {});
      st.fast = false;
      st.i = k - 1;
      void board.offsetWidth;
      root.classList.remove('fl-instant');
      if (st.at != null) { token.classList.remove('is-on'); place(st.at); }
      forward();
    }
    function pause() { st.playing = false; stopTimers(); sync(); }
    function play() {
      if (st.playing) return pause();
      st.playing = true;
      if (st.i >= script.length) { reset(); return forward(); }
      if (st.pending) return st.pending();
      if (st.i === 0) return forward();
      later(forward, 300);
      sync();
    }
    function stepNext() {
      if (st.playing) pause();
      if (st.pending) return st.pending();
      if (st.i < script.length) seek(st.i + 1);
    }
    function stepPrev() { if (st.playing) pause(); if (st.i > 1) seek(st.i - 1); }

    /* hauteur fixe : la ligne réserve la hauteur de sa brique la plus haute une fois ouverte (sous-agents et relais
       compris), pour que la page en dessous ne bouge pas quand une brique s'ouvre */
    var row = root.querySelector('.fl-row'), extra = {};
    script.forEach(function (ev) {
      var b = brickOf(ev.at).getAttribute('data-b'), e = extra[b] || { agents: 0, hand: false };
      if (ev.t === 'delegate') e.agents = Math.max(e.agents, ev.agents.length);
      if (ev.t === 'handoff') e.hand = true;
      extra[b] = e;
    });
    function reserve() {
      row.style.minHeight = '';
      root.classList.add('fl-instant');
      var max = row.offsetHeight;
      bricks.forEach(function (b) {
        var e = extra[b.getAttribute('data-b')] || {}, tray = b.querySelector('.fl-tray'), body = b.querySelector('.fl-body');
        var trayHtml = tray.innerHTML, trayOpen = tray.classList.contains('is-open'), hand = null;
        bricks.forEach(function (x) { x.classList.toggle('is-open', x === b); });
        if (e.agents) {
          tray.innerHTML = new Array(e.agents + 1).join('<div class="fl-sub"><span class="fl-dot"></span><span class="fl-sub-t"><b>a</b><small>a</small></span></div>');
          tray.classList.add('is-open');
        }
        if (e.hand) { hand = h('div', 'fl-hand', 'a'); body.appendChild(hand); }
        max = Math.max(max, row.offsetHeight);
        tray.innerHTML = trayHtml; tray.classList.toggle('is-open', trayOpen);
        if (hand) hand.remove();
      });
      bricks.forEach(function (x) { x.classList.toggle('is-open', x === st.open); });
      void row.offsetHeight;
      root.classList.remove('fl-instant');
      row.style.minHeight = Math.ceil(max) + 16 + 'px';  // marge : pendant une morphose, deux briques sont brièvement hautes
      if (st.at != null && token.classList.contains('is-on')) { token.classList.remove('is-on'); place(st.at); }  // la mise en page a pu bouger
    }
    reserve();
    if (document.fonts && document.fonts.ready) document.fonts.ready.then(reserve);
    // une largeur nouvelle (fenêtre, panneau latéral, zoom) : nouvelle hauteur réservée, puis le jeton se recale
    var sizing = null, lastWidth = board.clientWidth;
    var resized = function () { clearTimeout(sizing); sizing = setTimeout(reserve, 150); };
    window.addEventListener('resize', resized);
    if ('ResizeObserver' in window) {
      new ResizeObserver(function () { if (board.clientWidth !== lastWidth) { lastWidth = board.clientWidth; resized(); } }).observe(board);
    }

    var defs = document.createElementNS(NS, 'defs');
    defs.innerHTML = '<marker id="fl-head-' + root.id + '" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path d="M0 0L10 5L0 10z"/></marker>';
    arcs.appendChild(defs);
    root.flPause = function () { if (st.playing) pause(); };  // le sélecteur met en pause le workflow qu'on quitte
    root.flShow = function () { reserve(); };  // mesuré caché, un lecteur se remesure quand le sélecteur l'affiche
    playBtn.addEventListener('click', play);
    nextBtn.addEventListener('click', stepNext);
    prevBtn.addEventListener('click', stepPrev);
    restart.addEventListener('click', function () { pause(); reset(); sync(); play(); });
    root.addEventListener('keydown', function (e) {
      if (e.target.closest('.fl-opt')) return;
      if (e.key === 'ArrowRight') { e.preventDefault(); stepNext(); }
      if (e.key === 'ArrowLeft') { e.preventDefault(); stepPrev(); }
    });
    if ('IntersectionObserver' in window) {
      new IntersectionObserver(function (es) { watching = es[0].isIntersecting; }, { threshold: 0.05 }).observe(board);
    }
    sync();
    if (!reduced && 'IntersectionObserver' in window) {
      var io = new IntersectionObserver(function (es) {
        if (es[0].isIntersecting && !st.playing && st.i === 0) { io.disconnect(); play(); }
      }, { threshold: 0.35 });
      io.observe(board);
    }
  }

  each(document.querySelectorAll('.fl'), mount);

  /* sélecteur des workflows : un onglet par workflow, l'adresse suit (board.html#bug) */
  each(document.querySelectorAll('.fl-picker'), function (picker) {
    var tabs = Array.prototype.slice.call(picker.querySelectorAll('[data-flow-tab]'));
    function select(name, focus) {
      if (!tabs.some(function (t) { return t.getAttribute('data-flow-tab') === name; })) return;
      tabs.forEach(function (t) {
        var on = t.getAttribute('data-flow-tab') === name;
        t.setAttribute('aria-selected', String(on));
        t.tabIndex = on ? 0 : -1;
        if (on && focus) t.focus();
      });
      each(picker.querySelectorAll('[data-flow-panel]'), function (p) {
        var on = p.getAttribute('data-flow-panel') === name, fl = p.querySelector('.fl');
        if (!on && !p.hidden && fl && fl.flPause) fl.flPause();
        var shown = on && p.hidden;
        p.hidden = !on;
        if (shown && fl && fl.flShow) fl.flShow();
      });
      if (history.replaceState) history.replaceState(null, '', '#' + name);
    }
    tabs.forEach(function (t, i) {
      t.addEventListener('click', function () { select(t.getAttribute('data-flow-tab')); });
      t.addEventListener('keydown', function (ev) {
        var d = ev.key === 'ArrowRight' ? 1 : ev.key === 'ArrowLeft' ? -1 : 0;
        if (!d) return;
        ev.preventDefault();
        select(tabs[(i + d + tabs.length) % tabs.length].getAttribute('data-flow-tab'), true);
      });
    });
    if (location.hash.length > 1) select(location.hash.slice(1));
  });
})();
