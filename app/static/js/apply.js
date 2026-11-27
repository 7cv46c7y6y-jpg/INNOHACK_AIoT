/* 피해보상 서류 작성 (한 페이지): 입력 모으기, 실시간 계산, 증빙 첨부, 검토, 내려받기 */
(() => {
  "use strict";
  const { esc, fmt, toast } = window.AC;
  const LIMITS = window.AC_LIMITS || { maxBytes: 20 * 1024 * 1024, maxFiles: 30, accept: "" };
  const ALLOWED = new Set(LIMITS.accept.split(",").filter(Boolean));
  const form = document.getElementById("case-form");

  // 오류 위치(field) → 카드
  const FIELD_SECTION = [
    [/^disaster\./, "sec-disaster"], [/^(victim|reporter|license)\./, "sec-farm"], [/^relation/, "sec-farm"],
    [/^(stocking|outs|feed|rows|seed_source|sale|pre_disaster_reported)/, "sec-records"],
    [/^damage/, "sec-damage"], [/^form01\./, "sec-extra"], [/^evidence/, "sec-evidence"],
  ];

  // ------------------------------------------------------------ 경로 도구
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
  const getPath = (obj, path) => path.split(".").reduce((o, k) => (o == null ? undefined : o[isIndex(k) ? Number(k) : k]), obj);

  // ------------------------------------------------------------ 반복 줄
  const rowsBox = (name) => form.querySelector(`[data-rows="${name}"]`);

  function addRow(name, values) {
    const box = rowsBox(name);
    const max = Number(box.dataset.max || 99);
    if (box.querySelectorAll("[data-row]").length >= max) { toast(`서식에는 ${max}줄까지만 들어갑니다.`, "warning"); return null; }
    const node = document.getElementById(box.dataset.template).content.firstElementChild.cloneNode(true);
    if (values) {
      node.querySelectorAll("[data-field]").forEach((el) => {
        const v = values[el.dataset.field];
        if (v != null) el.value = v;
      });
    }
    box.appendChild(node);
    return node;
  }

  function updateAddButtons() {
    form.querySelectorAll("[data-add]").forEach((btn) => {
      const box = rowsBox(btn.dataset.add);
      btn.disabled = box.querySelectorAll("[data-row]").length >= Number(box.dataset.max || 99);
    });
  }

  // ------------------------------------------------------------ 증빙 파일 (브라우저에만 보관, 묶음 받을 때만 전송)
  const files = {};   // 항목 키 → File[]

  const totalFiles = () => Object.values(files).reduce((n, list) => n + list.length, 0);
  const totalBytes = () => Object.values(files).reduce((n, list) => n + list.reduce((s, f) => s + f.size, 0), 0);
  function size(bytes) {
    if (bytes >= 1048576) { const v = bytes / 1048576; return `${Number.isInteger(v) ? v : v.toFixed(1)}MB`; }
    return `${bytes ? Math.max(1, Math.round(bytes / 1024)) : 0}KB`;
  }
  const extOf = (name) => { const i = name.lastIndexOf("."); return i >= 0 ? name.slice(i).toLowerCase() : ""; };

  function addFiles(key, fileList) {
    files[key] = files[key] || [];
    for (const f of fileList) {
      if (!ALLOWED.has(extOf(f.name))) { toast(`'${f.name}'은(는) 첨부할 수 없는 형식입니다.`, "danger"); continue; }
      if (totalFiles() + 1 > LIMITS.maxFiles) { toast(`증빙 파일은 ${LIMITS.maxFiles}개까지 첨부할 수 있습니다.`, "danger"); break; }
      if (totalBytes() + f.size > LIMITS.maxBytes) { toast(`증빙 파일은 합계 ${size(LIMITS.maxBytes)}까지 첨부할 수 있습니다.`, "danger"); break; }
      files[key].push(f);
    }
    renderEvidence();
  }

  function renderEvidence() {
    document.querySelectorAll("[data-evidence]").forEach((item) => {
      const key = item.dataset.evidence;
      const list = files[key] || [];
      const paper = item.querySelector(`[data-path="evidence.${key}"]`).checked;
      const badge = item.querySelector("[data-evidence-badge]");
      if (list.length) { badge.className = "badge bg-label-success"; badge.textContent = `첨부 ${list.length}개`; }
      else if (paper) { badge.className = "badge bg-label-info"; badge.textContent = "종이로 보유"; }
      else { badge.className = "badge bg-label-secondary"; badge.textContent = "준비 필요"; }
      item.querySelector("[data-evidence-list]").innerHTML = list.map((f, i) =>
        `<li><i class="bx bx-paperclip"></i> ${esc(f.name)} <span class="text-muted">(${size(f.size)})</span>
          <button type="button" class="btn btn-link btn-sm p-0 ms-1 text-danger" data-remove-file="${key}" data-index="${i}">삭제</button></li>`).join("");
    });
    const count = totalFiles();
    document.getElementById("evidence-size").textContent = `첨부 ${count}개 · ${size(totalBytes())} / ${size(LIMITS.maxBytes)}`;
    document.getElementById("sum-files").textContent = `${count}개`;
  }

  document.addEventListener("change", (e) => {
    const input = e.target.closest("[data-evidence-files]");
    if (!input) return;
    addFiles(input.dataset.evidenceFiles, input.files);
    input.value = "";   // 같은 파일을 다시 고를 수 있게
  });

  // 끌어다 놓기: 항목 칸에 놓으면 그 항목에 붙고, 다른 곳에 놓으면 브라우저가 파일을 열지 않게 막는다
  const hasFiles = (e) => [...(e.dataTransfer?.types || [])].includes("Files");
  document.addEventListener("dragover", (e) => {
    if (!hasFiles(e)) return;
    e.preventDefault();
    const zone = e.target.closest("[data-evidence]");
    e.dataTransfer.dropEffect = zone ? "copy" : "none";
    document.querySelectorAll("[data-evidence].dragover").forEach((el) => { if (el !== zone) el.classList.remove("dragover"); });
    if (zone) zone.classList.add("dragover");
  });
  document.addEventListener("dragleave", (e) => {
    const zone = e.target.closest("[data-evidence]");
    if (zone && !zone.contains(e.relatedTarget)) zone.classList.remove("dragover");
  });
  document.addEventListener("drop", (e) => {
    if (!hasFiles(e)) return;
    e.preventDefault();
    document.querySelectorAll("[data-evidence].dragover").forEach((el) => el.classList.remove("dragover"));
    const zone = e.target.closest("[data-evidence]");
    if (zone) addFiles(zone.dataset.evidence, e.dataTransfer.files);
  });

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
    Object.entries(files).forEach(([key, list]) => { if (list.length) setPath(data, `evidence.${key}`, true); });
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
      if (el.type === "checkbox") { el.checked = el.id === "reporter-same" ? v !== false : !!v; return; }
      el.value = v ?? "";
    });
    (data.stocking || []).forEach((r) => addRow("stocking", r));
    (data.outs || []).forEach((r) => addRow("outs", r));
    (data.feed || []).forEach((r) => addRow("feed", r));
    const v = data.victim || {};
    const sub = (data.form01 || {}).mobile_subscriber || {};
    document.getElementById("sub-same").checked = !!v.name && sub.name === v.name;
    refreshUI();
  }

  // ------------------------------------------------------------ 화면 상태와 실시간 계산
  function refreshUI() {
    const data = serialize();
    document.getElementById("reporter-box").hidden = !!data.reporter_same;
    document.getElementById("sub-box").hidden = document.getElementById("sub-same").checked;
    form.querySelectorAll("[data-show-if]").forEach((el) => {
      const [path, value] = el.dataset.showIf.split("=");
      el.hidden = getPath(data, path) !== value;
    });
    document.getElementById("pre-report-warn").hidden = data.pre_disaster_reported === "예";
    live(data);
    updateAddButtons();
    renderEvidence();
  }

  function live(data) {
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
    document.getElementById("sum-stock").textContent = stock != null ? `${fmt(stock)}마리` : "-";
    document.getElementById("sum-dead").textContent = dead ? `${fmt(dead)}마리` : "-";
    document.getElementById("sum-rate").textContent = rate != null ? `${rate.toFixed(2)}%` : "-";
  }

  form.addEventListener("input", refreshUI);
  form.addEventListener("change", (e) => { if (!e.target.closest("[data-evidence-files]")) refreshUI(); });

  // 사람이 직접 입력했는지 (뒤로가기 전에 한 번 묻기 위해)
  let edited = false;
  form.addEventListener("input", () => { edited = true; });
  form.addEventListener("change", () => { edited = true; });

  // ------------------------------------------------------------ 버튼
  async function loadDemo() {
    const res = await fetch("/api/demo");
    fill(await res.json());
    toast("시연 데이터(통영 가상 어가)를 채웠습니다.");
  }

  function clearAll() {
    fill({});
    Object.keys(files).forEach((k) => { files[k] = []; });
    renderEvidence();
    document.getElementById("review").innerHTML = "";
    document.getElementById("sec-review").hidden = true;
    edited = false;
    toast("입력을 모두 지웠습니다.", "secondary");
  }

  function goField(field) {
    const hit = FIELD_SECTION.find(([re]) => re.test(field || ""));
    const el = form.querySelector(`[data-path="${field}"]`);
    const target = el || document.getElementById(hit ? hit[1] : "sec-disaster");
    target.scrollIntoView({ behavior: "smooth", block: "center" });
    if (el) {
      setTimeout(() => { el.focus({ preventScroll: true }); el.classList.add("flash"); setTimeout(() => el.classList.remove("flash"), 1600); }, 400);
    }
  }

  document.addEventListener("click", (e) => {
    const back = e.target.closest("[data-back]");
    if (back) {
      e.preventDefault();
      if ((edited || totalFiles()) && !window.confirm("입력한 내용과 첨부한 파일은 저장되지 않습니다. 뒤로 갈까요?")) return;
      // 이 사이트 안에서 왔으면 이전 화면으로, 주소를 직접 열었으면 홈으로
      let sameSite = false;
      try { sameSite = !!document.referrer && new URL(document.referrer).origin === window.location.origin; } catch (err) { sameSite = false; }
      if (sameSite && window.history.length > 1) window.history.back();
      else window.location.href = back.href;
      return;
    }
    const action = e.target.closest("[data-action]");
    if (action) {
      const name = action.dataset.action;
      if (name === "demo") loadDemo();
      if (name === "clear") clearAll();
      if (name === "review") runReview();
    }
    const add = e.target.closest("[data-add]");
    if (add) { addRow(add.dataset.add); refreshUI(); }
    const del = e.target.closest(".row-del");
    if (del) { del.closest("[data-row]").remove(); refreshUI(); }
    const pick = e.target.closest("[data-pick]");
    if (pick) document.querySelector(`[data-evidence-files="${pick.dataset.pick}"]`).click();
    const rm = e.target.closest("[data-remove-file]");
    if (rm) { files[rm.dataset.removeFile].splice(Number(rm.dataset.index), 1); renderEvidence(); }
    const fix = e.target.closest("[data-fix]");
    if (fix) goField(fix.dataset.fix);
    const dl = e.target.closest("[data-download]");
    if (dl) download(dl.dataset.download, dl);
    if (e.target.closest("[data-bundle]")) downloadBundle(e.target.closest("[data-bundle]"));
  });

  // 바로 가기: 보고 있는 카드 표시
  const navLinks = [...document.querySelectorAll("#section-nav a")];
  if ("IntersectionObserver" in window && navLinks.length) {
    const observer = new IntersectionObserver((entries) => {
      entries.forEach((entry) => {
        if (!entry.isIntersecting) return;
        navLinks.forEach((a) => a.classList.toggle("active", a.getAttribute("href") === `#${entry.target.id}`));
      });
    }, { rootMargin: "-40% 0px -55% 0px" });
    document.querySelectorAll("#case-form > .card[id]").forEach((card) => observer.observe(card));
  }

  // ------------------------------------------------------------ 검토
  const postJson = (url) => fetch(url, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(serialize()) });

  async function runReview() {
    const card = document.getElementById("sec-review");
    const box = document.getElementById("review");
    card.hidden = false;
    box.innerHTML = '<div class="d-flex align-items-center gap-2 text-muted"><div class="spinner-border spinner-border-sm"></div> 검토 중입니다…</div>';
    card.scrollIntoView({ behavior: "smooth", block: "start" });
    try {
      const res = await postJson("/api/review");
      const out = await res.json();
      if (!res.ok) throw new Error(out.error || "검토하지 못했습니다.");
      box.innerHTML = renderReview(out);
    } catch (err) {
      box.innerHTML = `<div class="alert alert-danger mb-0">${esc(err.message)}</div>`;
    }
    // 결과가 다 그려진 뒤 다시 맞춘다 (처음에는 페이지 끝이라 카드 위쪽까지 올라가지 못함)
    card.scrollIntoView({ behavior: "smooth", block: "start" });
  }

  const list = (items) => (items && items.length ? `<ul class="mb-0 ps-3">${items.map((i) => `<li>${i}</li>`).join("")}</ul>` : "");

  function renderReview(out) {
    const s = out.summary;
    const v = out.validation;
    const g = out.guidance;
    const notes = out.notes || {};
    const parts = [];
    const stat = (label, value, tone) => `
      <div class="col-6 col-md">
        <div class="border rounded p-3 h-100">
          <div class="small text-muted">${label}</div>
          <div class="fs-5 fw-semibold text-${tone}">${value}</div>
        </div>
      </div>`;
    parts.push(`<div class="row g-3 mb-3">
      ${stat("재해 직전 사육량", s.stock_before != null ? fmt(s.stock_before) + "마리" : "-", "body")}
      ${stat("이번 피해량", s.dead_count != null ? fmt(s.dead_count) + "마리" : "-", "body")}
      ${stat("피해율 (참고값)", s.damage_rate != null ? s.damage_rate.toFixed(2) + "%" : "-", "primary")}
      ${stat("자연재난 피해신고서 기한", s.deadline_01_03 || "재난 종료일 필요", "danger")}
      ${stat("어업피해발생신고서 기한", "지체 없이", "danger")}
    </div><p class="small text-muted">${esc(s.deadline_note)}</p>`);

    if (v.errors.length) {
      parts.push(`<div class="alert alert-danger"><h6 class="alert-heading mb-2">먼저 고쳐야 할 것 (${v.errors.length})</h6>
        <ul class="mb-0 ps-3">${v.errors.map((e) => `<li>${esc(e.message)} <button type="button" class="btn btn-link btn-sm p-0 align-baseline" data-fix="${esc(e.field)}">고치러 가기</button></li>`).join("")}</ul></div>`);
    }

    const disabled = v.ok ? "" : "disabled";
    const over = totalBytes() > LIMITS.maxBytes;
    parts.push(`<div class="card shadow-none border mb-3"><div class="card-body">
      <h6>서식 받기</h6>
      <p class="small text-muted">서명 전 초안입니다. 한글(한컴오피스)에서 열어 확인하고, 빈칸을 채운 뒤 서명해 주세요.</p>
      <button type="button" class="btn btn-primary btn-lg mb-3" data-bundle ${disabled || (over ? "disabled" : "")}>
        <i class="bx bx-package me-1"></i> 제출 묶음 받기 (서식 3종 + 증빙 ${totalFiles()}개 + 제출목록)
      </button>
      <div class="list-group">
        ${g.forms.map((f) => `<div class="list-group-item d-flex justify-content-between align-items-start flex-wrap gap-2">
          <div><div class="fw-semibold">${esc(f.name)}</div>
            <small class="text-muted">${esc(f.when)} · ${esc(f.where)}${f.due ? ` · 참고 기한 <b>${esc(f.due)}</b>` : ""}</small></div>
          <button type="button" class="btn btn-sm btn-outline-primary" data-download="${f.id}" ${disabled}><i class="bx bx-download"></i> 이 서식만</button>
        </div>`).join("")}
      </div>
    </div></div>`);

    // 꼭 필요한 것만 빨간 상자에: 제출 전에 확인할 것(경고·칸 넘침) / 직접 하셔야 할 일(직접 적기·서명·빈칸)
    const formName = Object.fromEntries(g.forms.map((f) => [f.id, f.name]));
    const checks = [
      ...v.warnings.map((w) => esc(w.message)),
      ...Object.entries(notes).flatMap(([id, items]) => items.map((n) => `<b>${esc(formName[id] || id)}</b>: ${esc(n)}`)),
    ];
    const blanks = Object.entries(v.unknown).filter(([, items]) => items.length)
      .map(([form, items]) => `<b>${esc(form)}</b>: ${items.map(esc).join(", ")}`);
    const todo = v.manual.map(esc);
    if (blanks.length) todo.push(`서식에 채우지 못한 곳(빈칸 또는 '미확인')은 내려받은 뒤 직접 채워 주세요.${list(blanks)}`);
    parts.push(`<div class="alert alert-danger review-must mb-0" role="alert">
      ${checks.length ? `<h6 class="alert-heading"><i class="bx bx-error-circle me-1"></i>제출 전에 꼭 확인하세요</h6>${list(checks)}<hr>` : ""}
      <h6 class="alert-heading"><i class="bx bx-edit me-1"></i>직접 하셔야 할 일</h6>${list(todo)}
    </div>`);

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

  async function save(res, fallback) {
    if (!res.ok) {
      const out = await res.json().catch(() => ({}));
      throw new Error(out.error || "파일을 만들지 못했습니다.");
    }
    const blob = await res.blob();
    const name = fileNameFrom(res.headers.get("Content-Disposition")) || fallback;
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = name;
    document.body.appendChild(a);
    a.click();
    a.remove();
    setTimeout(() => URL.revokeObjectURL(url), 3000);
    toast(`${name} 을(를) 내려받았습니다.`, "success");
  }

  async function download(formId, button) {
    button.disabled = true;
    try { await save(await postJson(`/api/forms/${formId}`), `${formId}.hwpx`); }
    catch (err) { toast(err.message, "danger"); }
    finally { button.disabled = false; }
  }

  async function downloadBundle(button) {
    button.disabled = true;
    const original = button.innerHTML;
    button.innerHTML = '<span class="spinner-border spinner-border-sm me-1"></span> 묶는 중…';
    try {
      const body = new FormData();
      body.append("case", JSON.stringify(serialize()));
      Object.entries(files).forEach(([key, list]) => list.forEach((f) => body.append(`evidence.${key}`, f, f.name)));
      await save(await fetch("/api/bundle", { method: "POST", body }), "제출묶음.zip");
    } catch (err) {
      toast(err.message, "danger");
    } finally {
      button.disabled = false;
      button.innerHTML = original;
    }
  }

  // ------------------------------------------------------------ 시작
  refreshUI();
  if (new URLSearchParams(window.location.search).get("demo")) loadDemo();
})();
