import { store } from "../store.js";
import { api } from "../api.js";
import { t } from "../i18n.js";
import { icon, escapeHtml } from "../utils.js";
import { navigate } from "../router.js";

export async function renderCategories(container) {
  const lang = store.lang;
  container.innerHTML = `
    <div class="page">
      <div class="container">
        <h1 class="section-title">${t("categories_title", lang)}</h1>
        <p class="section-sub">${t("categories_sub", lang)}</p>
        <div id="cat-list" class="grid cols-3"><div class="center-loading"><div class="spinner"></div></div></div>
      </div>
    </div>
  `;

  const list = container.querySelector("#cat-list");
  try {
    const { categories } = await api.get(`/api/categories?lang=${lang}`);
    if (!categories.length) {
      list.innerHTML = `<div class="empty-state">${t("common_error_generic", lang)}</div>`;
      return;
    }
    list.innerHTML = categories.map((c) => `
      <a href="#/quiz/${c.id}" class="category-card" style="background: linear-gradient(135deg, ${c.colorFrom}, ${c.colorTo});">
        <span class="qcount">${c.questionCount} ${t("category_questions", lang)}</span>
        <div class="icon-wrap">${icon(c.icon, 24)}</div>
        <div>
          <h3>${escapeHtml(c.name)}</h3>
          <p>${escapeHtml(c.description)}</p>
        </div>
      </a>
    `).join("");
  } catch (err) {
    list.innerHTML = `<div class="alert alert-error">${err.message}</div>`;
  }
}
