/* ============================================================
   api.js — Cliente HTTP de la API REST.
   Todas las peticiones envían/usan la cookie de sesión.
   ============================================================ */
const API = (() => {
  async function request(method, url, body, isForm = false) {
    const opts = { method, credentials: "same-origin", headers: {} };
    if (body !== undefined) {
      if (isForm) {
        opts.body = body; // FormData
      } else {
        opts.headers["Content-Type"] = "application/json";
        opts.body = JSON.stringify(body);
      }
    }
    const res = await fetch(url, opts);
    if (!res.ok) {
      let detail = `Error ${res.status}`;
      try {
        const data = await res.json();
        detail = data.detail || detail;
      } catch (_) {}
      throw new Error(detail);
    }
    return res.json();
  }

  return {
    get: (url) => request("GET", url),
    post: (url, body) => request("POST", url, body),
    put: (url, body) => request("PUT", url, body),

    session: () => request("GET", "/api/session"),

    upload: (file) => {
      const fd = new FormData();
      fd.append("file", file);
      return request("POST", "/api/upload", fd, true);
    },

    dashboard: () => request("GET", "/api/dashboard"),

    getWeights: () => request("GET", "/api/weights"),
    putWeights: (rows) => request("PUT", "/api/weights", { rows }),
    saveWeights: () => request("POST", "/api/weights/save"),
    restoreWeights: () => request("POST", "/api/weights/restore"),
    autoA: (eventos, decimales) => request("POST", "/api/weights/auto-a", { eventos, decimales }),
    defaultBudget: (eventos) => request("POST", "/api/weights/default-budget", { eventos }),
    equalize: (eventos, presupuesto_total) => request("POST", "/api/weights/equalize", { eventos, presupuesto_total }),

    getRetention: () => request("GET", "/api/retention"),
    putRetention: (rows) => request("PUT", "/api/retention", { rows }),
    saveRetention: () => request("POST", "/api/retention/save"),
    resetRetention: () => request("POST", "/api/retention/reset"),
    templateRetention: () => request("POST", "/api/retention/template"),

    events: () => request("GET", "/api/events"),
    eventAnalysis: (event) => request("GET", `/api/events/analysis?event=${encodeURIComponent(event)}`),

    process: (payload) => request("POST", "/api/process", payload),
    exportUrl: (kind) => `/api/export/${kind}`,
  };
})();
