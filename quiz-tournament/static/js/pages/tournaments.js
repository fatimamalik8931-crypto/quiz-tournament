import { store } from "../store.js";
import { api } from "../api.js";
import { t } from "../i18n.js";
import { escapeHtml, formatDateTime, icon } from "../utils.js";
import { navigate } from "../router.js";

function phaseLabel(phase, lang) {
  return {
    SCHEDULED: t("tournament_scheduled", lang),
    LIVE: t("tournament_live", lang),
    COMPLETED: t("tournament_completed", lang),
    CANCELLED: t("tournament_cancelled", lang),
  }[phase] || phase;
}
function phaseClass(phase) {
  return { SCHEDULED: "scheduled", LIVE: "live", COMPLETED: "completed", CANCELLED: "" }[phase] || "";
}

export async function renderTournaments(container) {
  const lang = store.lang;
  container.innerHTML = `
    <div class="page">
      <div class="container">
        <h1 class="section-title">${t("tournaments_title", lang)}</h1>
        <p class="section-sub">${t("tournaments_sub", lang)}</p>
        <div id="t-list" class="stack"><div class="center-loading"><div class="spinner"></div></div></div>
      </div>
    </div>
  `;

  const list = container.querySelector("#t-list");

  async function load() {
    try {
      const { tournaments } = await api.get(`/api/tournaments?lang=${lang}`);
      if (!tournaments.length) {
        list.innerHTML = `<div class="empty-state"><div class="icon">${icon("trophy", 36)}</div>${t("tournaments_sub", lang)}</div>`;
        return;
      }
      list.innerHTML = tournaments.map((tour) => `
        <div class="card row between" style="flex-wrap:wrap; gap:16px;">
          <div>
            <div class="row" style="margin-bottom:6px;">
              <span class="badge-pill ${phaseClass(tour.phase)}">${phaseLabel(tour.phase, lang)}</span>
              ${tour.categoryName ? `<span class="badge-pill">${escapeHtml(tour.categoryName)}</span>` : ""}
            </div>
            <h3 style="margin:0 0 4px;">${escapeHtml(tour.name)}</h3>
            <p class="text-muted" style="margin:0; font-size:14px;">
              ${formatDateTime(tour.startTime, lang)} &middot; ${tour.numQuestions} ${t("category_questions", lang)} &middot; ${tour.participantCount} ${t("tournament_players", lang)}
            </p>
          </div>
          <div>
            <a href="#/tournaments/${tour.id}" class="btn btn-primary">
              ${tour.phase === "COMPLETED" ? t("tournament_view_results", lang) : (tour.joined ? t("tournament_enter", lang) : t("tournament_join", lang))}
            </a>
          </div>
        </div>
      `).join("");
    } catch (err) {
      list.innerHTML = `<div class="alert alert-error">${err.message}</div>`;
    }
  }

  await load();
}
