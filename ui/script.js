// ---------- element refs ----------
const tokenInput = document.getElementById('token');
const slugInput = document.getElementById('slug');
const fetchBtn = document.getElementById('fetch-btn');
const saveBtn = document.getElementById('save-btn');
const resultsCard = document.getElementById('results-card');
const resultsMeta = document.getElementById('results-meta');
const tableBody = document.querySelector('#results-table tbody');
const getTokenLink = document.getElementById('get-token-link');

// credential card states
const credForm = document.getElementById('cred-form');
const credLoading = document.getElementById('cred-loading');
const credDone = document.getElementById('cred-done');
const loadingGreeting = document.getElementById('loading-greeting');
const loadingSub = document.getElementById('loading-sub');
const loadingDetail = document.getElementById('loading-detail');
const progressBar = document.getElementById('progress-bar');
const doneText = document.getElementById('done-text');
const rerunBtn = document.getElementById('rerun-btn');
const statusBox = document.getElementById('status');

// hero stats
const statCount = document.getElementById('stat-count');
const statAttendees = document.getElementById('stat-attendees');
const statAvg = document.getElementById('stat-avg');

// highlights
const hlBiggest = document.getElementById('highlight-biggest');
const hlSince = document.getElementById('highlight-since');

let chartInstance = null;

// ---------- helpers ----------
function fmtNumber(n) { return Number(n).toLocaleString(); }

function fmtDate(timestamp) {
  if (!timestamp) return '—';
  return new Date(timestamp * 1000).toISOString().slice(0, 10);
}

function fmtMonthYear(timestamp) {
  if (!timestamp) return '—';
  const d = new Date(timestamp * 1000);
  return d.toLocaleString('en-US', { month: 'long', year: 'numeric' });
}

function escapeHtml(s) {
  return String(s).replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
}

