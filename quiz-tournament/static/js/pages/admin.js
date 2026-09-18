import { store } from "../store.js";
import { api } from "../api.js";
import { t } from "../i18n.js";
import { escapeHtml, openModal, formatDateTime } from "../utils.js";
import { navigate } from "../router.js";

const LETTERS = ["A", "B", "C", "D"];

export async function renderAdmin(container) {
  const lang = store.lang;
  if (!store.token) { navigate("/login"); return; }
  if (!store.isAdmin()) {
    container.innerHTML = `<div class="page"><div class="container"><div class="alert alert-error">Admin access required.</div></div></div>`;
    return;
  }

  container.innerHTML = `
    <div class="page">
      <div class="container">
        <h1 class="section-title">${t("admin_title", lang)}</h1>
        <div class="tabs" id="admin-tabs">
          <button class="active" data-tab="dashboard">${t("admin_tab_dashboard", lang)}</button>
          <button data-tab="questions">${t("admin_tab_questions", lang)}</button>
          <button data-tab="tournaments">${t("admin_tab_tournaments", lang)}</button>
          <button data-tab="users">${t("admin_tab_users", lang)}</button>
        </div>
        <div id="admin-pane"></div>
      </div>
    </div>
  `;

  const pane = container.querySelector("#admin-pane");
  const tabs = container.querySelector("#admin-tabs");
  const renderers = {
    dashboard: renderDashboard,
    questions: renderQuestions,
    tournaments: renderTournamentsAdmin,
    users: renderUsersAdmin,
  };

  tabs.querySelectorAll("button").forEach((btn) => {
    btn.addEventListener("click", () => {
      tabs.querySelectorAll("button").forEach((b) => b.classList.remove("active"));
      btn.classList.add("active");
      renderers[btn.dataset.tab](pane, lang);
    });
  });

  renderDashboard(pane, lang);
}

// ---------------------------------------------------------------------------
async function renderDashboard(pane, lang) {
  pane.innerHTML = `<div class="center-loading"><div class="spinner"></div></div>`;
  try {
    const s = await api.get("/api/admin/stats");
    pane.innerHTML = `
      <div class="grid cols-3" style="margin-bottom:24px;">
        <div class="card stat-card"><div class="value">${s.users}</div><div class="label">${t("admin_stat_users", lang)}</div></div>
        <div class="card stat-card"><div class="value">${s.questions}</div><div class="label">${t("admin_stat_questions", lang)}</div></div>
        <div class="card stat-card"><div class="value">${s.quizAttempts}</div><div class="label">${t("admin_stat_attempts", lang)}</div></div>
        <div class="card stat-card"><div class="value">${s.tournaments}</div><div class="label">${t("admin_stat_tournaments", lang)}</div></div>
      </div>
      <div class="card">
        <h3 style="margin-top:0;">Most-played categories</h3>
        <div class="stack">
          ${s.topCategories.length ? s.topCategories.map((c) => `
            <div class="row between"><span>${escapeHtml(c.name)}</span><strong>${c.plays}</strong></div>
          `).join("") : `<p class="text-muted">No quiz attempts yet.</p>`}
        </div>
      </div>
    `;
  } catch (err) {
    pane.innerHTML = `<div class="alert alert-error">${err.message}</div>`;
  }
}

