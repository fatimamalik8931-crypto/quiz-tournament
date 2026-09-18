/* Minimal hash-based router. Each route: { pattern: "/quiz/:categoryId", render(container, params) } */

const routes = [];
let currentCleanup = null;
let containerRef = null;
let notFoundRef = null;

export function addRoute(pattern, render) {
  const paramNames = [];
  const regexStr = pattern
    .split("/")
    .map((seg) => {
      if (seg.startsWith(":")) {
        paramNames.push(seg.slice(1));
        return "([^/]+)";
      }
      return seg.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
    })
    .join("/");
  routes.push({ regex: new RegExp(`^${regexStr}/?$`), paramNames, render });
}

function matchRoute(path) {
  for (const r of routes) {
    const m = r.regex.exec(path);
    if (m) {
      const params = {};
      r.paramNames.forEach((name, i) => { params[name] = decodeURIComponent(m[i + 1]); });
      return { render: r.render, params };
    }
  }
  return null;
}

export function navigate(path) {
  window.location.hash = path;
}

async function handle() {
  const path = window.location.hash.slice(1) || "/";
  const match = matchRoute(path);
  if (typeof currentCleanup === "function") {
    try { currentCleanup(); } catch { /* ignore */ }
    currentCleanup = null;
  }
  containerRef.innerHTML = "";
  containerRef.scrollTop = 0;
  window.scrollTo(0, 0);
  if (match) {
    currentCleanup = await match.render(containerRef, match.params);
  } else if (notFoundRef) {
    currentCleanup = await notFoundRef(containerRef);
  }
  document.dispatchEvent(new CustomEvent("route-changed", { detail: { path } }));
}

export async function startRouter(container, notFoundRender) {
  containerRef = container;
  notFoundRef = notFoundRender;
  window.addEventListener("hashchange", handle);
  await handle();
}

/** Re-render whatever route is currently active (e.g. after a language switch). */
export async function reloadRoute() {
  if (containerRef) await handle();
}

export function currentPath() {
  return window.location.hash.slice(1) || "/";
}
