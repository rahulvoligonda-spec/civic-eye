// Civic Eye - admin panel (JavaScript)
const $ = id => document.getElementById(id);
let seen = null;          // IDs already shown, to mark new reports
let timer = null;

function mapLink(r){
  if(r.coords) return "https://www.google.com/maps?q=" + encodeURIComponent(r.coords);
  return "https://www.google.com/maps/search/?api=1&query=" + encodeURIComponent(r.addr);
}
function cell(tr, ...nodes){
  const td = document.createElement("td");
  nodes.forEach(n => td.appendChild(typeof n === "string" ? document.createTextNode(n) : n));
  tr.appendChild(td); return td;
}
function div(cls, text){ const d = document.createElement("div"); if(cls) d.className = cls; d.textContent = text; return d; }
function link(text, href){ const a = document.createElement("a"); a.textContent = text; a.href = href; a.target = "_blank"; a.rel = "noopener"; return a; }

async function api(url, opts){
  const res = await fetch(url, opts);
  if(res.status === 401){ location.href = "/admin/login"; throw new Error("login"); }
  return res.json();
}

async function loadStats(){
  const s = await api("/api/admin/stats");
  $("aTotal").textContent = s.total; $("aUnassigned").textContent = s.unassigned; $("aPending").textContent = s.pending;
  $("aProgress").textContent = s.progress; $("aResolved").textContent = s.resolved;
}

async function loadReports(){
  const p = new URLSearchParams({q:$("fq").value.trim(), dept:$("fdept").value, status:$("fstatus").value});
  const list = await api("/api/admin/reports?" + p);
  const firstLoad = seen === null;
  if(firstLoad) seen = new Set();
  const body = $("rows"); body.innerHTML = "";
  $("empty").style.display = list.length ? "none" : "block";

  list.forEach(r => {
    const tr = document.createElement("tr");
    const isNew = !firstLoad && !seen.has(r.id);
    if(isNew) tr.className = "fresh";
    seen.add(r.id);

    const img = document.createElement("img"); img.src = r.photo; img.alt = "Photo for " + r.id;
    cell(tr, link("", r.photo)).firstChild.appendChild(img);

    const t = cell(tr, div("id", r.id), div("small", r.date));
    if(isNew){ const n = document.createElement("span"); n.className = "newtag"; n.textContent = "NEW"; t.querySelector(".id").appendChild(n); }

    cell(tr, div("", r.addr), link("Open in Maps", mapLink(r)));

    // the admin decides which department gets this report
    const dsel = document.createElement("select"); dsel.setAttribute("aria-label", "Department for " + r.id);
    dsel.add(new Option("— Select department —", ""));
    DEPTS.forEach(d => dsel.add(new Option(d, d)));
    dsel.value = r.dept || "";
    const mark = () => dsel.classList.toggle("unset", !dsel.value);
    mark();
    dsel.onchange = async () => {
      await api("/api/admin/reports/" + r.id + "/department", {method:"POST", headers:{"Content-Type":"application/json"}, body:JSON.stringify({dept:dsel.value})});
      mark(); loadStats();
    };
    cell(tr, dsel);

    const sel = document.createElement("select"); sel.setAttribute("aria-label", "Status of " + r.id);
    ["Pending","In progress","Resolved"].forEach(o => sel.add(new Option(o, o)));
    sel.value = r.status;
    sel.onchange = async () => {
      await api("/api/admin/reports/" + r.id + "/status", {method:"POST", headers:{"Content-Type":"application/json"}, body:JSON.stringify({status:sel.value})});
      loadStats();
    };
    cell(tr, sel);

    const del = document.createElement("button"); del.className = "del"; del.textContent = "Delete";
    del.onclick = async () => {
      if(!confirm("Delete report " + r.id + "? This cannot be undone.")) return;
      await api("/api/admin/reports/" + r.id, {method:"DELETE"});
      refreshAll();
    };
    cell(tr, del);
    body.appendChild(tr);
  });
  $("live").textContent = "Last updated " + new Date().toLocaleTimeString() + ". Updates automatically every 10 seconds.";
}

function refreshAll(){ loadStats(); loadReports(); }
$("refresh").onclick = refreshAll;
$("fq").oninput = loadReports; $("fdept").onchange = loadReports; $("fstatus").onchange = loadReports;
refreshAll();
// auto-refresh so new citizen reports appear without reloading (skip while a dropdown is open)
timer = setInterval(() => { if(document.activeElement.tagName !== "SELECT") refreshAll(); }, 10000);
