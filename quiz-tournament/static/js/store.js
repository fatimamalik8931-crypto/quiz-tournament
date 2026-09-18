/* Tiny global store: auth token, current user, language preference.
   Persists to localStorage so a refresh doesn't log the player out. */

const LS_TOKEN = "qt_token";
const LS_LANG = "qt_lang";

function safeGet(key) {
  try { return localStorage.getItem(key); } catch { return null; }
}
function safeSet(key, val) {
  try { localStorage.setItem(key, val); } catch { /* ignore (private mode, etc.) */ }
}
function safeRemove(key) {
  try { localStorage.removeItem(key); } catch { /* ignore */ }
}

const listeners = new Set();

export const store = {
  token: safeGet(LS_TOKEN) || null,
  user: null,
  lang: safeGet(LS_LANG) || "en",

  setToken(token) {
    this.token = token;
    if (token) safeSet(LS_TOKEN, token); else safeRemove(LS_TOKEN);
    notify();
  },
  setUser(user) {
    this.user = user;
    notify();
  },
  setLang(lang) {
    this.lang = lang;
    safeSet(LS_LANG, lang);
    document.documentElement.lang = lang;
    document.body.dir = lang === "ur" ? "rtl" : "ltr";
    notify();
  },
  logout() {
    this.token = null;
    this.user = null;
    safeRemove(LS_TOKEN);
    notify();
  },
  isAdmin() {
    return this.user && this.user.role === "ADMIN";
  },
};

function notify() {
  listeners.forEach((fn) => fn(store));
}

export function subscribe(fn) {
  listeners.add(fn);
  return () => listeners.delete(fn);
}
