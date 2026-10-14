/* Les briques : onglets des fichiers d'exemple, et le choix « laquelle ? » qui mène à la bonne fiche. */
(function () {
  'use strict';
  Array.prototype.forEach.call(document.querySelectorAll('.br-card'), function (card) {
    var tabs = card.querySelectorAll('.br-tab'), files = card.querySelectorAll('.br-file');
    Array.prototype.forEach.call(tabs, function (t) {
      t.addEventListener('click', function () {
        Array.prototype.forEach.call(tabs, function (x) { x.setAttribute('aria-selected', String(x === t)); });
        Array.prototype.forEach.call(tabs, function (x) { x.tabIndex = x === t ? 0 : -1; });
        Array.prototype.forEach.call(files, function (f) { f.hidden = f.getAttribute('data-f') !== t.getAttribute('data-f'); });
      });
      t.addEventListener('keydown', function (ev) {
        var step = { ArrowRight: 1, ArrowLeft: tabs.length - 1 }[ev.key];
        if (!step) return;
        var i = Array.prototype.indexOf.call(tabs, t), n = tabs[(i + step) % tabs.length];
        ev.preventDefault(); n.focus(); n.click();
      });
    });
  });
  var namesEl = document.getElementById('br-names'), answer = document.getElementById('br-answer');
  if (!namesEl || !answer) return;
  var names = JSON.parse(namesEl.textContent), needs = document.querySelectorAll('.br-need');
  var guessBox = document.getElementById('br-guess'), guesses = guessBox ? guessBox.querySelectorAll('.br-g') : [], current = null;
  var each = function (list, fn) { Array.prototype.forEach.call(list, fn); };
  var reveal = function () {
    var to = current.getAttribute('data-to');
    answer.innerHTML = '';
    var a = document.createElement('a'); a.href = '#' + to; a.textContent = names[to];
    answer.appendChild(document.createTextNode('→ ')); answer.appendChild(a);
    answer.appendChild(document.createTextNode(' : ' + current.getAttribute('data-why') + '.'));
    each(document.querySelectorAll('.br-card'), function (c) { c.classList.toggle('br-hit', c.id === to); });
  };
  each(needs, function (b) {
    b.addEventListener('click', function () {
      current = b;
      each(needs, function (x) { x.setAttribute('aria-pressed', String(x === b)); });
      each(guesses, function (g) { g.classList.remove('br-ok', 'br-no'); g.disabled = false; });
      answer.textContent = '';
      if (guessBox) { guessBox.hidden = false; guesses[0].focus({ preventScroll: true }); } else { reveal(); }
    });
  });
  each(guesses, function (g) {
    g.addEventListener('click', function () {
      if (!current) return;
      var right = g.getAttribute('data-g') === current.getAttribute('data-to');
      g.classList.add(right ? 'br-ok' : 'br-no');
      if (right) { each(guesses, function (x) { x.disabled = true; }); }
      else { each(guesses, function (x) { if (x.getAttribute('data-g') === current.getAttribute('data-to')) x.classList.add('br-ok'); }); }
      reveal();
      if (!right) answer.insertBefore(document.createTextNode('Pas tout à fait. '), answer.firstChild);
    });
  });
})();
