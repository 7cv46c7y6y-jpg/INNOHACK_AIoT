/* 여러 화면에서 함께 쓰는 도구 */
window.AC = (() => {
  "use strict";

  const esc = (text) => String(text ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  const fmt = (n) => (n == null || Number.isNaN(Number(n)) ? "-" : Number(n).toLocaleString("ko-KR"));

  function toast(message, tone = "primary") {
    const el = document.getElementById("toast");
    if (!el || !window.bootstrap) { console.log(message); return; }
    el.className = `bs-toast toast fade bg-${tone}`;
    document.getElementById("toast-body").textContent = message;
    bootstrap.Toast.getOrCreateInstance(el).show();
  }

  // 폐사율 구간: 10% 미만 / 10~30% / 30% 이상
  const BAND_COLORS = { low: "#71dd37", mid: "#ffab00", high: "#ff3e1d" };
  const band = (rate) => (rate == null ? "low" : rate >= 30 ? "high" : rate >= 10 ? "mid" : "low");

  function tileLayer() {
    return L.tileLayer("https://tile.openstreetmap.org/{z}/{x}/{y}.png", {
      maxZoom: 18, attribution: "&copy; OpenStreetMap contributors",
    });
  }

  function farmMarker(f) {
    const isSeed = f.source === "가상 데이터";
    return L.circleMarker([f.lat, f.lng], {
      radius: 10,
      color: isSeed ? "#8592a3" : "#233446",
      weight: isSeed ? 2 : 3,
      dashArray: isSeed ? "3 3" : null,
      fillColor: BAND_COLORS[band(f.damage_rate)],
      fillOpacity: 0.85,
    }).bindPopup(`
      <b>${esc(f.species || "품종 미입력")}</b><br>
      폐사율 <b>${f.damage_rate != null ? Number(f.damage_rate).toFixed(2) + "%" : "-"}</b><br>
      수온 ${f.water_temp_c != null ? esc(f.water_temp_c) + "℃" : "미입력"}${f.measured_at ? ` (${esc(f.measured_at)})` : ""}<br>
      기록일 ${esc(f.recorded_on || "-")}<br>
      <small class="text-muted">${esc(f.source)} · 어가 자체 입력·미확인</small>`);
  }

  function summarize(farms) {
    const counts = { low: 0, mid: 0, high: 0 };
    farms.forEach((f) => { counts[band(f.damage_rate)] += 1; });
    const temps = farms.map((f) => f.water_temp_c).filter((t) => t != null);
    const avg = temps.length ? temps.reduce((a, b) => a + b, 0) / temps.length : null;
    return { total: farms.length, counts, avgTemp: avg, tempCount: temps.length };
  }

  return { esc, fmt, toast, band, BAND_COLORS, tileLayer, farmMarker, summarize };
})();
