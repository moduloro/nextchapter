function readCookie(name) {
  return document.cookie.split('; ').reduce((acc, part) => {
    const [k, v] = part.split('=');
    if (k === name) acc = decodeURIComponent(v || '');
    return acc;
  }, '');
}

document.addEventListener('DOMContentLoaded', () => {
  const authLinks = document.getElementById('auth-links');

  if (authLinks) {
    fetch('/me', {credentials: 'include'})
      .then(r => {
        if (r.status === 401) return null;
        if (!r.ok) throw new Error('me failed');
        return r.json();
      })
      .then(data => {
        if (!data || !data.user) return;
        authLinks.innerHTML = `<span class="muted">Hi, ${data.user.email}</span> <button id="logout" class="btn ghost">Log Out</button>`;
        const btn = document.getElementById('logout');
        if (btn) {
          btn.addEventListener('click', async () => {
            const csrf = readCookie('csrf_token');
            try {
              await fetch('/logout', { method: 'POST', credentials: 'include', headers: { 'X-CSRF-Token': csrf } });
            } catch (_) {}
            location.reload();
          });
        }
      })
      .catch(() => {});
  }

  const signUpForm = document.getElementById('signup-form');
  if (signUpForm) {
    signUpForm.addEventListener('submit', async (e) => {
      e.preventDefault();
      const email = signUpForm.querySelector('input[name="email"]')?.value || '';
      const password = signUpForm.querySelector('input[name="password"]')?.value || '';
      const msg = document.getElementById('signup-msg');
      try {
        const resp = await fetch('/signup', {
          method: 'POST',
          credentials: 'include',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ email, password })
        });
        if (resp.ok) {
          window.location.href = '/signin.html?registered=1';
        } else {
          const data = await resp.json().catch(() => ({}));
          if (msg) msg.textContent = data.error || 'Sign-up failed.';
        }
      } catch (_) {
        if (msg) msg.textContent = 'Sign-up failed.';
      }
    });
  }

  const signInForm = document.getElementById('signin-form');
  if (signInForm) {
    signInForm.addEventListener('submit', async (e) => {
      e.preventDefault();
      const email = signInForm.querySelector('input[name="email"]')?.value || '';
      const password = signInForm.querySelector('input[name="password"]')?.value || '';
      const msg = document.getElementById('signin-msg');
      try {
        const resp = await fetch('/login', {
          method: 'POST',
          credentials: 'include',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ email, password })
        });
        if (resp.ok) {
          window.location.href = '/';
        } else {
          const data = await resp.json().catch(() => ({}));
          if (msg) msg.textContent = data.error || 'Invalid credentials.';
        }
      } catch (_) {
        if (msg) msg.textContent = 'Sign-in failed.';
      }
    });
  }

  const forgotLink = document.getElementById('forgot-password');
  const resetForm = document.getElementById('reset-form');
  if (forgotLink && resetForm) {
    forgotLink.addEventListener('click', (e) => {
      e.preventDefault();
      resetForm.style.display = 'grid';
    });

    resetForm.addEventListener('submit', async (e) => {
      e.preventDefault();
      const email = document.getElementById('reset-email').value.trim();
      const msg = document.getElementById('reset-msg');
      if (!email) {
        msg.textContent = 'Please enter your email.';
        return;
      }
      msg.textContent = 'Sending...';
      try {
        const res = await fetch('/reset-password', {
          method: 'POST',
          credentials: 'include',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ email })
        });
        const data = await res.json();
        msg.textContent = res.ok ? (data.message || 'Reset email sent!') : (data.error || 'Failed to send reset email.');
      } catch (err) {
        msg.textContent = 'Error sending email.';
      }
    });
  }
});
