// ---------- element refs ----------
const tokenInput = document.getElementById('token');
const slugInput = document.getElementById('slug');
const fetchBtn = document.getElementById('fetch-btn');
const saveBtn = document.getElementById('save-btn');
const statusBox = document.getElementById('status');
const resultsCard = document.getElementById('results-card');
const resultsMeta = document.getElementById('results-meta');
const statCount = document.getElementById('stat-count');
const statAttendees = document.getElementById('stat-attendees');
const tableBody = document.querySelector('#results-table tbody');
const getTokenLink = document.getElementById('get-token-link');

function setStatus(message, kind) {
  if (!message) { statusBox.hidden = true; return; }
  statusBox.hidden = false;
  statusBox.textContent = message;
  statusBox.className = `status ${kind || ''}`;
}

function fmtNumber(n) { return n.toLocaleString(); }

function fmtDate(timestamp) {
  if (!timestamp) return '—';
  return new Date(timestamp * 1000).toISOString().slice(0, 10);
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

async function handleFetch() {
  const token = tokenInput.value.trim();
  const slug = slugInput.value.trim();
  if (!token || !slug) { setStatus('Both token and slug are required.', 'error'); return; }

  fetchBtn.disabled = true;
  setStatus('Verifying credentials…', 'working');

  try {
    const verify = await post('/api/verify', { token, slug });
    if (!verify.ok) { setStatus(verify.error, 'error'); return; }

    setStatus(`Authenticated as ${verify.user_name}. Fetching tournaments… (may take a moment)`, 'working');

    const result = await post('/api/fetch', { token, slug });
    if (!result.ok) { setStatus(result.error, 'error'); return; }

    renderResults(result);
    setStatus(`Done — pulled ${result.count} tournament${result.count === 1 ? '' : 's'}.`, 'success');
  } catch (err) {
    setStatus(`Unexpected error: ${err}`, 'error');
  } finally {
    fetchBtn.disabled = false;
  }
}

function renderResults({ count, total_attendees, tournaments }) {
  resultsCard.hidden = false;
  statCount.textContent = fmtNumber(count);
  statAttendees.textContent = fmtNumber(total_attendees);
  resultsMeta.textContent = count
    ? `Across ${count} tournament${count === 1 ? '' : 's'} you've organized.`
    : 'No tournaments found for this user.';

  tableBody.innerHTML = '';
  const sorted = [...tournaments].sort((a, b) => (b.start_at || 0) - (a.start_at || 0));
  for (const t of sorted) {
    const row = document.createElement('tr');
    row.innerHTML = `<td>${escapeHtml(t.name)}</td><td>${fmtDate(t.start_at)}</td><td class="num">${fmtNumber(t.attendees)}</td>`;
    tableBody.appendChild(row);
  }
}

async function handleSave() {
  saveBtn.disabled = true;
  try {
    const result = await post('/api/save', { path: 'my_startgg_tournaments.csv' });
    setStatus(result.ok ? `Saved to: ${result.path}` : result.error, result.ok ? 'success' : 'error');
  } finally {
    saveBtn.disabled = false;
  }
}

fetchBtn.addEventListener('click', handleFetch);
saveBtn.addEventListener('click', handleSave);
getTokenLink.addEventListener('click', (e) => {
  e.preventDefault();
  window.open('https://start.gg/admin/profile/developer', '_blank');
});
