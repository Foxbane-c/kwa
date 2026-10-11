/* Les cinq workflows de l'accueil : onglets, et apparition des étapes l'une après l'autre (CSS, via la classe wf-play).
   En mouvement réduit, tout est visible d'emblée. Script classique, sans dépendance. */
(function () {
  'use strict';
  var root = document.getElementById('wf');
  if (!root) return;
  var reduced = window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  var tabs = root.querySelectorAll('.wf-tab');

  function play(panel) {
    if (reduced) return;
    panel.classList.remove('wf-play');
    void panel.offsetWidth; // relance l'animation
    panel.classList.add('wf-play');
  }
  function show(key) {
    Array.prototype.forEach.call(tabs, function (t) { t.setAttribute('aria-selected', String(t.getAttribute('data-wf') === key)); });
    Array.prototype.forEach.call(root.querySelectorAll('.wf-panel'), function (p) {
      var on = p.getAttribute('data-panel') === key;
      p.hidden = !on;
      if (on) play(p);
    });
  }
  Array.prototype.forEach.call(tabs, function (t, i) {
    t.addEventListener('click', function () { show(t.getAttribute('data-wf')); });
    t.addEventListener('keydown', function (e) {
      var d = e.key === 'ArrowRight' ? 1 : e.key === 'ArrowLeft' ? -1 : 0;
      if (!d) return;
      var n = tabs[(i + d + tabs.length) % tabs.length];
      n.focus(); show(n.getAttribute('data-wf'));
    });
  });
  if (!reduced && 'IntersectionObserver' in window) {
    root.classList.add('wf-wait');
    var io = new IntersectionObserver(function (es) {
      if (!es[0].isIntersecting) return;
      io.disconnect();
      root.classList.remove('wf-wait');
      play(root.querySelector('.wf-panel:not([hidden])'));
    }, { threshold: 0.12 });
    io.observe(root);
    // filet : si l'observateur ne se déclenche jamais (onglet caché, ancien navigateur), les étapes restent lisibles
    setTimeout(function () { if (root.classList.contains('wf-wait')) { io.disconnect(); root.classList.remove('wf-wait'); } }, 4000);
  }
})();
