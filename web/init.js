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

  document.querySelectorAll('.back-btn').forEach(btn => {
    btn.addEventListener('click', (e) => { e.preventDefault(); history.back(); });
  });

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
