let API_BASE = localStorage.getItem('api_base') || 'http://127.0.0.1:6543';

document.addEventListener('DOMContentLoaded', () => {
  const input = document.getElementById('api-base');
  if (input) input.value = API_BASE;
  const btn = document.getElementById('save-base');
  if (btn) btn.onclick = () => { API_BASE = document.getElementById('api-base').value.trim(); localStorage.setItem('api_base', API_BASE); };
});

async function postFile(file) {
  const fd = new FormData();
  fd.append('file', file);
  const res = await fetch(`${API_BASE}/api/process`, { method: 'POST', body: fd });
  const data = await res.json();
  if (!res.ok) throw data;
  return data;
}

function renderTable(el, rows, opts = {}) {
  el.innerHTML = '';
  if (!rows || rows.length === 0) { el.textContent = 'No data'; return; }
  const table = document.createElement('table');
  const thead = document.createElement('thead');
  let keys = Object.keys(rows[0]);
  if (opts.hidden && opts.hidden.length) keys = keys.filter(k => !opts.hidden.includes(k));
  const trh = document.createElement('tr');
  keys.forEach(k => { const th = document.createElement('th'); th.textContent = k; th.dataset.key = k; trh.appendChild(th); });
  thead.appendChild(trh);
  table.appendChild(thead);
  const tbody = document.createElement('tbody');
  const format = opts.format || ((k, v) => v);
  rows.forEach(r => {
    const tr = document.createElement('tr');
    keys.forEach(k => { const td = document.createElement('td'); td.textContent = format(k, r[k]); tr.appendChild(td); });
    tbody.appendChild(tr);
  });
  table.appendChild(tbody);
  el.appendChild(table);
}

function formatNumber(x) { try { return Number(x).toLocaleString('en-IN', { maximumFractionDigits: 2 }); } catch { return x; } }
function formatCell(key, val) {
  const moneyCols = new Set(['BuyUnitCost','BuyCostTotal','SellUnitPrice','SellProceedsGross','SellCostsAllocated','SellProceedsNet','Gain','STCG_Total','LTCG_Total','Net_Total_Gain','Total_Sell_Proceeds','Total_Buy_Cost','UnitCost','TotalCost']);
  if (moneyCols.has(key)) return formatNumber(val);
  return val;
}

document.getElementById('upload-form').addEventListener('submit', async (e) => {
  e.preventDefault();
  const msg = document.getElementById('messages');
  const results = document.getElementById('results');
  msg.textContent = ''; msg.className = '';
  try {
    const file = e.target.querySelector('input[type=file]').files[0];
    if (!file) { msg.textContent = 'Please select a file'; msg.className = 'error'; return; }
    msg.textContent = 'Processing...';
    const data = await postFile(file);
    msg.textContent = 'Processed successfully'; msg.className = 'muted';
    results.style.display = '';
    const overall = (data.overall_summary && data.overall_summary[0]) || null;
    const metrics = [
      { key: 'STCG_Total', label: 'Short-Term Gain', value: overall?.STCG_Total || 0 },
      { key: 'LTCG_Total', label: 'Long-Term Gain', value: overall?.LTCG_Total || 0 },
      { key: 'Net_Total_Gain', label: 'Net Gain', value: overall?.Net_Total_Gain || 0 },
      { key: 'Total_Sell_Proceeds', label: 'Sell Proceeds', value: overall?.Total_Sell_Proceeds || 0 },
      { key: 'Total_Buy_Cost', label: 'Buy Cost', value: overall?.Total_Buy_Cost || 0 },
    ];
    const overallDiv = document.getElementById('overall-cards');
    overallDiv.innerHTML = metrics.map(m => `<div class="metric"><div class="label">${m.label}</div><div class="value ${m.value>=0?'pos':'neg'}">${formatNumber(m.value)}</div></div>`).join('');
    renderTable(document.getElementById('per-scrip'), data.per_scrip_summary, { format: formatCell });
    const realizedDiv = document.getElementById('realized');
    const renderRealized = () => {
      const term = document.getElementById('filter-term').value;
      const scrip = document.getElementById('filter-scrip').value.trim().toLowerCase();
      const showTrace = document.getElementById('toggle-trace').checked;
      const rows = data.realized_lots.filter(r => (!term || r.Term === term) && (!scrip || String(r.Scrip).toLowerCase().includes(scrip)));
      const hidden = showTrace ? [] : ['BuyRef','SellRef'];
      renderTable(realizedDiv, rows, { hidden, format: formatCell });
    };
    document.getElementById('filter-term').onchange = renderRealized;
    document.getElementById('filter-scrip').oninput = renderRealized;
    document.getElementById('toggle-trace').onchange = renderRealized;
    renderRealized();
    renderTable(document.getElementById('open'), data.open_positions, { format: formatCell });
    const dl = document.getElementById('downloads');
    dl.innerHTML = '';
    const a1 = document.createElement('a'); a1.href = `${API_BASE}/download/${data.token}/csv`; a1.textContent = 'Download CSV (.zip)';
    const a2 = document.createElement('a'); a2.href = `${API_BASE}/download/${data.token}/excel`; a2.textContent = 'Download Excel (.xlsx)';
    dl.appendChild(a1); dl.appendChild(a2);
    if (data.validations && data.validations.warnings && data.validations.warnings.length) {
      const w = document.createElement('div'); w.className = 'warn'; w.textContent = 'Warnings: ' + data.validations.warnings.join('; ');
      msg.appendChild(w);
    }
  } catch (err) {
    const msgEl = document.getElementById('messages');
    msgEl.className = 'error';
    const text = err && err.validations ? err.validations.errors.join('; ') : (err && err.error) || 'Unexpected error';
    msgEl.textContent = text;
  }
});

