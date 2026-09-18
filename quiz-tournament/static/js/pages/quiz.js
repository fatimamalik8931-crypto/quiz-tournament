import { store } from "../store.js";
import { api } from "../api.js";
import { t } from "../i18n.js";
import { escapeHtml, timerRingSvg, launchConfetti } from "../utils.js";
import { navigate } from "../router.js";

const LETTERS = ["A", "B", "C", "D"];

export async function renderQuiz(container, { categoryId }) {
  const lang = store.lang;

  if (!store.token) {
    navigate("/login");
    return;
  }

  const root = document.createElement("div");
  root.className = "page";
  root.innerHTML = `<div class="container"><div id="quiz-body"></div></div>`;
  container.appendChild(root);
  const body = root.querySelector("#quiz-body");

  let attemptId, questions;
  let index = 0;
  let timerHandle = null;
  let questionStartedAt = 0;
  let answered = false;
  let totalScore = 0;
  let correctCount = 0;
  let destroyed = false;

  function clearTimer() {
    if (timerHandle) { clearInterval(timerHandle); timerHandle = null; }
  }

  async function loadSession() {
    index = 0; totalScore = 0; correctCount = 0;
    body.innerHTML = `<div class="center-loading"><div class="spinner"></div></div>`;
    try {
      const session = await api.post("/api/quiz/start", { categoryId, language: lang, count: 10 });
      attemptId = session.attemptId;
      questions = session.questions;
    } catch (err) {
      body.innerHTML = `<div class="alert alert-error">${err.message}</div>`;
      return;
    }
    if (destroyed) return;
    renderQuestion();
  }

  function renderQuestion() {
    answered = false;
    const q = questions[index];
    questionStartedAt = performance.now();
    const total = q.timeLimitSeconds * 1000;

    body.innerHTML = `
      <div class="row between" style="margin-bottom:10px;">
        <span class="text-muted" style="font-weight:700; font-size:14px;">${t("quiz_question", lang)} ${index + 1} ${t("quiz_of", lang)} ${questions.length}</span>
        <span class="badge-pill">${q.points} ${t("quiz_points", lang)}</span>
      </div>
      <div class="quiz-progress-bar"><div style="width:${(index / questions.length) * 100}%"></div></div>
      <div class="card" style="margin-top:20px;">
        <div class="row between">
          <div class="timer-ring" id="timer-ring">
            ${timerRingSvg(1, 64)}
            <div class="num" id="timer-num">${q.timeLimitSeconds}</div>
          </div>
          <div class="badge-pill">${escapeHtml(q.difficulty)}</div>
        </div>
        <div class="question-text">${escapeHtml(q.text)}</div>
        <div class="options-grid" id="options-grid">
          ${q.options.map((opt, i) => `
            <button class="option-btn" data-index="${i}">
              <span class="letter">${LETTERS[i]}</span>
              <span>${escapeHtml(opt)}</span>
            </button>
          `).join("")}
        </div>
        <div id="feedback-area" style="margin-top:16px;"></div>
      </div>
    `;

    const ringEl = body.querySelector("#timer-ring");
    const grid = body.querySelector("#options-grid");

    clearTimer();
    timerHandle = setInterval(() => {
      const elapsed = performance.now() - questionStartedAt;
      const remaining = Math.max(0, total - elapsed);
      const pct = remaining / total;
      ringEl.innerHTML = timerRingSvg(pct, 64) + `<div class="num" id="timer-num">${Math.ceil(remaining / 1000)}</div>`;
      ringEl.classList.toggle("warn", pct <= 0.5 && pct > 0.2);
      ringEl.classList.toggle("danger", pct <= 0.2);
      if (remaining <= 0 && !answered) {
        clearTimer();
        submitAnswer(null);
      }
    }, 100);

    grid.querySelectorAll(".option-btn").forEach((btn) => {
      btn.addEventListener("click", () => {
        if (answered) return;
        submitAnswer(parseInt(btn.dataset.index, 10));
      });
    });
  }

  async function submitAnswer(selectedIndex) {
    if (answered || destroyed) return;
    answered = true;
    clearTimer();
    const q = questions[index];
    const timeMs = Math.round(performance.now() - questionStartedAt);
    const grid = body.querySelector("#options-grid");
    const buttons = grid.querySelectorAll(".option-btn");

    let result;
    try {
      result = await api.post("/api/quiz/answer", {
        attemptId, questionId: q.id, selectedIndex, timeMs,
      });
    } catch (err) {
      body.querySelector("#feedback-area").innerHTML = `<div class="alert alert-error">${err.message}</div>`;
      return;
    }
    if (destroyed) return;

    totalScore += result.pointsAwarded;
    if (result.correct) correctCount++;

    buttons.forEach((btn) => {
      const i = parseInt(btn.dataset.index, 10);
      btn.disabled = true;
      if (i === result.correctIndex) btn.classList.add("correct");
      else if (i === selectedIndex) btn.classList.add("incorrect");
    });

    const feedback = body.querySelector("#feedback-area");
    feedback.innerHTML = `
      <div class="feedback-banner ${result.correct ? "correct" : "incorrect"}">
        ${result.correct ? t("quiz_correct", lang) : (selectedIndex === null ? t("quiz_time_up", lang) : t("quiz_incorrect", lang))}
        ${result.correct ? `<span style="margin-inline-start:auto;">+${result.pointsAwarded} ${t("quiz_points", lang)}</span>` : ""}
      </div>
      <button class="btn btn-primary btn-block" id="next-btn" style="margin-top:14px;">
        ${index + 1 < questions.length ? t("quiz_next", lang) : t("quiz_finish", lang)}
      </button>
    `;
    feedback.querySelector("#next-btn").addEventListener("click", () => {
      index++;
      if (index < questions.length) renderQuestion();
      else finishQuiz();
    });
  }

  async function finishQuiz() {
    let result;
    try {
      result = await api.post("/api/quiz/finish", { attemptId });
    } catch (err) {
      result = { score: totalScore, correctCount, totalQuestions: questions.length, badgesAwarded: [] };
    }
    if (destroyed) return;

    const pct = result.totalQuestions ? result.correctCount / result.totalQuestions : 0;
    body.innerHTML = `
      <div class="result-hero card">
        <div class="score-circle">
          <div class="num">${result.score}</div>
          <div class="label">${t("result_score", lang)}</div>
        </div>
        <h2 style="margin:0 0 6px;">${t("result_title", lang)}</h2>
        <p class="text-muted">${result.correctCount} / ${result.totalQuestions} ${t("result_correct", lang)}</p>
        ${result.badgesAwarded && result.badgesAwarded.length ? `
          <div class="alert alert-success" style="display:inline-flex; margin:10px auto;">
            🏅 ${t("result_badge_unlocked", lang)}: ${result.badgesAwarded.map(escapeHtml).join(", ")}
          </div>` : ""}
        <div class="row" style="justify-content:center; margin-top:20px; flex-wrap:wrap;">
          <button class="btn btn-primary" id="again-btn">${t("result_play_again", lang)}</button>
          <a href="#/play" class="btn btn-secondary">${t("result_new_category", lang)}</a>
        </div>
      </div>
    `;
    if (pct >= 0.6 || (result.badgesAwarded && result.badgesAwarded.length)) {
      launchConfetti(pct === 1 ? 140 : 80);
    }
    body.querySelector("#again-btn").addEventListener("click", loadSession);
  }

  loadSession();

  return () => { destroyed = true; clearTimer(); };
}
