// Phase 6: vanilla JS client for the FastAPI endpoints.
let currentIncident = null;
const $ = (s) => document.querySelector(s);

async function api(path, opts = {}) {
  const res = await fetch(path, opts);
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    toast(body.detail || `Request failed (${res.status})`);
    throw new Error(res.status);
  }
  return res.json();
}

function toast(msg) {
  const t = $("#toast"); t.textContent = msg; t.hidden = false;
  setTimeout(() => (t.hidden = true), 4000);
}

async function loadHealth() {
  const h = await api("/health");
  $("#health").textContent = `status: ${h.status}`;
}

async function loadIncidents() {
  const list = await api("/api/incidents");
  $("#incident-list").innerHTML = list.map((i) =>
    `<li data-id="${i.id}" class="${i.id === currentIncident ? "active" : ""}">
       <strong>${i.severity}</strong> ${i.title}<br><small>${i.id} · ${i.service || ""}</small></li>`).join("");
}

async function selectIncident(id) {
  currentIncident = id;
  $("#chat-title").textContent = id;
  $("#ask input").disabled = $("#ask button").disabled = false;
  const history = await api(`/api/chat/${id}/history`);
  $("#messages").innerHTML = "";
  history.forEach((m) => addMessage(m.role, m.content));
  loadIncidents();
}

function addMessage(role, text, extra = {}) {
  const div = document.createElement("div");
  div.className = `msg ${role}`;
  div.textContent = text;
  if (extra.sources) {
    extra.sources.forEach((s) => {
      const c = document.createElement("span");
      c.className = `chip ${s.doc_type === "web" ? "web" : ""}`;
      c.textContent = s.title || s.source;
      div.appendChild(c);
    });
  }
  if (extra.route_trace) {
    const d = document.createElement("details");
    d.innerHTML = `<summary>How I got this</summary>${extra.route_trace.join(" → ")}`;
    div.appendChild(d);
  }
  $("#messages").appendChild(div);
  div.scrollIntoView();
}

async function loadDocs() {
  const docs = await api("/api/documents");
  $("#doc-list").innerHTML = docs.map((d) => `<li>${d.filename} <small>(${d.doc_type}, ${d.chunks} chunks)</small></li>`).join("");
}

async function loadAudit() {
  const rows = await api("/api/audit?limit=20");
  $("#audit tbody").innerHTML = rows.map((r) =>
    `<tr><td>${r.ts.slice(11, 19)}</td><td>${r.action}</td><td>${r.status}</td><td>${r.latency_ms ?? ""}</td></tr>`).join("");
}

$("#incident-list").addEventListener("click", (e) => {
  const li = e.target.closest("li"); if (li) selectIncident(li.dataset.id);
});

$("#new-incident").addEventListener("submit", async (e) => {
  e.preventDefault();
  const body = Object.fromEntries(new FormData(e.target));
  const inc = await api("/api/incidents", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });
  e.target.reset(); await loadIncidents(); selectIncident(inc.id);
});

$("#ask").addEventListener("submit", async (e) => {
  e.preventDefault();
  const input = e.target.message; const message = input.value.trim(); if (!message) return;
  addMessage("human", message); input.value = ""; input.disabled = true;
  try {
    const r = await api("/api/chat", { method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ incident_id: currentIncident, message }) });
    addMessage("ai", r.answer, r);
  } finally { input.disabled = false; loadAudit(); }
});

$("#upload").addEventListener("submit", async (e) => {
  e.preventDefault();
  const r = await api("/api/ingest", { method: "POST", body: new FormData(e.target) });
  toast(`Upload: ${r.status}`); e.target.reset(); loadDocs(); loadAudit();
});

loadHealth(); loadIncidents(); loadDocs(); loadAudit();
