(function () {
  const API_BASE = "/api/v1";

  function safeJsonParse(s, fallback) { try { return JSON.parse(s); } catch { return fallback; } }

  const Storage = {
    mode: () => localStorage.getItem("pp_storage_mode") || "local",
    setMode: (mode) => localStorage.setItem("pp_storage_mode", mode),
    _store: function () { return this.mode() === "session" ? sessionStorage : localStorage; },
    get: function (k) { return this._store().getItem(k); },
    set: function (k, v) { this._store().setItem(k, v); },
    clearAuth: function () {
      localStorage.removeItem("pp_access"); localStorage.removeItem("pp_refresh"); localStorage.removeItem("pp_user");
      sessionStorage.removeItem("pp_access"); sessionStorage.removeItem("pp_refresh"); sessionStorage.removeItem("pp_user");
    }
  };

  function getTokens() { return { access: Storage.get("pp_access"), refresh: Storage.get("pp_refresh") }; }
  function setTokens(access, refresh) { if (access) Storage.set("pp_access", access); if (refresh) Storage.set("pp_refresh", refresh); }
  function setUser(userObj) { Storage.set("pp_user", JSON.stringify(userObj || {})); }
  function getUser() { return safeJsonParse(Storage.get("pp_user") || "{}", {}); }
  function isAuthed() { return Boolean(getTokens().access); }

  function escapeHtml(s) {
    return String(s).replace(/[&<>"']/g, (m) => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#039;'}[m]));
  }

  function renderAlert(targetEl, message, type) {
    if (!targetEl) return;
    const cls = type === "danger" ? "alert-danger" :
                type === "warning" ? "alert-warning" :
                type === "success" ? "alert-success" : "alert-secondary";
    targetEl.innerHTML = `
      <div class="alert ${cls} alert-dismissible fade show" role="alert">
        ${escapeHtml(message)}
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
      </div>`;
  }

  function toast(title, message, type) {
    const container = document.getElementById("toastContainer");
    if (!container || typeof bootstrap === "undefined") return;

    const id = "t" + Math.random().toString(16).slice(2);
    const typeClass = type === "danger" ? "text-bg-danger" :
                      type === "warning" ? "text-bg-warning" :
                      type === "success" ? "text-bg-success" : "text-bg-dark";

    container.insertAdjacentHTML("beforeend", `
      <div class="toast ${typeClass}" role="alert" aria-live="assertive" aria-atomic="true" id="${id}">
        <div class="d-flex">
          <div class="toast-body">
            <div class="fw-semibold">${escapeHtml(title)}</div>
            <div class="small">${escapeHtml(message || "")}</div>
          </div>
          <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast"></button>
        </div>
      </div>
    `);

    const el = document.getElementById(id);
    const t = new bootstrap.Toast(el, { delay: 3500 });
    t.show();
    el.addEventListener("hidden.bs.toast", () => el.remove());
  }

  async function refreshAccessToken() {
    const { refresh } = getTokens();
    if (!refresh) return null;

    const resp = await fetch(`${API_BASE}/auth/token/refresh/`, {
      method: "POST",
      headers: { "Content-Type": "application/json", "Accept": "application/json" },
      body: JSON.stringify({ refresh })
    });
    if (!resp.ok) return null;

    const data = await resp.json().catch(() => null);
    if (data?.access) {
      setTokens(data.access, refresh);
      return data.access;
    }
    return null;
  }

  async function apiFetch(path, options) {
    const opts = options || {};
    const headers = new Headers(opts.headers || {});
    headers.set("Accept", "application/json");

    const { access } = getTokens();
    if (access) headers.set("Authorization", `Bearer ${access}`);

    if (!(opts.body instanceof FormData) && opts.body && !headers.get("Content-Type")) {
      headers.set("Content-Type", "application/json");
    }
    opts.headers = headers;

    let resp = await fetch(`${API_BASE}${path}`, opts);

    // Auto-refresh on 401
    if (resp.status === 401) {
      const newAccess = await refreshAccessToken();
      if (newAccess) {
        headers.set("Authorization", `Bearer ${newAccess}`);
        resp = await fetch(`${API_BASE}${path}`, opts);
      }
    }
    return resp;
  }

  function requireAuth() {
    const p = window.location.pathname;
    // Landing page: redirect authenticated users to dashboard
    if (p === "/" && isAuthed()) {
      window.location.href = "/dashboard/";
      return;
    }
    // Public pages that don't require auth
    if (p === "/" || p.startsWith("/login") || p.startsWith("/register") || p.startsWith("/forgot-password") || p.startsWith("/reset-password") || p.startsWith("/about") || p.startsWith("/api/docs")) return;
    if (!isAuthed()) window.location.href = "/login/";
  }

  function hydrateNav() {
    const u = getUser();
    const name = u.username || "Account";
    const el1 = document.getElementById("navUsername");
    const el2 = document.getElementById("sidebarUser");
    if (el1) el1.textContent = name;
    if (el2) el2.textContent = name;

    const logoutLink = document.getElementById("navLogout");
    if (logoutLink) logoutLink.addEventListener("click", (e) => { e.preventDefault(); logout(true); });
  }

  function logout(redirect) {
    Storage.clearAuth();
    if (redirect !== false) window.location.href = "/login/";
  }

  window.ParsePro = {
    apiFetch, toast, renderAlert,
    getTokens, setTokens,
    getUser, setUser,
    storage: Storage,
    requireAuth, logout,
    escapeHtml
  };
  window.ParseProAuth = { logout };

  document.addEventListener("DOMContentLoaded", () => {
    requireAuth();
    hydrateNav();
  });
})();

