document.addEventListener('DOMContentLoaded', () => {
  document.querySelectorAll('.phase-step').forEach(el => {
    el.addEventListener('click', () => {
      const p = el.dataset.phase;
      if (p && window.savePhase) window.savePhase(p);
    });
  });

  const chip = document.getElementById('phase-chip');
  if (chip && window.savePhase) {
    chip.addEventListener('change', e => window.savePhase(String(e.target.value || '').toLowerCase()));
  }

  document.querySelectorAll('.tile[id^="tile-"], .tile[data-href]').forEach(el => {
    const href = el.getAttribute('data-href');
    if (href) {
      el.style.cursor = 'pointer';
      el.addEventListener('click', () => { window.location.href = href; });
    }
  });

  const openLib = document.getElementById('open-library');
  if (openLib) {
    openLib.addEventListener('click', (e) => {
      e.preventDefault();
      // Navigate to the tools section on the home page
      window.location.href = '/index.html#tools';
    });
  }

  document.querySelectorAll('.back-btn').forEach(btn => {
    btn.addEventListener('click', (e) => { e.preventDefault(); history.back(); });
  });

  // ----- Coach drawer wiring (open/close) -----
  (function () {
    // Try common IDs/classes without assuming exact markup
    const openers = [
      document.getElementById('open-coach'),
      document.querySelector('[data-open="coach"]'),
      document.querySelector('#coach-link'),
      document.querySelector('.open-coach')
    ].filter(Boolean);

    const drawer = document.getElementById('coach-drawer')
      || document.querySelector('[data-drawer="coach"]')
      || document.querySelector('.coach-drawer');

    const closeBtn = document.getElementById('close-coach')
      || (drawer ? drawer.querySelector('.close-coach,[data-close="coach"]') : null);

    const backdrop = document.getElementById('coach-backdrop')
      || document.querySelector('.coach-backdrop,[data-backdrop="coach"]');

    if (!drawer) return;

    // Choose a non-breaking "open" mechanism:
    // Prefer a CSS class 'open' or 'is-open' if present; otherwise toggle [data-state="open"] and hidden attr.
    function hasOpenClass() {
      return drawer.classList.contains('open') || drawer.classList.contains('is-open');
    }
    function setOpen(on) {
      // Remove hidden if present (some drawers use it)
      if (on) drawer.removeAttribute('hidden'); else drawer.setAttribute('hidden', '');
      // Toggle common classes
      drawer.classList.toggle('open', on);
      drawer.classList.toggle('is-open', on);
      // ARIA/state
      drawer.setAttribute('aria-hidden', on ? 'false' : 'true');
      drawer.setAttribute('data-state', on ? 'open' : 'closed');

      // Backdrop mirror if it exists
      if (backdrop) {
        backdrop.toggleAttribute('hidden', !on);
        backdrop.classList.toggle('open', on);
        backdrop.classList.toggle('is-open', on);
        backdrop.setAttribute('aria-hidden', on ? 'false' : 'true');
      }
    }

    function openCoach(e) {
      if (e) e.preventDefault();
      setOpen(true);
      // Move focus into drawer if a focusable exists
      const focusable = drawer.querySelector('button, [href], input, textarea, [tabindex]:not([tabindex="-1"])');
      if (focusable) focusable.focus();
    }

    function closeCoach(e) {
      if (e) e.preventDefault();
      setOpen(false);
      // Return focus to the last opener if available
      if (openers[0]) openers[0].focus?.();
    }

    // Bind all “open coach” triggers
    openers.forEach(el => {
      el.setAttribute('aria-expanded', String(hasOpenClass()));
      el.addEventListener('click', openCoach);
      el.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); openCoach(e); }
      });
    });

    // Close controls
    if (closeBtn) {
      closeBtn.addEventListener('click', closeCoach);
      closeBtn.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); closeCoach(e); }
      });
    }

    // Backdrop click closes
    if (backdrop) {
      backdrop.addEventListener('click', (e) => {
        // Only close if click is on backdrop itself (not inside drawer)
        if (e.target === backdrop) closeCoach(e);
      });
    }

    // ESC key closes (when drawer is open)
    document.addEventListener('keydown', (e) => {
      if (e.key === 'Escape') {
        // Detect open state by aria-hidden or classes
        const open = drawer.getAttribute('aria-hidden') === 'false' ||
          drawer.classList.contains('open') ||
          drawer.classList.contains('is-open');
        if (open) closeCoach(e);
      }
    });
  })();

  fetch('/me', {credentials: 'include'})
    .then(r => {
      if (r.status === 401) return null;
      if (!r.ok) throw new Error('me failed');
      return r.json();
    })
    .then(data => {
      if (!data || !data.user) return;
      const phase = String(data.user.phase || '').toLowerCase();

      if (chip) chip.value = phase;

      document.querySelectorAll('.phase-step').forEach(el => {
        el.classList.remove('current','active','selected');
        if (String(el.dataset.phase || '').toLowerCase() === phase) {
          el.classList.add('current');
        }
      });
    })
    .catch(() => {});

  const pathname = window.location.pathname;
  if (pathname.endsWith('/signin.html') || pathname.endsWith('/signup.html')) {
    fetch('/me', { credentials: 'include' })
      .then(r => r.ok ? r.json() : null)
      .then(data => { if (data && data.user) window.location.href = '/'; })
      .catch(() => {});
  }
});
