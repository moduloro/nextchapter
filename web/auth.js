// Simple client-side authentication using localStorage
// Shows auth links in header and handles sign-up/sign-in forms

document.addEventListener('DOMContentLoaded', () => {
  const authLinks = document.getElementById('auth-links');
  const currentUser = localStorage.getItem('loggedInUser');

  if (authLinks && currentUser) {
    authLinks.innerHTML = `<span class="muted">Hi, ${currentUser}</span> <button id="logout" class="btn ghost">Log Out</button>`;
    document.getElementById('logout').addEventListener('click', () => {
      localStorage.removeItem('loggedInUser');
      location.reload();
    });
  }

  const signupForm = document.getElementById('signup-form');
  if (signupForm) {
    signupForm.addEventListener('submit', (e) => {
      e.preventDefault();
      const username = document.getElementById('signup-username').value.trim();
      const password = document.getElementById('signup-password').value;
      const msg = document.getElementById('signup-msg');
      if (!username || !password) {
        msg.textContent = 'Please fill in all fields.';
        return;
      }
      const users = JSON.parse(localStorage.getItem('users') || '{}');
      if (users[username]) {
        msg.textContent = 'User already exists.';
        return;
      }
      users[username] = { password };
      localStorage.setItem('users', JSON.stringify(users));
      localStorage.setItem('loggedInUser', username);
      msg.textContent = 'Sign-up successful!';
      setTimeout(() => { window.location.href = 'index.html'; }, 800);
    });
  }

  const signinForm = document.getElementById('signin-form');
  if (signinForm) {
    signinForm.addEventListener('submit', (e) => {
      e.preventDefault();
      const username = document.getElementById('signin-username').value.trim();
      const password = document.getElementById('signin-password').value;
      const msg = document.getElementById('signin-msg');
      const users = JSON.parse(localStorage.getItem('users') || '{}');
      if (users[username] && users[username].password === password) {
        localStorage.setItem('loggedInUser', username);
        msg.textContent = 'Sign-in successful!';
        setTimeout(() => { window.location.href = 'index.html'; }, 800);
      } else {
        msg.textContent = 'Invalid credentials.';
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
