export function escapeHtml(str) {
  return String(str ?? "").replace(/[&<>"']/g, (c) => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;",
  }[c]));
}

export function el(html) {
  const t = document.createElement("template");
  t.innerHTML = html.trim();
  return t.content.firstElementChild;
}

export function qs(sel, root = document) { return root.querySelector(sel); }
export function qsa(sel, root = document) { return Array.from(root.querySelectorAll(sel)); }

const ICONS = {
  book: '<path d="M4 4.5A2.5 2.5 0 0 1 6.5 2H20v17H6.5A2.5 2.5 0 0 0 4 21.5v-17Z"/><path d="M4 19a2.5 2.5 0 0 1 2.5-2.5H20"/>',
  cpu: '<rect x="6" y="6" width="12" height="12" rx="2"/><path d="M9 2v3M15 2v3M9 19v3M15 19v3M2 9h3M2 15h3M19 9h3M19 15h3"/>',
  globe: '<circle cx="12" cy="12" r="9"/><path d="M3 12h18M12 3a14 14 0 0 1 0 18M12 3a14 14 0 0 0 0 18"/>',
  trophy: '<path d="M8 21h8M12 17v4M7 4h10v5a5 5 0 0 1-10 0V4Z"/><path d="M7 5H4a1 1 0 0 0-1 1 5 5 0 0 0 4 5M17 5h3a1 1 0 0 1 1 1 5 5 0 0 1-4 5"/>',
  film: '<rect x="3" y="4" width="18" height="16" rx="2"/><path d="M7 4v16M17 4v16M3 9h4M3 15h4M17 9h4M17 15h4"/>',
  leaf: '<path d="M11 20A7 7 0 0 1 4 13c0-6 5-11 15-11 0 10-5 15-11 15Z"/><path d="M4 20c4-4 8-8 15-15"/>',
  flag: '<path d="M5 3v18"/><path d="M5 4h13l-3 4 3 4H5"/>',
  star: '<path d="M12 2l3.09 6.26L22 9.27l-5 4.87L18.18 22 12 18.56 5.82 22 7 14.14l-5-4.87 6.91-1.01L12 2Z"/>',
  medal: '<circle cx="12" cy="15" r="6"/><path d="M9 10 6 3h3l3 6 3-6h3l-3 7"/>',
  crown: '<path d="M3 8l4 4 5-7 5 7 4-4-2 11H5L3 8Z"/>',
  bolt: '<path d="M13 2 4 14h6l-1 8 9-12h-6l1-8Z"/>',
  clock: '<circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 3"/>',
  users: '<circle cx="9" cy="8" r="3"/><path d="M2 20c0-3.3 3-6 7-6s7 2.7 7 6"/><circle cx="17" cy="9" r="2.5"/><path d="M23 20c0-2.5-2-4.5-4.5-5"/>',
  check: '<path d="M20 6 9 17l-5-5"/>',
  x: '<path d="M18 6 6 18M6 6l12 12"/>',
};

export function icon(name, size = 22) {
  const path = ICONS[name] || ICONS.star;
  return `<svg width="${size}" height="${size}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">${path}</svg>`;
}

export function timerRingSvg(pct, size = 64) {
  const r = (size - 8) / 2;
  const c = 2 * Math.PI * r;
  const offset = c * (1 - pct);
  return `<svg viewBox="0 0 ${size} ${size}">
    <circle class="track" cx="${size / 2}" cy="${size / 2}" r="${r}"></circle>
    <circle class="progress" cx="${size / 2}" cy="${size / 2}" r="${r}" stroke-dasharray="${c}" stroke-dashoffset="${offset}"></circle>
  </svg>`;
}

export function launchConfetti(count = 80) {
  const colors = ["#7C3AED", "#EC4899", "#06B6D4", "#10B981", "#F59E0B"];
  for (let i = 0; i < count; i++) {
    const piece = document.createElement("div");
    piece.className = "confetti-piece";
    piece.style.left = Math.random() * 100 + "vw";
    piece.style.background = colors[i % colors.length];
    piece.style.transform = `rotate(${Math.random() * 360}deg)`;
    const duration = 2.2 + Math.random() * 1.6;
    const drift = (Math.random() - 0.5) * 200;
    piece.animate(
      [
        { transform: `translate(0, 0) rotate(0deg)`, opacity: 1 },
        { transform: `translate(${drift}px, 100vh) rotate(${360 + Math.random() * 360}deg)`, opacity: 0.9 },
      ],
      { duration: duration * 1000, easing: "cubic-bezier(.25,.46,.45,.94)" }
    );
    document.body.appendChild(piece);
    setTimeout(() => piece.remove(), duration * 1000 + 100);
  }
}

export function formatDateTime(iso, lang) {
  try {
    const d = new Date(iso);
    return d.toLocaleString(lang === "ur" ? "ur-PK" : "en-US", {
      dateStyle: "medium", timeStyle: "short",
    });
  } catch {
    return iso;
  }
}

export function countdownLabel(ms) {
  if (ms <= 0) return "0:00";
  const totalSec = Math.ceil(ms / 1000);
  const h = Math.floor(totalSec / 3600);
  const m = Math.floor((totalSec % 3600) / 60);
  const s = totalSec % 60;
  if (h > 0) return `${h}:${String(m).padStart(2, "0")}:${String(s).padStart(2, "0")}`;
  return `${m}:${String(s).padStart(2, "0")}`;
}

export function openModal(html) {
  const overlay = el(`<div class="modal-overlay"><div class="modal">${html}</div></div>`);
  document.body.appendChild(overlay);
  function close() { overlay.remove(); }
  overlay.addEventListener("click", (e) => { if (e.target === overlay) close(); });
  return { overlay, modal: overlay.querySelector(".modal"), close };
}

export function debounce(fn, ms) {
  let t;
  return (...args) => {
    clearTimeout(t);
    t = setTimeout(() => fn(...args), ms);
  };
}
