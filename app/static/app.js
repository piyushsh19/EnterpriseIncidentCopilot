// Phase 6: vanilla JS client for the FastAPI endpoints. No framework, no build step.
// Everything user- or model-supplied goes through esc() before it touches innerHTML.

const $ = (s, root = document) => root.querySelector(s);
const state = { incidents: [], current: null, busy: false };

// ---------- helpers ----------
function esc(s) {
  return String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
}

function user() {
  return ($("#user-name").value || "").trim() || "anonymous";
}

async function api(path, opts = {}) {
  const headers = { "X-User": user(), ...(opts.headers || {}) };
  if (opts.json !== undefined) {
    headers["Content-Type"] = "application/json";
    opts.body = JSON.stringify(opts.json);
  }
  let res;
  try {
    res = await fetch(path, { ...opts, headers });
  } catch {
    toast("Can't reach the server. Is it running?", "error");
    throw new Error("network");
  }
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    toast(errorText(res.status, body), "error");
    throw new Error(String(res.status));
  }
  return res.json();
}

function errorText(status, body) {
  const d = body.detail;
  if (Array.isArray(d)) return d.map((e) => `${(e.loc || []).slice(-1)[0]}: ${e.msg}`).join("; ");
  return d || `Request failed (${status})`;
}

function toast(msg, kind = "") {
  const t = document.createElement("div");
  t.className = `toast ${kind}`;
  t.textContent = msg;
  $("#toasts").appendChild(t);
  setTimeout(() => t.remove(), kind === "error" ? 6000 : 3500);
}

function timeAgo(iso) {
  const s = (Date.now() - new Date(iso).getTime()) / 1000;
  if (s < 60) return "just now";
  if (s < 3600) return `${Math.floor(s / 60)}m ago`;
  if (s < 86400) return `${Math.floor(s / 3600)}h ago`;
  return new Date(iso).toLocaleDateString();
}

