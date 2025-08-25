// Auth helpers that call server-side endpoints
// Shows auth links in header and handles sign-up/sign-in forms

function readCookie(name) {
  return document.cookie.split('; ').reduce((acc, part) => {
    const [k, v] = part.split('=');
    if (k === name) acc = decodeURIComponent(v || '');
    return acc;
  }, '');
}

document.addEventListener('DOMContentLoaded', () => {
  const authLinks = document.getElementById('auth-links');
  const currentUser = localStorage.getItem('loggedInUser');

  if (authLinks && currentUser) {
    authLinks.innerHTML = `<span class="muted">Hi, ${currentUser}</span> <button id="logout" class="btn ghost">Log Out</button>`;
    document.getElementById('logout').addEventListener('click', async () => {
      const csrf = readCookie('csrf_token');
      try {
        await fetch('/logout', {
          method: 'POST',
          credentials: 'include',
          headers: { 'X-CSRF-Token': csrf }
        });
      } catch (err) {
        console.warn('logout failed', err);
      } finally {
        localStorage.removeItem('loggedInUser');
        location.reload();
      }
    });
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
        if (res.ok) {
          msg.textContent = data.message || 'Account created. Please verify via email.';
        } else {
          msg.textContent = data.error || 'Sign-up failed.';
        }
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
          localStorage.setItem('loggedInUser', data.user.email);
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
        if (res.ok) {
          msg.textContent = data.message || 'Reset email sent!';
        } else {
          msg.textContent = data.error || 'Failed to send reset email.';
        }
      } catch (err) {
        msg.textContent = 'Error sending email.';
      }
    });
  }
});