async function post(endpoint, body) {
  const res = await fetch(endpoint, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
  return res.json();
}

// ---------- card state management ----------
function showForm() {
  credForm.hidden = false;
  credLoading.hidden = true;
  credDone.hidden = true;
  statusBox.hidden = true;
}

function showLoading(greeting, sub, detail) {
  credForm.hidden = true;
  credLoading.hidden = false;
  credDone.hidden = true;
  loadingGreeting.textContent = greeting;
  loadingSub.textContent = sub;
  loadingDetail.textContent = detail;
  progressBar.style.width = '0%';
  progressBar.classList.add('indeterminate');
}

function updateLoading(detail, pct) {
  loadingDetail.textContent = detail;
  if (pct !== undefined) {
    progressBar.classList.remove('indeterminate');
    progressBar.style.width = pct + '%';
  }
}

function showDone(name, count) {
  credForm.hidden = true;
  credLoading.hidden = true;
  credDone.hidden = false;
  doneText.textContent = `✅ ${name}'s Wrapped is ready — ${count} tournament${count === 1 ? '' : 's'} found`;
}

function showError(msg) {
  showForm();
  statusBox.hidden = false;
  statusBox.textContent = msg;
  statusBox.className = 'status error';
}

// ---------- handlers ----------
async function handleFetch() {
  const token = tokenInput.value.trim();
  const slug = slugInput.value.trim();
  if (!token || !slug) { showError('Both token and slug are required.'); return; }

  showLoading('Hey there 👋', 'Hang tight — checking your credentials…', 'Connecting to start.gg…');

  try {
    const verify = await post('/api/verify', { token, slug });
    if (!verify.ok) { showError(verify.error); return; }

    const tag = verify.gamer_tag;
    showLoading(
      `Hello, ${tag}`,
      'Pulling your tournament history…',
      'Fetching from start.gg…'
    );

    // Simulate progress stages since we don't have real-time page info
    let fakeProgress = 10;
    const progressInterval = setInterval(() => {
      fakeProgress = Math.min(fakeProgress + 8, 85);
      updateLoading('Crunching the numbers…', fakeProgress);
    }, 600);

    const result = await post('/api/fetch', { token, slug });
    clearInterval(progressInterval);

    if (!result.ok) { showError(result.error); return; }

    updateLoading('Almost there…', 100);
    await new Promise(r => setTimeout(r, 400));

    renderResults(result);
    // Wait for the DOM to paint the results before collapsing the card
    await new Promise(r => requestAnimationFrame(() => setTimeout(r, 300)));
    showDone(tag, result.stats.count);
  } catch (err) {
    showError(`Something went wrong: ${err}`);
  }
}

function renderResults({ stats, tournaments }) {
  resultsCard.hidden = false;

  statCount.textContent = fmtNumber(stats.count);
  statAttendees.textContent = fmtNumber(stats.total_attendees);
  statAvg.textContent = fmtNumber(stats.average_attendees);

  resultsMeta.textContent = stats.count
    ? `You've run ${stats.count} tournament${stats.count === 1 ? '' : 's'}. That's a lot of brackets.`
    : 'No tournaments found — double check your slug.';

  if (stats.biggest) {
    hlBiggest.textContent = `${stats.biggest.name} — ${fmtNumber(stats.biggest.attendees)} attendees`;
  } else {
    hlBiggest.textContent = '—';
  }

  if (stats.first_event) {
    hlSince.textContent = fmtMonthYear(stats.first_event.date);
  } else {
    hlSince.textContent = '—';
  }

  renderPodium(tournaments);
  renderChart(stats.timeline);

  tableBody.innerHTML = '';
  const sorted = [...tournaments].sort((a, b) => (b.start_at || 0) - (a.start_at || 0));
  for (const t of sorted) {
    const row = document.createElement('tr');
    row.innerHTML = `<td>${escapeHtml(t.name)}</td><td>${fmtDate(t.start_at)}</td><td class="num">${fmtNumber(t.attendees)}</td>`;
    tableBody.appendChild(row);
  }
}

function renderPodium(tournaments) {
  const podium = document.getElementById('podium');
  podium.innerHTML = '';

  const medals = ['🥇', '🥈', '🥉', '4️⃣', '5️⃣'];
  const top5 = [...tournaments]
    .sort((a, b) => b.attendees - a.attendees)
    .slice(0, 5);

  for (let i = 0; i < top5.length; i++) {
    const t = top5[i];
    const row = document.createElement('div');
    row.className = 'podium-row';
    row.innerHTML = `
      <span class="podium-rank">${medals[i]}</span>
      <div class="podium-info">
        <div class="podium-name">${escapeHtml(t.name)}</div>
        <div class="podium-date">${fmtDate(t.start_at)}</div>
      </div>
      <div style="text-align:right">
        <div class="podium-attendees">${fmtNumber(t.attendees)}</div>
        <div class="podium-attendees-label">attendees</div>
      </div>
    `;
    podium.appendChild(row);
  }
}

function renderChart(timeline) {
  const ctx = document.getElementById('timeline-chart').getContext('2d');

  if (chartInstance) chartInstance.destroy();

  if (!timeline.length) {
    ctx.canvas.style.display = 'none';
    return;
  }
  ctx.canvas.style.display = 'block';

  const labels = timeline.map(t => String(new Date(t.date * 1000).getFullYear()));
  const data   = timeline.map(t => t.attendees);
  const names  = timeline.map(t => t.name);

  const yearIndices = {};
  labels.forEach((year, i) => {
    if (!yearIndices[year]) yearIndices[year] = [];
    yearIndices[year].push(i);
  });
  const yearMidpoints = {};
  for (const [year, indices] of Object.entries(yearIndices)) {
    yearMidpoints[indices[Math.floor(indices.length / 2)]] = year;
  }

  chartInstance = new Chart(ctx, {
    type: 'line',
    data: {
      labels,
      datasets: [{
        label: 'Attendees',
        data,
        borderColor: '#e0218a',
        backgroundColor: 'rgba(224, 33, 138, 0.15)',
        pointBackgroundColor: '#e0218a',
        pointRadius: 4,
        pointHoverRadius: 6,
        tension: 0.2,
        fill: true,
      }],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      height: 220,
      plugins: {
        legend: { display: false },
        tooltip: {
          callbacks: {
            title: (items) => names[items[0].dataIndex],
            label: (item) => `${labels[item.dataIndex]} — ${item.raw} attendees`,
          },
        },
      },
      scales: {
        x: {
          ticks: {
            color: '#9aa0ad',
            maxRotation: 0,
            autoSkip: false,
            callback: function(val, index) {
              return yearMidpoints[index] || null;
            },
          },
          grid: { color: 'rgba(255,255,255,0.05)' },
        },
        y: {
          beginAtZero: true,
          ticks: { color: '#9aa0ad' },
          grid: { color: 'rgba(255,255,255,0.05)' },
        },
      },
    },
  });
}

async function handleSave() {
  saveBtn.disabled = true;
  try {
    const result = await post('/api/save', { path: 'my_startgg_tournaments.csv' });
    doneText.textContent = result.ok ? `✅ Saved to: ${result.path}` : `❌ ${result.error}`;
  } finally {
    saveBtn.disabled = false;
  }
}

fetchBtn.addEventListener('click', handleFetch);
saveBtn.addEventListener('click', handleSave);
rerunBtn.addEventListener('click', () => {
  tokenInput.value = '';
  slugInput.value = '';
  doneText.textContent = '';
  showForm();
  resultsCard.hidden = true;
});
getTokenLink.addEventListener('click', (e) => {
  e.preventDefault();
  window.open('https://start.gg/admin/profile/developer', '_blank');
});