// ---------------------------------------------------------------------------
async function renderQuestions(pane, lang) {
  pane.innerHTML = `<div class="center-loading"><div class="spinner"></div></div>`;
  let categories, questions;
  try {
    [categories, questions] = await Promise.all([
      api.get(`/api/categories?lang=en`).then((r) => r.categories),
      api.get(`/api/admin/questions`).then((r) => r.questions),
    ]);
  } catch (err) {
    pane.innerHTML = `<div class="alert alert-error">${err.message}</div>`;
    return;
  }

  const catName = (id) => categories.find((c) => c.id === id)?.name || "-";

  pane.innerHTML = `
    <div class="row between" style="margin-bottom:16px; flex-wrap:wrap; gap:10px;">
      <div class="field" style="max-width:240px;">
        <select id="cat-filter">
          <option value="">All categories</option>
          ${categories.map((c) => `<option value="${c.id}">${escapeHtml(c.name)}</option>`).join("")}
        </select>
      </div>
      <div class="row">
        <button class="btn btn-secondary btn-sm" id="add-cat-btn">${t("admin_add_category", lang)}</button>
        <button class="btn btn-primary btn-sm" id="add-q-btn">${t("admin_add_question", lang)}</button>
      </div>
    </div>
    <div class="table-scroll card">
      <table class="data-table">
        <thead><tr><th>${t("admin_category", lang)}</th><th>Question (EN)</th><th>${t("admin_difficulty", lang)}</th><th>${t("admin_points", lang)}</th><th></th></tr></thead>
        <tbody id="q-tbody"></tbody>
      </table>
    </div>
  `;

  const tbody = pane.querySelector("#q-tbody");
  const catFilter = pane.querySelector("#cat-filter");

  function renderRows() {
    const filterVal = catFilter.value;
    const rows = questions.filter((q) => !filterVal || q.categoryId === filterVal);
    if (!rows.length) {
      tbody.innerHTML = `<tr><td colspan="5" class="text-muted">No questions.</td></tr>`;
      return;
    }
    tbody.innerHTML = rows.map((q) => `
      <tr>
        <td>${escapeHtml(catName(q.categoryId))}</td>
        <td>${escapeHtml((q.translations.en && q.translations.en.text) || "-")}</td>
        <td>${escapeHtml(q.difficulty)}</td>
        <td>${q.points}</td>
        <td class="row">
          <button class="btn btn-secondary btn-sm" data-edit="${q.id}">${t("admin_edit", lang)}</button>
          <button class="btn btn-danger btn-sm" data-del="${q.id}">${t("admin_delete", lang)}</button>
        </td>
      </tr>
    `).join("");

    tbody.querySelectorAll("[data-edit]").forEach((btn) => {
      btn.addEventListener("click", () => {
        const q = questions.find((x) => x.id === btn.dataset.edit);
        openQuestionForm(lang, categories, q, async (saved) => {
          await api.put(`/api/admin/questions/${q.id}`, saved);
          Object.assign(q, { categoryId: saved.categoryId, difficulty: saved.difficulty, points: saved.points, timeLimitSeconds: saved.timeLimitSeconds, correctIndex: saved.correctIndex, translations: saved.translations });
          renderRows();
        });
      });
    });
    tbody.querySelectorAll("[data-del]").forEach((btn) => {
      btn.addEventListener("click", async () => {
        if (!confirm(t("admin_confirm_delete", lang))) return;
        await api.del(`/api/admin/questions/${btn.dataset.del}`);
        questions = questions.filter((x) => x.id !== btn.dataset.del);
        renderRows();
      });
    });
  }

  catFilter.addEventListener("change", renderRows);
  pane.querySelector("#add-q-btn").addEventListener("click", () => {
    openQuestionForm(lang, categories, null, async (saved) => {
      const res = await api.post("/api/admin/questions", saved);
      questions.unshift({ id: res.id, ...saved });
      renderRows();
    });
  });
  pane.querySelector("#add-cat-btn").addEventListener("click", () => {
    openCategoryForm(lang, null, async (saved) => {
      await api.post("/api/admin/categories", saved);
      const { categories: fresh } = await api.get(`/api/categories?lang=en`);
      categories = fresh;
      catFilter.innerHTML = `<option value="">All categories</option>` + categories.map((c) => `<option value="${c.id}">${escapeHtml(c.name)}</option>`).join("");
      renderRows();
    });
  });

  renderRows();
}

