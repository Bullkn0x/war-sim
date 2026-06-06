const ctx = document.getElementById('chart').getContext('2d');

const chart = new Chart(ctx, {
  type: 'line',
  data: {
    labels: [],
    datasets: [
      {
        label: 'Player 1',
        data: [],
        borderColor: '#58a6ff',
        backgroundColor: 'rgba(88,166,255,0.06)',
        borderWidth: 2,
        pointRadius: 0,
        pointHoverRadius: 4,
        tension: 0.3,
        fill: true,
      },
      {
        label: 'Player 2',
        data: [],
        borderColor: '#f78166',
        backgroundColor: 'rgba(247,129,102,0.06)',
        borderWidth: 2,
        pointRadius: 0,
        pointHoverRadius: 4,
        tension: 0.3,
        fill: true,
      },
    ],
  },
  options: {
    animation: false,
    responsive: true,
    maintainAspectRatio: false,
    interaction: { mode: 'index', intersect: false },
    plugins: {
      legend: {
        labels: { color: '#8b949e', font: { size: 12 }, boxWidth: 12, padding: 16 },
      },
      tooltip: {
        backgroundColor: '#161b22',
        borderColor: '#30363d',
        borderWidth: 1,
        titleColor: '#8b949e',
        bodyColor: '#c9d1d9',
        padding: 10,
      },
    },
    scales: {
      x: {
        grid: { color: '#21262d' },
        ticks: { color: '#484f58', maxTicksLimit: 10, font: { size: 11 } },
        title: { display: true, text: 'Game', color: '#484f58', font: { size: 11 } },
      },
      y: {
        grid: { color: '#21262d' },
        ticks: { color: '#484f58', font: { size: 11 } },
        title: { display: true, text: 'Cumulative Wins', color: '#484f58', font: { size: 11 } },
        beginAtZero: true,
      },
    },
  },
});

let source = null;

function resetChart() {
  chart.data.labels = [];
  chart.data.datasets[0].data = [];
  chart.data.datasets[1].data = [];
  chart.update('none');

  document.getElementById('p1Count').textContent = '0';
  document.getElementById('p2Count').textContent = '0';
  document.getElementById('p1Pct').textContent = '—';
  document.getElementById('p2Pct').textContent = '—';
  document.getElementById('p1Fill').style.width = '0%';
  document.getElementById('p2Fill').style.width = '0%';
  document.getElementById('totalGames').textContent = '0';
  document.getElementById('avgRounds').textContent = '—';
  document.getElementById('p1Rate').textContent = '—';
  document.getElementById('p2Rate').textContent = '—';
  document.getElementById('logEntries').innerHTML = '';
  document.getElementById('progressFill').style.width = '0%';
}

function startRun() {
  if (source) { source.close(); source = null; }

  const count = parseInt(document.getElementById('gameCount').value, 10) || 50;
  resetChart();

  document.getElementById('runBtn').disabled = true;
  document.getElementById('statusText').textContent = 'Running...';

  source = new EventSource(`/stream?count=${count}`);

  source.onmessage = function(e) {
    const d = JSON.parse(e.data);

    if (d.done) {
      source.close();
      source = null;
      document.getElementById('runBtn').disabled = false;
      document.getElementById('statusText').textContent = `Done — ${count} games simulated`;
      document.getElementById('progressFill').style.width = '100%';
      return;
    }

    const skipEvery = d.total > 200 ? Math.ceil(d.total / 200) : 1;
    if (d.game % skipEvery === 0 || d.game === d.total) {
      chart.data.labels.push(d.game);
      chart.data.datasets[0].data.push(d.p1_wins);
      chart.data.datasets[1].data.push(d.p2_wins);
      chart.update('none');
    }

    const total = d.p1_wins + d.p2_wins;
    const p1pct = total ? ((d.p1_wins / total) * 100).toFixed(1) : 0;
    const p2pct = total ? ((d.p2_wins / total) * 100).toFixed(1) : 0;

    document.getElementById('p1Count').textContent = d.p1_wins;
    document.getElementById('p2Count').textContent = d.p2_wins;
    document.getElementById('p1Pct').textContent = `${p1pct}% win rate`;
    document.getElementById('p2Pct').textContent = `${p2pct}% win rate`;
    document.getElementById('p1Fill').style.width = `${p1pct}%`;
    document.getElementById('p2Fill').style.width = `${p2pct}%`;

    document.getElementById('totalGames').textContent = d.game;
    document.getElementById('avgRounds').textContent = d.avg_rounds;
    document.getElementById('p1Rate').textContent = `${p1pct}%`;
    document.getElementById('p2Rate').textContent = `${p2pct}%`;

    document.getElementById('progressFill').style.width = `${(d.game / d.total) * 100}%`;
    document.getElementById('statusText').textContent = `Game ${d.game} of ${d.total}`;

    const log = document.getElementById('logEntries');
    const entry = document.createElement('div');
    entry.className = 'log-entry';
    const cls = d.winner === 'Player 1' ? 'p1-color' : 'p2-color';
    entry.innerHTML = `
      <span class="gnum">#${d.game}</span>
      <span class="lwinner ${cls}">${d.winner}</span>
      <span class="lrounds">${d.rounds}r</span>
    `;
    log.insertBefore(entry, log.firstChild);
    if (log.children.length > 60) log.removeChild(log.lastChild);
  };

  source.onerror = function() {
    document.getElementById('runBtn').disabled = false;
    document.getElementById('statusText').textContent = 'Connection error.';
    if (source) { source.close(); source = null; }
  };
}
