function getCsrf() {
  if (window.readCookie) return window.readCookie('csrf_token');
  return document.cookie.split('; ').reduce((acc, part) => {
    const [k, v] = part.split('=');
    if (k === 'csrf_token') acc = decodeURIComponent(v || '');
    return acc;
  }, '');
}

window.savePhase = async function(phase) {
  const val = String(phase || '').toLowerCase();
  const csrf = getCsrf();
  const resp = await fetch('/phase', {
    method: 'POST',
    credentials: 'include',
    headers: {
      'Content-Type': 'application/json',
      'X-CSRF-Token': csrf
    },
    body: JSON.stringify({ phase: val })
  });
  if (!resp.ok) return;

  const chip = document.getElementById('phase-chip');
  if (chip) chip.value = val;

  document.querySelectorAll('.phase-step').forEach(el => {
    el.classList.remove('current','active','selected');
    if (String(el.dataset.phase || '').toLowerCase() === val) {
      el.classList.add('current');
    }
  });
};
