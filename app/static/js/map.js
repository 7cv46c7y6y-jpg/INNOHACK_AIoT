/* 가두리 피해 지도: 폐사율 구간별 색, 수온, 어가 자체 입력 표시 */
(() => {
  "use strict";

  const COLORS = { low: "#2e9e6b", mid: "#e0a100", high: "#d64545" };
  const band = (rate) => (rate == null ? "low" : rate >= 30 ? "high" : rate >= 10 ? "mid" : "low");
  const esc = (t) => String(t ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));

  const map = L.map("farm-map").setView([34.76, 128.40], 10);
  L.tileLayer("https://tile.openstreetmap.org/{z}/{x}/{y}.png", {
    maxZoom: 18, attribution: "&copy; OpenStreetMap contributors",
  }).addTo(map);

  const focus = new URLSearchParams(window.location.search).get("focus");

  fetch("/api/farms")
    .then((res) => res.json())
    .then(({ farms }) => {
      const markers = [];
      let focused = null;
      farms.forEach((f) => {
        const isSeed = f.source === "가상 데이터";
        const marker = L.circleMarker([f.lat, f.lng], {
          radius: 11,
          color: isSeed ? "#8a94a6" : "#0b2545",
          weight: isSeed ? 2 : 3,
          dashArray: isSeed ? "3 3" : null,
          fillColor: COLORS[band(f.damage_rate)],
          fillOpacity: 0.85,
        }).bindPopup(`
          <b>${esc(f.species || "품종 미입력")}</b><br>
          폐사율 <b>${f.damage_rate != null ? Number(f.damage_rate).toFixed(2) + "%" : "-"}</b><br>
          수온 ${f.water_temp_c != null ? esc(f.water_temp_c) + "℃" : "미입력"}${f.measured_at ? ` (${esc(f.measured_at)})` : ""}<br>
          기록일 ${esc(f.recorded_on || "-")}<br>
          <small>${esc(f.source)} · 어가 자체 입력·미확인</small>`);
        marker.addTo(map);
        markers.push(marker);
        if (focus && f.id === focus) focused = marker;
      });
      if (focused) {
        map.setView(focused.getLatLng(), 12);
        focused.openPopup();
      } else if (markers.length) {
        map.fitBounds(L.featureGroup(markers).getBounds().pad(0.2));
      }

      const counts = { low: 0, mid: 0, high: 0 };
      const temps = farms.map((f) => f.water_temp_c).filter((t) => t != null);
      farms.forEach((f) => { counts[band(f.damage_rate)] += 1; });
      const avg = temps.length ? (temps.reduce((a, b) => a + b, 0) / temps.length).toFixed(1) : null;
      document.getElementById("map-summary").innerHTML = `
        <p>표시된 가두리 <b>${farms.length}</b>곳</p>
        <p>폐사율 30% 이상 <b>${counts.high}</b>곳, 10~30% <b>${counts.mid}</b>곳, 10% 미만 <b>${counts.low}</b>곳</p>
        <p>입력된 수온 평균 <b>${avg != null ? avg + "℃" : "-"}</b> (${temps.length}곳)</p>`;
    })
    .catch(() => {
      document.getElementById("map-summary").textContent = "지도 데이터를 불러오지 못했습니다.";
    });
})();
