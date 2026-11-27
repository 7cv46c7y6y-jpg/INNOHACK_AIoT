/* 아쿠아클레임 입력 화면: 단계 이동, 입력값 모으기, 검토, 서식 내려받기, 지도 공유 */
(() => {
  "use strict";

  const form = document.getElementById("case-form");
  const steps = [...document.querySelectorAll(".step")];
  const pills = [...document.querySelectorAll("#stepper li")];
  const LAST = steps.length - 1;
  let current = 0;

  // 오류 위치(field) → 단계 번호
  const FIELD_STEP = [
    [/^disaster\./, 1], [/^(victim|reporter|license|farm)\./, 2], [/^relation/, 2],
    [/^(stocking|outs|feed|rows|seed_source|sale|pre_disaster_reported)/, 3],
    [/^damage/, 4], [/^form01\./, 5], [/^evidence/, 6],
  ];

  // ------------------------------------------------------------ 공통 도구
  const isIndex = (k) => /^\d+$/.test(k);

  function setPath(obj, path, value) {
    const keys = path.split(".");
    let cur = obj;
    keys.forEach((k, i) => {
      const key = isIndex(k) ? Number(k) : k;
      if (i === keys.length - 1) { cur[key] = value; return; }
      if (cur[key] == null) cur[key] = isIndex(keys[i + 1]) ? [] : {};
      cur = cur[key];
    });
  }

  function getPath(obj, path) {
    return path.split(".").reduce((o, k) => (o == null ? undefined : o[isIndex(k) ? Number(k) : k]), obj);
  }

  function esc(text) {
    return String(text ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  }

  const fmt = (n) => (n == null || Number.isNaN(n) ? "-" : Number(n).toLocaleString("ko-KR"));

  function toast(message) {
    let el = document.getElementById("toast");
    if (!el) {
      el = document.createElement("div");
      el.id = "toast";
      el.setAttribute("role", "status");
      document.body.appendChild(el);
    }
    el.textContent = message;
    el.classList.add("show");
    clearTimeout(el._timer);
    el._timer = setTimeout(() => el.classList.remove("show"), 3200);
  }

  // ------------------------------------------------------------ 반복 줄
  function rowsBox(name) { return form.querySelector(`[data-rows="${name}"]`); }

  function addRow(name, values) {
    const box = rowsBox(name);
    const max = Number(box.dataset.max || 99);
    if (box.querySelectorAll("[data-row]").length >= max) {
      toast(`서식에는 ${max}줄까지만 들어갑니다.`);
      return null;
    }
    const node = document.getElementById(box.dataset.template).content.firstElementChild.cloneNode(true);
    if (values) {
      node.querySelectorAll("[data-field]").forEach((el) => {
        const v = values[el.dataset.field];
        if (v != null) el.value = v;
      });
    }
    box.appendChild(node);
    updateAddButtons();
    return node;
  }

  function updateAddButtons() {
    form.querySelectorAll("[data-add]").forEach((btn) => {
      const box = rowsBox(btn.dataset.add);
      btn.disabled = box.querySelectorAll("[data-row]").length >= Number(box.dataset.max || 99);
    });
  }

  // ------------------------------------------------------------ 입력값 모으기 / 채우기
  function serialize() {
    const data = {};
    form.querySelectorAll("[data-path]").forEach((el) => {
      const path = el.dataset.path;
      if (el.type === "radio") {
        if (el.checked) setPath(data, path, el.value || null);
        else if (getPath(data, path) === undefined) setPath(data, path, null);
        return;
      }
      if (el.type === "checkbox") { setPath(data, path, el.checked); return; }
      const v = el.value.trim();
      setPath(data, path, v === "" ? null : v);
    });
    form.querySelectorAll("[data-rows]").forEach((box) => {
      data[box.dataset.rows] = [...box.querySelectorAll("[data-row]")].map((row) => {
        const o = {};
        row.querySelectorAll("[data-field]").forEach((el) => {
          const v = el.value.trim();
          o[el.dataset.field] = v === "" ? null : v;
        });
        return o;
      });
    });
    if (data.reporter_same) data.relation = "본인";
    if (document.getElementById("sub-same").checked) {
      const v = data.victim || {};
      ["mobile_subscriber", "landline_subscriber"].forEach((k) => {
        setPath(data, `form01.${k}.name`, v.name || null);
        setPath(data, `form01.${k}.birth`, v.birth || null);
      });
    }
    return data;
  }

  function fill(data) {
    form.reset();
    ["stocking", "outs", "feed"].forEach((name) => { rowsBox(name).innerHTML = ""; });
    form.querySelectorAll("[data-path]").forEach((el) => {
      const v = getPath(data, el.dataset.path);
      if (el.type === "radio") {
        const want = v === true ? "예" : v === false ? "아니오" : (v ?? "");
        el.checked = el.value === want;
        return;
      }
      if (el.type === "checkbox") { el.checked = !!v; return; }
      el.value = v ?? "";
    });
    (data.stocking || []).forEach((r) => addRow("stocking", r));
    (data.outs || []).forEach((r) => addRow("outs", r));
    (data.feed || []).forEach((r) => addRow("feed", r));
    const v = data.victim || {};
    const sub = (data.form01 || {}).mobile_subscriber || {};
    document.getElementById("sub-same").checked = !!v.name && sub.name === v.name;
    const farm = data.farm || {};
    if (farm.lat != null && farm.lng != null) setPick(Number(farm.lat), Number(farm.lng));
    refreshUI();
  }

  // ------------------------------------------------------------ 화면 상태
  function refreshUI() {
    const data = serialize();
    document.getElementById("reporter-box").hidden = !!data.reporter_same;
    document.getElementById("sub-box").hidden = document.getElementById("sub-same").checked;
    form.querySelectorAll("[data-show-if]").forEach((el) => {
      const [path, value] = el.dataset.showIf.split("=");
      el.hidden = getPath(data, path) !== value;
    });
    const pre = data.pre_disaster_reported;
    document.getElementById("pre-report-warn").hidden = pre === "예";
    live(data);
    updateAddButtons();
  }

  function live(data = serialize()) {
    const sum = (rows, pred) => (rows || []).filter(pred).reduce((s, r) => s + (Number(r.count) || 0), 0);
    const stocked = sum(data.stocking, () => true);
    const shipped = sum(data.outs, (r) => r.kind === "출하");
    const priorDead = sum(data.outs, (r) => r.kind === "폐사");
    const stock = stocked ? stocked - shipped - priorDead : null;
    const dead = Number((data.damage || {}).dead_count) || null;
    const rate = stock > 0 && dead ? (dead / stock) * 100 : null;
    document.getElementById("live-stock").innerHTML = stocked
      ? `재해 직전 사육량 <b>${fmt(stock)}마리</b> = 입식 ${fmt(stocked)} − 출하 ${fmt(shipped)} − 기존 폐사 ${fmt(priorDead)}`
      : "입식 기록을 넣으면 재해 직전 사육량을 계산합니다.";
    document.getElementById("live-rate").innerHTML = rate != null
      ? `피해율 참고값 <b>${rate.toFixed(2)}%</b> (재해 직전 사육량 ${fmt(stock)}마리 대비 ${fmt(dead)}마리). 공적으로 확정된 값이 아닙니다.`
      : "사육 기록과 폐사량을 넣으면 피해율 참고값을 계산합니다.";
  }

  form.addEventListener("input", () => refreshUI());
  form.addEventListener("change", () => refreshUI());
  form.addEventListener("click", (e) => {
    const add = e.target.closest("[data-add]");
    if (add) { addRow(add.dataset.add); refreshUI(); return; }
    const del = e.target.closest(".row-del");
    if (del) { del.closest("[data-row]").remove(); refreshUI(); }
  });

  // ------------------------------------------------------------ 단계 이동
  function showStep(i) {
    current = Math.max(0, Math.min(LAST, i));
    steps.forEach((s, idx) => { s.hidden = idx !== current; });
    pills.forEach((p, idx) => {
      p.classList.toggle("active", idx === current);
      p.classList.toggle("done", idx < current);
    });
    form.querySelector("[data-prev]").disabled = current === 0;
    form.querySelector(".nav [data-next]").hidden = current === LAST;
    window.scrollTo({ top: 0, behavior: "smooth" });
    if (current === 2) initPickMap();
    if (current === LAST) runReview();
  }

  function goField(field) {
    const hit = FIELD_STEP.find(([re]) => re.test(field || ""));
    showStep(hit ? hit[1] : 1);
    const el = form.querySelector(`[data-path="${field}"]`);
    if (el) setTimeout(() => { el.focus({ preventScroll: false }); el.classList.add("flash"); setTimeout(() => el.classList.remove("flash"), 1600); }, 300);
  }

  document.addEventListener("click", (e) => {
    if (e.target.closest("[data-next]")) showStep(current + 1);
    else if (e.target.closest("[data-prev]")) showStep(current - 1);
    const pill = e.target.closest("[data-go]");
    if (pill) showStep(Number(pill.dataset.go));
    const fix = e.target.closest("[data-fix]");
    if (fix) goField(fix.dataset.fix);
    const dl = e.target.closest("[data-download]");
    if (dl) download(dl.dataset.download, dl);
    if (e.target.closest("#share-map")) shareMap();
  });

  document.getElementById("load-demo").addEventListener("click", async () => {
    const res = await fetch("/api/demo");
    fill(await res.json());
    toast("시연 데이터(통영 가상 어가)를 채웠습니다.");
    showStep(1);
  });

  // ------------------------------------------------------------ 위치 찍기 지도
  let pickMap = null;
  let pickMarker = null;

  function initPickMap() {
    if (pickMap || typeof L === "undefined") { if (pickMap) setTimeout(() => pickMap.invalidateSize(), 50); return; }
    pickMap = L.map("pick-map").setView([34.76, 128.40], 10);
    L.tileLayer("https://tile.openstreetmap.org/{z}/{x}/{y}.png", {
      maxZoom: 18, attribution: "&copy; OpenStreetMap contributors",
    }).addTo(pickMap);
    pickMap.on("click", (e) => setPick(e.latlng.lat, e.latlng.lng));
    const lat = Number(document.getElementById("farm-lat").value);
    const lng = Number(document.getElementById("farm-lng").value);
    if (lat && lng) setPick(lat, lng);
    setTimeout(() => pickMap.invalidateSize(), 50);
  }

  function setPick(lat, lng) {
    document.getElementById("farm-lat").value = lat.toFixed(4);
    document.getElementById("farm-lng").value = lng.toFixed(4);
    document.getElementById("pick-coords").textContent = `위도 ${lat.toFixed(4)}, 경도 ${lng.toFixed(4)}`;
    if (!pickMap) return;
    if (pickMarker) pickMarker.setLatLng([lat, lng]);
    else pickMarker = L.marker([lat, lng]).addTo(pickMap);
    pickMap.setView([lat, lng], Math.max(pickMap.getZoom(), 11));
  }

  // ------------------------------------------------------------ 검토
  async function post(url) {
    return fetch(url, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(serialize()) });
  }

  async function runReview() {
    const box = document.getElementById("review");
    box.innerHTML = "<p>검토 중입니다…</p>";
    try {
      const res = await post("/api/review");
      const out = await res.json();
      if (!res.ok) throw new Error(out.error || "검토하지 못했습니다.");
      box.innerHTML = renderReview(out);
    } catch (err) {
      box.innerHTML = `<p class="error">${esc(err.message)}</p>`;
    }
  }

  function list(items, cls = "") {
    if (!items || !items.length) return "";
    return `<ul class="${cls}">${items.map((i) => `<li>${i}</li>`).join("")}</ul>`;
  }

  function renderReview(out) {
    const s = out.summary;
    const v = out.validation;
    const g = out.guidance;
    const data = serialize();
    const parts = [];

    parts.push(`<div class="stats">
      <div><span>재해 직전 사육량</span><b>${s.stock_before != null ? fmt(s.stock_before) + "마리" : "-"}</b></div>
      <div><span>이번 피해량</span><b>${s.dead_count != null ? fmt(s.dead_count) + "마리" : "-"}</b></div>
      <div><span>피해율 (참고값)</span><b>${s.damage_rate != null ? s.damage_rate.toFixed(2) + "%" : "-"}</b></div>
      <div><span>①③ 신고 기한</span><b>${s.deadline_01_03 || "재난 종료일 필요"}</b></div>
      <div><span>② 신고 기한</span><b>지체 없이</b></div>
    </div>
    <p class="hint">${esc(s.deadline_note)}</p>`);

    if (v.errors.length) {
      parts.push(`<div class="panel error"><h3>먼저 고쳐야 할 것 (${v.errors.length})</h3>
        <ul>${v.errors.map((e) => `<li>${esc(e.message)} <button type="button" class="link" data-fix="${esc(e.field)}">고치러 가기</button></li>`).join("")}</ul></div>`);
    }

    const disabled = v.ok ? "" : "disabled";
    const notes = out.notes || {};
    const noteList = (id) => list((notes[id] || []).map(esc), "notes");
    parts.push(`<div class="panel"><h3>서식 받기 (HWPX)</h3>
      <p class="hint">서명 전 초안입니다. 한글(한컴오피스)에서 열어 확인하고, 빈칸은 직접 채운 뒤 서명해 주세요.</p>
      <div class="downloads">
        ${g.forms.map((f) => `<div class="dl">
          <button type="button" class="btn primary" data-download="${f.id}" ${disabled}>${esc(f.name)}</button>
          <small>${esc(f.when)} · ${esc(f.where)}${f.due ? ` · 참고 기한 <b>${esc(f.due)}</b>` : ""}</small>
          ${noteList(f.id)}
        </div>`).join("")}
        <div class="dl"><button type="button" class="btn" data-download="all" ${disabled}>3종 한 번에 (zip)</button></div>
      </div></div>`);

    if (v.warnings.length) {
      parts.push(`<div class="panel warn"><h3>확인할 것</h3>${list(v.warnings.map((w) => esc(w.message)))}</div>`);
    }
    if (v.infos.length) parts.push(`<div class="panel info">${list(v.infos.map((i) => esc(i.message)))}</div>`);

    parts.push(`<div class="panel"><h3>직접 하실 일</h3>${list(v.manual.map(esc))}</div>`);

    const unknown = Object.entries(v.unknown).filter(([, items]) => items.length);
    if (unknown.length) {
      parts.push(`<div class="panel"><h3>미확인 항목 (서식에서 빈칸)</h3>
        ${unknown.map(([form, items]) => `<p><b>${esc(form)}</b>: ${items.map(esc).join(", ")}</p>`).join("")}</div>`);
    }

    parts.push(`<div class="panel"><h3>서식별 제출 안내</h3><div class="table-wrap"><table>
      <thead><tr><th>서식</th><th>누가</th><th>언제</th><th>어디에</th><th>근거</th></tr></thead>
      <tbody>${g.forms.map((f) => `<tr><td>${esc(f.name)}<br><small>${esc(f.note)}</small></td><td>${esc(f.who)}</td><td>${esc(f.when)}</td><td>${esc(f.where)}</td><td>${esc(f.basis)}</td></tr>`).join("")}</tbody>
    </table></div></div>`);

    parts.push(`<div class="panel"><h3>① 3쪽 동의 5가지 (동의하는 항목에만 직접 서명)</h3><div class="table-wrap"><table>
      <thead><tr><th>동의</th><th>뜻</th><th>동의하지 않으면</th></tr></thead>
      <tbody>${g.consents.map((c) => `<tr><td>${esc(c.name)}</td><td>${esc(c.meaning)}</td><td>${esc(c.if_not)}</td></tr>`).join("")}</tbody>
    </table></div></div>`);

    parts.push(`<div class="panel"><h3>④ 피해조사 준비</h3><p>${esc(g.survey_note)}</p>${list(g.survey_prep.map(esc))}
      <h4>증빙 준비 상태</h4>
      <ul class="evidence">${g.evidence.map((e) => `<li class="${e.ready ? "ok" : "todo"}">${e.ready ? "준비됨" : "준비 필요"} · ${esc(e.label)}</li>`).join("")}</ul></div>`);

    const farm = data.farm || {};
    if (farm.share && farm.lat && farm.lng) {
      parts.push(`<div class="panel"><h3>피해 지도에 공유</h3>
        <p>위치·품종·폐사율·수온만 올라갑니다. 이름·주소·면허번호는 올라가지 않습니다.</p>
        <button type="button" class="btn" id="share-map" ${v.ok ? "" : "disabled"}>지도에 올리기</button> <a href="/map">지도 보기</a></div>`);
    }
    return parts.join("");
  }

  // ------------------------------------------------------------ 내려받기
  function fileNameFrom(header) {
    if (!header) return null;
    const star = /filename\*=UTF-8''([^;]+)/i.exec(header);
    if (star) return decodeURIComponent(star[1]);
    const plain = /filename="?([^";]+)"?/i.exec(header);
    return plain ? plain[1] : null;
  }

  async function download(formId, button) {
    if (button) button.disabled = true;
    try {
      const res = await post(`/api/forms/${formId}`);
      if (!res.ok) {
        const out = await res.json().catch(() => ({}));
        throw new Error(out.error || "서식을 만들지 못했습니다.");
      }
      const blob = await res.blob();
      const name = fileNameFrom(res.headers.get("Content-Disposition")) || `${formId}.hwpx`;
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = name;
      document.body.appendChild(a);
      a.click();
      a.remove();
      setTimeout(() => URL.revokeObjectURL(url), 3000);
      toast(`${name} 을(를) 내려받았습니다.`);
    } catch (err) {
      toast(err.message);
    } finally {
      if (button) button.disabled = false;
    }
  }

  async function shareMap() {
    try {
      const res = await post("/api/farms");
      const out = await res.json();
      if (!res.ok) throw new Error(out.error || "지도에 올리지 못했습니다.");
      toast("피해 지도에 올렸습니다.");
      window.location.href = `/map?focus=${encodeURIComponent(out.farm.id)}`;
    } catch (err) {
      toast(err.message);
    }
  }

  // ------------------------------------------------------------ 시작
  showStep(0);
  refreshUI();
})();
