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
    fetch('/me', { credentials: 'include' })
      .then(r => r.ok ? r.json() : null)
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

  const signupForm = document.getElementById('signup-form');
  if (signupForm) {
    signupForm.addEventListener('submit', async (e) => {
      e.preventDefault();
      const email = document.getElementById('signup-email').value.trim();
      const password = document.getElementById('signup-password').value;
      const msg = document.getElementById('signup-msg');
      if (!email || !password) {
        msg.textContent = 'Please fill in all fields.';
        return;
      }
      msg.textContent = 'Creating...';
      try {
        const res = await fetch('/signup', {
          method: 'POST',
          credentials: 'include',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ email, password })
        });
        const data = await res.json();
        msg.textContent = res.ok ? (data.message || 'Account created. Please verify via email.') : (data.error || 'Sign-up failed.');
      } catch (err) {
        msg.textContent = 'Sign-up failed.';
      }
    });
  }

  const signinForm = document.getElementById('signin-form');
  if (signinForm) {
    signinForm.addEventListener('submit', async (e) => {
      e.preventDefault();
      const email = document.getElementById('signin-email').value.trim();
      const password = document.getElementById('signin-password').value;
      const msg = document.getElementById('signin-msg');
      msg.textContent = 'Signing in...';
      try {
        const res = await fetch('/login', {
          method: 'POST',
          credentials: 'include',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ email, password })
        });
        const data = await res.json();
        if (res.ok && data.ok) {
          msg.textContent = 'Sign-in successful!';
          setTimeout(() => { window.location.href = 'index.html'; }, 800);
        } else {
          msg.textContent = data.error || 'Invalid credentials.';
        }
      } catch (err) {
        msg.textContent = 'Sign-in failed.';
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