// Minimal, safe markdown for the answer format (headings, lists, bold, code).
function renderMarkdown(text) {
  const inline = (s) => esc(s)
    .replace(/`([^`]+)`/g, "<code>$1</code>")
    .replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>")
    .replace(/CONFIRM FIRST/g, '<span class="confirm">CONFIRM FIRST</span>')
    .replace(/\(external, verify before applying\)/gi, '<span class="external">external, verify before applying</span>');

  const out = [];
  let list = null;
  const close = () => { if (list) { out.push(`</${list}>`); list = null; } };

  for (const raw of String(text || "").split("\n")) {
    const line = raw.trim();
    if (!line) { close(); continue; }
    let m;
    if ((m = line.match(/^\*\*([^*]+)\*\*(?:\s*\([^)]*\))?:?$/)) || (m = line.match(/^#{1,4}\s+(.*)$/))) {
      close(); out.push(`<h3>${inline(m[1])}</h3>`);
    } else if ((m = line.match(/^\d+[.)]\s+(.*)$/))) {
      if (list !== "ol") { close(); out.push("<ol>"); list = "ol"; }
      out.push(`<li>${inline(m[1])}</li>`);
    } else if ((m = line.match(/^[-*•]\s+(.*)$/))) {
      if (list !== "ul") { close(); out.push("<ul>"); list = "ul"; }
      out.push(`<li>${inline(m[1])}</li>`);
    } else {
      close(); out.push(`<p>${inline(line)}</p>`);
    }
  }
  close();
  return out.join("");
}

// ---------- health ----------
async function loadHealth(deep = false) {
  const el = $("#health");
  el.className = "health";
  $(".label", el).textContent = deep ? "Checking all services…" : "Checking…";
  try {
    const h = await fetch(`/health${deep ? "?deep=true" : ""}`).then((r) => r.json());
    el.classList.add(h.status === "ok" ? "ok" : "degraded");
    $(".label", el).textContent = `${h.provider === "ollama" ? "Ollama" : "OpenAI"} · ${h.status}`;
    el.title = Object.entries(h.checks)
      .map(([k, v]) => `${v.ok ? "✓" : "✗"} ${k}${v.error ? ": " + v.error : ""}${v.vectors !== undefined ? ` (${v.vectors} vectors)` : ""}`)
      .join("\n") + "\n\nClick to run a deep check";
    if (deep) toast(h.status === "ok" ? "All services reachable" : "Some services are failing; hover for details", h.status === "ok" ? "ok" : "error");
  } catch {
    el.classList.add("down");
    $(".label", el).textContent = "Server down";
  }
}

// ---------- incidents ----------
async function loadIncidents() {
  const status = $("#incident-filter").value;
  state.incidents = await api(`/api/incidents${status ? `?status=${status}` : ""}`);
  renderIncidents();
}

function renderIncidents() {
  const ul = $("#incident-list");
  if (!state.incidents.length) {
    ul.innerHTML = '<li class="empty-note">No incidents yet.</li>';
    return;
  }
  ul.innerHTML = state.incidents.map((i) => `
    <li data-id="${esc(i.id)}" class="${i.id === state.current?.id ? "active" : ""}">
      <span class="sev ${esc(i.severity)}">${esc(i.severity)}</span>
      <span class="pill ${esc(i.status)}">${esc(i.status)}</span>
      <span class="title">${esc(i.title)}</span>
      <span class="meta">${esc(i.id)}${i.service ? " · " + esc(i.service) : ""} · ${timeAgo(i.created_at)}</span>
    </li>`).join("");
}

async function selectIncident(id) {
  const inc = await api(`/api/incidents/${encodeURIComponent(id)}`);
  state.current = inc;
  $("#chat-empty").hidden = true;
  $("#chat-main").hidden = false;
  $("#chat-id").textContent = inc.id + (inc.service ? ` · ${inc.service}` : "");
  $("#chat-title").textContent = inc.title;
  $("#chat-status").value = inc.status;
  $("#chat-severity").value = inc.severity;
  renderIncidents();

  const history = await api(`/api/chat/${encodeURIComponent(id)}/history`);
  $("#messages").innerHTML = "";
  history.forEach((m) => addMessage(m.role === "human" ? "human" : "ai", m.content));
  renderSuggestions(history.length === 0);
  $("#ask textarea").focus();
  if ($("#audit-this").checked) loadAudit();
}

async function patchIncident(changes) {
  if (!state.current) return;
  const inc = await api(`/api/incidents/${encodeURIComponent(state.current.id)}`, { method: "PATCH", json: changes });
  state.current = inc;
  toast(`Incident ${inc.id} updated`, "ok");
  await loadIncidents();
  loadAudit();
}

// ---------- chat ----------
function addMessage(role, text, meta = null) {
  const div = document.createElement("div");
  div.className = `msg ${role}`;
  if (role === "human") {
    div.textContent = text;
  } else {
    if (meta?.status === "degraded") div.classList.add("degraded");
    div.innerHTML = `<div class="md">${renderMarkdown(text)}</div>`;
    if (meta) div.appendChild(answerFooter(meta));
  }
  $("#messages").appendChild(div);
  div.scrollIntoView({ block: "end" });
  return div;
}

function answerFooter(r) {
  const foot = document.createElement("div");
  foot.className = "msg-foot";

  const seen = new Set();
  const chips = (r.sources || []).filter((s) => {
    const key = s.source || s.title;
    if (seen.has(key)) return false;
    seen.add(key); return true;
  }).map((s) => {
    const isWeb = s.doc_type === "web";
    const label = esc(s.title || s.source);
    const tip = esc(isWeb ? s.source : `${s.doc_type || "doc"}${s.service ? " · " + s.service : ""}`);
    return isWeb && /^https?:\/\//.test(s.source || "")
      ? `<a class="chip web" href="${esc(s.source)}" target="_blank" rel="noopener noreferrer" title="${tip}">🌐 ${label}</a>`
      : `<span class="chip" title="${tip}">📘 ${label}</span>`;
  });

  const status = r.status ? `<span class="pill ${esc(r.status)}">${esc(r.status)}</span>` : "";
  foot.innerHTML = `
    <div class="chips">${status}<span class="label">Sources:</span>${chips.join("") || '<span class="muted">none</span>'}</div>
    ${r.web_used ? '<div class="muted">Your runbooks did not cover this, so web results were used. Verify external steps before applying.</div>' : ""}
    <details>
      <summary>How I got this</summary>
      <div class="trace">${(r.route_trace || []).map(traceStep).join("")}</div>
      ${graderTable(r.grader_scores || {})}
    </details>`;
  return foot;
}

function traceStep(step) {
  const cls = { transform_query: "loop", web_search: "web", finalize: "end", give_up: "give" }[step] || "";
  return `<span class="${cls}">${esc(step)}</span>`;
}

function graderTable(g) {
  const rows = [];
  if (g.relevant_docs !== undefined) rows.push(["Relevant docs", g.relevant_docs]);
  (g.answer_checks || []).forEach((c, i) => rows.push([`Draft ${i + 1}`, `${c.grounded ? "grounded" : "not grounded"}, ${c.useful ? "useful" : "not useful"}`]));
  if (!rows.length) return "";
  return `<div class="kv">${rows.map(([k, v]) => `<span>${esc(k)}</span><span>${esc(v)}</span>`).join("")}</div>`;
}

function renderSuggestions(isNew) {
  const box = $("#suggestions");
  const service = state.current?.service ? ` on ${state.current.service}` : "";
  const items = isNew
    ? [`${state.current?.title || "Describe the symptoms"}`, `What should I check first${service}?`]
    : ["What if that doesn't help?", "How do I confirm the root cause?", "Who do I escalate to?"];
  box.innerHTML = items.map((t) => `<button type="button">${esc(t)}</button>`).join("");
}

async function ask(message) {
  if (!state.current || state.busy || !message.trim()) return;
  state.busy = true;
  const form = $("#ask");
  form.querySelector("button").disabled = true;
  $("#suggestions").innerHTML = "";
  addMessage("human", message.trim());

  const thinking = document.createElement("div");
  thinking.className = "msg ai thinking";
  thinking.innerHTML = '<span class="spinner"></span><span>Searching runbooks and checking the answer… <b>0s</b></span>';
  $("#messages").appendChild(thinking);
  thinking.scrollIntoView({ block: "end" });
  const started = Date.now();
  const timer = setInterval(() => { $("b", thinking).textContent = `${Math.round((Date.now() - started) / 1000)}s`; }, 1000);

  try {
    const r = await api("/api/chat", { method: "POST", json: { incident_id: state.current.id, message: message.trim() } });
    thinking.remove();
    addMessage("ai", r.answer, r);
    renderSuggestions(false);
  } catch {
    thinking.remove();
    addMessage("ai", "**Request failed**\nThe copilot could not answer. Check the health indicator (top right) and try again.", { status: "error" });
  } finally {
    clearInterval(timer);
    state.busy = false;
    form.querySelector("button").disabled = false;
    $("#ask textarea").focus();
    loadAudit();
  }
}

// ---------- runbooks ----------
async function loadDocs() {
  const docs = await api("/api/documents");
  $("#doc-list").innerHTML = docs.length
    ? docs.map((d) => `
      <li><button class="del" type="button" data-doc="${esc(d.doc_id)}" data-name="${esc(d.filename)}" title="Remove from the index">✕</button>
      <div class="name">${esc(d.filename)}</div>
      <div class="meta">${esc(d.doc_type)} · ${esc(d.service || "general")} · ${esc(d.chunks)} chunk${d.chunks === 1 ? "" : "s"} · ${timeAgo(d.ingested_at)}</div></li>`).join("")
    : '<li class="muted">No documents indexed yet. Run <code>python scripts/seed_ingest.py</code> or upload one above.</li>';
}

function upload(form) {
  const file = form.file.files[0];
  if (!file) { toast("Choose a file first", "error"); return; }
  if (file.size > 10 * 1024 * 1024) { toast("File is larger than 10 MB", "error"); return; }

  const data = new FormData(form);
  if (!data.get("doc_type")) data.delete("doc_type");
  if (!data.get("service")) data.delete("service");

  const bar = $("#upload-progress");
  const btn = form.querySelector("button");
  bar.hidden = false; $("div", bar).style.width = "0%"; btn.disabled = true;

  // XHR (not fetch) so we can show upload progress.
  const xhr = new XMLHttpRequest();
  xhr.open("POST", "/api/ingest");
  xhr.setRequestHeader("X-User", user());
  xhr.upload.onprogress = (e) => { if (e.lengthComputable) $("div", bar).style.width = `${(e.loaded / e.total) * 90}%`; };
  xhr.onload = () => {
    $("div", bar).style.width = "100%";
    let body = {};
    try { body = JSON.parse(xhr.responseText); } catch { /* ignore */ }
    if (xhr.status >= 200 && xhr.status < 300) {
      const msg = { ingested: `Indexed ${file.name} (${body.chunks} chunks)`, updated: `Updated ${file.name}: old vectors replaced`, duplicate: `${file.name} is already indexed` }[body.status] || `Upload: ${body.status}`;
      toast(msg, body.status === "duplicate" ? "" : "ok");
      form.reset(); $("#drop-label").innerHTML = "Drop a file or click to choose<br /><small>PDF, Markdown, TXT, DOCX · max 10 MB</small>";
      loadDocs();
    } else {
      toast(errorText(xhr.status, body), "error");
    }
    finishUpload();
  };
  xhr.onerror = () => { toast("Upload failed: server unreachable", "error"); finishUpload(); };
  xhr.send(data);

  function finishUpload() {
    btn.disabled = false;
    setTimeout(() => { bar.hidden = true; }, 600);
    loadAudit();
  }
}

$("#doc-list").addEventListener("click", async (e) => {
  const btn = e.target.closest("button.del");
  if (!btn || !confirm(`Remove ${btn.dataset.name} from the index? The copilot will stop citing it.`)) return;
  await api(`/api/documents/${encodeURIComponent(btn.dataset.doc)}`, { method: "DELETE" });
  toast(`Removed ${btn.dataset.name}`, "ok");
  loadDocs(); loadAudit();
});

// ---------- audit ----------
async function loadAudit() {
  const params = new URLSearchParams({ limit: "50" });
  if ($("#audit-action").value) params.set("action", $("#audit-action").value);
  if ($("#audit-status").value) params.set("status", $("#audit-status").value);
  if ($("#audit-this").checked && state.current) params.set("incident_id", state.current.id);
  const rows = await api(`/api/audit?${params}`).catch(() => []);
  $("#audit-list").innerHTML = rows.length ? rows.map(auditRow).join("") : '<div class="muted">No audit entries match.</div>';
}

function auditRow(r) {
  const t = new Date(r.ts);
  const detail = {
    user: r.user, incident: r.incident_id, web_used: !!r.web_used,
    rewritten_queries: r.rewritten_queries, docs: r.doc_ids, route: r.route_trace,
    graders: r.grader_scores, error: r.error,
  };
  Object.keys(detail).forEach((k) => (detail[k] == null || (Array.isArray(detail[k]) && !detail[k].length)) && delete detail[k]);
  return `
    <details class="audit-row">
      <summary>
        <span class="time">${t.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit" })}</span>
        <span class="act">${esc(r.action)}</span>
        <span class="pill ${esc(r.status)}">${esc(r.status)}</span>
        <span class="ms">${r.latency_ms != null ? (r.latency_ms / 1000).toFixed(1) + "s" : ""}</span>
      </summary>
      ${r.question ? `<div class="q">${esc(r.question)}</div>` : ""}
      <pre>${esc(JSON.stringify(detail, null, 2))}</pre>
    </details>`;
}

// ---------- wiring ----------
$("#incident-list").addEventListener("click", (e) => {
  const li = e.target.closest("li[data-id]");
  if (li) selectIncident(li.dataset.id);
});
$("#incident-filter").addEventListener("change", loadIncidents);

$("#new-incident").addEventListener("submit", async (e) => {
  e.preventDefault();
  const body = Object.fromEntries(new FormData(e.target));
  if (!body.service) delete body.service;
  const inc = await api("/api/incidents", { method: "POST", json: body });
  e.target.reset();
  $("#incident-filter").value = "";
  await loadIncidents();
  await selectIncident(inc.id);
  toast(`Created ${inc.id}`, "ok");
});

$("#chat-status").addEventListener("change", (e) => patchIncident({ status: e.target.value }));
$("#chat-severity").addEventListener("change", (e) => patchIncident({ severity: e.target.value }));

$("#ask").addEventListener("submit", (e) => {
  e.preventDefault();
  const ta = e.target.message;
  const msg = ta.value;
  ta.value = "";
  ask(msg);
});
$("#ask textarea").addEventListener("keydown", (e) => {
  if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); $("#ask").requestSubmit(); }
});
$("#suggestions").addEventListener("click", (e) => {
  if (e.target.tagName === "BUTTON") ask(e.target.textContent);
});

$("#upload").addEventListener("submit", (e) => { e.preventDefault(); upload(e.target); });
const drop = $("#drop");
drop.querySelector("input").addEventListener("change", (e) => {
  const f = e.target.files[0];
  if (f) $("#drop-label").textContent = `${f.name} (${Math.ceil(f.size / 1024)} KB)`;
});
["dragenter", "dragover"].forEach((ev) => drop.addEventListener(ev, (e) => { e.preventDefault(); drop.classList.add("over"); }));
["dragleave", "drop"].forEach((ev) => drop.addEventListener(ev, (e) => { e.preventDefault(); drop.classList.remove("over"); }));
drop.addEventListener("drop", (e) => {
  const input = drop.querySelector("input");
  input.files = e.dataTransfer.files;
  input.dispatchEvent(new Event("change"));
});

document.querySelectorAll(".tab").forEach((tab) => tab.addEventListener("click", () => {
  document.querySelectorAll(".tab").forEach((t) => t.classList.toggle("active", t === tab));
  $("#tab-runbooks").hidden = tab.dataset.tab !== "runbooks";
  $("#tab-audit").hidden = tab.dataset.tab !== "audit";
  if (tab.dataset.tab === "audit") loadAudit();
}));
["#audit-action", "#audit-status", "#audit-this"].forEach((s) => $(s).addEventListener("change", loadAudit));

$("#health").addEventListener("click", () => loadHealth(true));

const nameInput = $("#user-name");
nameInput.value = localStorage.getItem("copilot-user") || "";
nameInput.addEventListener("change", () => localStorage.setItem("copilot-user", nameInput.value.trim()));

loadHealth();
loadIncidents();
loadDocs();
loadAudit();
setInterval(loadHealth, 30000);
