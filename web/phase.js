(function () {
  const API = "";
  const root = document.getElementById("app-root");
  const pillLabel = document.getElementById("phase-pill-label");

  function getEmail() {
    return localStorage.getItem("loggedInEmail") || "";
  }

  function normalize(s) {
    return (s || "").trim().toLowerCase();
  }

  function setUIPhase(phaseKey) {
    if (!phaseKey) return;
    if (pillLabel) {
      pillLabel.textContent = phaseKey.charAt(0).toUpperCase() + phaseKey.slice(1);
    }
    document.querySelectorAll(".pill-option[data-phase]").forEach(el => {
      el.classList.toggle("is-active", normalize(el.dataset.phase) === phaseKey);
    });
    if (root) root.setAttribute("data-current-phase", phaseKey);
    const select = document.getElementById("intake-phase");
    if (select) {
      select.value = phaseKey;
    } else {
      document
        .querySelectorAll('#intake-phase-group input[name="phase"]')
        .forEach(r => (r.checked = normalize(r.value) === phaseKey));
    }
  }

  async function fetchMeAndRender() {
    const email = getEmail();
    if (!email) return;
    try {
      const res = await fetch(`${API}/me?email=` + encodeURIComponent(email));
      const data = await res.json();
      if (data.ok && data.user) setUIPhase(normalize(data.user.phase || "explore"));
    } catch (e) {
      console.warn("Failed to fetch /me:", e);
    }
  }

  async function savePhase(phaseKey) {
    const email = getEmail();
    if (!email) return;
    try {
      const res = await fetch(`${API}/phase`, {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify({ email, phase: phaseKey })
      });
      const data = await res.json();
      if (data.ok && data.user) {
        setUIPhase(normalize(data.user.phase));
      } else {
        console.warn("Phase update failed", data);
        alert(data.error || "Could not update phase");
      }
    } catch (e) {
      console.error("Phase update error:", e);
      alert("Network error saving phase");
    }
  }

  function bindPill() {
    document.querySelectorAll(".pill-option[data-phase]").forEach(el => {
      el.addEventListener("click", () => {
        const phaseKey = normalize(el.dataset.phase);
        if (phaseKey) savePhase(phaseKey);
      });
    });
  }

  function bindIntake() {
    const select = document.getElementById("intake-phase");
    if (select) {
      select.addEventListener("change", () => {
        const val = normalize(select.value);
        if (val) savePhase(val);
      });
      return;
    }
    const radios = document.querySelectorAll('#intake-phase-group input[name="phase"]');
    radios.forEach(r => {
      r.addEventListener("change", () => {
        if (r.checked) savePhase(normalize(r.value));
      });
    });
  }

  document.addEventListener("DOMContentLoaded", () => {
    bindPill();
    bindIntake();
    fetchMeAndRender();
  });
})();
