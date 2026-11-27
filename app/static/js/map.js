/* 가두리 피해 지도 */
(() => {
  "use strict";
  const { tileLayer, farmMarker, summarize } = window.AC;

  const map = L.map("farm-map").setView([34.76, 128.40], 10);
  tileLayer().addTo(map);
  const focus = new URLSearchParams(window.location.search).get("focus");

  fetch("/api/farms")
    .then((res) => res.json())
    .then(({ farms }) => {
      let focused = null;
      const markers = farms.map((f) => {
        const m = farmMarker(f).addTo(map);
        if (focus && f.id === focus) focused = m;
        return m;
      });
      if (focused) {
        map.setView(focused.getLatLng(), 12);
        focused.openPopup();
      } else if (markers.length) {
        map.fitBounds(L.featureGroup(markers).getBounds().pad(0.2));
      }
      const s = summarize(farms);
      document.getElementById("map-summary").innerHTML = `
        <p class="mb-2">표시된 가두리 <b>${s.total}</b>곳</p>
        <p class="mb-2">폐사율 30% 이상 <b>${s.counts.high}</b>곳<br>10~30% <b>${s.counts.mid}</b>곳<br>10% 미만 <b>${s.counts.low}</b>곳</p>
        <p class="mb-0">입력된 수온 평균 <b>${s.avgTemp != null ? s.avgTemp.toFixed(1) + "℃" : "-"}</b> (${s.tempCount}곳)</p>`;
    })
    .catch(() => { document.getElementById("map-summary").textContent = "지도 데이터를 불러오지 못했습니다."; });
})();
