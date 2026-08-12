const REFRESH_MS = 4000;

const fmtZAR = (n) =>
  "R" + Number(n).toLocaleString("en-ZA", { minimumFractionDigits: 2, maximumFractionDigits: 2 });

const fmtTime = (iso) =>
  new Date(iso).toLocaleTimeString("en-ZA", { hour: "2-digit", minute: "2-digit", second: "2-digit" });

const escapeHTML = (value) =>
  String(value ?? "").replace(/[&<>"']/g, (char) => ({
    "&": "&amp;",
    "<": "&lt;",
    ">": "&gt;",
    '"': "&quot;",
    "'": "&#39;",
  })[char]);

const chartColors = {
  text: "#93a4bb",
  grid: "rgba(148, 163, 184, 0.12)",
  gold: "#d4a24e",
  goldBright: "#f4c86d",
  teal: "#2dd4bf",
  green: "#22c55e",
  orange: "#f97316",
  red: "#ef4444",
  blue: "#60a5fa",
};

function scoreClass(score) {
  const value = Number(score || 0);
  if (value >= 75) return "score-high";
  if (value >= 50) return "score-medium";
  return "score-low";
}

function statusClass(row) {
  const score = Number(row.fraud_score || 0);
  if (row.is_flagged || score >= 50) return "status-flagged";
  if (score >= 30) return "status-review";
  return "status-clear";
}

function statusLabel(row) {
  const score = Number(row.fraud_score || 0);
  if (row.is_flagged || score >= 50) return "Flagged";
  if (score >= 30) return "Review";
  return "Clear";
}

async function fetchJSON(url) {
  const res = await fetch(url);
  if (!res.ok) throw new Error(`${url} -> ${res.status}`);
  return res.json();
}

function setStatus(online) {
  const status = document.getElementById("status");
  const label = document.querySelector(".status-label");
  if (!status || !label) return;

  status.classList.toggle("is-live", online);
  status.classList.toggle("is-offline", !online);
  label.textContent = online ? "Streaming" : "Disconnected";
}

function setWaitingStatus() {
  const status = document.getElementById("status");
  const label = document.querySelector(".status-label");
  if (!status || !label) return;

  status.classList.remove("is-offline");
  status.classList.add("is-live");
  label.textContent = "Connected";
}

function setChartState(canvasId, hasData) {
  const canvas = document.getElementById(canvasId);
  const frame = canvas?.closest(".chart-frame");
  if (!frame) return;
  frame.classList.toggle("has-data", hasData);
}

function buildCityRows(transactions) {
  const grouped = new Map();
  transactions.forEach((txn) => {
    const city = txn.city || "Unknown";
    const current = grouped.get(city) || { city, total: 0, flagged: 0 };
    current.total += 1;
    if (txn.is_flagged || Number(txn.fraud_score || 0) >= 50) current.flagged += 1;
    grouped.set(city, current);
  });

  return [...grouped.values()].sort((a, b) => b.total - a.total);
}

function buildCategoryRows(transactions) {
  const grouped = new Map();
  transactions.forEach((txn) => {
    if (!(txn.is_flagged || Number(txn.fraud_score || 0) >= 50)) return;
    const category = txn.merchant_category || "Unknown";
    const current = grouped.get(category) || { category, flagged: 0 };
    current.flagged += 1;
    grouped.set(category, current);
  });

  return [...grouped.values()].sort((a, b) => b.flagged - a.flagged);
}

function renderSummary(data) {
  document.getElementById("kpi-total").textContent = Number(data.total_transactions || 0).toLocaleString();
  document.getElementById("kpi-volume").textContent = `${fmtZAR(data.total_amount || 0)} total volume`;
  document.getElementById("kpi-flagged").textContent = Number(data.flagged_count || 0).toLocaleString();
  document.getElementById("kpi-alert-sub").textContent =
    `${Number(data.flagged_count || 0).toLocaleString()} flagged transactions`;
  document.getElementById("kpi-fraud-rate").textContent = `${data.fraud_rate ?? 0}%`;
  document.getElementById("kpi-score").textContent = data.avg_fraud_score ?? 0;
}