function openQuestionForm(lang, categories, existing, onSave) {
  const isEdit = !!existing;
  const en = (existing && existing.translations.en) || { text: "", options: ["", "", "", ""] };
  const ur = (existing && existing.translations.ur) || { text: "", options: ["", "", "", ""] };
  const { modal, close } = openModal(`
    <h3 style="margin-top:0;">${isEdit ? t("admin_edit", lang) : t("admin_add_question", lang)}</h3>
    <form id="q-form" class="stack">
      <div class="field">
        <label>${t("admin_category", lang)}</label>
        <select name="categoryId" required>
          ${categories.map((c) => `<option value="${c.id}" ${existing && existing.categoryId === c.id ? "selected" : ""}>${escapeHtml(c.name)}</option>`).join("")}
        </select>
      </div>
      <div class="grid cols-3">
        <div class="field"><label>${t("admin_difficulty", lang)}</label>
          <select name="difficulty">
            ${["easy", "medium", "hard"].map((d) => `<option ${existing && existing.difficulty === d ? "selected" : ""}>${d}</option>`).join("")}
          </select>
        </div>
        <div class="field"><label>${t("admin_points", lang)}</label><input type="number" name="points" min="1" value="${existing ? existing.points : 10}"></div>
        <div class="field"><label>${t("admin_time_limit", lang)}</label><input type="number" name="timeLimitSeconds" min="5" value="${existing ? existing.timeLimitSeconds : 20}"></div>
      </div>
      <div class="field">
        <label>${t("admin_question_text_en", lang)}</label>
        <input name="text_en" required value="${escapeHtml(en.text)}">
      </div>
      <div class="grid cols-2">
        ${[0, 1, 2, 3].map((i) => `
          <div class="field"><label>${t("admin_option", lang)} ${LETTERS[i]} (EN)</label>
            <input name="opt_en_${i}" required value="${escapeHtml(en.options[i] || "")}"></div>
        `).join("")}
      </div>
      <div class="field">
        <label>${t("admin_question_text_ur", lang)}</label>
        <input name="text_ur" dir="rtl" value="${escapeHtml(ur.text)}">
      </div>
      <div class="grid cols-2">
        ${[0, 1, 2, 3].map((i) => `
          <div class="field"><label>${t("admin_option", lang)} ${LETTERS[i]} (UR)</label>
            <input name="opt_ur_${i}" dir="rtl" value="${escapeHtml(ur.options[i] || "")}"></div>
        `).join("")}
      </div>
      <div class="field">
        <label>${t("admin_correct_option", lang)}</label>
        <select name="correctIndex">
          ${[0, 1, 2, 3].map((i) => `<option value="${i}" ${existing && existing.correctIndex === i ? "selected" : ""}>${LETTERS[i]}</option>`).join("")}
        </select>
      </div>
      <div id="q-form-alert"></div>
      <div class="row" style="justify-content:flex-end;">
        <button type="button" class="btn btn-secondary" id="q-cancel">${t("common_cancel", lang)}</button>
        <button type="submit" class="btn btn-primary">${t("admin_save", lang)}</button>
      </div>
    </form>
  `);
  modal.querySelector("#q-cancel").addEventListener("click", close);
  modal.querySelector("#q-form").addEventListener("submit", async (e) => {
    e.preventDefault();
    const fd = new FormData(e.target);
    const translations = {
      en: { text: fd.get("text_en"), options: [0, 1, 2, 3].map((i) => fd.get(`opt_en_${i}`)) },
    };
    if (fd.get("text_ur") && [0, 1, 2, 3].every((i) => fd.get(`opt_ur_${i}`))) {
      translations.ur = { text: fd.get("text_ur"), options: [0, 1, 2, 3].map((i) => fd.get(`opt_ur_${i}`)) };
    }
    const payload = {
      categoryId: fd.get("categoryId"),
      difficulty: fd.get("difficulty"),
      points: parseInt(fd.get("points"), 10),
      timeLimitSeconds: parseInt(fd.get("timeLimitSeconds"), 10),
      correctIndex: parseInt(fd.get("correctIndex"), 10),
      translations,
    };
    try {
      await onSave(payload);
      close();
    } catch (err) {
      modal.querySelector("#q-form-alert").innerHTML = `<div class="alert alert-error">${err.message}</div>`;
    }
  });
}

