import { store } from "../store.js";
import { api } from "../api.js";
import { t } from "../i18n.js";
import { escapeHtml, timerRingSvg, launchConfetti, countdownLabel, icon } from "../utils.js";
import { navigate } from "../router.js";

const LETTERS = ["A", "B", "C", "D"];

export async function renderTournamentRoom(container, { id }) {
  const lang = store.lang;
  if (!store.token) { navigate("/login"); return; }

  const root = document.createElement("div");
  root.className = "page";
  root.innerHTML = `<div class="container"><div id="room-body"><div class="center-loading"><div class="spinner"></div></div></div></div>`;
  container.appendChild(root);
  const body = root.querySelector("#room-body");

  let tournament, es;
  let destroyed = false;
  let lastRenderedIndex = -1;
  let answeredCurrent = false;
  let scheduleTimer = null;

  function cleanup() {
    destroyed = true;
    if (es) es.close();
    if (scheduleTimer) clearInterval(scheduleTimer);
  }

  async function loadTournament() {
    try {
      const res = await api.get(`/api/tournaments/${id}?lang=${lang}`);
      tournament = res.tournament;
    } catch (err) {
      body.innerHTML = `<div class="alert alert-error">${err.message}</div>`;
      return false;
    }
    return true;
  }

  function renderJoinScreen() {
    body.innerHTML = `
      <div class="card" style="text-align:center; padding:40px 24px;">
        <h2 style="margin:0 0 8px;">${escapeHtml(tournament.name)}</h2>
        <p class="text-muted">${tournament.numQuestions} ${t("category_questions", lang)} &middot; ${tournament.participantCount} ${t("tournament_players", lang)}</p>
        <button class="btn btn-primary" id="join-btn" style="margin-top:18px;">${t("tournament_join", lang)}</button>
      </div>
    `;
    body.querySelector("#join-btn").addEventListener("click", async (e) => {
      e.target.disabled = true;
      try {
        await api.post(`/api/tournaments/${id}/join`, {});
        tournament.joined = true;
        startRoomFlow();
      } catch (err) {
        body.insertAdjacentHTML("beforeend", `<div class="alert alert-error" style="margin-top:12px;">${err.message}</div>`);
        e.target.disabled = false;
      }
    });
  }

  function renderLobby() {
    body.innerHTML = `
      <div class="card" style="text-align:center; padding:40px 24px;">
        <h2 style="margin:0 0 8px;">${escapeHtml(tournament.name)}</h2>
        <p class="text-muted">${t("tournament_waiting", lang)}</p>
        <div id="countdown" style="font-size:42px; font-weight:800; color:#7C3AED; margin:18px 0;"></div>
        <p class="text-muted" style="font-size:13px;">${t("tournament_lobby_hint", lang)}</p>
        <p class="row" style="justify-content:center; margin-top:14px;">
          <span class="badge-pill">${icon("users", 14)} <span id="p-count">${tournament.participantCount}</span> ${t("tournament_players", lang)}</span>
        </p>
      </div>
    `;
    if (scheduleTimer) clearInterval(scheduleTimer);
    const startMs = new Date(tournament.startTime).getTime();
    scheduleTimer = setInterval(() => {
      const remaining = startMs - Date.now();
      const el = body.querySelector("#countdown");
      if (el) el.textContent = countdownLabel(Math.max(0, remaining));
      if (remaining <= 0) clearInterval(scheduleTimer);
    }, 250);
  }

  function renderQuestion(q, msRemaining, index, total, alreadyAnswered) {
    lastRenderedIndex = index;
    answeredCurrent = !!alreadyAnswered;
    // Track remaining precisely using server-provided msRemaining as the source of truth.
    let localRemaining = msRemaining;

    body.innerHTML = `
      <div class="row between" style="margin-bottom:10px;">
        <span class="text-muted" style="font-weight:700; font-size:14px;">${t("tournament_question_progress", lang)} ${index + 1} ${t("quiz_of", lang)} ${total}</span>
        <span class="badge-pill">${q.points} ${t("quiz_points", lang)}</span>
      </div>
      <div class="quiz-progress-bar"><div style="width:${(index / total) * 100}%"></div></div>
      <div class="card" style="margin-top:20px;">
        <div class="row between">
          <div class="timer-ring" id="timer-ring">
            ${timerRingSvg(1, 64)}
            <div class="num" id="timer-num">${Math.ceil(msRemaining / 1000)}</div>
          </div>
          <div class="badge-pill">${escapeHtml(q.difficulty)}</div>
        </div>
        <div class="question-text">${escapeHtml(q.text)}</div>
        <div class="options-grid" id="options-grid">
          ${q.options.map((opt, i) => `
            <button class="option-btn" data-index="${i}" ${answeredCurrent ? "disabled" : ""}>
              <span class="letter">${LETTERS[i]}</span>
              <span>${escapeHtml(opt)}</span>
            </button>
          `).join("")}
        </div>
        <div id="feedback-area" style="margin-top:16px;">
          ${answeredCurrent ? `<div class="alert alert-info">${t("tournament_waiting", lang)}</div>` : ""}
        </div>
      </div>
    `;

    const ringEl = body.querySelector("#timer-ring");
    if (scheduleTimer) clearInterval(scheduleTimer);
    const total_ms = q.timeLimitSeconds * 1000;
    scheduleTimer = setInterval(() => {
      localRemaining -= 100;
      const pct = Math.max(0, localRemaining / total_ms);
      ringEl.innerHTML = timerRingSvg(pct, 64) + `<div class="num">${Math.max(0, Math.ceil(localRemaining / 1000))}</div>`;
      ringEl.classList.toggle("warn", pct <= 0.5 && pct > 0.2);
      ringEl.classList.toggle("danger", pct <= 0.2);
      if (localRemaining <= 0) clearInterval(scheduleTimer);
    }, 100);

    if (!answeredCurrent) {
      body.querySelectorAll(".option-btn").forEach((btn) => {
        btn.addEventListener("click", async () => {
          if (answeredCurrent) return;
          answeredCurrent = true;
          const selectedIndex = parseInt(btn.dataset.index, 10);
          const timeMs = q.timeLimitSeconds * 1000 - localRemaining;
          body.querySelectorAll(".option-btn").forEach((b) => (b.disabled = true));
          try {
            const result = await api.post(`/api/tournaments/${id}/answer`, {
              questionIndex: index, selectedIndex, timeMs: Math.max(0, Math.round(timeMs)),
            });
            body.querySelectorAll(".option-btn").forEach((b) => {
              const i = parseInt(b.dataset.index, 10);
              if (i === result.correctIndex) b.classList.add("correct");
              else if (i === selectedIndex) b.classList.add("incorrect");
            });
            body.querySelector("#feedback-area").innerHTML = `
              <div class="feedback-banner ${result.correct ? "correct" : "incorrect"}">
                ${result.correct ? t("quiz_correct", lang) : t("quiz_incorrect", lang)}
                ${result.correct ? `<span style="margin-inline-start:auto;">+${result.pointsAwarded} ${t("quiz_points", lang)}</span>` : ""}
              </div>
              <div class="alert alert-info" style="margin-top:10px;">${t("tournament_waiting", lang)}</div>
            `;
          } catch (err) {
            body.querySelector("#feedback-area").innerHTML = `<div class="alert alert-error">${err.message}</div>`;
          }
        });
      });
    }
  }

  async function fetchAndRenderQuestion(index, msRemaining) {
    try {
      const res = await api.get(`/api/tournaments/${id}/question?lang=${lang}`);
      if (destroyed) return;
      if (res.phase !== "LIVE") return;
      renderQuestion(res.question, res.msRemaining, res.index, res.total, res.alreadyAnswered);
    } catch (err) {
      body.innerHTML = `<div class="alert alert-error">${err.message}</div>`;
    }
  }

  function renderFinal(leaderboard) {
    if (scheduleTimer) clearInterval(scheduleTimer);
    const mine = leaderboard.find((p) => p.userId === store.user.id);
    const iWon = mine && mine.rank === 1;
    body.innerHTML = `
      <div class="result-hero card">
        <div class="score-circle">
          <div class="num">${mine ? mine.rank : "-"}</div>
          <div class="label">${t("tournament_you_finished", lang)}</div>
        </div>
        <h2 style="margin:0 0 6px;">${t("tournament_final_results", lang)}</h2>
        ${iWon ? `<p style="color:#15803D; font-weight:700;">🏆 ${t("tournament_winner_msg", lang)}</p>` : ""}
        <div class="stack" style="text-align:start; margin-top:20px;">
          ${leaderboard.map((p) => `
            <div class="leaderboard-row ${p.rank === 1 ? "top1" : p.rank === 2 ? "top2" : p.rank === 3 ? "top3" : ""}">
              <div class="rank">${p.rank}</div>
              <div class="name">${escapeHtml(p.name)}</div>
              <div class="points">${p.score}</div>
            </div>
          `).join("")}
        </div>
        <div class="row" style="justify-content:center; margin-top:24px;">
          <a href="#/tournaments" class="btn btn-primary">${t("nav_tournaments", lang)}</a>
        </div>
      </div>
    `;
    if (iWon) launchConfetti(150);
  }

  async function startRoomFlow() {
    body.innerHTML = `<div class="center-loading"><div class="spinner"></div></div>`;
    es = new EventSource(`/api/tournaments/${id}/stream`);
    es.onmessage = async (evt) => {
      if (destroyed) return;
      let payload;
      try { payload = JSON.parse(evt.data); } catch { return; }

      const pCountEl = body.querySelector("#p-count");
      if (pCountEl) pCountEl.textContent = payload.participantCount;

      if (payload.phase === "SCHEDULED") {
        if (!body.querySelector("#countdown")) renderLobby();
        return;
      }
      if (payload.phase === "LIVE") {
        if (payload.currentIndex !== lastRenderedIndex) {
          await fetchAndRenderQuestion(payload.currentIndex, payload.msRemainingInQuestion);
        }
        return;
      }
      if (payload.phase === "COMPLETED") {
        es.close();
        try {
          const { leaderboard } = await api.get(`/api/tournaments/${id}/leaderboard`);
          if (!destroyed) renderFinal(leaderboard);
        } catch (err) {
          body.innerHTML = `<div class="alert alert-error">${err.message}</div>`;
        }
        return;
      }
      if (payload.phase === "CANCELLED") {
        es.close();
        body.innerHTML = `<div class="empty-state">${t("tournament_cancelled", lang)}</div>`;
      }
    };
    es.onerror = () => { /* browser auto-reconnects EventSource by default */ };
  }

  const ok = await loadTournament();
  if (!ok) return cleanup;

  if (tournament.phase === "COMPLETED") {
    try {
      const { leaderboard } = await api.get(`/api/tournaments/${id}/leaderboard`);
      renderFinal(leaderboard);
    } catch (err) {
      body.innerHTML = `<div class="alert alert-error">${err.message}</div>`;
    }
    return cleanup;
  }
  if (tournament.phase === "CANCELLED") {
    body.innerHTML = `<div class="empty-state">${t("tournament_cancelled", lang)}</div>`;
    return cleanup;
  }
  if (!tournament.joined) {
    renderJoinScreen();
  } else {
    startRoomFlow();
  }

  return cleanup;
}
