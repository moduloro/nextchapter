// web/phase.js
console.log("[phase] phase.js requested");

(function () {
  try {
    console.log("[phase] IIFE start");

    const PHASES = ["stabilize","reframe","position","explore","apply","secure","transition"];
    const pillLabel = document.getElementById("phase-pill-label");

    function getEmail() {
      return (localStorage.getItem("loggedInEmail")
           || localStorage.getItem("currentUserEmail")
           || "").toLowerCase();
    }

    function cap(s){ return s ? s.charAt(0).toUpperCase() + s.slice(1) : ""; }

    function setUI(phase) {
      if (!phase) return;

      // Highlight the active bubble
      document.querySelectorAll(".phase-step").forEach(el => {
        el.classList.toggle("active", (el.dataset.phase || "").toLowerCase() === phase);
      });

      // Update pill label (if present)
      if (pillLabel) {
        const cap = s => s ? s.charAt(0).toUpperCase() + s.slice(1) : "";
        pillLabel.textContent = cap(phase);
      }

      // Body data attribute (optional hook for CSS/logic)
      document.body.setAttribute("data-current-phase", phase);

      // NEW: sync dropdown #phase-chip if present
      const dd = document.getElementById("phase-chip");
      if (dd) {
        // normalize options to lowercase for comparison
        const options = Array.from(dd.options || []);
        const has = options.some(o => (o.value || "").toLowerCase() === phase);
        if (has) {
          dd.value = phase; // no event dispatch; we’re just reflecting state
        } else {
          // if the dropdown uses capitalized labels as values, try to coerce
          const match = options.find(o => (o.textContent || "").trim().toLowerCase() === phase);
          if (match) dd.value = match.value;
        }
      }
    }

    async function fetchMe() {
      const email = getEmail();
      if (!email) { console.warn("[phase] no email found"); return; }
      const r = await fetch(`/me?email=${encodeURIComponent(email)}`);
      const data = await r.json();
      console.log("[phase] GET /me →", data);
      if (data.ok && data.user) {
        let p = (data.user.phase||"").toLowerCase();
        if (!PHASES.includes(p)) p = "stabilize";
        setUI(p);
      }
    }

    async function doSavePhase(phase) {
      const email = getEmail();
      if (!email) { alert("Not logged in."); return; }
      const r = await fetch(`/phase`, {
        method: "POST",
        headers: {"Content-Type":"application/json"},
        body: JSON.stringify({ email, phase })
      });
      const data = await r.json();
      console.log("[phase] POST /phase →", data);
      if (data.ok && data.user) {
        setUI((data.user.phase||"").toLowerCase());
      } else {
        alert(data.error || "Could not update phase");
      }
    }

    // expose globally so Console can see it
    window.savePhase = (p) => doSavePhase(p).catch(e => console.error("[phase] ERROR", e));
    console.log("[phase] savePhase exposed");

    function bindClicks() {
      const nodes = document.querySelectorAll(".phase-step");
      console.log("[phase] .phase-step count =", nodes.length);
      nodes.forEach(el => {
        el.addEventListener("click", () => {
          const p = (el.dataset.phase||"").toLowerCase();
          console.log("[phase] click →", p);
          if (p) window.savePhase(p);
        });
      });
    }

    function bindDropdown() {
      const dropdown = document.getElementById("phase-chip");
      if (!dropdown) {
        console.log("[phase] no #phase-chip found");
        return;
      }
      console.log("[phase] binding dropdown");
      dropdown.addEventListener("change", () => {
        const val = (dropdown.value || "").toLowerCase();
        console.log("[phase] dropdown change →", val);
        if (val) window.savePhase(val);
      });
    }

    document.addEventListener("DOMContentLoaded", () => {
      console.log("[phase] DOMContentLoaded");
      bindClicks();
      bindDropdown();
      fetchMe().catch(e => console.error("[phase] fetchMe error", e));
    });

    console.log("[phase] IIFE end");
  } catch (e) {
    console.error("[phase] FATAL", e);
  }
})();