function renderLedger(rows) {
  const body = document.getElementById("ledger-body");
  if (!rows.length) {
    body.innerHTML = `<tr><td colspan="8" class="empty-row">Waiting for transactions...</td></tr>`;
    return;
  }

  body.innerHTML = rows
    .map((r) => {
      const score = Number(r.fraud_score || 0);
      return `
      <tr>
        <td class="mono">${fmtTime(r.timestamp)}</td>
        <td>${escapeHTML(r.account_holder)}</td>
        <td class="amount-cell">${fmtZAR(r.amount)}</td>
        <td>${escapeHTML(r.merchant_name)}</td>
        <td>${escapeHTML(r.merchant_category)}</td>
        <td>${escapeHTML(r.city)}</td>
        <td><span class="score-pill ${scoreClass(score)}">${score}</span></td>
        <td><span class="status-pill ${statusClass(r)}">${statusLabel(r)}</span></td>
      </tr>`;
    })
    .join("");
}

function renderAlerts(rows) {
  const list = document.getElementById("alerts-list");
  if (!rows.length) {
    list.innerHTML = `<p class="empty-row">No alerts yet.</p>`;
    return;
  }

  list.innerHTML = rows
    .map((a) => {
      const severity = String(a.severity || "medium").toLowerCase();
      const reason = String(a.reasons || "No reason supplied").split(" | ")[0];
      return `
      <article class="alert-card ${escapeHTML(severity)}">
        <div class="alert-top">
          <div class="alert-title">
            <strong>${escapeHTML(a.account_holder)}</strong>
            <span>${escapeHTML(a.merchant_name)} | ${escapeHTML(a.city)}</span>
          </div>
          <span class="severity-pill ${escapeHTML(severity)}">${escapeHTML(severity)}</span>
        </div>
        <div class="alert-meta">
          <span>${fmtTime(a.created_at)}</span>
          <span>${fmtZAR(a.amount)}</span>
          <span>Score ${Number(a.fraud_score || 0)}</span>
        </div>
        <p class="alert-reason">${escapeHTML(reason)}</p>
      </article>`;
    })
    .join("");
}

function baseChartOptions(extra = {}) {
  return {
    responsive: true,
    maintainAspectRatio: false,
    animation: { duration: 350 },
    plugins: {
      legend: {
        labels: {
          color: chartColors.text,
          boxWidth: 10,
          boxHeight: 10,
          font: { size: 11, weight: "600" },
        },
      },
      tooltip: {
        backgroundColor: "#0b1220",
        borderColor: "rgba(148, 163, 184, 0.22)",
        borderWidth: 1,
        titleColor: "#eef2f8",
        bodyColor: "#cbd5e1",
      },
    },
    scales: {
      x: {
        ticks: { color: chartColors.text, font: { size: 10 } },
        grid: { display: false },
      },
      y: {
        beginAtZero: true,
        ticks: { color: chartColors.text, precision: 0 },
        grid: { color: chartColors.grid },
      },
    },
    ...extra,
  };
}

let cityChart;
let categoryChart;
let scoreChart;
let activityChart;

function renderCityChart(rows) {
  setChartState("chart-city", rows.length > 0 && typeof Chart !== "undefined");
  if (!rows.length || typeof Chart === "undefined") return;

  const labels = rows.map((r) => r.city);
  const totals = rows.map((r) => Number(r.total || 0));
  const flagged = rows.map((r) => Number(r.flagged || 0));
  const ctx = document.getElementById("chart-city");

  if (!cityChart) {
    cityChart = new Chart(ctx, {
      type: "bar",
      data: {
        labels,
        datasets: [
          { label: "Total", data: totals, backgroundColor: chartColors.teal, borderRadius: 5 },
          { label: "Flagged", data: flagged, backgroundColor: chartColors.red, borderRadius: 5 },
        ],
      },
      options: baseChartOptions(),
    });
    return;
  }

  cityChart.data.labels = labels;
  cityChart.data.datasets[0].data = totals;
  cityChart.data.datasets[1].data = flagged;
  cityChart.update();
}

