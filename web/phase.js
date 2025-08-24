(function () {
  const API = "";
  const root = document.getElementById("app-root");
  const pillLabel = document.getElementById("phase-pill-label");
  const PHASES = ["stabilize","reframe","position","explore","apply","secure","transition"];

  function getEmail() {
    // Use the same key your login code writes; adjust if different.
    return localStorage.getItem("loggedInEmail") || "";
  }

  function cap(s){ return s ? s.charAt(0).toUpperCase() + s.slice(1) : ""; }

  function setUI(phase) {
    if (!phase) return;
    // highlight in the strip
    document.querySelectorAll(".phase-step").forEach(el => {
      el.classList.toggle("active", el.dataset.phase === phase);
    });
    // header pill label
    if (pillLabel) pillLabel.textContent = cap(phase);
    // body attribute for others to react to
    if (root) root.setAttribute("data-current-phase", phase);
  }

  async function fetchMe() {
    const email = getEmail();
    if (!email) return;
    try {
      const res = await fetch(`/me?email=${encodeURIComponent(email)}`);
      const data = await res.json();
      if (data.ok && data.user) {
        let phase = (data.user.phase || "").toLowerCase();
        if (!PHASES.includes(phase)) phase = "stabilize";
        setUI(phase);
      }
    } catch (e) { console.warn("fetch /me failed", e); }
  }

  async function savePhase(phase) {
    const email = getEmail();
    if (!email) return;
    try {
      const res = await fetch(`/phase`, {
        method: "POST",
        headers: {"Content-Type":"application/json"},
        body: JSON.stringify({ email, phase })
      });
      const data = await res.json();
      if (data.ok && data.user) setUI(data.user.phase.toLowerCase());
      else alert(data.error || "Could not update phase");
    } catch (e) { console.error("savePhase failed", e); }
  }

  function bindClicks() {
    document.querySelectorAll(".phase-step").forEach(el => {
      el.addEventListener("click", () => {
        const p = (el.dataset.phase || "").toLowerCase();
        if (p) savePhase(p);
      });
    });
  }

  document.addEventListener("DOMContentLoaded", () => {
    bindClicks();
    fetchMe();
  });
})();