function openCategoryForm(lang, existing, onSave) {
  const { modal, close } = openModal(`
    <h3 style="margin-top:0;">${t("admin_add_category", lang)}</h3>
    <form id="c-form" class="stack">
      <div class="field"><label>Key (slug)</label><input name="key" required placeholder="e.g. history"></div>
      <div class="field"><label>Name (EN)</label><input name="name_en" required></div>
      <div class="field"><label>Description (EN)</label><input name="desc_en"></div>
      <div class="field"><label>Name (UR)</label><input name="name_ur" dir="rtl"></div>
      <div class="field"><label>Description (UR)</label><input name="desc_ur" dir="rtl"></div>
      <div class="grid cols-2">
        <div class="field"><label>Gradient from</label><input type="color" name="colorFrom" value="#7C3AED"></div>
        <div class="field"><label>Gradient to</label><input type="color" name="colorTo" value="#C026D3"></div>
      </div>
      <div class="field"><label>Icon</label>
        <select name="icon">
          ${["book", "cpu", "globe", "trophy", "film", "leaf", "star", "flag"].map((i) => `<option>${i}</option>`).join("")}
        </select>
      </div>
      <div id="c-form-alert"></div>
      <div class="row" style="justify-content:flex-end;">
        <button type="button" class="btn btn-secondary" id="c-cancel">${t("common_cancel", lang)}</button>
        <button type="submit" class="btn btn-primary">${t("admin_save", lang)}</button>
      </div>
    </form>
  `);
  modal.querySelector("#c-cancel").addEventListener("click", close);
  modal.querySelector("#c-form").addEventListener("submit", async (e) => {
    e.preventDefault();
    const fd = new FormData(e.target);
    const payload = {
      key: fd.get("key"),
      icon: fd.get("icon"),
      colorFrom: fd.get("colorFrom"),
      colorTo: fd.get("colorTo"),
      translations: {
        en: { name: fd.get("name_en"), description: fd.get("desc_en") || "" },
        ur: { name: fd.get("name_ur") || fd.get("name_en"), description: fd.get("desc_ur") || "" },
      },
    };
    try {
      await onSave(payload);
      close();
    } catch (err) {
      modal.querySelector("#c-form-alert").innerHTML = `<div class="alert alert-error">${err.message}</div>`;
    }
  });
}

