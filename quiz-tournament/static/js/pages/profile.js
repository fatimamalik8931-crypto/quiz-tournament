import { store } from "../store.js";
import { api } from "../api.js";
import { t } from "../i18n.js";
import { escapeHtml, icon, formatDateTime } from "../utils.js";
import { navigate } from "../router.js";
import { LANGUAGES } from "../i18n.js";

export async function renderProfile(container) {
  const lang = store.lang;
  if (!store.token) { navigate("/login"); return; }

  container.innerHTML = `
    <div class="page">
      <div class="container">
        <div class="card row between" style="flex-wrap:wrap; gap:16px; margin-bottom:20px;">
          <div>
            <h1 class="section-title" style="margin-bottom:2px;">${escapeHtml(store.user.name)}</h1>
            <p class="text-muted" style="margin:0;">${escapeHtml(store.user.email)}</p>
          </div>
          <div class="field" style="max-width:220px;">
            <label>${t("profile_language_pref", lang)}</label>
            <select id="lang-pref">
              ${LANGUAGES.map((l) => `<option value="${l.code}" ${store.user.preferred_language === l.code ? "selected" : ""}>${l.label}</option>`).join("")}
            </select>
          </div>
        </div>

        <div id="stats-grid" class="grid cols-2" style="margin-bottom:24px;"></div>

        <div class="grid cols-2">
          <div>
            <h2 style="font-size:18px;">${t("profile_badges", lang)}</h2>
            <div id="badges-grid" class="grid cols-3" style="gap:12px;"><div class="center-loading"><div class="spinner"></div></div></div>
          </div>
          <div>
            <h2 style="font-size:18px;">${t("profile_history", lang)}</h2>
            <div id="history-list" class="stack"><div class="center-loading"><div class="spinner"></div></div></div>
          </div>
        </div>
      </div>
    </div>
  `;

  const statsGrid = container.querySelector("#stats-grid");
  const badgesGrid = container.querySelector("#badges-grid");
  const historyList = container.querySelector("#history-list");
  const langSelect = container.querySelector("#lang-pref");

  langSelect.addEventListener("change", async () => {
    try {
      const { user } = await api.put("/api/auth/me", { preferredLanguage: langSelect.value });
      store.setUser(user);
    } catch { /* ignore */ }
  });

  try {
    const stats = await api.get("/api/users/me/stats");
    statsGrid.innerHTML = `
      <div class="card stat-card"><div class="value">${stats.totalPoints}</div><div class="label">${t("profile_stats_points", lang)}</div></div>
      <div class="card stat-card"><div class="value">${stats.quizzesPlayed}</div><div class="label">${t("profile_stats_quizzes", lang)}</div></div>
      <div class="card stat-card"><div class="value">${stats.tournamentsPlayed}</div><div class="label">${t("profile_stats_tournaments", lang)}</div></div>
      <div class="card stat-card"><div class="value">${stats.tournamentsWon}</div><div class="label">${t("profile_stats_wins", lang)}</div></div>
    `;
  } catch (err) {
    statsGrid.innerHTML = `<div class="alert alert-error">${err.message}</div>`;
  }

  try {
    const { badges } = await api.get("/api/users/me/badges");
    badgesGrid.innerHTML = badges.map((b) => `
      <div class="badge-card ${b.earned ? "earned" : "locked"}">
        <div class="badge-icon">${icon(b.icon, 24)}</div>
        <h4>${escapeHtml(b.name)}</h4>
        <p>${escapeHtml(b.description)}</p>
      </div>
    `).join("");
  } catch (err) {
    badgesGrid.innerHTML = `<div class="alert alert-error">${err.message}</div>`;
  }

  try {
    const { practiceAttempts, tournaments } = await api.get("/api/users/me/history");
    const combined = [
      ...practiceAttempts.map((a) => ({ ...a, sortKey: a.createdAt })),
      ...tournaments.map((tt) => ({ ...tt, sortKey: tt.startTime })),
    ].sort((a, b) => new Date(b.sortKey) - new Date(a.sortKey));

    if (!combined.length) {
      historyList.innerHTML = `<div class="empty-state">${t("profile_no_history", lang)}</div>`;
    } else {
      historyList.innerHTML = combined.slice(0, 20).map((item) => item.mode === "practice" ? `
        <div class="card row between">
          <div>
            <strong>${escapeHtml(item.categoryName)}</strong>
            <div class="text-muted" style="font-size:12px;">${formatDateTime(item.createdAt, lang)}</div>
          </div>
          <div class="text-muted">${item.correctCount}/${item.totalQuestions} &middot; <strong style="color:#7C3AED;">${item.score}</strong></div>
        </div>
      ` : `
        <div class="card row between">
          <div>
            <strong>${escapeHtml(item.tournamentName)}</strong>
            <div class="text-muted" style="font-size:12px;">${formatDateTime(item.startTime, lang)}</div>
          </div>
          <div class="text-muted">${item.rank ? `#${item.rank}` : "-"} &middot; <strong style="color:#7C3AED;">${item.score}</strong></div>
        </div>
      `).join("");
    }
  } catch (err) {
    historyList.innerHTML = `<div class="alert alert-error">${err.message}</div>`;
  }
}
