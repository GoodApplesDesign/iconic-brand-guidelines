// ICONIC brand guidelines: menu, scroll-spy, copy buttons, logo variant selector
(function () {
  var body = document.body;

  // mobile menu
  var btn = document.querySelector('.menu-btn');
  function setNav(open) { body.classList.toggle('nav-open', open); if (btn) btn.setAttribute('aria-expanded', open ? 'true' : 'false'); }
  if (btn) btn.addEventListener('click', function () { setNav(!body.classList.contains('nav-open')); });
  document.addEventListener('click', function (e) {
    if (!body.classList.contains('nav-open')) return;
    if (e.target.closest('.nav a') || (!e.target.closest('.sidebar') && !e.target.closest('.menu-btn'))) setNav(false);
  });
  document.addEventListener('keydown', function (e) { if (e.key === 'Escape') setNav(false); });

  // scroll-spy: highlight the section in view
  var links = {};
  document.querySelectorAll('.nav-subs a[data-spy]').forEach(function (a) { if (a.closest('.is-current')) links[a.dataset.spy] = a; });
  var current = null;
  if ('IntersectionObserver' in window && Object.keys(links).length) {
    var io = new IntersectionObserver(function (entries) {
      entries.forEach(function (en) {
        if (!en.isIntersecting || !links[en.target.id]) return;
        if (current) current.classList.remove('is-active');
        current = links[en.target.id]; current.classList.add('is-active');
      });
    }, { rootMargin: '-30% 0px -60% 0px' });
    Object.keys(links).forEach(function (id) { var s = document.getElementById(id); if (s) io.observe(s); });
  }

  // click to copy colour values
  document.querySelectorAll('.copyable').forEach(function (b) {
    b.addEventListener('click', function () {
      var v = b.dataset.copy || b.textContent.trim();
      var done = function () { b.classList.add('copied'); setTimeout(function () { b.classList.remove('copied'); }, 1400); };
      if (navigator.clipboard) navigator.clipboard.writeText(v).then(done, function () {});
    });
  });

  // tabs: show one panel at a time (e.g. gradient / flat colourways)
  document.querySelectorAll('[data-tabs]').forEach(function (box) {
    var tabs = box.querySelectorAll('[role="tab"]'), panels = box.querySelectorAll('[data-panel]');
    tabs.forEach(function (t) {
      t.addEventListener('click', function () {
        tabs.forEach(function (o) { o.setAttribute('aria-selected', o === t ? 'true' : 'false'); });
        panels.forEach(function (p) { p.hidden = p.dataset.panel !== t.dataset.tab; });
      });
    });
  });

  // looping videos always autoplay (muted); nudge them if the browser held back, and resume when scrolled into view
  document.querySelectorAll('video[autoplay]').forEach(function (v) {
    v.muted = true; v.playsInline = true;
    var go = function () { if (v.paused) { var p = v.play(); if (p && p.catch) p.catch(function () {}); } };
    go();
    v.addEventListener('canplay', go);
    document.addEventListener('visibilitychange', function () { if (!document.hidden) go(); });
    if ('IntersectionObserver' in window) new IntersectionObserver(function (es) { es.forEach(function (e) { if (e.isIntersecting) go(); }); }).observe(v);
  });

  // diagrams that animate in once, when they scroll into view
  document.querySelectorAll('[data-animate]').forEach(function (el) {
    if (!('IntersectionObserver' in window)) return;
    el.classList.add('armed');
    var io = new IntersectionObserver(function (es) {
      es.forEach(function (e) { if (e.isIntersecting) { el.classList.add('in-view'); io.disconnect(); } });
    }, { threshold: 0.45 });
    io.observe(el);
  });

  // logo variant selector
  document.querySelectorAll('[data-selector]').forEach(function (sel) {
    var stage = sel.querySelector('.stage'), img = stage.querySelector('img');
    var res = sel.querySelector('.result');
    sel.querySelectorAll('.chip').forEach(function (c) {
      c.addEventListener('click', function () {
        sel.querySelectorAll('.chip').forEach(function (o) { o.setAttribute('aria-pressed', o === c ? 'true' : 'false'); });
        stage.style.background = c.dataset.bg;
        img.style.opacity = 0;
        setTimeout(function () { img.src = c.dataset.logo; img.alt = c.dataset.name; img.style.opacity = 1; }, 180);
        res.innerHTML = '<strong>' + c.dataset.name + '</strong>' + c.dataset.note;
      });
    });
  });
})();
