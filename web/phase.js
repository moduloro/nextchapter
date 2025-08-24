(function () {
  const API_BASE = ""; // same origin

  function getEmail() {
    // wherever you store the logged-in email (adjust if your key differs)
    return localStorage.getItem("loggedInEmail") || "";
  }

  function setActivePhase(phase) {
    document.querySelectorAll(".phase").forEach(el => {
      el.classList.toggle("active", el.dataset.phase === phase);
    });
  }

  async function fetchMeAndRender() {
    const email = getEmail();
    if (!email) return; // not logged in

    const res = await fetch(`${API_BASE}/me?email=` + encodeURIComponent(email));
    const data = await res.json();
    if (data.ok && data.user) {
      setActivePhase(data.user.phase || "explore");
    }
  }

  async function updatePhase(newPhase) {
    const email = getEmail();
    if (!email) return;
    const res = await fetch(`${API_BASE}/phase`, {
      method: "POST",
      headers: {"Content-Type": "application/json"},
      body: JSON.stringify({ email, phase: newPhase })
    });
    const data = await res.json();
    if (data.ok && data.user) {
      setActivePhase(data.user.phase);
    } else {
      console.warn("Phase update failed:", data);
      alert(data.error || "Could not update phase");
    }
  }

  function bindPhaseClicks() {
    document.querySelectorAll(".phase").forEach(el => {
      el.addEventListener("click", () => {
        const p = el.dataset.phase;
        if (p) updatePhase(p);
      });
    });
  }

  document.addEventListener("DOMContentLoaded", () => {
    bindPhaseClicks();
    fetchMeAndRender();
  });
})();
