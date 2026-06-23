/* ============================================================
   ui.js — Helpers de presentación: formato, toasts, tablas,
   pestañas y overlay de carga.
   ============================================================ */
const UI = (() => {
  // ---- Formato ----
  const eur = (v) =>
    "€" + Number(v ?? 0).toLocaleString("es-ES", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  const eur4 = (v) =>
    "€" + Number(v ?? 0).toLocaleString("es-ES", { minimumFractionDigits: 4, maximumFractionDigits: 4 });
  const pct = (v, d = 1) => Number(v ?? 0).toFixed(d) + "%";
  const num = (v, d = 4) => Number(v ?? 0).toFixed(d);

  // ---- Helpers DOM ----
  const $ = (sel, root = document) => root.querySelector(sel);
  const $$ = (sel, root = document) => Array.from(root.querySelectorAll(sel));

  // ---- Toasts ----
  function toast(text, level = "info", timeout = 4200) {
    const wrap = $("#toasts");
    const el = document.createElement("div");
    el.className = `toast ${level}`;
    el.textContent = text;
    wrap.appendChild(el);
    setTimeout(() => {
      el.style.opacity = "0";
      setTimeout(() => el.remove(), 250);
    }, timeout);
  }
  function toastMessages(messages) {
    (messages || []).forEach((m) => toast(m.text, m.level, 5000));
  }

  // ---- Contador animado (count-up) ----
  function animateValue(el, to, { prefix = "", suffix = "", decimals = 0, duration = 750 } = {}) {
    if (!el) return;
    const reduce = window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    const fmt = (v) =>
      prefix + Number(v).toLocaleString("es-ES", { minimumFractionDigits: decimals, maximumFractionDigits: decimals }) + suffix;
    if (reduce) {
      el.textContent = fmt(to);
      return;
    }
    const start = performance.now();
    function frame(now) {
      const t = Math.min(1, (now - start) / duration);
      const eased = 1 - Math.pow(1 - t, 3); // easeOutCubic
      el.textContent = fmt(to * eased);
      if (t < 1) requestAnimationFrame(frame);
    }
    requestAnimationFrame(frame);
  }

  // ---- Loading overlay ----
  function loading(on, text = "Procesando…") {
    const ov = $("#loading");
    $("#loading-text").textContent = text;
    ov.classList.toggle("hidden", !on);
  }

  // ---- Tablas ----
  // columns: [{key, label, fmt?, cls?, classer?}]
  function renderTable(table, columns, rows) {
    const thead = `<thead><tr>${columns
      .map((c) => `<th class="${c.cls || ""}">${c.label}</th>`)
      .join("")}</tr></thead>`;
    const body = rows
      .map((r) => {
        const tds = columns
          .map((c) => {
            const raw = r[c.key];
            const val = c.fmt ? c.fmt(raw, r) : raw ?? "";
            const extra = c.classer ? c.classer(raw, r) : "";
            return `<td class="${c.cls || ""} ${extra}">${val}</td>`;
          })
          .join("");
        return `<tr>${tds}</tr>`;
      })
      .join("");
    table.innerHTML = thead + `<tbody>${body}</tbody>`;
  }

  // Tabla genérica a partir de records (claves = columnas)
  function renderRecords(table, records, moneyCols = []) {
    if (!records || !records.length) {
      table.innerHTML = "<tbody><tr><td>Sin datos</td></tr></tbody>";
      return;
    }
    const keys = Object.keys(records[0]);
    const columns = keys.map((k) => ({
      key: k,
      label: k,
      cls: typeof records[0][k] === "number" ? "num" : "",
      fmt: moneyCols.includes(k)
        ? (v) => (v == null ? "" : eur(v))
        : (v) => (typeof v === "number" ? v.toLocaleString("es-ES", { maximumFractionDigits: 2 }) : v ?? ""),
    }));
    renderTable(table, columns, records);
  }

  // ---- Tabs (delegado dentro de un contenedor card) ----
  function initTabs(scope) {
    $$(".tabs", scope).forEach((tabsEl) => {
      const card = tabsEl.parentElement;
      tabsEl.addEventListener("click", (e) => {
        const btn = e.target.closest(".tab");
        if (!btn) return;
        $$(".tab", tabsEl).forEach((t) => t.classList.toggle("active", t === btn));
        const name = btn.dataset.tab;
        $$(".tab-panel", card).forEach((p) =>
          p.classList.toggle("hidden", p.dataset.panel !== name)
        );
      });
    });
  }

  return { eur, eur4, pct, num, $, $$, toast, toastMessages, loading, animateValue, renderTable, renderRecords, initTabs };
})();
