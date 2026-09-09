(() => {
  const status = document.getElementById('status');
  status.textContent = JSON.stringify({
    mode: 'frontend',
    execution: 'OFF',
    chart_control: 'chart-only',
    kfoo_roles: { gravity: ['4h','1h'], leader: '15m', entry: ['5m','3m'], excluded: ['2m'] },
    backend: 'not_connected'
  }, null, 2);
})();
