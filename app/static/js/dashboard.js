/* 대시보드: 피해 현황 숫자와 지도 미리보기 */
(() => {
  "use strict";
  const { tileLayer, farmMarker, summarize } = window.AC;

  const map = L.map("mini-map", { scrollWheelZoom: false }).setView([34.76, 128.40], 10);
  tileLayer().addTo(map);

  fetch("/api/farms")
    .then((res) => res.json())
    .then(({ farms }) => {
      const markers = farms.map((f) => farmMarker(f).addTo(map));
      if (markers.length) map.fitBounds(L.featureGroup(markers).getBounds().pad(0.2));
      const s = summarize(farms);
      document.getElementById("stat-total").textContent = `${s.total}곳`;
      document.getElementById("stat-high").textContent = `${s.counts.high}곳`;
      document.getElementById("stat-mid").textContent = `${s.counts.mid}곳`;
      document.getElementById("stat-temp").textContent = s.avgTemp != null ? `${s.avgTemp.toFixed(1)}℃` : "-";
    })
    .catch(() => { document.getElementById("stat-total").textContent = "불러오지 못함"; });
})();
