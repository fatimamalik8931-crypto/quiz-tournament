import { store } from "../store.js";
import { t } from "../i18n.js";
import { icon } from "../utils.js";

export async function renderHome(container) {
  const lang = store.lang;
  container.innerHTML = `
    <div class="page">
      <div class="container">
        <div class="card" style="background: linear-gradient(135deg,#7C3AED,#EC4899); color:#fff; text-align:center; padding:56px 24px;">
          <h1 style="font-size:34px; font-weight:800; max-width:640px; margin:0 auto 14px;">${t("home_title", lang)}</h1>
          <p style="opacity:.95; max-width:560px; margin:0 auto 28px; font-size:16px;">${t("home_sub", lang)}</p>
          <div class="row" style="justify-content:center; flex-wrap:wrap;">
            <a href="#/play" class="btn" style="background:#fff; color:#7C3AED;">${t("home_cta_play", lang)}</a>
            <a href="#/tournaments" class="btn" style="background:rgba(255,255,255,.18); color:#fff;">${t("home_cta_tournaments", lang)}</a>
          </div>
        </div>

        <div class="grid cols-3" style="margin-top:28px;">
          <div class="card">
            <div class="icon-wrap" style="width:44px;height:44px;border-radius:12px;background:#F1F0FA;display:flex;align-items:center;justify-content:center;color:#7C3AED;">${icon("book", 22)}</div>
            <h3 style="margin:14px 0 4px;">${t("home_feature_categories", lang)}</h3>
            <p class="text-muted" style="margin:0; font-size:14px;">${t("home_feature_categories_sub", lang)}</p>
          </div>
          <div class="card">
            <div class="icon-wrap" style="width:44px;height:44px;border-radius:12px;background:#F1F0FA;display:flex;align-items:center;justify-content:center;color:#EC4899;">${icon("bolt", 22)}</div>
            <h3 style="margin:14px 0 4px;">${t("home_feature_modes", lang)}</h3>
            <p class="text-muted" style="margin:0; font-size:14px;">${t("home_feature_modes_sub", lang)}</p>
          </div>
          <div class="card">
            <div class="icon-wrap" style="width:44px;height:44px;border-radius:12px;background:#F1F0FA;display:flex;align-items:center;justify-content:center;color:#06B6D4;">${icon("globe", 22)}</div>
            <h3 style="margin:14px 0 4px;">${t("home_feature_langs", lang)}</h3>
            <p class="text-muted" style="margin:0; font-size:14px;">${t("home_feature_langs_sub", lang)}</p>
          </div>
        </div>
      </div>
    </div>
  `;
}
