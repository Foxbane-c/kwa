/* Lecteur commun aux widgets pas à pas (contrôles : shell.player). Le widget ne fournit que show(i), qui affiche
   l'état complet de l'étape i (pour revenir en arrière, il rejoue ce qu'il faut), et reset(). Le lecteur tient
   l'indice, la lecture automatique, la pause, le compteur et les flèches du clavier.
   KwaPlayer(racine, { count: n ou fonction, show: f(i), reset: f(), interval: ms }) → { reset, refresh, stop }.
   Script classique, sans dépendance. */
(function () {
  'use strict';
  var reduced = window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  window.KwaPlayer = function (root, opt) {
    var ctl = root.querySelector('.kp');
    if (!ctl) return null;
    var b = function (p) { return ctl.querySelector('[data-p="' + p + '"]'); };
    var prev = b('prev'), play = b('play'), next = b('next'), restart = b('restart'), count = ctl.querySelector('.kp-count');
    var i = -1, timer = null;
    var n = function () { return typeof opt.count === 'function' ? opt.count() : opt.count; };

    function sync() {
      var playing = !!timer;
      play.setAttribute('aria-pressed', String(playing));
      play.setAttribute('aria-label', playing ? 'Mettre en pause' : (i >= n() - 1 ? 'Rejouer depuis le début' : 'Lancer la lecture'));
      prev.disabled = i <= 0;
      next.disabled = i >= n() - 1;
      if (count) count.textContent = n() ? Math.max(i + 1, 0) + ' / ' + n() : '';
    }
    function stop() { if (timer) { clearInterval(timer); timer = null; } sync(); }
    function go(k) { i = k; opt.show(i); sync(); }
    function forward() { if (i < n() - 1) go(i + 1); if (i >= n() - 1) stop(); }
    function start() {
      if (i >= n() - 1) { i = -1; if (opt.reset) opt.reset(); }
      forward();
      if (!reduced && i < n() - 1) timer = setInterval(forward, opt.interval || 2200);
      sync();
    }
    play.addEventListener('click', function () { if (timer) stop(); else start(); });
    next.addEventListener('click', function () { stop(); forward(); });
    prev.addEventListener('click', function () { stop(); if (i > 0) go(i - 1); });
    if (restart) restart.addEventListener('click', function () { stop(); i = -1; if (opt.reset) opt.reset(); start(); });
    root.addEventListener('keydown', function (e) {
      if (/^(INPUT|TEXTAREA|SELECT)$/.test(e.target.tagName)) return;
      if (e.key === 'ArrowRight') { e.preventDefault(); next.click(); }
      if (e.key === 'ArrowLeft') { e.preventDefault(); prev.click(); }
    });
    sync();
    return {
      reset: function () { stop(); i = -1; if (opt.reset) opt.reset(); sync(); },
      refresh: sync,
      stop: stop,
      play: function () { stop(); i = -1; if (opt.reset) opt.reset(); start(); }
    };
  };
})();
