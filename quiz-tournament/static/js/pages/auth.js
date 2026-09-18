import { store } from "../store.js";
import { api } from "../api.js";
import { t } from "../i18n.js";
import { navigate } from "../router.js";

export function renderAuth(mode) {
  return async function (container) {
    const lang = store.lang;
    const isLogin = mode === "login";

    container.innerHTML = `
      <div class="page">
        <div class="container">
          <div class="card auth-card">
            <h2 class="section-title" style="text-align:center;">${t(isLogin ? "auth_login_title" : "auth_register_title", lang)}</h2>
            <p class="section-sub" style="text-align:center;">${t(isLogin ? "auth_login_sub" : "auth_register_sub", lang)}</p>
            <div id="auth-alert"></div>
            <form id="auth-form" class="stack">
              ${!isLogin ? `
              <div class="field">
                <label>${t("auth_name", lang)}</label>
                <input name="name" type="text" required minlength="2" />
              </div>` : ""}
              <div class="field">
                <label>${t("auth_email", lang)}</label>
                <input name="email" type="email" required />
              </div>
              <div class="field">
                <label>${t("auth_password", lang)}</label>
                <input name="password" type="password" required minlength="6" />
              </div>
              <button type="submit" class="btn btn-primary btn-block">
                ${t(isLogin ? "auth_login_btn" : "auth_register_btn", lang)}
              </button>
            </form>
            <p style="text-align:center; margin-top:18px; font-size:14px;">
              ${t(isLogin ? "auth_no_account" : "auth_have_account", lang)}
              <a href="#${isLogin ? "/register" : "/login"}" style="color:#7C3AED; font-weight:700;">
                ${t(isLogin ? "auth_switch_register" : "auth_switch_login", lang)}
              </a>
            </p>
            ${isLogin ? `<p class="text-muted" style="text-align:center; font-size:12px; margin-top:10px;">Demo: demo@quiz.local / demo1234 &middot; Admin: admin@quiz.local / admin123</p>` : ""}
          </div>
        </div>
      </div>
    `;

    const form = container.querySelector("#auth-form");
    const alertBox = container.querySelector("#auth-alert");

    form.addEventListener("submit", async (e) => {
      e.preventDefault();
      alertBox.innerHTML = "";
      const fd = new FormData(form);
      const submitBtn = form.querySelector("button[type=submit]");
      submitBtn.disabled = true;
      try {
        const payload = {
          email: fd.get("email"),
          password: fd.get("password"),
        };
        if (!isLogin) {
          payload.name = fd.get("name");
          payload.preferredLanguage = lang;
        }
        const res = await api.post(`/api/auth/${isLogin ? "login" : "register"}`, payload);
        store.setToken(res.token);
        store.setUser(res.user);
        navigate("/play");
      } catch (err) {
        alertBox.innerHTML = `<div class="alert alert-error" style="margin-bottom:16px;">${err.message}</div>`;
      } finally {
        submitBtn.disabled = false;
      }
    });
  };
}
