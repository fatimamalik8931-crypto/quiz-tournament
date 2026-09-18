import { store, subscribe } from "./store.js";
import { api } from "./api.js";
import { t, LANGUAGES } from "./i18n.js";
import { addRoute, startRouter, currentPath, navigate, reloadRoute } from "./router.js";
import { icon } from "./utils.js";

import { renderHome } from "./pages/home.js";
import { renderAuth } from "./pages/auth.js";
import { renderCategories } from "./pages/categories.js";
import { renderQuiz } from "./pages/quiz.js";
import { renderTournaments } from "./pages/tournaments.js";
import { renderTournamentRoom } from "./pages/tournamentRoom.js";
import { renderLeaderboard } from "./pages/leaderboard.js";
import { renderProfile } from "./pages/profile.js";
import { renderAdmin } from "./pages/admin.js";

const app = document.getElementById("app");

document.documentElement.lang = store.lang;
document.body.dir = store.lang === "ur" ? "rtl" : "ltr";

app.innerHTML = `
  <header class="site-header">
    <div class="container">
      <div class="row">
        <button class="mobile-nav-toggle" id="mobile-toggle" aria-label="Menu">&#9776;</button>
        <a href="#/" class="brand">
          <span class="logo-badge">${icon("trophy", 20)}</span>
          <span id="brand-name">${t("appName", store.lang)}</span>
        </a>
      </div>
      <nav class="nav-links" id="nav-links"></nav>
      <div class="header-actions">
        <div class="lang-switch" id="lang-switch"></div>
        <div id="auth-actions"></div>
      </div>
    </div>
  </header>
  <main id="page-root" style="flex:1;"></main>
  <footer class="site-footer">Quiz Tournament &middot; built for learning &amp; friendly competition</footer>
`;

const navLinks = document.getElementById("nav-links");
const langSwitch = document.getElementById("lang-switch");
const authActions = document.getElementById("auth-actions");
const mobileToggle = document.getElementById("mobile-toggle");
const pageRoot = document.getElementById("page-root");
const brandName = document.getElementById("brand-name");

mobileToggle.addEventListener("click", () => navLinks.classList.toggle("open"));

function renderHeader() {
  const lang = store.lang;
  brandName.textContent = t("appName", lang);

  const links = [
    { path: "/", label: t("nav_home", lang) },
    { path: "/play", label: t("nav_categories", lang) },
    { path: "/tournaments", label: t("nav_tournaments", lang) },
    { path: "/leaderboard", label: t("nav_leaderboard", lang) },
  ];
  if (store.token) links.push({ path: "/profile", label: t("nav_profile", lang) });
  if (store.isAdmin()) links.push({ path: "/admin", label: t("nav_admin", lang) });

  const active = currentPath();
  navLinks.innerHTML = links.map((l) => `<a href="#${l.path}" class="${active === l.path ? "active" : ""}">${l.label}</a>`).join("");
  navLinks.querySelectorAll("a").forEach((a) => a.addEventListener("click", () => navLinks.classList.remove("open")));

  langSwitch.innerHTML = LANGUAGES.map((l) => `<button data-lang="${l.code}" class="${lang === l.code ? "active" : ""}">${l.label}</button>`).join("");
  langSwitch.querySelectorAll("button").forEach((btn) => {
    btn.addEventListener("click", () => {
      if (btn.dataset.lang === store.lang) return;
      store.setLang(btn.dataset.lang);
      reloadRoute();
    });
  });

  if (store.token && store.user) {
    authActions.innerHTML = `<button class="btn btn-secondary btn-sm" id="logout-btn">${t("nav_logout", lang)}</button>`;
    authActions.querySelector("#logout-btn").addEventListener("click", () => {
      store.logout();
      navigate("/");
    });
  } else {
    authActions.innerHTML = `
      <a href="#/login" class="btn btn-secondary btn-sm">${t("nav_login", lang)}</a>
      <a href="#/register" class="btn btn-primary btn-sm">${t("nav_register", lang)}</a>
    `;
  }
}

subscribe(renderHeader);
document.addEventListener("route-changed", renderHeader);

addRoute("/", renderHome);
addRoute("/login", renderAuth("login"));
addRoute("/register", renderAuth("register"));
addRoute("/play", renderCategories);
addRoute("/quiz/:categoryId", renderQuiz);
addRoute("/tournaments", renderTournaments);
addRoute("/tournaments/:id", renderTournamentRoom);
addRoute("/leaderboard", renderLeaderboard);
addRoute("/profile", renderProfile);
addRoute("/admin", renderAdmin);

async function bootstrap() {
  if (store.token) {
    try {
      const { user } = await api.get("/api/auth/me");
      store.setUser(user);
      if (user.preferred_language) store.setLang(user.preferred_language);
    } catch {
      store.logout();
    }
  }
  renderHeader();
  await startRouter(pageRoot, async (container) => {
    container.innerHTML = `<div class="page"><div class="container"><div class="empty-state">Page not found. <a href="#/">Go home</a></div></div></div>`;
  });
}

bootstrap();