// ---------------------------------------------------------------------------
async function renderTournamentsAdmin(pane, lang) {
  pane.innerHTML = `<div class="center-loading"><div class="spinner"></div></div>`;
  let categories, tournaments;
  try {
    [categories, tournaments] = await Promise.all([
      api.get(`/api/categories?lang=en`).then((r) => r.categories),
      api.get(`/api/tournaments?lang=en`).then((r) => r.tournaments),
    ]);
  } catch (err) {
    pane.innerHTML = `<div class="alert alert-error">${err.message}</div>`;
    return;
  }

  pane.innerHTML = `
    <div class="row" style="justify-content:flex-end; margin-bottom:16px;">
      <button class="btn btn-primary btn-sm" id="add-t-btn">${t("admin_schedule_tournament", lang)}</button>
    </div>
    <div class="table-scroll card">
      <table class="data-table">
        <thead><tr><th>${t("admin_name", lang)}</th><th>${t("admin_category", lang)}</th><th>${t("admin_start_time", lang)}</th><th>${t("admin_status", lang)}</th><th></th></tr></thead>
        <tbody id="t-tbody"></tbody>
      </table>
    </div>
  `;
  const tbody = pane.querySelector("#t-tbody");

  function renderRows() {
    if (!tournaments.length) {
      tbody.innerHTML = `<tr><td colspan="5" class="text-muted">No tournaments yet.</td></tr>`;
      return;
    }
    tbody.innerHTML = tournaments.map((tt) => `
      <tr>
        <td>${escapeHtml(tt.name)}</td>
        <td>${escapeHtml(tt.categoryName || "Mixed")}</td>
        <td>${formatDateTime(tt.startTime, lang)}</td>
        <td><span class="badge-pill">${tt.phase}</span></td>
        <td>${tt.phase === "SCHEDULED" ? `<button class="btn btn-danger btn-sm" data-cancel="${tt.id}">${t("admin_cancel", lang)}</button>` : ""}</td>
      </tr>
    `).join("");
    tbody.querySelectorAll("[data-cancel]").forEach((btn) => {
      btn.addEventListener("click", async () => {
        if (!confirm(t("admin_confirm_delete", lang))) return;
        await api.post(`/api/tournaments/${btn.dataset.cancel}/cancel`, {});
        const tour = tournaments.find((x) => x.id === btn.dataset.cancel);
        if (tour) tour.phase = "CANCELLED";
        renderRows();
      });
    });
  }

  pane.querySelector("#add-t-btn").addEventListener("click", () => {
    const { modal, close } = openModal(`
      <h3 style="margin-top:0;">${t("admin_schedule_tournament", lang)}</h3>
      <form id="t-form" class="stack">
        <div class="field"><label>${t("admin_name", lang)}</label><input name="name" required></div>
        <div class="field"><label>${t("admin_category", lang)}</label>
          <select name="categoryId">
            <option value="">Mixed (all categories)</option>
            ${categories.map((c) => `<option value="${c.id}">${escapeHtml(c.name)}</option>`).join("")}
          </select>
        </div>
        <div class="field"><label>${t("admin_start_time", lang)}</label><input type="datetime-local" name="startTime" required></div>
        <div class="grid cols-3">
          <div class="field"><label>${t("admin_question_count", lang)}</label><input type="number" name="questionCount" value="10" min="3" max="25"></div>
          <div class="field"><label>${t("admin_per_question_secs", lang)}</label><input type="number" name="perQuestionSecs" value="20" min="5" max="60"></div>
          <div class="field"><label>${t("admin_duration", lang)}</label><input type="number" name="durationMinutes" value="10" min="1"></div>
        </div>
        <div id="t-form-alert"></div>
        <div class="row" style="justify-content:flex-end;">
          <button type="button" class="btn btn-secondary" id="t-cancel-btn">${t("common_cancel", lang)}</button>
          <button type="submit" class="btn btn-primary">${t("admin_save", lang)}</button>
        </div>
      </form>
    `);
    modal.querySelector("#t-cancel-btn").addEventListener("click", close);
    modal.querySelector("#t-form").addEventListener("submit", async (e) => {
      e.preventDefault();
      const fd = new FormData(e.target);
      const localVal = fd.get("startTime");
      const iso = new Date(localVal).toISOString();
      try {
        const res = await api.post("/api/tournaments", {
          name: fd.get("name"),
          categoryId: fd.get("categoryId") || null,
          startTime: iso,
          questionCount: parseInt(fd.get("questionCount"), 10),
          perQuestionSecs: parseInt(fd.get("perQuestionSecs"), 10),
          durationMinutes: parseInt(fd.get("durationMinutes"), 10),
        });
        tournaments.unshift(res.tournament);
        renderRows();
        close();
      } catch (err) {
        modal.querySelector("#t-form-alert").innerHTML = `<div class="alert alert-error">${err.message}</div>`;
      }
    });
  });

  renderRows();
}

// ---------------------------------------------------------------------------
async function renderUsersAdmin(pane, lang) {
  pane.innerHTML = `<div class="center-loading"><div class="spinner"></div></div>`;
  try {
    const { users } = await api.get("/api/admin/users");
    pane.innerHTML = `
      <div class="table-scroll card">
        <table class="data-table">
          <thead><tr><th>${t("admin_name", lang)}</th><th>Email</th><th>${t("admin_role", lang)}</th><th>${t("leaderboard_points", lang)}</th><th>${t("leaderboard_quizzes", lang)}</th><th>${t("admin_joined", lang)}</th></tr></thead>
          <tbody>
            ${users.map((u) => `
              <tr>
                <td>${escapeHtml(u.name)}</td>
                <td>${escapeHtml(u.email)}</td>
                <td><span class="badge-pill">${u.role}</span></td>
                <td>${u.totalPoints}</td>
                <td>${u.quizzesPlayed}</td>
                <td>${formatDateTime(u.createdAt, lang)}</td>
              </tr>
            `).join("")}
          </tbody>
        </table>
      </div>
    `;
  } catch (err) {
    pane.innerHTML = `<div class="alert alert-error">${err.message}</div>`;
  }
}
