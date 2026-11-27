/* 홈: 가두리 피해 현황 숫자 (지도는 피해 지도 화면에만 둔다) */
(() => {
  "use strict";
  const { summarize } = window.AC;

  fetch("/api/farms")
    .then((res) => res.json())
    .then(({ farms }) => {
      const s = summarize(farms);
      document.getElementById("stat-total").textContent = `${s.total}곳`;
      document.getElementById("stat-high").textContent = `${s.counts.high}곳`;
      document.getElementById("stat-mid").textContent = `${s.counts.mid}곳`;
      document.getElementById("stat-temp").textContent = s.avgTemp != null ? `${s.avgTemp.toFixed(1)}℃` : "-";
    })
    .catch(() => { document.getElementById("stat-total").textContent = "불러오지 못함"; });
})();