function renderCategoryChart(rows) {
  setChartState("chart-category", rows.length > 0 && typeof Chart !== "undefined");
  if (!rows.length || typeof Chart === "undefined") return;

  const labels = rows.map((r) => r.category);
  const flagged = rows.map((r) => Number(r.flagged || 0));
  const ctx = document.getElementById("chart-category");

  if (!categoryChart) {
    categoryChart = new Chart(ctx, {
      type: "bar",
      data: {
        labels,
        datasets: [
          { label: "Flagged", data: flagged, backgroundColor: chartColors.red, borderRadius: 5 },
        ],
      },
      options: baseChartOptions({
        indexAxis: "y",
        scales: {
          x: {
            beginAtZero: true,
            ticks: { color: chartColors.text, precision: 0 },
            grid: { color: chartColors.grid },
          },
          y: {
            ticks: { color: chartColors.text, font: { size: 10 } },
            grid: { display: false },
          },
        },
      }),
    });
    return;
  }

  categoryChart.data.labels = labels;
  categoryChart.data.datasets[0].data = flagged;
  categoryChart.update();
}

function renderScoreChart(rows) {
  setChartState("chart-score", rows.length > 0 && typeof Chart !== "undefined");
  if (!rows.length || typeof Chart === "undefined") return;

  const buckets = [
    { label: "0-24", min: 0, max: 24, count: 0 },
    { label: "25-49", min: 25, max: 49, count: 0 },
    { label: "50-74", min: 50, max: 74, count: 0 },
    { label: "75-100", min: 75, max: 100, count: 0 },
  ];

  rows.forEach((row) => {
    const score = Number(row.fraud_score || 0);
    const bucket = buckets.find((b) => score >= b.min && score <= b.max);
    if (bucket) bucket.count += 1;
  });

  const ctx = document.getElementById("chart-score");
  const data = buckets.map((b) => b.count);

  if (!scoreChart) {
    scoreChart = new Chart(ctx, {
      type: "bar",
      data: {
        labels: buckets.map((b) => b.label),
        datasets: [{
          label: "Recent transactions",
          data,
          backgroundColor: [chartColors.green, chartColors.gold, chartColors.orange, chartColors.red],
          borderRadius: 5,
        }],
      },
      options: baseChartOptions(),
    });
    return;
  }

  scoreChart.data.datasets[0].data = data;
  scoreChart.update();
}

function renderActivityChart(summary) {
  const flagged = Number(summary.flagged_count || 0);
  const legitimate = Math.max(Number(summary.total_transactions || 0) - flagged, 0);
  setChartState("chart-activity", legitimate + flagged > 0 && typeof Chart !== "undefined");
  if (legitimate + flagged === 0 || typeof Chart === "undefined") return;

  const ctx = document.getElementById("chart-activity");

  if (!activityChart) {
    activityChart = new Chart(ctx, {
      type: "doughnut",
      data: {
        labels: ["Legitimate", "Flagged"],
        datasets: [{
          data: [legitimate, flagged],
          backgroundColor: [chartColors.teal, chartColors.red],
          borderColor: "#101827",
          borderWidth: 3,
        }],
      },
      options: baseChartOptions({
        cutout: "68%",
        scales: {},
      }),
    });
    return;
  }

  activityChart.data.datasets[0].data = [legitimate, flagged];
  activityChart.update();
}

async function refresh() {
  try {
    const [summary, recent, alerts] = await Promise.all([
      fetchJSON("/api/summary"),
      fetchJSON("/api/recent"),
      fetchJSON("/api/alerts"),
    ]);

    renderSummary(summary);
    renderLedger(recent);
    renderAlerts(alerts);

    if (Number(summary.total_transactions || 0) > 0 || recent.length > 0) {
      setStatus(true);
    } else {
      setWaitingStatus();
    }
    document.getElementById("last-updated").textContent =
      "updated " + new Date().toLocaleTimeString("en-ZA");

    try {
      renderCityChart(buildCityRows(recent));
      renderCategoryChart(buildCategoryRows(recent));
      renderScoreChart(recent);
      renderActivityChart(summary);
    } catch (chartErr) {
      console.error("Chart refresh failed:", chartErr);
    }
  } catch (err) {
    setStatus(false);
    document.getElementById("last-updated").textContent = "refresh failed";
    console.error("Refresh failed:", err);
  }
}

refresh();
setInterval(refresh, REFRESH_MS);
