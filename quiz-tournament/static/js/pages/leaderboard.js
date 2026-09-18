import { store } from "../store.js";
import { api } from "../api.js";
import { t } from "../i18n.js";
import { escapeHtml } from "../utils.js";

export async function renderLeaderboard(container) {
  const lang = store.lang;
  container.innerHTML = `
    <div class="page">
      <div class="container">
        <h1 class="section-title">${t("leaderboard_title", lang)}</h1>
        <p class="section-sub">${t("leaderboard_sub", lang)}</p>
        <div class="tabs" id="lb-tabs">
          <button class="active" data-tab="overall">${t("leaderboard_overall", lang)}</button>
          <button data-tab="category">${t("leaderboard_by_category", lang)}</button>
        </div>
        <div id="cat-select-wrap" class="field hidden" style="max-width:280px; margin-bottom:16px;">
          <select id="cat-select"></select>
        </div>
        <div id="lb-list" class="stack"><div class="center-loading"><div class="spinner"></div></div></div>
      </div>
    </div>
  `;

  const list = container.querySelector("#lb-list");
  const tabs = container.querySelector("#lb-tabs");
  const catWrap = container.querySelector("#cat-select-wrap");
  const catSelect = container.querySelector("#cat-select");
  let categories = [];

  function renderRows(rows, unitKey) {
    if (!rows.length) {
      list.innerHTML = `<div class="empty-state">${t("leaderboard_empty", lang)}</div>`;
      return;
    }
    list.innerHTML = rows.map((r) => `
      <div class="leaderboard-row ${r.rank === 1 ? "top1" : r.rank === 2 ? "top2" : r.rank === 3 ? "top3" : ""}">
        <div class="rank">${r.rank}</div>
        <div class="name">${escapeHtml(r.name)}</div>
        <div class="points">${r.points} ${t(unitKey, lang)}</div>
      </div>
    `).join("");
  }

  async function loadOverall() {
    list.innerHTML = `<div class="center-loading"><div class="spinner"></div></div>`;
    try {
      const { leaderboard } = await api.get("/api/leaderboard/overall?limit=50");
      renderRows(leaderboard, "leaderboard_points");
    } catch (err) {
      list.innerHTML = `<div class="alert alert-error">${err.message}</div>`;
    }
  }

  async function loadCategory(categoryId) {
    list.innerHTML = `<div class="center-loading"><div class="spinner"></div></div>`;
    try {
      const { leaderboard } = await api.get(`/api/leaderboard/category/${categoryId}?lang=${lang}`);
      renderRows(leaderboard, "leaderboard_points");
    } catch (err) {
      list.innerHTML = `<div class="alert alert-error">${err.message}</div>`;
    }
  }

  tabs.querySelectorAll("button").forEach((btn) => {
    btn.addEventListener("click", async () => {
      tabs.querySelectorAll("button").forEach((b) => b.classList.remove("active"));
      btn.classList.add("active");
      if (btn.dataset.tab === "overall") {
        catWrap.classList.add("hidden");
        loadOverall();
      } else {
        catWrap.classList.remove("hidden");
        if (!categories.length) {
          const { categories: cats } = await api.get(`/api/categories?lang=${lang}`);
          categories = cats;
          catSelect.innerHTML = categories.map((c) => `<option value="${c.id}">${escapeHtml(c.name)}</option>`).join("");
        }
        loadCategory(catSelect.value);
      }
    });
  });
  catSelect.addEventListener("change", () => loadCategory(catSelect.value));

  await loadOverall();
}
