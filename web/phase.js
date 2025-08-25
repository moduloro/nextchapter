// web/phase.js
console.log("[phase] phase.js requested");

// Replace the value with the actual class from your CSS:
const BUBBLE_CURRENT_CLASS = "active";

function readCookie(name) {
  return document.cookie.split("; ").reduce((acc, part) => {
    const [k, v] = part.split("=");
    if (k === name) acc = decodeURIComponent(v || "");
    return acc;
  }, "");
}

(function () {
  try {
    console.log("[phase] IIFE start");

    const PHASES = ["stabilize","reframe","position","explore","apply","secure","transition"];
    const pillLabel = document.getElementById("phase-pill-label");

    function setUI(phase) {
      if (!phase) return;

      // Remove current class from all bubbles, then apply to the matching one
      document.querySelectorAll(".phase-step").forEach(el => {
        el.classList.remove(BUBBLE_CURRENT_CLASS);
      });
      const active = document.querySelector(`.phase-step[data-phase="${phase}"]`);
      if (active) active.classList.add(BUBBLE_CURRENT_CLASS);

      // Pill label stays as-is
      if (pillLabel) {
        const cap = s => s ? s.charAt(0).toUpperCase() + s.slice(1) : "";
        pillLabel.textContent = cap(phase);
      }
      document.body.setAttribute("data-current-phase", phase);

      // Keep dropdown sync
      const dd = document.getElementById("phase-chip");
      if (dd) {
        const options = Array.from(dd.options || []);
        const has = options.some(o => (o.value || "").toLowerCase() === phase);
        if (has) dd.value = phase;
      }
    }

    async function fetchMe() {
      try {
        const r = await fetch(`/me`, { credentials: "include" });
        const data = await r.json();
        console.log("[phase] GET /me →", data);
        if (data.ok && data.user) {
          let p = (data.user.phase || "").toLowerCase();
          if (!PHASES.includes(p)) p = "stabilize";
          setUI(p);
        } else if (r.status === 401) {
          console.warn("[phase] not logged in");
        }
      } catch (e) {
        console.error("[phase] fetchMe error", e);
      }
    }

    async function doSavePhase(phase) {
      const csrf = readCookie("csrf_token");
      if (!csrf) { alert("Missing CSRF token; please log in again."); return; }

      const r = await fetch(`/phase`, {
        method: "POST",
        credentials: "include",
        headers: {
          "Content-Type": "application/json",
          "X-CSRF-Token": csrf
        },
        body: JSON.stringify({ phase })
      });
      const data = await r.json();
      console.log("[phase] POST /phase →", data);
      if (data.ok && data.user) {
        setUI((data.user.phase || "").toLowerCase());
      } else if (r.status === 401) {
        alert("Please log in again.");
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
