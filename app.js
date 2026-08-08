let SESSION_DATA = null;
let ALL_MACHINE_DATA = {};
let ALL_MACHINE_NAMES = [];
let CURRENT_MACHINE = null;

// IndexedDB persistence — survives page refresh
const DB_NAME = 'BDRDashboard';
const DB_VERSION = 1;
const DB_STORE = 'appData';

function openDB() {
    return new Promise((resolve, reject) => {
        const req = indexedDB.open(DB_NAME, DB_VERSION);
        req.onupgradeneeded = (e) => {
            const db = e.target.result;
            if (!db.objectStoreNames.contains(DB_STORE)) db.createObjectStore(DB_STORE);
        };
        req.onsuccess = (e) => resolve(e.target.result);
        req.onerror = (e) => reject(e.target.error);
    });
}

async function dbSave(key, data) {
    try {
        const db = await openDB();
        return new Promise((resolve, reject) => {
            const tx = db.transaction(DB_STORE, 'readwrite');
            tx.objectStore(DB_STORE).put(data, key);
            tx.oncomplete = () => resolve();
            tx.onerror = (e) => reject(e.target.error);
        });
    } catch (e) { console.warn('dbSave failed', e); }
}

async function dbLoad(key) {
    try {
        const db = await openDB();
        return new Promise((resolve, reject) => {
            const tx = db.transaction(DB_STORE, 'readonly');
            const req = tx.objectStore(DB_STORE).get(key);
            req.onsuccess = () => resolve(req.result);
            req.onerror = (e) => reject(e.target.error);
        });
    } catch (e) { console.warn('dbLoad failed', e); return null; }
}

async function dbDelete(key) {
    try {
        const db = await openDB();
        return new Promise((resolve, reject) => {
            const tx = db.transaction(DB_STORE, 'readwrite');
            tx.objectStore(DB_STORE).delete(key);
            tx.oncomplete = () => resolve();
            tx.onerror = (e) => reject(e.target.error);
        });
    } catch (e) { console.warn('dbDelete failed', e); }
}

function getAqcMachineNames(names = Object.keys(ALL_MACHINE_DATA)) {
    return [...names].sort((a, b) => a.localeCompare(b, undefined, { numeric: true }));
}

// ── View Switcher: BDR Dashboard / Ring Slots ──

let currentView = 'bdr';
let isDrilldownActive = false;
let _serialBrowserFilteredResults = [];
let _serialBrowserCategoryFilter = '';
let _serialBrowserBulkMode = false;
let _serialBrowserBulkSerials = [];
let ringsData = [];
let ringsAssignedTimes = {};
let ringsFetchCompleted = false;
let ringsDirHandle = null;
let ringsFileHashes = new Map();
let ringsFileSizes = new Map();
let ringsWatchTimer = null;
let ringsWatching = false;
let ringsSelectedSlot = null;
let ringsSelectedMachine = null;
let ringsStatusFilter = '';
let ringsKpiFilter = '';
let ringsStatusColors = {};
let chargerStatusByMachine = {};
let chargerStatusFetches = {};

function normalizeAqcMachineName(name) {
  return String(name || '').trim().toLowerCase().replace(/\s+/g, '-').replace(/^aqc-?0?(\d)$/i, 'aqc-0$1');
}

function renderChargerControls(containerId, machineName, slot, enabled) {
  const container = document.getElementById(containerId);
  if (!container) return;
  container.innerHTML = '';
  const machine = normalizeAqcMachineName(machineName);
  const slotNum = parseInt(slot, 10);
  if (!enabled || !machine || !slotNum) return;

  const statusId = containerId + '-status';
  const stateId = containerId + '-state';
  container.innerHTML =
    '<button class="floorplan-toggle" style="padding:4px 10px;color:#059669;" title="Turn charger on for this slot" onclick="setSlotCharger(\'' + machine.replace(/'/g, "\\'") + '\',' + slotNum + ',\'on\',\'' + statusId + '\', this)">Charger ON</button>' +
    '<button class="floorplan-toggle" style="padding:4px 10px;color:#DC2626;" title="Turn charger off for this slot" onclick="setSlotCharger(\'' + machine.replace(/'/g, "\\'") + '\',' + slotNum + ',\'off\',\'' + statusId + '\', this)">Charger OFF</button>' +
    '<span id="' + stateId + '" style="font-size:11px;font-weight:600;color:var(--muted);">Charger: checking...</span>' +
    '<span id="' + statusId + '" style="font-size:11px;color:var(--muted);"></span>';
  updateChargerStateBadge(containerId, machine, slotNum);
  refreshMachineChargerStatus(machine).then(() => updateChargerStateBadge(containerId, machine, slotNum));
}

function isAvailableChargerSlot(slotData) {
  if (!slotData || typeof slotData !== 'object') return false;
  const sn = String(slotData.serial_number || '').trim();
  const mac = String(slotData.ring_mac || '').trim();
  return (sn && sn !== '--' && sn !== 'N/A') || (mac && mac !== '--' && mac !== 'N/A');
}

function getBdrAvailableChargerSlots() {
  const healthActive = window.heatmapFilterActive;
  const hasHealthFilter = healthActive && healthActive.size > 0;
  const fwActive = window.firmwareFilterActive;
  const hasFwFilter = fwActive && fwActive.size > 0;

  return globalHeatmapData
    .filter(hm => {
      if (!hm || !isAvailableChargerSlot(hm.raw)) return false;
      if (hasHealthFilter && !healthActive.has(hm.cls)) return false;
      if (hasFwFilter && !fwActive.has(hm.fw || '')) return false;
      return true;
    })
    .map(hm => parseInt(hm.id, 10))
    .filter(slot => Number.isInteger(slot) && slot >= 1 && slot <= 64)
    .sort((a, b) => a - b);
}

function getRingsAvailableChargerSlots(machineName) {
  const machine = normalizeAqcMachineName(machineName);
  const q = (document.getElementById('rings-search')?.value || '').toLowerCase();
  const statusFilter = ringsStatusFilter || ringsKpiFilter || '';
  return ringsData
    .filter(d => {
      if (normalizeAqcMachineName(d.file) !== machine) return false;
      if (!isAvailableChargerSlot(d)) return false;
      if (q) {
        const match = d.serial_number.toLowerCase().includes(q) || d.ring_mac.toLowerCase().includes(q) || d.ring_name.toLowerCase().includes(q);
        if (!match) return false;
      }
      if (statusFilter) {
        const cls = ringsGetSlotClass(d.state, d.serial_number);
        const clsForFilter = { ASSIGNED: 'ring-assigned', BDR_RUNNING: 'ring-run', PASSED: 'ring-ok', FAILED: 'ring-fail' };
        if (cls !== (clsForFilter[statusFilter] || '')) return false;
      }
      return true;
    })
    .map(d => parseInt(d.slot, 10))
    .filter(slot => Number.isInteger(slot) && slot >= 1 && slot <= 64)
    .sort((a, b) => a - b);
}

function renderBulkChargerControls(containerId, machineName, slots) {
  const container = document.getElementById(containerId);
  if (!container) return;
  container.innerHTML = '';
  const machine = normalizeAqcMachineName(machineName);
  const uniqueSlots = [...new Set(slots || [])];
  if (!machine || uniqueSlots.length === 0) {
    container.innerHTML = '<span style="font-size:11px;color:var(--muted);">No matching charger slots</span>';
    return;
  }

  const filterText = (containerId === 'bulk-charger-controls' && isBdrFilterActive()) || (containerId === 'rings-bulk-charger-controls' && isRingsFilterActive()) ? ' filtered' : '';
  const statusId = containerId + '-status';
  container.innerHTML =
    '<button class="floorplan-toggle" style="padding:4px 10px;color:#059669;" title="Turn charger on for all available slots" onclick="setAllSlotChargers(\'' + machine.replace(/'/g, "\\'") + '\',\'on\',\'' + containerId + '\',\'' + statusId + '\')">All ON</button>' +
    '<button class="floorplan-toggle" style="padding:4px 10px;color:#DC2626;" title="Turn charger off for all available slots" onclick="setAllSlotChargers(\'' + machine.replace(/'/g, "\\'") + '\',\'off\',\'' + containerId + '\',\'' + statusId + '\')">All OFF</button>' +
    '<span id="' + statusId + '" data-slots="' + uniqueSlots.join(',') + '" style="font-size:11px;color:var(--muted);">' + uniqueSlots.length + filterText + ' slots</span>';
}

function isBdrFilterActive() {
  return (window.heatmapFilterActive && window.heatmapFilterActive.size > 0) ||
         (window.firmwareFilterActive && window.firmwareFilterActive.size > 0);
}

function isRingsFilterActive() {
  return !!(ringsStatusFilter || ringsKpiFilter || (document.getElementById('rings-search')?.value || '').trim());
}

function updateBdrBulkChargerControls() {
  renderBulkChargerControls('bulk-charger-controls', CURRENT_MACHINE, getBdrAvailableChargerSlots());
}

function updateRingsBulkChargerControls() {
  renderBulkChargerControls('rings-bulk-charger-controls', ringsSelectedMachine, ringsSelectedMachine ? getRingsAvailableChargerSlots(ringsSelectedMachine) : []);
}

async function sendSlotChargerCommand(machine, slot, action) {
  const res = await fetch('/api/machine/' + encodeURIComponent(machine) + '/slot/' + encodeURIComponent(slot) + '/charger/' + encodeURIComponent(action), {
    method: 'POST',
    cache: 'no-store'
  });
  let payload = {};
  try { payload = await res.json(); } catch (e) {}
  if (!res.ok) throw new Error(payload.detail || ('HTTP ' + res.status));
  return payload;
}

function formatChargerState(record) {
  if (!record) return { text: 'Charger: Unknown', color: 'var(--muted)' };
  const currentText = record.charging_current_ma != null ? ' (' + Number(record.charging_current_ma).toFixed(1) + ' mA)' : '';
  if (record.state === 'on') return { text: 'Charger: ON' + currentText, color: '#059669' };
  if (record.state === 'off') return { text: 'Charger: OFF' + currentText, color: '#DC2626' };
  return { text: 'Charger: Unknown' + currentText, color: 'var(--muted)' };
}

function updateChargerStateBadge(containerId, machine, slot) {
  const el = document.getElementById(containerId + '-state');
  if (!el) return;
  const machineKey = normalizeAqcMachineName(machine);
  const record = chargerStatusByMachine[machineKey]?.[String(slot)];
  const formatted = formatChargerState(record);
  el.textContent = formatted.text;
  el.style.color = formatted.color;
}

function setLocalChargerState(machine, slot, action) {
  const machineKey = normalizeAqcMachineName(machine);
  if (!chargerStatusByMachine[machineKey]) chargerStatusByMachine[machineKey] = {};
  chargerStatusByMachine[machineKey][String(slot)] = {
    ...(chargerStatusByMachine[machineKey][String(slot)] || {}),
    state: action,
    source: 'sent_command'
  };
}

async function refreshMachineChargerStatus(machine, force = false) {
  const machineKey = normalizeAqcMachineName(machine);
  if (!machineKey) return null;
  if (!force && chargerStatusFetches[machineKey]) return chargerStatusFetches[machineKey];

  chargerStatusFetches[machineKey] = fetch('/api/machine/' + encodeURIComponent(machineKey) + '/charger-status?ts=' + Date.now(), { cache: 'no-store' })
    .then(async res => {
      const payload = await res.json();
      if (!res.ok) throw new Error(payload.detail || ('HTTP ' + res.status));
      chargerStatusByMachine[machineKey] = payload.slots || {};
      return chargerStatusByMachine[machineKey];
    })
    .catch(err => {
      console.warn('Charger status refresh failed:', machineKey, err);
      return null;
    })
    .finally(() => {
      delete chargerStatusFetches[machineKey];
    });

  return chargerStatusFetches[machineKey];
}

function delay(ms) {
  return new Promise(resolve => setTimeout(resolve, ms));
}

async function setSlotCharger(machine, slot, action, statusId, button) {
  const statusEl = document.getElementById(statusId);
  const panel = button ? button.parentElement : null;
  const buttons = panel ? Array.from(panel.querySelectorAll('button')) : [];
  buttons.forEach(btn => btn.disabled = true);
  if (statusEl) {
    statusEl.textContent = action === 'on' ? 'Turning on...' : 'Turning off...';
    statusEl.style.color = 'var(--muted)';
  }

  try {
    await sendSlotChargerCommand(machine, slot, action);
    setLocalChargerState(machine, slot, action);
    updateChargerStateBadge('dt-charger-controls', machine, slot);
    updateChargerStateBadge('rings-charger-controls', machine, slot);
    if (statusEl) {
      statusEl.textContent = 'Charger ' + action.toUpperCase() + ' sent';
      statusEl.style.color = action === 'on' ? '#059669' : '#DC2626';
    }
    setTimeout(() => {
      refreshMachineChargerStatus(machine, true).then(() => {
        updateChargerStateBadge('dt-charger-controls', machine, slot);
        updateChargerStateBadge('rings-charger-controls', machine, slot);
      });
    }, 500);
  } catch (err) {
    if (statusEl) {
      statusEl.textContent = 'Failed: ' + err.message;
      statusEl.style.color = '#DC2626';
    } else {
      alert('Charger command failed: ' + err.message);
    }
  } finally {
    buttons.forEach(btn => btn.disabled = false);
  }
}

async function setAllSlotChargers(machine, action, containerId, statusId) {
  const statusEl = document.getElementById(statusId);
  const container = document.getElementById(containerId);
  const slots = (statusEl?.dataset.slots || '')
    .split(',')
    .map(v => parseInt(v, 10))
    .filter(v => Number.isInteger(v));
  if (!machine || slots.length === 0) return;

  const confirmText = 'Turn charger ' + action.toUpperCase() + ' for ' + slots.length + ' available slots in ' + machine.toUpperCase() + '?';
  if (!confirm(confirmText)) return;

  const buttons = container ? Array.from(container.querySelectorAll('button')) : [];
  buttons.forEach(btn => btn.disabled = true);
  if (statusEl) {
    statusEl.textContent = 'Sending 0/' + slots.length + '...';
    statusEl.style.color = 'var(--muted)';
  }

  let ok = 0;
  const failed = [];
  for (let i = 0; i < slots.length; i++) {
    const slot = slots[i];
    try {
      await sendSlotChargerCommand(machine, slot, action);
      setLocalChargerState(machine, slot, action);
      ok++;
    } catch (err) {
      failed.push(slot);
      console.warn('Bulk charger failed:', machine, slot, action, err);
    }
    if (statusEl) statusEl.textContent = 'Sending ' + (i + 1) + '/' + slots.length + '...';
    if (i < slots.length - 1) await delay(1000);
  }

  if (statusEl) {
    statusEl.textContent = failed.length === 0 ? 'Done: ' + ok + '/' + slots.length : 'Done: ' + ok + '/' + slots.length + ', failed: ' + failed.join(', ');
    statusEl.style.color = failed.length === 0 ? (action === 'on' ? '#059669' : '#DC2626') : '#F59E0B';
  }
  buttons.forEach(btn => btn.disabled = false);
  refreshMachineChargerStatus(machine, true);
}

// ── AWM Control Functions ──────────────────────────────────────────

async function sendSlotAWMCommand(machine, slot, action) {
  const res = await fetch('/api/machine/' + encodeURIComponent(machine) + '/slot/' + encodeURIComponent(slot) + '/awm/' + encodeURIComponent(action), {
    method: 'POST',
    cache: 'no-store'
  });
  let payload = {};
  try { payload = await res.json(); } catch (e) {}
  if (!res.ok) throw new Error(payload.detail || ('HTTP ' + res.status));
  return payload;
}

function renderAWMControls(containerId, machineName, slot, enabled) {
  const container = document.getElementById(containerId);
  if (!container) return;
  container.innerHTML = '';
  const machine = normalizeAqcMachineName(machineName);
  const slotNum = parseInt(slot, 10);
  if (!enabled || !machine || !slotNum) return;

  const statusId = containerId + '-awm-status';
  container.innerHTML =
    '<button class="floorplan-toggle" style="padding:4px 10px;color:#2563EB;" title="Send AWM Start to this slot" onclick="triggerSlotAWM(\'' + machine.replace(/'/g, "\\'") + '\',' + slotNum + ',\'start\',\'' + statusId + '\', this)">AWM START</button>' +
    '<button class="floorplan-toggle" style="padding:4px 10px;color:#7C3AED;" title="Send AWM Stop to this slot" onclick="triggerSlotAWM(\'' + machine.replace(/'/g, "\\'") + '\',' + slotNum + ',\'stop\',\'' + statusId + '\', this)">AWM STOP</button>' +
    '<span id="' + statusId + '" style="font-size:11px;color:var(--muted);margin-left:4px;"></span>';
}

async function triggerSlotAWM(machine, slot, action, statusId, button) {
  const statusEl = document.getElementById(statusId);
  const panel = button ? button.parentElement : null;
  const buttons = panel ? Array.from(panel.querySelectorAll('button')) : [];
  buttons.forEach(btn => btn.disabled = true);
  if (statusEl) {
    statusEl.textContent = (action === 'start' ? 'Starting...' : 'Stopping...') + ' (may take a minute)';
    statusEl.style.color = 'var(--muted)';
  }

  try {
    await sendSlotAWMCommand(machine, slot, action);
    if (statusEl) {
      statusEl.textContent = 'AWM ' + action.toUpperCase() + ' done';
      statusEl.style.color = '#059669';
    }
  } catch (err) {
    if (statusEl) {
      statusEl.textContent = 'Failed: ' + err.message;
      statusEl.style.color = '#DC2626';
    } else {
      alert('AWM command failed: ' + err.message);
    }
  } finally {
    buttons.forEach(btn => btn.disabled = false);
  }
}

// ── End AWM Control Functions ──────────────────────────────────────

function switchView(view) {
  currentView = view;
  const ws = document.querySelector('.mes-workspace-container');
  if (ws) ws.classList.toggle('ws-non-bdr', view !== 'bdr');
  const bdrContent = document.getElementById('dashboard-content');
  const ringsView = document.getElementById('rings-view');
  const dataVizView = document.getElementById('data-viz-view');
  const diagView = document.getElementById('diagnostics-view');
  const oldDataView = document.getElementById('old-data-view');
  const bdrBtn = document.getElementById('view-bdr-btn');
  const ringsBtn = document.getElementById('view-rings-btn');
  const dataVizBtn = document.getElementById('view-data-viz-btn');
  const diagBtn = document.getElementById('view-diag-btn');
  const oldDataBtn = document.getElementById('view-old-data-btn');

  if (bdrContent) bdrContent.style.display = view === 'bdr' ? 'flex' : 'none';
  if (ringsView) ringsView.style.display = view === 'rings' ? 'flex' : 'none';
  if (dataVizView) dataVizView.style.display = view === 'data-viz' ? 'flex' : 'none';
  if (diagView) diagView.style.display = view === 'diagnostics' ? 'flex' : 'none';
  if (oldDataView) oldDataView.style.display = view === 'old-data' ? 'flex' : 'none';
  if (bdrBtn) bdrBtn.classList.toggle('active', view === 'bdr');
  if (ringsBtn) ringsBtn.classList.toggle('active', view === 'rings');
  if (dataVizBtn) dataVizBtn.classList.toggle('active', view === 'data-viz');
  if (diagBtn) diagBtn.classList.toggle('active', view === 'diagnostics');
  if (oldDataBtn) oldDataBtn.classList.toggle('active', view === 'old-data');
  if (view === 'bdr') loadSessionFilesFromServer();
  if (view === 'rings') loadRingsFromAPI();
  if (view === 'data-viz') {
    renderDataViz();
    if (!ringsData || ringsData.length === 0) {
      loadRingsFromAPI();
    }
  }
  if (view === 'old-data') {
    const input = document.getElementById('od-search-input');
    if (input) setTimeout(() => input.focus(), 100);
  }
  if (view !== 'diagnostics') diagStopMonitor();
}

function showDiagSelection() {
    const sel = document.getElementById('diag-selection-screen');
    const ctrl = document.getElementById('diag-controls-screen');
    if (sel) sel.style.display = 'flex';
    if (ctrl) ctrl.style.display = 'none';
}

function startMachineDiag(machineName) {
    openDiagnostics(machineName);
}

async function populateDiagMachineGrid() {
    const grid = document.getElementById('diag-machine-grid');
    const noMachines = document.getElementById('diag-no-machines-msg');
    if (!grid) return;
    const nameSet = new Set(ALL_MACHINE_NAMES);
    try {
        const res = await fetch('/api/machines');
        if (res.ok) {
            const data = await res.json();
            (data.machines || []).forEach(m => nameSet.add(m));
        }
    } catch (e) {
        console.warn('Could not fetch machine list from API', e);
    }
    const names = [...nameSet].sort((a, b) => a.localeCompare(b, undefined, { numeric: true }));
    grid.innerHTML = '';
    if (names.length === 0) {
        if (noMachines) noMachines.style.display = 'block';
        return;
    }
    if (noMachines) noMachines.style.display = 'none';
    names.forEach(name => {
        const btn = document.createElement('button');
        btn.className = 'heatmap-filter machine-btn';
        btn.dataset.machine = name;
        btn.innerHTML = '<span class="machine-name">' + name + '</span>';
        btn.onclick = function() { startMachineDiag(name); };
        grid.appendChild(btn);
    });
}

function openRingsFolder() {
  stopApiPolling();
  if (ringsWatchTimer) { clearTimeout(ringsWatchTimer); ringsWatchTimer = null; }
  ringsWatching = false;
  (async () => {
    try {
      ringsDirHandle = await window.showDirectoryPicker({ mode: 'read' });
      await loadRingsFromDir();
    } catch (err) {
      if (err.name === 'AbortError' || err.name === 'SecurityError') return;
      alert('Error opening folder: ' + err.message);
    }
  })();
}

async function loadRingsFromDir() {
  if (!ringsDirHandle) return;
  const entries = [];
  for await (const entry of ringsDirHandle.values()) {
    if (entry.kind === 'file' && entry.name.toLowerCase().endsWith('.json')) entries.push(entry);
  }
  if (entries.length === 0) { alert('No JSON files found.'); return; }
  ringsFileHashes.clear(); ringsFileSizes.clear();
  const slots = [];
  for (const entry of entries) {
    try {
      const file = await entry.getFile();
      const text = await file.text();
      if (!text.trim()) continue;
      const data = JSON.parse(text);
      const fname = entry.name.replace(/\.json$/i, '');
      ringsFileHashes.set(entry.name, await ringsHash(text));
      ringsFileSizes.set(entry.name, file.size);
      if (data && typeof data === 'object') {
        Object.entries(data).forEach(([slotId, s]) => {
          if (s && typeof s === 'object') {
            slots.push({ slot: slotId, file: fname, serial_number: s.serial_number || '--', ring_mac: s.ring_mac || '--', ring_name: s.ring_name || '--', state: s.state || '--', firmware_version: s.firmware_version || '--', dead_state: s.dead_state || null, discharge_connect_failures: s.discharge_connect_failures || 0, hardware_version: s.hardware_version || null, step_statuses: s.step_statuses || {}, queued_at: s.queued_at || null });
          }
        });
      }
    } catch (e) { console.warn('Error loading ' + entry.name + ': ' + e.message); }
  }
  ringsData = slots;
  try {
    populateRingsFilter();
    ringsRenderGrid();
    const fpPanel = document.getElementById('floorplan-panel');
    if (fpPanel && fpPanel.classList.contains('visible')) renderFloorplan();
  } catch (e) { console.warn('Error rendering rings data:', e); }
  if (currentView === 'data-viz') renderDataViz();
  ringsStartWatching();
  dbSave('ringsDirHandle', ringsDirHandle);
  const badge = document.getElementById('rings-watch-badge');
  if (badge) badge.classList.remove('hidden');
}

function ringsGetSlotClass(state, sn) {
  if (!sn || sn === '--' || sn === 'N/A' || !sn) return 'ring-empty';
  const s = (state || '').toUpperCase();
  if (s === 'BDR_RUNNING') return 'ring-run';
  if (s === 'PASSED' || s === 'PASS') return 'ring-ok';
  if (s === 'FAILED') return 'ring-fail';
  return 'ring-assigned';
}

function ringsHash(text) {
  return crypto.subtle.digest('SHA-256', new TextEncoder().encode(text)).then(buf => Array.from(new Uint8Array(buf)).map(b => b.toString(16).padStart(2, '0')).join(''));
}

function populateRingsFilter() {
  const container = document.getElementById('rings-machine-buttons');
  const countEl = document.getElementById('rings-total-machines');
  if (!container) return;
  let files = [...new Set(ringsData.map(d => d.file))].sort();
  if (ringsKpiFilter) {
    if (ringsKpiFilter === 'ASSIGNED') {
      const machinesWithAssigned = new Set(ringsData.filter(d => {
        const sn = d.serial_number || '';
        const s = (d.state || '').toUpperCase();
        return sn && sn !== '--' && sn !== 'N/A' && s !== 'BDR_RUNNING' && s !== 'PASSED' && s !== 'PASS' && s !== 'FAILED';
      }).map(d => d.file));
      files = files.filter(f => machinesWithAssigned.has(f));
    } else {
      const machinesWithStatus = new Set(ringsData.filter(d => (d.state || '').toUpperCase() === ringsKpiFilter).map(d => d.file));
      files = files.filter(f => machinesWithStatus.has(f));
    }
  }
  if (countEl) countEl.textContent = files.length;
  container.innerHTML = files.map(f => '<button class="floorplan-toggle' + (ringsSelectedMachine === f ? ' active' : '') + '" onclick="selectRingsMachine(\'' + f.replace(/'/g,"\\'") + '\')">' + f + '</button>').join('');
  buildRingsStatusFilters();
  updateRingsBulkChargerControls();
}

function buildRingsStatusFilters() {
  ringsStatusColors = { BDR_RUNNING: '#3B82F6', PASSED: '#22C55E', FAILED: '#EF4444', ASSIGNED: '#F59E0B' };

  const container = document.getElementById('rings-status-filters');
  if (!container) return;
  const filters = ['ASSIGNED', 'BDR_RUNNING', 'FAILED', 'PASSED'];
  if (ringsStatusFilter && !filters.includes(ringsStatusFilter) && ringsStatusFilter !== '') ringsStatusFilter = '';

  container.innerHTML =
    '<button class="heatmap-filter' + (ringsStatusFilter === '' ? ' active' : '') + '" data-filter="">All</button>' +
    filters.map(function(s) {
      return '<button class="heatmap-filter' + (ringsStatusFilter === s ? ' active' : '') + '" data-filter="' + s + '"><span class="fdot" style="background:' + ringsStatusColors[s] + ';"></span>' + s + '</button>';
    }).join('');

  container.onclick = function(e) {
    const btn = e.target.closest('.heatmap-filter');
    if (!btn) return;
    ringsSetStatusFilter(btn.dataset.filter || '');
  };

  const legend = document.getElementById('rings-legend');
  if (legend) {
    const emptyClr = window.matchMedia('(prefers-color-scheme:dark)').matches ? '#374151' : '#9CA3AF';
    const emptyBg = window.matchMedia('(prefers-color-scheme:dark)').matches ? 'rgba(107,114,128,0.08)' : '#F3F4F6';
    legend.innerHTML = filters.map(function(s) {
      return '<span class="legend-dot" style="background:' + ringsStatusColors[s] + ';margin-left:' + (s === filters[0] ? '0' : '12px') + ';"></span>' + s + ' ';
    }).join('') + '<span class="legend-dot" style="background:' + emptyBg + ';border:1px solid ' + emptyClr + ';margin-left:12px;"></span>Empty';
  }
}

function selectRingsMachine(name) {
  ringsSelectedMachine = ringsSelectedMachine === name ? null : name;
  populateRingsFilter();
  ringsRenderGrid();
  setTimeout(() => {
    const rg = document.getElementById('rings-grid');
    if (rg) rg.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
  }, 50);
}

function ringsSetStatusFilter(status) {
  ringsStatusFilter = status;
  ringsKpiFilter = '';
  populateRingsFilter();
  ringsRenderGrid();
}

function ringsRenderGrid() {
  try {
    const grid = document.getElementById('rings-grid');
    const empty = document.getElementById('rings-empty');
    const detail = document.getElementById('rings-detail-panel');
    const legend = document.getElementById('rings-legend');
    if (!grid) return;
    grid.innerHTML = '';
    if (detail) detail.classList.add('hidden');
    ringsSelectedSlot = null;

    const statsEl = document.getElementById('rings-stats');
    if (!ringsData || ringsData.length === 0) {
      if (empty) empty.style.display = 'flex';
      if (legend) legend.style.display = 'none';
      if (statsEl) statsEl.style.display = 'none';
      updateRingsBulkChargerControls();
      return;
    }
    if (empty) empty.style.display = 'none';
    if (legend) legend.style.display = 'flex';
    if (statsEl) statsEl.style.display = 'grid';

  // Build lookup — filter by machine first so each slot picks that machine's data
  let dataForLookup = ringsData || [];
  if (ringsSelectedMachine) dataForLookup = ringsData.filter(d => d && d.file === ringsSelectedMachine);
  const lookup = {};
  dataForLookup.forEach(d => { if (d) lookup[d.slot] = d; });
  const searchEl = document.getElementById('rings-search');
  const q = (searchEl?.value || '').toLowerCase();

  // Determine removed slots for selected machine
  let ringsRemovedSet = new Set();
  if (ringsSelectedMachine) {
    const norm = normalizeAqcMachineName(ringsSelectedMachine);
    ringsRemovedSet = removedSlotsByMachine[norm] || new Set();
  }

  // Set machine name label and count
  const machineLabel = document.getElementById('rings-grid-machine-label');
  const countLabel = document.getElementById('rings-grid-count-label');
  if (machineLabel) {
    machineLabel.textContent = ringsSelectedMachine ? ringsSelectedMachine.toUpperCase() : 'All Machines';
  }
  if (countLabel) {
    const occupiedCount = dataForLookup.filter(d => isOccupiedRingSlotRecord(d) && !ringsRemovedSet.has(String(d.slot))).length;
    countLabel.textContent = occupiedCount + ' / ' + occupiedCount + ' slots';
  }

  // 64 slots in 16x4 grid
  for (let i = 1; i <= 64; i++) {
    const key = String(i);
    const d = lookup[key] || null;
    // Force removed slots to appear as empty
    if (ringsRemovedSet.has(key) && d) {
      d.serial_number = '--';
      d.ring_mac = '--';
      d.ring_name = '--';
      d.state = '--';
    }

    const sn = d && d.serial_number ? d.serial_number : '--';
    const state = d && d.state ? d.state : '--';
    const cls = d ? (ringsGetSlotClass ? ringsGetSlotClass(state, sn) : 'ring-empty') : 'ring-empty';

    // Apply search and status filters (dim non-matching)
    let dimmed = false;
    if (q && d && d.serial_number) {
      const match = d.serial_number.toLowerCase().includes(q) || (d.ring_mac && d.ring_mac.toLowerCase().includes(q)) || (d.ring_name && d.ring_name.toLowerCase().includes(q));
      if (!match) dimmed = true;
    }
    if (!dimmed && ringsStatusFilter && d) {
      const clsForFilter = { ASSIGNED: 'ring-assigned', BDR_RUNNING: 'ring-run', PASSED: 'ring-ok', FAILED: 'ring-fail' };
      if (cls !== (clsForFilter[ringsStatusFilter] || '')) dimmed = true;
    }

    const el = document.createElement('div');
    el.className = 'slot-cell ' + cls + (dimmed ? ' ring-dimmed' : '');
    el.dataset.slot = key;
    el.innerHTML = key + slotBadgeHtml(d ? d.serial_number : '--');
    el.onclick = d ? () => ringsOpenDetail(d, key, el) : null;
    grid.appendChild(el);
  }

  ringsUpdateStats();

  // Refresh floorplan if visible
  const fpP = document.getElementById('floorplan-panel');
  if (fpP && fpP.classList.contains('visible') && renderFloorplan) renderFloorplan();
  } catch (e) {
    console.warn('Error rendering rings grid:', e);
  }
}

function ringsClearAllFilters() {
  ringsKpiFilter = '';
  ringsStatusFilter = '';
  ringsSelectedMachine = null;
  const search = document.getElementById('rings-search');
  if (search) search.value = '';
  document.querySelectorAll('#rings-status-filters .heatmap-filter').forEach(b => {
    b.classList.toggle('active', b.dataset.filter === '');
  });
  populateRingsFilter();
  ringsRenderGrid();
}

function ringsKpiClick(status) {
  ringsKpiFilter = status;
  ringsStatusFilter = status;
  ringsSelectedMachine = null;
  document.querySelectorAll('#rings-status-filters .heatmap-filter').forEach(b => {
    b.classList.toggle('active', b.dataset.filter === ringsStatusFilter);
  });
  populateRingsFilter();
  ringsRenderGrid();
}

function isOccupiedRingSlotRecord(slotData) {
  if (!slotData || typeof slotData !== 'object') return false;
  const sn = String(slotData.serial_number || '').trim();
  return !!(sn && sn !== '--' && sn !== 'N/A');
}

function ringsUpdateStats() {
  try {
    let data = ringsData || [];
    if (ringsSelectedMachine) data = (ringsData || []).filter(d => d && d.file === ringsSelectedMachine);
    const occupiedData = data.filter(isOccupiedRingSlotRecord);
    const total = occupiedData.length;
    const counts = { BDR_RUNNING: 0, PASSED: 0, FAILED: 0, ASSIGNED: 0 };
    occupiedData.forEach(d => {
      if (!d) return;
      const s = (d.state || '').toUpperCase();
      if (s === 'BDR_RUNNING') counts.BDR_RUNNING++;
      else if (s === 'PASSED' || s === 'PASS') counts.PASSED++;
      else if (s === 'FAILED') counts.FAILED++;
      else {
        const sn = d.serial_number || '';
        if (sn && sn !== '--' && sn !== 'N/A') counts.ASSIGNED++;
      }
    });
    const ss = document.getElementById('rings-stat-slots');
    if (ss) ss.textContent = total;

    const grid = document.getElementById('rings-stats');
    if (!grid) return;
    const ordered = ['BDR_RUNNING', 'PASSED', 'FAILED', 'ASSIGNED'];

    const iconMap = {
      total: '◈',
      BDR_RUNNING: '⚡',
      PASSED: '✔',
      FAILED: '✕',
      ASSIGNED: '⌘'
    };

    // Enhance the Total Slots card
    const totalCard = grid.querySelector('.kpi-card');
    if (totalCard) {
      const clr = '#3B82F6';
      totalCard.className = 'kpi-card ring-kpi ring-kpi-total';
      totalCard.style.setProperty('--kpi-accent', clr);
      totalCard.style.cursor = 'pointer';
      totalCard.onclick = ringsClearAllFilters;
      if (!totalCard.querySelector('.kpi-progress-row')) {
        totalCard.innerHTML =
          '<div class="kpi-header"><div class="kpi-left"><span class="kpi-dot"></span><span class="kpi-label">Total Slots</span></div><div class="kpi-icon">' + iconMap.total + '</div></div>' +
          '<div class="kpi-value" id="rings-stat-slots">' + total + '</div>' +
          '<div class="kpi-progress-row"><div class="kpi-progress-track"><div class="kpi-progress-fill" style="width:100%"></div></div><div class="kpi-percent">100%</div></div>';
      } else {
        const tv = totalCard.querySelector('.kpi-value');
        if (tv) tv.textContent = total;
      }
    }

    const cards = [];
    if (totalCard) cards.push(totalCard);
    ordered.forEach(s => {
      const count = counts[s];
      const pct = total > 0 ? ((count / total) * 100).toFixed(1) : 0;
      const existing = grid.querySelector('.kpi-card[data-status="' + s + '"]');
      const clr = ringsStatusColors[s] || '#6B7280';
      if (existing) {
        const valueEl = existing.querySelector('.kpi-value');
        if (valueEl) valueEl.textContent = count;
        const pctEl = existing.querySelector('.kpi-percent');
        if (pctEl) pctEl.textContent = pct + '%';
        const fill = existing.querySelector('.kpi-progress-fill');
        if (fill) fill.style.width = pct + '%';
        existing.style.setProperty('--kpi-accent', clr);
        existing.style.cursor = 'pointer';
        existing.onclick = () => ringsKpiClick(s);
        cards.push(existing);
      } else {
        const c = document.createElement('div');
        c.className = 'kpi-card ring-kpi';
        c.setAttribute('data-status', s);
        c.style.setProperty('--kpi-accent', clr);
        c.style.cursor = 'pointer';
        c.onclick = () => ringsKpiClick(s);
        const label = s === 'BDR_RUNNING' ? 'Running' : s === 'PASSED' ? 'Passed' : s === 'FAILED' ? 'Failed' : s;
        c.innerHTML =
          '<div class="kpi-header"><div class="kpi-left"><span class="kpi-dot"></span><span class="kpi-label">' + label + '</span></div><div class="kpi-icon">' + iconMap[s] + '</div></div>' +
          '<div class="kpi-value">' + count + '</div>' +
          '<div class="kpi-progress-row"><div class="kpi-progress-track"><div class="kpi-progress-fill" style="width:' + pct + '%"></div></div><div class="kpi-percent">' + pct + '%</div></div>';
        cards.push(c);
      }
    });
    Array.from(grid.children).forEach(child => { if (!cards.includes(child)) child.remove(); });
    cards.forEach(c => { if (!c.parentNode) grid.appendChild(c); });
  } catch (e) {
    console.warn('Error in ringsUpdateStats:', e);
  }
}

function ringsOpenDetail(d, slotKey, el) {
  const detail = document.getElementById('rings-detail-panel');
  if (!d || !detail) return;
  document.querySelectorAll('#rings-grid .slot-cell').forEach(c => c.classList.remove('active'));
  if (el) el.classList.add('active');
  ringsSelectedSlot = slotKey;

  detail.classList.remove('hidden');
  document.getElementById('rings-detail-slot').textContent = 'SLOT ' + slotKey;
  document.getElementById('rings-detail-serial').textContent = d.serial_number || '--';
  document.getElementById('rings-detail-mac').textContent = d.ring_mac || '--';
  document.getElementById('rings-detail-state').textContent = d.state || '--';
  document.getElementById('rings-detail-state').className = 'badge ' + (d.state === 'BDR_RUNNING' ? 'ok' : d.state === 'PASSED' || d.state === 'PASS' ? 'pass' : d.state === 'FAILED' ? 'danger' : 'neutral');
  document.getElementById('rings-detail-fw').textContent = d.firmware_version || '--';
  renderChargerControls('rings-charger-controls', d.file || ringsSelectedMachine, slotKey, true);
  renderAWMControls('rings-awm-controls', d.file || ringsSelectedMachine, slotKey, true);

  requestAnimationFrame(() => {
    const top = detail.getBoundingClientRect().top + window.scrollY - 16;
    window.scrollTo({ top, behavior: 'smooth' });
  });
}

function ringsCloseDetail() {
  const detail = document.getElementById('rings-detail-panel');
  if (detail) detail.classList.add('hidden');
  document.querySelectorAll('#rings-grid .slot-cell').forEach(c => c.classList.remove('active'));
  ringsSelectedSlot = null;
}

function ringsFilterGrid() {
  ringsRenderGrid();
}

function ringsSearchSerial(value) {
  const q = (value || '').trim().toLowerCase();
  if (!q) return;
  for (const d of ringsData) {
    const sn = (d.serial_number || '').toLowerCase();
    const mac = (d.ring_mac || '').toLowerCase();
    const name = (d.ring_name || '').toLowerCase();
    if (sn === q || sn.includes(q) || mac.includes(q) || name.includes(q)) {
      ringsSelectedMachine = d.file;
      document.getElementById('rings-search').value = '';
      populateRingsFilter();
      ringsRenderGrid();
      requestAnimationFrame(function() {
        const el = document.querySelector('#rings-grid .slot-cell[data-slot="' + d.slot + '"]');
        ringsOpenDetail(d, d.slot, el);
      });
      return;
    }
  }
  alert('Serial number not found in any ring machine.');
}

function ringAssignedTimestamp(d) {
  const e = ringsAssignedTimes[d.file] && ringsAssignedTimes[d.file][d.slot];
  if (e && e.serial === d.serial_number && e.ts) {
    const t = new Date(e.ts);
    if (!isNaN(t.getTime())) return t;
  }
  if (d.queued_at) {
    const t = new Date(d.queued_at);
    if (!isNaN(t.getTime())) return t;
  }
  return null;
}

function pad2(n) { return String(n).padStart(2, '0'); }

function ringsExportCSV() {
  if (ringsData.length === 0) { alert('No data to export.'); return; }
  let filtered = ringsData;
  if (ringsKpiFilter) filtered = filtered.filter(d => (d.state || '').toUpperCase() === ringsKpiFilter);
  if (ringsStatusFilter && !ringsKpiFilter) filtered = filtered.filter(d => (d.state || '').toUpperCase() === ringsStatusFilter);
  if (ringsSelectedMachine) filtered = filtered.filter(d => d.file === ringsSelectedMachine);
  if (filtered.length === 0) { alert('No data matches current filters.'); return; }
  const rows = [['Date','Time','Machine','Slot','SKU','Category','Battery %','Serial Number','MAC ID','Status']];
  filtered.forEach(d => {
    let batt = '';
    const md = ALL_MACHINE_DATA && ALL_MACHINE_DATA[d.file];
    if (md && md.slots) {
      const s = md.slots[d.slot];
      if (s && s.battery_current != null) batt = s.battery_current;
    }
    const cls = classifySerial(d.serial_number) || {};
    const t = ringAssignedTimestamp(d);
    const date = t ? t.getFullYear() + '-' + pad2(t.getMonth() + 1) + '-' + pad2(t.getDate()) : '';
    const time = t ? pad2(t.getHours()) + ':' + pad2(t.getMinutes()) + ':' + pad2(t.getSeconds()) : '';
    rows.push([date, time, d.file, d.slot, cls.sku || '', cls.category || '', batt, d.serial_number, d.ring_mac, d.state]);
  });
  const csv = rows.map(r => r.map(c => '"' + String(c).replace(/"/g, '""') + '"').join(',')).join('\n');
  const blob = new Blob([csv], { type: 'text/csv' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a'); a.href = url; a.download = 'ring_slots_' + new Date().toISOString().split('T')[0] + '.csv';
  document.body.appendChild(a); a.click(); document.body.removeChild(a); URL.revokeObjectURL(url);
}

function ringsStartWatching() { ringsWatching = true; ringsScheduleCheck(); }
function ringsScheduleCheck() { if (ringsWatching) ringsWatchTimer = setTimeout(ringsCheckChanges, 300); }
function ringsStopWatching() { ringsWatching = false; if (ringsWatchTimer) { clearTimeout(ringsWatchTimer); ringsWatchTimer = null; } ringsDirHandle = null; ringsFileHashes.clear(); ringsFileSizes.clear(); }

async function ringsCheckChanges() {
  if (!ringsDirHandle || !ringsWatching) { if (ringsWatching) ringsScheduleCheck(); return; }
  try {
    const currentFiles = new Set();
    const changed = [];
    for await (const entry of ringsDirHandle.values()) {
      if (entry.kind === 'file' && entry.name.toLowerCase().endsWith('.json')) {
        currentFiles.add(entry.name);
        try {
          const file = await entry.getFile();
          const oldSize = ringsFileSizes.get(entry.name);
          if (oldSize === undefined || file.size !== oldSize) {
            const text = await file.text();
            if (text.trim()) {
              const h = await ringsHash(text);
              if (h !== ringsFileHashes.get(entry.name)) {
                ringsFileSizes.set(entry.name, file.size); ringsFileHashes.set(entry.name, h);
                changed.push(entry.name);
                console.log('[RingsWatch] Change detected: ' + entry.name);
              }
            }
          }
        } catch (e) { console.warn('[RingsWatch] Error checking ' + entry.name + ': ' + e.message); }
      }
    }
    // Detect deleted files
    const deleted = [];
    for (const [fileName] of ringsFileHashes) {
      if (!currentFiles.has(fileName)) {
        ringsFileHashes.delete(fileName);
        ringsFileSizes.delete(fileName);
        deleted.push(fileName);
        console.log('[RingsWatch] File deleted: ' + fileName);
      }
    }
    if (changed.length > 0 || deleted.length > 0) {
      await loadRingsFromDir();
      console.log('[RingsWatch] Reloaded after ' + changed.length + ' change(s), ' + deleted.length + ' deletion(s)');
    }
  } catch (e) { console.warn('[RingsWatch] Error:', e.message); }
  if (ringsWatching) { clearTimeout(ringsWatchTimer); ringsScheduleCheck(); }
}

// ── Data Visualisation ──

let dvBarChart = null;
let dvCurrentCategory = null;
let dvCurrentSku = null;
let modalChartInstance = null;
let dvModalContext = null;
let currentModalExportData = [];
let dvSkuDetailChart = null;
let dvSkuBarChart = null;

const DV_CATEGORIES = [
  { name: 'AIR',           color: '#38BDF8', cardClass: 'air-card' },
  { name: 'PRO',           color: '#6366F1', cardClass: 'pro-card' },
  { name: 'DIESEL',        color: '#10B981', cardClass: 'diesel-card' },
  { name: 'RT CONVERSION', color: '#F59E0B', cardClass: 'rt-conversion-card' },
  { name: 'WABI SABI',     color: '#8B5CF6', cardClass: 'wabi-sabi-card' },
  { name: 'LUX',           color: '#EAB308', cardClass: 'lux-card' }
];

function dvCategoryColor(catName) {
  const def = DV_CATEGORIES.find(c => c.name === catName);
  return def ? def.color : '#94A3B8';
}

function classifySerial(serial) {
  if (!serial || serial === '--' || serial === 'N/A') return null;
  const parts = serial.split('-');
  const catCode = (parts[2] || '').toUpperCase();
  const modelCode = (parts[4] || '').toUpperCase();

  if (['IW1', 'IW2', 'IW3'].includes(catCode)) return { category: 'WABI SABI', sku: modelCode || '--' };
  if (['IR2', 'IR3', 'IR4'].includes(catCode)) return { category: 'RT CONVERSION', sku: modelCode || '--' };
  if (modelCode.startsWith('L')) return { category: 'LUX', sku: modelCode };
  if (modelCode.charAt(0) === 'D') return { category: 'DIESEL', sku: modelCode };
  if ((parts[0] || '').toUpperCase() === 'RA') return { category: 'AIR', sku: modelCode || '--' };
  if ((parts[0] || '').toUpperCase() === 'RP') return { category: 'PRO', sku: modelCode || '--' };
  return null;
}

function getSlotProduct(s) {
  if (!s) return null;
  if (s.product && String(s.product).trim() !== '' && String(s.product).trim() !== '--') return String(s.product).trim().toUpperCase();
  if (s.bdr_state && s.bdr_state.product && String(s.bdr_state.product).trim() !== '') return String(s.bdr_state.product).trim().toUpperCase();
  const cls = classifySerial(String(s.serial_number || '').trim());
  return cls ? cls.category : null;
}

function getSlotBdrRange(s) {
  const product = getSlotProduct(s);
  if (product === 'PRO') return { product, min: 1.8, max: 3.5 };
  return { product, min: 5.0, max: 12.0 };
}

const SLOT_BADGE_DEFS = {
  'PRO':           { key: 'pro',          label: 'PRO' },
  'AIR':           { key: 'air',          label: 'AIR' },
  'DIESEL':        { key: 'diesel',       label: 'DSL' },
  'LUX':           { key: 'lux',          label: 'LUX' },
  'WABI SABI':     { key: 'wabisabi',     label: 'WS' },
  'RT CONVERSION': { key: 'rtconversion', label: 'RTC' }
};

function slotBadgeHtml(serial) {
  const cls = classifySerial(String(serial || '').trim());
  if (!cls) return '';
  const def = SLOT_BADGE_DEFS[cls.category];
  if (!def) return '';
  return '<span class="slot-badge badge-' + def.key + '">' + def.label + '</span>';
}

function buildDataVizData() {
  const categories = {};
  DV_CATEGORIES.forEach(c => { categories[c.name] = { count: 0, skus: {} }; });
  ringsData.forEach(s => {
    const sn = (s.serial_number || '').toString().trim();
    const cls = classifySerial(sn);
    if (!cls) return;
    const cat = categories[cls.category];
    if (cat) {
      cat.count++;
      const sku = cls.sku;
      cat.skus[sku] = (cat.skus[sku] || 0) + 1;
    }
  });
  return categories;
}

function renderDataViz() {
  try {
    const empty = document.getElementById('dv-empty');
    const content = document.getElementById('dv-content');
    if (!empty || !content) {
      console.warn('Missing data-viz DOM elements');
      return;
    }
    if (!ringsData || ringsData.length === 0) {
      empty.style.display = 'flex';
      content.style.display = 'none';
      return;
    }
    empty.style.display = 'none';
    content.style.display = 'flex';
    const data = buildDataVizData();
    if (!data) {
      console.warn('buildDataVizData returned null');
      empty.style.display = 'flex';
      content.style.display = 'none';
      return;
    }
    if (isDrilldownActive || dvCurrentCategory) {
      dvRefreshDrilldownSoft();
      dvRefreshSerialsTab();
      return;
    }
    dvCurrentCategory = null;
    dvCurrentSku = null;
    renderDvMainView(data);
    dvRefreshSerialsTab();
  } catch (e) {
    console.warn('Error in renderDataViz:', e);
    const empty = document.getElementById('dv-empty');
    const content = document.getElementById('dv-content');
    if (empty && content) {
      empty.style.display = 'flex';
      content.style.display = 'none';
    }
  }
}

function renderDvMainView(data) {
  try {
    if (!data) {
      console.warn('renderDvMainView: data is null');
      return;
    }
    dvCurrentCategory = null;
    dvCurrentSku = null;
    const breadcrumb = document.getElementById('dv-breadcrumb');
    if (breadcrumb) {
      breadcrumb.innerHTML = '<span style="font-weight:600;color:var(--text);cursor:pointer;" onclick="renderDvMainView(buildDataVizData())">Categories</span>';
    }
    const nav = document.getElementById('dv-category-nav');
    if (nav) {
      nav.innerHTML = '';
    }
    const content = document.getElementById('dv-category-content');
    if (content) {
      dvDestroyDrillCharts();
      content.innerHTML = '';
    }
    renderDvSummaryCards(data);
    renderDvCharts(data);
    dvRenderCategoryBreakdown(data);

    DV_CATEGORIES.forEach(catDef => {
      const cat = catDef.name;
      const d = data[cat];
      if (!d || d.count === 0) return;
      const btn = document.createElement('button');
      btn.className = 'floorplan-toggle';
      btn.style.cssText = 'padding:10px 20px;font-size:13px;font-weight:700;border-color:' + catDef.color + ';color:' + catDef.color + ';';
      btn.innerHTML = cat + ' <span style="background:' + catDef.color + ';color:#fff;border-radius:10px;padding:1px 8px;font-size:11px;margin-left:6px;">' + d.count + '</span>';
      btn.onclick = () => renderDvCategory(d, cat, catDef.color, data);
      if (nav) nav.appendChild(btn);
    });
  } catch (e) {
    console.warn('Error in renderDvMainView:', e);
  }
}

function renderDvCategory(catData, catName, color, allData) {
  try {
    if (!catData || !allData) {
      console.warn('renderDvCategory: missing data');
      return;
    }
    dvCurrentCategory = catName;
    dvCurrentSku = null;
    const breadcrumb = document.getElementById('dv-breadcrumb');
    if (breadcrumb) {
      breadcrumb.innerHTML = '<span style="cursor:pointer;color:var(--muted);" onclick="renderDvMainView(buildDataVizData())">Categories</span> <span style="color:var(--muted);">/</span> <span style="font-weight:600;color:' + color + ';">' + catName + '</span>';
    }
    const nav = document.getElementById('dv-category-nav');
    if (nav) {
      nav.innerHTML = '';
    }
    const content = document.getElementById('dv-category-content');
    if (content) {
      dvDestroyDrillCharts();
      content.innerHTML = dvSkuVizBlock(catData, color, catName);
    }

    renderDvSkuBarChart(catData, color, catName);
    renderDvSummaryCards(allData, catName);
    renderDvCharts(allData, catData.skus || {});
  } catch (e) {
    console.warn('Error in renderDvCategory:', e);
  }
}

function renderDvSku(sku, count, color, catName) {
  dvCurrentSku = sku;
  const breadcrumb = document.getElementById('dv-breadcrumb');
  breadcrumb.innerHTML = '<span style="cursor:pointer;color:var(--muted);" onclick="renderDvMainView(buildDataVizData())">Categories</span> <span style="color:var(--muted);">/</span> ' +
    '<span style="cursor:pointer;color:' + color + ';" onclick="renderDvCategory(buildDataVizData()[\'' + catName + '\'],\'' + catName + '\',\'' + color + '\',buildDataVizData())">' + catName + '</span> <span style="color:var(--muted);">/</span> ' +
    '<span style="font-weight:600;color:var(--text);">' + sku + '</span>';
  const content = document.getElementById('dv-category-content');
  if (!content) return;
  const data = buildDataVizData();
  const rows = dvDrillRows(catName, sku).rows;
  dvDrillExportRows = rows;
  const counts = { RUNNING: 0, PASSED: 0, FAILED: 0, ASSIGNED: 0 };
  rows.forEach(r => { if (counts[r.state] != null) counts[r.state]++; });
  const machineSet = {};
  rows.forEach(r => { machineSet[r.machine] = (machineSet[r.machine] || 0) + 1; });
  const machineCount = Object.keys(machineSet).length;

  const chip = (label, val, chipColor) =>
    '<div class="dv-drill-chip" style="--drill-chip-accent:' + chipColor + ';">' +
    '<span class="dv-drill-chip-label">' + label + '</span><span class="dv-drill-chip-value">' + val + '</span></div>';
  const statusRow = '<div class="dv-drill-status-row">' +
    chip('Total', rows.length, color) +
    chip('Running', counts.RUNNING, '#3B82F6') +
    chip('Passed', counts.PASSED, '#22C55E') +
    chip('Failed', counts.FAILED, '#EF4444') +
    chip('Assigned', counts.ASSIGNED, '#F59E0B') +
    '</div>';

  const serialTable =
    '<div class="serials-actions" style="justify-content:space-between;margin-bottom:10px;">' +
      '<div class="section-label" style="margin:0;">Serials &mdash; Machine &amp; Slot</div>' +
      '<button class="premium-export-btn" type="button" onclick="dvExportDrillSerialsCsv()">' +
        '<svg viewBox="0 0 24 24" width="14" height="14" stroke="currentColor" stroke-width="2" fill="none" stroke-linecap="round" stroke-linejoin="round"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path><polyline points="7 10 12 15 17 10"></polyline><line x1="12" y1="15" x2="12" y2="3"></line></svg>' +
        '<span>Export CSV</span>' +
      '</button>' +
    '</div>' +
    '<div class="dv-drill-table-wrap">' +
      '<table class="ca-table dv-drill-table">' +
      '<thead><tr><th>Serial</th><th>Machine</th><th>Slot</th><th>Status</th><th>Workouts</th><th>Avg BDR</th><th>Current</th></tr></thead>' +
      '<tbody>' + dvDrillTableHtml(rows) + '</tbody>' +
      '</table>' +
    '</div>';

  content.innerHTML =
    '<div class="dv-sku-detail">' +
      '<div class="dv-sku-detail-head">' +
        '<div>' +
          '<div class="section-label" style="margin:0;">SKU Detail</div>' +
          '<div class="dv-sku-detail-sub">' + escapeHtml(String(sku)) + ' &middot; ' + rows.length + ' serials &middot; ' + machineCount + ' machine' + (machineCount === 1 ? '' : 's') + '</div>' +
        '</div>' +
      '</div>' +
      statusRow +
      '<div class="dv-sku-viz-grid" style="margin-top:14px;align-items:stretch;">' +
        '<div class="ops-heatmap-card" style="padding:14px;">' +
          '<div class="ops-section-title" style="margin-bottom:10px;">Serial Distribution by Machine</div>' +
          '<div id="dv-sku-machine-chart" style="height:250px;"></div>' +
        '</div>' +
        '<div class="ops-heatmap-card" style="padding:14px;">' + serialTable + '</div>' +
      '</div>' +
    '</div>';

  renderDvSkuMachineChart(rows, color);
  renderDvSummaryCards(data, catName);
}

function dvSkuVizBlock(catData, color, catName) {
  const skuEntries = Object.entries(catData.skus || {}).sort((a, b) => b[1] - a[1]);
  const total = skuEntries.reduce((s, e) => s + e[1], 0);
  const chips = skuEntries.map(([sku, cnt]) => {
    const escSku = String(sku).replace(/'/g, "\\'");
    const escCat = String(catName).replace(/'/g, "\\'");
    const go = "renderDvSku('" + escSku + "'," + cnt + ",'" + color + "','" + escCat + "')";
    return '<button type="button" class="dv-sku-chip" style="--sku-accent:' + color + ';" title="View ' + escapeHtml(String(sku)) + ' details" onclick="' + go + '">' +
      '<span class="dv-sku-chip-name">' + escapeHtml(String(sku)) + '</span>' +
      '<span class="dv-sku-chip-count">' + cnt + '</span>' +
      '</button>';
  }).join('');
  return '<div class="dv-sku-viz">' +
    '<div class="dv-sku-viz-head">' +
      '<div class="section-label" style="margin:0;">SKU Breakdown</div>' +
      '<span class="dv-sku-viz-sub">' + total + ' serials &middot; ' + skuEntries.length + ' SKUs</span>' +
    '</div>' +
    '<div id="dv-sku-bar" style="height:220px;"></div>' +
    '<div class="dv-sku-chips">' + chips + '</div>' +
  '</div>';
}

function renderDvSkuBarChart(catData, color, catName) {
  const chartEl = document.getElementById('dv-sku-bar');
  if (!chartEl) { dvSkuBarChart = null; return; }
  const entries = Object.entries(catData.skus || {}).sort((a, b) => b[1] - a[1]);
  if (entries.length === 0) {
    chartEl.innerHTML = '<div style="display:flex;align-items:center;justify-content:center;height:100%;color:var(--muted);font-size:13px;">No SKU data</div>';
    dvSkuBarChart = null;
    return;
  }
  const labels = entries.map(e => e[0]);
  const series = entries.map(e => e[1]);
  const colors = dvModalPalette(color, labels.length);
  const key = JSON.stringify(series) + '|' + JSON.stringify(labels) + '|' + color;
  if (dvSkuBarChart && dvSkuBarChart.__dvKey === key) return;
  const themeMode = document.documentElement.getAttribute('data-theme') === 'dark' ? 'dark' : 'light';
  const options = {
    chart: {
      type: 'bar',
      height: 220,
      toolbar: { show: false },
      events: {
        dataPointSelection: function(event, chartContext, config) {
          const i = config.dataPointIndex;
          if (i >= 0 && labels[i] != null) renderDvSku(labels[i], series[i], color, catName);
        }
      }
    },
    series: [{ name: 'Serials', data: series }],
    xaxis: { categories: labels, labels: { style: { fontSize: '11px' } } },
    yaxis: { labels: { style: { fontSize: '11px' } } },
    colors: colors,
    fill: {
      type: 'gradient',
      gradient: { shade: 'dark', type: 'vertical', shadeIntensity: 0.6, inverseColors: false, opacityFrom: 1, opacityTo: 0.5, stops: [0, 90, 100] }
    },
    plotOptions: { bar: { borderRadius: 6, borderRadiusApplication: 'end', columnWidth: '45%', distributed: true, dataLabels: { position: 'top' } } },
    dataLabels: { enabled: true, position: 'top', offsetY: -8, style: { fontSize: '11px', fontWeight: 700, colors: ['#94A3B8'] } },
    legend: { show: false },
    grid: getApexGrid(),
    theme: { mode: themeMode },
    tooltip: { theme: 'dark', y: { formatter: v => v + (v === 1 ? ' serial' : ' serials') } }
  };
  if (dvSkuBarChart) {
    try { dvSkuBarChart.destroy(); } catch (e) {}
    dvSkuBarChart = null;
  }
  dvSkuBarChart = new ApexCharts(chartEl, options);
  dvSkuBarChart.__dvKey = key;
  dvSkuBarChart.render();
}

function renderDvSkuMachineChart(rows, color) {
  const el = document.getElementById('dv-sku-machine-chart');
  if (!el) { dvSkuDetailChart = null; return; }
  if (dvSkuDetailChart) {
    try { dvSkuDetailChart.destroy(); } catch (e) {}
    dvSkuDetailChart = null;
  }
  if (!rows || rows.length === 0) {
    el.innerHTML = '<div style="display:flex;align-items:center;justify-content:center;height:100%;color:var(--muted);font-size:13px;">No serials in this SKU</div>';
    return;
  }
  const freq = {};
  rows.forEach(r => { freq[r.machine] = (freq[r.machine] || 0) + 1; });
  const entries = Object.entries(freq).sort((a, b) => b[1] - a[1] || String(a[0]).localeCompare(String(b[0]), undefined, { numeric: true }));
  const themeMode = document.documentElement.getAttribute('data-theme') === 'dark' ? 'dark' : 'light';
  dvSkuDetailChart = new ApexCharts(el, {
    chart: { type: 'bar', height: 250, toolbar: { show: false } },
    series: [{ name: 'Serials', data: entries.map(e => e[1]) }],
    xaxis: { categories: entries.map(e => e[0]), labels: { style: { fontSize: '11px' } } },
    plotOptions: { bar: { horizontal: true, borderRadius: 4, distributed: true } },
    colors: dvModalPalette(color, entries.length),
    dataLabels: { enabled: true, style: { fontSize: '11px', fontWeight: 700, colors: ['#fff'] } },
    legend: { show: false },
    grid: getApexGrid(),
    theme: { mode: themeMode },
    tooltip: { theme: 'dark', y: { formatter: v => v + (v === 1 ? ' serial' : ' serials') } }
  });
  dvSkuDetailChart.render();
}

function dvDestroyDrillCharts() {
  if (dvSkuBarChart) {
    try { dvSkuBarChart.destroy(); } catch (e) {}
    dvSkuBarChart = null;
  }
  if (dvSkuDetailChart) {
    try { dvSkuDetailChart.destroy(); } catch (e) {}
    dvSkuDetailChart = null;
  }
}


function renderDvSummaryCards(data, activeCategory) {
  const container = document.getElementById('dv-summary-cards');
  const total = Object.values(data).reduce((s, d) => s + d.count, 0);
  container.innerHTML = '<div class="kpi-card total-serials-card' + (!activeCategory ? ' active' : '') + '" role="button" tabindex="0" title="Back to all categories" onclick="renderDvMainView(buildDataVizData())">' +
    '<div class="card-header"><span class="color-indicator"></span><span class="card-label">TOTAL SERIALS</span></div>' +
    '<div class="card-body"><h1 class="metric-value">' + total + '</h1></div>' +
    '<div class="card-footer"><span class="sub-text">All categories</span></div>' +
    '</div>' +
    DV_CATEGORIES.map(catDef => {
      const d = data[catDef.name];
      if (!d || d.count === 0) return '';
      const pct = total > 0 ? (d.count / total * 100).toFixed(1) : 0;
      const active = activeCategory === catDef.name ? ' active' : '';
      return '<div class="kpi-card ' + catDef.cardClass + active + '" role="button" tabindex="0" title="Drill into ' + catDef.name + '" onclick="renderDvKpiDrilldown(\'' + catDef.name.replace(/'/g, "\\'") + '\',\'' + catDef.color + '\')">' +
        '<div class="card-header"><span class="color-indicator"></span><span class="card-label">' + catDef.name + '</span></div>' +
        '<div class="card-body"><h1 class="metric-value">' + d.count + '</h1></div>' +
        '<div class="card-footer"><span class="sub-text">' + Object.keys(d.skus).length + ' SKUs | ' + pct + '%</span></div>' +
        '</div>';
    }).join('');
}

function dvDrillCategorySerials(catName) {
  const rows = [];
  (ringsData || []).forEach(r => {
    const sn = String(r.serial_number || '').trim();
    const cls = classifySerial(sn);
    if (cls && cls.category === catName) {
      rows.push(r);
    }
  });
  return rows;
}

function dvDrillSlotFor(machineName, slotKey) {
  if (!machineName || slotKey == null) return null;
  const md = ALL_MACHINE_DATA || {};
  const direct = md[machineName];
  if (direct && direct.slots) return direct.slots[String(slotKey)] || null;
  const norm = String(machineName).toLowerCase();
  for (const key of Object.keys(md)) {
    if (key.toLowerCase() === norm && md[key].slots) {
      return md[key].slots[String(slotKey)] || null;
    }
  }
  return null;
}

function dvDrillSlotState(ringRec) {
  const s = (ringRec.state || '').toUpperCase();
  if (s === 'BDR_RUNNING') return 'RUNNING';
  if (s === 'PASSED' || s === 'PASS') return 'PASSED';
  if (s === 'FAILED') return 'FAILED';
  const sn = String(ringRec.serial_number || '').trim();
  if (sn && sn !== '--' && sn !== 'N/A') return 'ASSIGNED';
  return 'EMPTY';
}

function dvDrillRows(catName, sku) {
  const serials = (sku != null)
    ? (ringsData || []).filter(r => {
        const sn = String(r.serial_number || '').trim();
        const cls = classifySerial(sn);
        return !!cls && cls.category === catName && cls.sku === sku;
      })
    : dvDrillCategorySerials(catName);
  const counts = { TOTAL: serials.length, RUNNING: 0, PASSED: 0, FAILED: 0, ASSIGNED: 0 };
  const rows = serials.map(r => {
    const st = dvDrillSlotState(r);
    if (counts[st] != null) counts[st]++;
    const slotData = dvDrillSlotFor(r.file, r.slot);
    const workouts = slotData ? calculateCompletedCycleWorkouts(slotData) : [];
    const avgBdr = slotData ? getSlotAvgBdr(slotData, workouts) : null;
    const lastBatt = slotData && slotData.battery_current != null ? slotData.battery_current : null;
    return {
      serial: String(r.serial_number || '--'),
      machine: String(r.file || '--'),
      slot: String(r.slot == null ? '--' : r.slot),
      state: st,
      stateRaw: String(r.state || '--'),
      workouts: workouts,
      avgBdr: avgBdr,
      battery: lastBatt,
      hasCycle: !!slotData
    };
  });
  return { rows: rows, counts: counts };
}

function dvDrillTableHtml(rows) {
  const badgeCls = st => st === 'RUNNING' ? 'ok' : st === 'PASSED' ? 'pass' : st === 'FAILED' ? 'danger' : 'neutral';
  if (!rows || rows.length === 0) {
    return '<tr><td colspan="7" style="text-align:center;color:var(--muted);">No serials in this category</td></tr>';
  }
  return rows.map(r =>
    '<tr>' +
    '<td style="font-family:var(--f-mono);font-weight:600;">' + escapeHtml(r.serial) + '</td>' +
    '<td>' + escapeHtml(r.machine) + '</td>' +
    '<td>' + escapeHtml(r.slot) + '</td>' +
    '<td><span class="badge ' + badgeCls(r.state) + '">' + r.state + '</span></td>' +
    '<td>' + r.workouts.length + '</td>' +
    '<td>' + (r.avgBdr != null ? r.avgBdr.toFixed(2) : '<span class="dv-drill-muted">—</span>') + '</td>' +
    '<td>' + (r.battery != null ? r.battery.toFixed(2) + ' mA' : '<span class="dv-drill-muted">—</span>') + '</td>' +
    '</tr>'
  ).join('');
}

const DV_WORKOUT_MAX = 6;

function dvWorkoutDistRows(catRows) {
  const machines = {};
  (catRows || []).forEach(r => {
    const key = String(r.machine || '--');
    if (!machines[key]) {
      machines[key] = { occupied: 0, buckets: new Array(DV_WORKOUT_MAX + 1).fill(0) };
    }
    machines[key].occupied++;
    const wc = (r.workouts && r.workouts.length) || 0;
    machines[key].buckets[Math.min(wc, DV_WORKOUT_MAX)]++;
  });
  return Object.entries(machines).sort((a, b) =>
    String(a[0]).localeCompare(String(b[0]), undefined, { numeric: true })
  );
}

function dvWorkoutDistBodyHtml(catRows) {
  const rows = dvWorkoutDistRows(catRows);
  if (rows.length === 0) {
    return '<tr><td colspan="' + (DV_WORKOUT_MAX + 3) + '" style="text-align:center;color:var(--muted);padding:14px;">No serials with cycle data</td></tr>';
  }
  return rows.map(([machine, m]) => {
    let tr = '<tr><td style="font-family:var(--f-mono);font-weight:600;">' + escapeHtml(machine) + '</td>' +
      '<td>' + m.occupied + '</td>' +
      '<td class="dv-wk-0">' + m.buckets[0] + '</td>';
    for (let w = 1; w <= DV_WORKOUT_MAX; w++) {
      tr += '<td' + (w === DV_WORKOUT_MAX ? ' class="dv-wk-6"' : '') + '>' + m.buckets[w] + '</td>';
    }
    tr += '</tr>';
    return tr;
  }).join('');
}

function dvWorkoutDistTableHtml(catRows) {
  let head = '<thead><tr><th>Machine</th><th>Serials</th><th>No Workout</th>';
  for (let w = 1; w <= DV_WORKOUT_MAX; w++) {
    head += '<th' + (w === DV_WORKOUT_MAX ? ' class="dv-wk-6"' : '') + '>' + ordinal(w) + '</th>';
  }
  head += '</tr></thead><tbody>';
  return '<table class="ca-table ca-table-compact dv-workout-dist-table">' +
    head + dvWorkoutDistBodyHtml(catRows) + '</tbody></table>';
}

function renderDvKpiDrilldown(catName, color) {
  try {
    const data = buildDataVizData();
    const catData = data && data[catName];
    if (!catData || catData.count === 0) {
      console.warn('renderDvKpiDrilldown: no data for category ' + catName);
      return;
    }
    dvCurrentCategory = catName;
    dvCurrentSku = null;

    const breadcrumb = document.getElementById('dv-breadcrumb');
    if (breadcrumb) {
      breadcrumb.innerHTML = '<span style="cursor:pointer;color:var(--muted);" onclick="renderDvMainView(buildDataVizData())">Categories</span> <span style="color:var(--muted);">/</span> <span style="font-weight:600;color:' + color + ';">' + catName + ' <span style="color:var(--muted);font-weight:500;">Ring Status</span></span>';
    }
    const nav = document.getElementById('dv-category-nav');
    if (nav) nav.innerHTML = '';
    const content = document.getElementById('dv-category-content');
    if (content) {
      dvDestroyDrillCharts();
      content.innerHTML = '';
    }

    const skuBlock = dvSkuVizBlock(catData, color, catName);

    const { rows, counts } = dvDrillRows(catName);
    const statusColors = { RUNNING: '#3B82F6', PASSED: '#22C55E', FAILED: '#EF4444', ASSIGNED: '#F59E0B' };

    const chip = (label, val, chipColor, st) => {
      const clickable = st === 'RUNNING' || st === 'PASSED' || st === 'FAILED' || st === 'ASSIGNED';
      const base = 'data-status="' + (st || '') + '"';
      if (clickable) {
        const fn = "dvOpenStatusModal('" + catName.replace(/'/g, "\\'") + "','" + st + "','" + color.replace(/'/g, "\\'") + "')";
        return '<div class="dv-drill-chip dv-drill-chip-clickable" role="button" tabindex="0" ' + base +
          ' title="View ' + label + ' units"' +
          ' onclick="' + fn + '"' +
          ' onkeydown="if(event.key===\'Enter\'||event.key===\' \'){event.preventDefault();' + fn + '}"' +
          ' style="--drill-chip-accent:' + chipColor + ';cursor:pointer;">' +
          '<span class="dv-drill-chip-label">' + label + '</span><span class="dv-drill-chip-value">' + val + '</span></div>';
      }
      return '<div class="dv-drill-chip" ' + base + ' style="--drill-chip-accent:' + chipColor + ';">' +
        '<span class="dv-drill-chip-label">' + label + '</span><span class="dv-drill-chip-value">' + val + '</span></div>';
    };

    const statusRow = '<div class="dv-drill-status-row">' +
      chip('Total', counts.TOTAL, color, 'TOTAL') +
      chip('Running', counts.RUNNING, statusColors.RUNNING, 'RUNNING') +
      chip('Passed', counts.PASSED, statusColors.PASSED, 'PASSED') +
      chip('Failed', counts.FAILED, statusColors.FAILED, 'FAILED') +
      chip('Assigned', counts.ASSIGNED, statusColors.ASSIGNED, 'ASSIGNED') +
      '</div>';

    const serialTable =
      '<div class="serials-actions" style="justify-content:space-between;margin-bottom:12px;">' +
        '<div class="section-label" style="margin:0;">Serials &mdash; Machine &amp; Slot</div>' +
        '<button id="btn-export-drill-serials" class="premium-export-btn" type="button">' +
          '<svg viewBox="0 0 24 24" width="14" height="14" stroke="currentColor" stroke-width="2" fill="none" stroke-linecap="round" stroke-linejoin="round"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path><polyline points="7 10 12 15 17 10"></polyline><line x1="12" y1="15" x2="12" y2="3"></line></svg>' +
          '<span>Export CSV</span>' +
        '</button>' +
      '</div>' +
      '<div class="dv-drill-table-wrap">' +
      '<table class="ca-table dv-drill-table">' +
      '<thead><tr><th>Serial</th><th>Machine</th><th>Slot</th><th>Status</th><th>Workouts</th><th>Avg BDR</th><th>Current</th></tr></thead>' +
      '<tbody>' + dvDrillTableHtml(rows) + '</tbody>' +
      '</table></div>';

    const cycleSection =
      '<div class="section-label" style="margin-bottom:8px;">Cycle Analysis &mdash; Workout Distribution (per Machine)</div>' +
      '<div class="dv-drill-table-wrap">' + dvWorkoutDistTableHtml(rows, color) + '</div>';

    const drillTabs =
      '<div class="drill-sub-tabs" role="tablist">' +
        '<button type="button" class="drill-sub-tab active" role="tab" aria-selected="true" data-target="drill-analytics">Analytics</button>' +
        '<button type="button" class="drill-sub-tab" role="tab" aria-selected="false" data-target="drill-serials">Serials (' + rows.length + ')</button>' +
      '</div>';

    content.innerHTML = drillTabs +
      '<div id="drill-analytics" class="drill-sub-panel">' + statusRow + cycleSection + skuBlock + '</div>' +
      '<div id="drill-serials" class="drill-sub-panel" style="display:none;">' + serialTable + '</div>';

    dvDrillExportRows = rows;

    renderDvSkuBarChart(catData, color, catName);
    renderDvSummaryCards(data, catName);
    renderDvCharts(data);
  } catch (e) {
    console.warn('Error in renderDvKpiDrilldown:', e);
  }
}

function dvSetDrillTab(target) {
  const content = document.getElementById('dv-category-content');
  if (!content) return;
  content.querySelectorAll('.drill-sub-tab').forEach(b => {
    const on = b.dataset.target === target;
    b.classList.toggle('active', on);
    b.setAttribute('aria-selected', on ? 'true' : 'false');
  });
  content.querySelectorAll('.drill-sub-panel').forEach(p => {
    p.style.display = p.id === target ? 'block' : 'none';
  });
}

function dvExportDrillSerialsCsv() {
  if (!dvDrillExportRows || dvDrillExportRows.length === 0) {
    dvFlashExportEmpty('btn-export-drill-serials');
    return;
  }
  const csvContent = 'Serial,Machine,Slot,Status,Workouts,Avg BDR,Current mA\n' + dvDrillExportRows.map(r =>
    [dvCsvEscape(r.serial), dvCsvEscape(r.machine), dvCsvEscape(r.slot), dvCsvEscape(r.state), r.workouts.length,
     r.avgBdr != null ? r.avgBdr.toFixed(2) : '', r.battery != null ? r.battery.toFixed(2) : ''].join(',')
  ).join('\n');
  const baseName = String(dvCurrentCategory || 'Drill').replace(/[^A-Za-z0-9_-]+/g, '_') +
    (dvCurrentSku ? '_' + String(dvCurrentSku).replace(/[^A-Za-z0-9_-]+/g, '_') : '');
  dvTriggerCsvDownload(csvContent, baseName + '_Serials.csv');
}

function dvStatusUnits(catName, status) {
  const rows = [];
  (ringsData || []).forEach(r => {
    const sn = String(r.serial_number || '').trim();
    const cls = classifySerial(sn);
    if (cls && cls.category === catName && dvDrillSlotState(r) === status) {
      rows.push({
        machine: String(r.file || '--'),
        slot: String(r.slot == null ? '--' : r.slot),
        serial: sn || '--'
      });
    }
  });
  rows.sort((a, b) => {
    if (a.machine !== b.machine) return a.machine.localeCompare(b.machine, undefined, { numeric: true });
    const na = parseInt(a.slot, 10), nb = parseInt(b.slot, 10);
    if (!isNaN(na) && !isNaN(nb)) return na - nb;
    return String(a.slot).localeCompare(String(b.slot), undefined, { numeric: true });
  });
  return rows;
}

function dvOpenStatusModal(catName, status, color) {
  const modal = document.getElementById('dv-status-modal');
  if (!modal) return;
  isDrilldownActive = true;
  dvModalContext = { catName: catName, status: status, color: color };
  const rows = dvStatusUnits(catName, status);
  currentModalExportData = rows;
  const title = document.getElementById('dv-status-modal-title');
  const subtitle = document.getElementById('dv-status-modal-subtitle');
  const body = document.getElementById('dv-status-modal-body');
  if (title) title.textContent = catName + ' - ' + status + ' Units';
  if (subtitle) subtitle.textContent = 'Category: ' + catName + ' | Status: ' + status + ' | ' + rows.length + ' unit' + (rows.length === 1 ? '' : 's');
  if (body) {
    body.innerHTML = rows.length === 0
      ? '<tr><td class="drilldown-empty" colspan="3">No units match ' + escapeHtml(catName) + ' / ' + escapeHtml(status) + '</td></tr>'
      : rows.map(r =>
          '<tr><td>' + escapeHtml(r.machine) + '</td><td>' + escapeHtml(r.slot) + '</td><td style="font-family:var(--f-mono);font-weight:600;">' + escapeHtml(r.serial) + '</td></tr>'
        ).join('');
  }
  dvRenderAnalyticsSummary(rows);
  dvSetModalTab('tab-analytics');
  modal.style.display = 'flex';
}

function dvMixHex(hex, target, t) {
  const a = parseInt(hex.slice(1), 16);
  const b = parseInt(target.slice(1), 16);
  const r = Math.round(((a >> 16) & 255) + ((((b >> 16) & 255) - ((a >> 16) & 255)) * t));
  const g = Math.round(((a >> 8) & 255) + ((((b >> 8) & 255) - ((a >> 8) & 255)) * t));
  const bl = Math.round((a & 255) + (((b & 255) - (a & 255)) * t));
  return '#' + ((1 << 24) + (r << 16) + (g << 8) + bl).toString(16).slice(1);
}

function dvModalPalette(base, n) {
  const themeMode = document.documentElement.getAttribute('data-theme') === 'dark' ? 'dark' : 'light';
  const target = themeMode === 'dark' ? '#0B1220' : '#FFFFFF';
  const out = [];
  for (let i = 0; i < n; i++) {
    const t = n === 1 ? 0 : 0.5 * (1 - i / (n - 1));
    out.push(dvMixHex(base, target, t));
  }
  return out;
}

function dvModalChartConfig(rows, status, fallbackColor) {
  if (!rows || rows.length === 0) return null;
  const freq = {};
  rows.forEach(r => { freq[r.machine] = (freq[r.machine] || 0) + 1; });
  const entries = Object.entries(freq).sort((a, b) =>
    b[1] - a[1] || String(a[0]).localeCompare(String(b[0]), undefined, { numeric: true })
  );
  const statusColors = { RUNNING: '#3B82F6', PASSED: '#22C55E', FAILED: '#EF4444', ASSIGNED: '#F59E0B' };
  const chartColor = statusColors[status] || fallbackColor || '#0D9488';
  const themeMode = document.documentElement.getAttribute('data-theme') === 'dark' ? 'dark' : 'light';
  const labels = entries.map(e => e[0]);
  return {
    options: {
      chart: {
        type: 'bar',
        height: 250,
        toolbar: { show: false },
        events: {
          dataPointSelection: function(event, chartContext, config) {
            dvOpenSkuDrilldown(config.w.globals.labels[config.dataPointIndex]);
          }
        }
      },
      series: [{ name: status + ' Units', data: entries.map(e => e[1]) }],
      xaxis: { categories: labels, labels: { style: { fontSize: '11px' }, rotate: -45 } },
      colors: dvModalPalette(chartColor, labels.length),
      fill: {
        type: 'gradient',
        gradient: { shade: 'dark', type: 'vertical', shadeIntensity: 0.5, inverseColors: false, opacityFrom: 1, opacityTo: 0.8, stops: [0, 100] }
      },
      plotOptions: { bar: { borderRadius: 4, columnWidth: '45%', distributed: true } },
      dataLabels: { enabled: true, position: 'top', offsetY: -6, style: { fontSize: '11px', fontWeight: 700, colors: ['#94A3B8'] } },
      legend: { show: false },
      grid: getApexGrid(),
      theme: { mode: themeMode },
      tooltip: { theme: 'dark', y: { formatter: v => v + (v === 1 ? ' unit' : ' units') } }
    }
  };
}

function renderDvModalChart(rows, catName, status, fallbackColor) {
  const chartEl = document.getElementById('drilldown-modal-chart');
  if (!chartEl) return;
  if (modalChartInstance) {
    try { modalChartInstance.destroy(); } catch (e) {}
    modalChartInstance = null;
  }
  chartEl.innerHTML = '';
  const cfg = dvModalChartConfig(rows, status, fallbackColor);
  if (!cfg) {
    chartEl.innerHTML = '<div style="display:flex;align-items:center;justify-content:center;height:100%;color:var(--muted);font-size:13px;">No data to chart</div>';
    return;
  }
  modalChartInstance = new ApexCharts(chartEl, cfg.options);
  modalChartInstance.render();
}

function dvUpdateModalChart(rows, status, fallbackColor) {
  const chartEl = document.getElementById('drilldown-modal-chart');
  if (!chartEl) return;
  const cfg = dvModalChartConfig(rows, status, fallbackColor);
  if (!cfg) {
    if (modalChartInstance) {
      try { modalChartInstance.destroy(); } catch (e) {}
      modalChartInstance = null;
    }
    chartEl.innerHTML = '<div style="display:flex;align-items:center;justify-content:center;height:100%;color:var(--muted);font-size:13px;">No data to chart</div>';
    return;
  }
  if (modalChartInstance) {
    modalChartInstance.updateOptions({
      series: cfg.options.series,
      xaxis: cfg.options.xaxis,
      colors: cfg.options.colors,
      fill: cfg.options.fill
    });
  } else {
    modalChartInstance = new ApexCharts(chartEl, cfg.options);
    modalChartInstance.render();
  }
}

function dvCountStatuses(catName) {
  const counts = { RUNNING: 0, PASSED: 0, FAILED: 0, ASSIGNED: 0 };
  (ringsData || []).forEach(r => {
    const sn = String(r.serial_number || '').trim();
    const cls = classifySerial(sn);
    if (cls && cls.category === catName) {
      const st = dvDrillSlotState(r);
      if (counts[st] != null) counts[st]++;
    }
  });
  return counts;
}

function dvRefreshDrilldownSoft() {
  try {
    if (dvCurrentCategory) {
      dvRefreshCategorySoft(dvCurrentCategory);
    }
    const data = buildDataVizData();
    if (data) {
      const total = Object.values(data).reduce((s, d) => s + d.count, 0);
      const totalEl = document.querySelector('#dv-summary-cards .total-serials-card .metric-value');
      if (totalEl) totalEl.textContent = total;
      DV_CATEGORIES.forEach(catDef => {
        const d = data[catDef.name];
        const cardEl = document.querySelector('#dv-summary-cards .' + catDef.cardClass + ' .metric-value');
        if (cardEl) cardEl.textContent = d ? d.count : 0;
      });
    }
    if (dvModalContext) {
      const { catName, status, color } = dvModalContext;
      const rows = dvStatusUnits(catName, status);
      currentModalExportData = rows;
      const subtitle = document.getElementById('dv-status-modal-subtitle');
      if (subtitle) {
        subtitle.textContent = 'Category: ' + catName + ' | Status: ' + status + ' | ' + rows.length + ' unit' + (rows.length === 1 ? '' : 's');
      }
      const tbody = document.getElementById('dv-status-modal-body');
      if (tbody) {
        tbody.innerHTML = rows.length === 0
          ? '<tr><td class="drilldown-empty" colspan="3">No units match ' + escapeHtml(catName) + ' / ' + escapeHtml(status) + '</td></tr>'
          : rows.map(r =>
              '<tr><td>' + escapeHtml(r.machine) + '</td><td>' + escapeHtml(r.slot) + '</td><td style="font-family:var(--f-mono);font-weight:600;">' + escapeHtml(r.serial) + '</td></tr>'
            ).join('');
      }
      dvRenderAnalyticsSummary(rows);
      dvUpdateModalChart(rows, status, color);
    }
  } catch (e) {
    console.warn('Error in dvRefreshDrilldownSoft:', e);
  }
}

function dvRefreshCategorySoft(catName) {
  const content = document.getElementById('dv-category-content');
  if (!content) return;
  if (content.querySelector('.dv-drill-status-row')) {
    dvRefreshKpiDrilldownSoft(catName);
    return;
  }
  const data = buildDataVizData();
  const catData = data && data[catName];
  const color = dvCategoryColor(catName);
  if (!catData || catData.count === 0) {
    dvCurrentCategory = null;
    dvCurrentSku = null;
    renderDvMainView(data);
    return;
  }
  if (dvCurrentSku) {
    const freshCount = (catData.skus || {})[dvCurrentSku];
    if (freshCount == null) {
      dvCurrentSku = null;
      renderDvCategory(catData, catName, color, data);
    } else {
      renderDvSku(dvCurrentSku, freshCount, color, catName);
    }
  } else {
    renderDvCategory(catData, catName, color, data);
  }
}

function dvRefreshKpiDrilldownSoft(catName) {
  const content = document.getElementById('dv-category-content');
  if (!content) return;
  const { rows, counts } = dvDrillRows(catName);
  const color = dvCategoryColor(catName);
  content.querySelectorAll('.dv-drill-chip[data-status]').forEach(chip => {
    const st = chip.dataset.status;
    const val = st === 'TOTAL' ? counts.TOTAL : (st && counts[st] != null ? counts[st] : null);
    if (val != null) {
      const el = chip.querySelector('.dv-drill-chip-value');
      if (el) el.textContent = val;
    }
  });
  const tbody = content.querySelector('#drill-serials .dv-drill-table tbody');
  if (tbody) tbody.innerHTML = dvDrillTableHtml(rows);
  const wdBody = content.querySelector('#drill-analytics .dv-workout-dist-table tbody');
  if (wdBody) wdBody.innerHTML = dvWorkoutDistBodyHtml(rows, color);
  dvDrillExportRows = rows;
  content.querySelectorAll('.drill-sub-tab[data-target="drill-serials"]').forEach(b => {
    b.innerHTML = 'Serials (' + rows.length + ')';
  });
  const catData = buildDataVizData();
  const fresh = catData && catData[catName];
  if (fresh) {
    renderDvSkuBarChart(fresh, color, catName);
    const chips = content.querySelectorAll('.dv-sku-chip');
    chips.forEach(chip => {
      const nameEl = chip.querySelector('.dv-sku-chip-name');
      if (!nameEl) return;
      const nm = nameEl.textContent;
      const cnt = fresh.skus[nm] != null ? fresh.skus[nm] : 0;
      const cntEl = chip.querySelector('.dv-sku-chip-count');
      if (cntEl) cntEl.textContent = cnt;
    });
    const sub = content.querySelector('.dv-sku-viz-sub');
    if (sub) {
      const totals = Object.values(fresh.skus).reduce((s, v) => s + v, 0);
      sub.textContent = totals + ' serials &middot; ' + Object.keys(fresh.skus).length + ' SKUs';
    }
  }
}

function dvCloseStatusModal() {
  isDrilldownActive = false;
  dvModalContext = null;
  if (modalChartInstance) {
    try { modalChartInstance.destroy(); } catch (e) {}
    modalChartInstance = null;
  }
  const modal = document.getElementById('dv-status-modal');
  if (modal) modal.style.display = 'none';
  dvCloseSkuDrilldown();
}

document.addEventListener('keydown', function(e) {
  if (e.key === 'Escape') {
    const sku = document.getElementById('sku-drilldown-overlay');
    if (sku && sku.style.display === 'flex') {
      dvCloseSkuDrilldown();
      return;
    }
    const modal = document.getElementById('dv-status-modal');
    if (modal && modal.style.display === 'flex') dvCloseStatusModal();
  }
  if (e.key === 'ArrowLeft' || e.key === 'ArrowRight') {
    const modal = document.getElementById('dv-status-modal');
    if (!modal || modal.style.display !== 'flex') return;
    const sku = document.getElementById('sku-drilldown-overlay');
    if (sku && sku.style.display === 'flex') return;
    const btns = Array.from(document.querySelectorAll('#dv-status-modal .tab-btn'));
    const idx = btns.findIndex(b => b.classList.contains('active'));
    if (idx === -1) return;
    const next = e.key === 'ArrowRight' ? (idx + 1) % btns.length : (idx - 1 + btns.length) % btns.length;
    dvSetModalTab(btns[next].dataset.target);
    e.preventDefault();
  }
});

function dvSetModalTab(target) {
  const tabs = document.querySelectorAll('#dv-status-modal .tab-btn');
  tabs.forEach(b => {
    const isActive = b.dataset.target === target;
    b.classList.toggle('active', isActive);
    b.setAttribute('aria-selected', isActive ? 'true' : 'false');
  });
  ['tab-analytics', 'tab-serials'].forEach(id => {
    const el = document.getElementById(id);
    if (el) el.style.display = id === target ? 'block' : 'none';
  });
  if (target === 'tab-analytics') dvRevealAnalyticsTab();
}

function dvRevealAnalyticsTab() {
  if (!dvModalContext) return;
  const ctx = dvModalContext;
  const rows = dvStatusUnits(ctx.catName, ctx.status);
  currentModalExportData = rows;
  renderDvModalChart(rows, ctx.catName, ctx.status, ctx.color);
  dvRenderAnalyticsSummary(rows);
}

function dvAnalyticsSummaryHtml(rows) {
  if (!rows || rows.length === 0) {
    return '<tr><td class="drilldown-empty" colspan="3">No units to summarize</td></tr>';
  }
  const freq = {};
  rows.forEach(r => { freq[r.machine] = (freq[r.machine] || 0) + 1; });
  const entries = Object.entries(freq).sort((a, b) => b[1] - a[1] || String(a[0]).localeCompare(String(b[0]), undefined, { numeric: true }));
  const total = rows.length;
  return entries.map(([m, c]) =>
    '<tr><td style="font-family:var(--f-mono);font-weight:600;">' + escapeHtml(m) + '</td><td>' + c + '</td><td>' + (total ? (c / total * 100).toFixed(1) : '0.0') + '%</td></tr>'
  ).join('');
}

function dvRenderAnalyticsSummary(rows) {
  const tbody = document.getElementById('analytics-summary-body');
  if (!tbody) return;
  tbody.innerHTML = dvAnalyticsSummaryHtml(rows);
}

function dvOpenSkuDrilldown(machine) {
  const overlay = document.getElementById('sku-drilldown-overlay');
  if (!overlay || !dvModalContext) return;
  const ctx = dvModalContext;
  const rows = dvStatusUnits(ctx.catName, ctx.status).filter(r => r.machine === machine);
  const skuMap = {};
  rows.forEach(r => {
    const cls = classifySerial(String(r.serial || '--'));
    const sku = cls && cls.sku ? cls.sku : 'Unknown';
    skuMap[sku] = (skuMap[sku] || 0) + 1;
  });
  const entries = Object.entries(skuMap).sort((a, b) => b[1] - a[1] || String(a[0]).localeCompare(String(b[0])));
  const total = rows.length;

  const title = document.getElementById('sku-drilldown-title');
  if (title) title.textContent = machine + ' \u2014 SKU Breakdown';
  const subtitle = document.getElementById('sku-drilldown-subtitle');
  if (subtitle) subtitle.textContent = ctx.catName + ' \u00b7 ' + ctx.status + ' \u00b7 ' + total + ' unit' + (total === 1 ? '' : 's');

  const summary = document.getElementById('sku-drilldown-summary');
  if (summary) {
    summary.innerHTML = entries.length === 0
      ? ''
      : entries.map(([sku, c]) =>
          '<span class="sku-chip"><span>' + escapeHtml(sku) + '</span><span class="sku-chip-count">' + c + '</span></span>'
        ).join('');
  }

  const content = document.getElementById('sku-drilldown-content');
  if (content) {
    content.innerHTML = entries.length === 0
      ? '<div class="drilldown-empty">No units match ' + escapeHtml(machine) + '</div>'
      : '<table class="drilldown-table sku-drilldown-table">' +
        '<thead><tr><th>SKU</th><th>Units</th><th>% Share</th></tr></thead>' +
        '<tbody>' + entries.map(([sku, c]) =>
          '<tr><td style="font-family:var(--f-mono);font-weight:600;">' + escapeHtml(sku) + '</td><td>' + c + '</td><td>' + (total ? (c / total * 100).toFixed(1) : '0.0') + '%</td></tr>'
        ).join('') + '</tbody>' +
        '</table>';
  }

  overlay.style.display = 'flex';
}

function dvCloseSkuDrilldown() {
  const overlay = document.getElementById('sku-drilldown-overlay');
  if (overlay) overlay.style.display = 'none';
}

function dvBackToChart() {
  dvCloseSkuDrilldown();
}

function dvCsvEscape(v) {
  const s = String(v == null ? '' : v);
  if (/[",\n]/.test(s)) return '"' + s.replace(/"/g, '""') + '"';
  return s;
}

function dvTriggerCsvDownload(csvContent, filename) {
  const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}

function dvFlashExportEmpty(btnId) {
  const btn = document.getElementById(btnId);
  if (!btn) return;
  const orig = btn.innerHTML;
  btn.disabled = true;
  btn.innerHTML = 'No data';
  setTimeout(() => { btn.disabled = false; btn.innerHTML = orig; }, 1200);
}

function dvExportSerialsCsv() {
  const ctx = dvModalContext || {};
  if (!currentModalExportData || currentModalExportData.length === 0) {
    dvFlashExportEmpty('btn-export-serials');
    return;
  }
  const csvContent = 'Machine,Slot,Serial Number\n' + currentModalExportData.map(r =>
    [dvCsvEscape(r.machine), dvCsvEscape(r.slot), dvCsvEscape(r.serial)].join(',')
  ).join('\n');
  dvTriggerCsvDownload(csvContent, 'Export_' + String(ctx.catName || 'Drilldown').replace(/[^A-Za-z0-9_-]+/g, '_') + '_' + String(ctx.status || 'Units').replace(/[^A-Za-z0-9_-]+/g, '_') + '.csv');
}

(function initModalTabs() {
  const tabsEl = document.querySelector('.modal-tabs');
  if (tabsEl) {
    tabsEl.addEventListener('click', function(e) {
      const btn = e.target.closest && e.target.closest('.tab-btn');
      if (!btn) return;
      dvSetModalTab(btn.dataset.target);
    });
  }
  const exportBtn = document.getElementById('btn-export-serials');
  if (exportBtn) {
    exportBtn.addEventListener('click', function() {
      if (exportBtn.disabled) return;
      dvExportSerialsCsv();
    });
  }
})();

/* ── Data Viz master tabbed architecture ── */

let currentAllSerialsExportData = [];
let dvDrillExportRows = [];

function dvSetVizTab(target) {
  const content = document.getElementById('dv-content');
  const btns = Array.from(document.querySelectorAll('.premium-nav-tabs .viz-tab-btn'));
  const panels = Array.from(document.querySelectorAll('#dv-content .viz-tab-content'));
  btns.forEach(b => {
    const on = b.dataset.target === target;
    b.classList.toggle('active', on);
    b.setAttribute('aria-selected', on ? 'true' : 'false');
  });
  panels.forEach(p => {
    const on = p.id === target;
    p.classList.toggle('active', on);
    p.style.display = on ? 'flex' : 'none';
  });
  if (content) content.setAttribute('data-active-tab', target);
  if (target === 'viz-analysis') dvRenderAnalysisTab();
  if (target === 'viz-serials') renderDvGlobalSerials();
}

function dvRenderAnalysisTab() {
  if (dvPendingChartArgs) {
    renderDvCharts(dvPendingChartArgs.data, dvPendingChartArgs.skuData);
  }
  window.dispatchEvent(new Event('resize'));
}

function dvRenderCategoryBreakdown(data) {
  const body = document.getElementById('viz-category-breakdown-body');
  if (!body) return;
  const total = Object.values(data).reduce((s, d) => s + d.count, 0);
  const rows = DV_CATEGORIES.map(catDef => {
    const d = data[catDef.name];
    if (!d || d.count === 0) return null;
    const pct = total > 0 ? (d.count / total * 100).toFixed(1) : 0;
    return '<tr>' +
      '<td><span class="viz-cat-dot" style="background:' + catDef.color + ';"></span>' + escapeHtml(catDef.name) + '</td>' +
      '<td>' + d.count + '</td>' +
      '<td>' + pct + '%</td>' +
      '<td>' + Object.keys(d.skus).length + '</td>' +
      '</tr>';
  }).filter(Boolean).join('');
  body.innerHTML = rows || '<tr><td colspan="4" class="drilldown-empty">No classified serials</td></tr>';
}

function dvGlobalSerialsRows() {
  const rows = [];
  (ringsData || []).forEach(r => {
    const sn = String(r.serial_number || '').trim();
    if (!sn || sn === '--' || sn === 'N/A') return;
    const cls = classifySerial(sn);
    rows.push({
      category: cls ? cls.category : 'UNKNOWN',
      machine: String(r.file || '--'),
      slot: String(r.slot == null ? '--' : r.slot),
      serial: sn,
      state: dvDrillSlotState(r)
    });
  });
  rows.sort((a, b) => {
    if (a.category !== b.category) return a.category.localeCompare(b.category);
    if (a.machine !== b.machine) return a.machine.localeCompare(b.machine, undefined, { numeric: true });
    const na = parseInt(a.slot, 10), nb = parseInt(b.slot, 10);
    if (!isNaN(na) && !isNaN(nb)) return na - nb;
    return String(a.slot).localeCompare(String(b.slot), undefined, { numeric: true });
  });
  return rows;
}

function renderDvGlobalSerials() {
  const body = document.getElementById('viz-serials-body');
  if (!body) return;
  const rows = dvGlobalSerialsRows();
  currentAllSerialsExportData = rows;
  const stateCls = { RUNNING: 'running', PASSED: 'passed', FAILED: 'failed', ASSIGNED: 'assigned', EMPTY: 'empty' };
  body.innerHTML = rows.length === 0
    ? '<tr><td colspan="5" class="drilldown-empty">No serials found</td></tr>'
    : rows.map(r =>
        '<tr>' +
        '<td><span class="viz-cat-dot" style="background:' + (dvCategoryColor(r.category) || '#64748B') + ';"></span>' + escapeHtml(r.category) + '</td>' +
        '<td>' + escapeHtml(r.machine) + '</td>' +
        '<td>' + escapeHtml(r.slot) + '</td>' +
        '<td style="font-family:var(--f-mono);font-weight:600;">' + escapeHtml(r.serial) + '</td>' +
        '<td><span class="viz-status-badge ' + (stateCls[r.state] || 'empty') + '">' + escapeHtml(r.state) + '</span></td>' +
        '</tr>'
      ).join('');
}

function dvRefreshSerialsTab() {
  const panel = document.getElementById('viz-serials');
  if (panel && panel.style.display !== 'none') renderDvGlobalSerials();
}

function dvExportAllSerialsCsv() {
  if (!currentAllSerialsExportData || currentAllSerialsExportData.length === 0) {
    dvFlashExportEmpty('btn-export-all-serials');
    return;
  }
  const csvContent = 'Category,Machine,Slot,Serial Number,Status\n' + currentAllSerialsExportData.map(r =>
    [dvCsvEscape(r.category), dvCsvEscape(r.machine), dvCsvEscape(r.slot), dvCsvEscape(r.serial), dvCsvEscape(r.state)].join(',')
  ).join('\n');
  dvTriggerCsvDownload(csvContent, 'Export_GlobalSerials.csv');
}

(function initVizTabs() {
  const nav = document.querySelector('.premium-nav-tabs');
  if (nav) {
    nav.addEventListener('click', function(e) {
      const btn = e.target.closest && e.target.closest('.viz-tab-btn');
      if (!btn || !btn.dataset.target) return;
      dvSetVizTab(btn.dataset.target);
    });
  }
  const allExportBtn = document.getElementById('btn-export-all-serials');
  if (allExportBtn) {
    allExportBtn.addEventListener('click', function() {
      if (allExportBtn.disabled) return;
      dvExportAllSerialsCsv();
    });
  }
  const drillContent = document.getElementById('dv-category-content');
  if (drillContent) {
    drillContent.addEventListener('click', function(e) {
      const tabBtn = e.target.closest && e.target.closest('.drill-sub-tab');
      if (tabBtn && tabBtn.dataset.target) {
        dvSetDrillTab(tabBtn.dataset.target);
        return;
      }
      const drillExportBtn = e.target.closest && e.target.closest('#btn-export-drill-serials');
      if (drillExportBtn) {
        if (drillExportBtn.disabled) return;
        dvExportDrillSerialsCsv();
      }
    });
  }
})();

let dvPendingChartArgs = null;

function renderDvCharts(data, skuData) {
  dvPendingChartArgs = { data: data, skuData: skuData || null };

  const analysisEl = document.getElementById('viz-analysis');
  if (analysisEl && analysisEl.style.display === 'none') {
    if (dvBarChart) {
      try { dvBarChart.destroy(); } catch (e) {}
      dvBarChart = null;
    }
    return;
  }

  const labels = [];
  const values = [];
  const barColors = [];

  if (skuData) {
    const entries = Object.entries(skuData).sort((a, b) => b[1] - a[1]);
    entries.forEach(([sku, count]) => {
      labels.push(sku);
      values.push(count);
      barColors.push(dvCurrentCategory ? dvCategoryColor(dvCurrentCategory) : '#38BDF8');
    });
  } else {
    DV_CATEGORIES.forEach(catDef => {
      const d = data[catDef.name];
      if (d && d.count > 0) {
        labels.push(catDef.name);
        values.push(d.count);
        barColors.push(catDef.color);
      }
    });
  }

  const barEl = document.getElementById('dv-bar-chart');
  if (dvBarChart) dvBarChart.destroy();
  dvBarChart = new ApexCharts(barEl, {
    chart: { type: 'bar', height: 250, toolbar: { show: false } },
    series: [{ name: 'Serials', data: values }],
    xaxis: { categories: labels },
    colors: barColors,
    plotOptions: { bar: { borderRadius: 4, distributed: true } },
    legend: { show: false },
    grid: getApexGrid(),
    theme: { mode: document.documentElement.getAttribute('data-theme') === 'dark' ? 'dark' : 'light' },
    tooltip: { y: { formatter: v => v + ' serials' } }
  });
  dvBarChart.render();
}

// ── Live File Watching (File System Access API) ──

let dirHandle = null;
let watchingActive = false;
let fileWatchTimer = null;
let fileHashes = new Map();
let fileSizes = new Map();

async function computeContentHash(text) {
    const encoder = new TextEncoder();
    const data = encoder.encode(text);
    const hashBuffer = await crypto.subtle.digest('SHA-256', data);
    const hashArray = Array.from(new Uint8Array(hashBuffer));
    return hashArray.map(b => b.toString(16).padStart(2, '0')).join('');
}

function safeParseJSON(text, fileName) {
    if (!text || text.trim().length === 0) throw new Error('Empty file');
    const trimmed = text.trim();
    if (!trimmed.startsWith('{') && !trimmed.startsWith('[')) throw new Error('Invalid JSON');
    if (!trimmed.endsWith('}') && !trimmed.endsWith(']')) throw new Error('Invalid JSON');
    try {
        const parsed = JSON.parse(trimmed);
        if (typeof parsed !== 'object' || parsed === null) throw new Error('JSON must be an object');
        return parsed;
    } catch (e) { throw new Error('JSON parse error: ' + e.message); }
}

async function openFolder() {
    stopFileWatching();
    stopApiPolling();
    const hint = document.getElementById('live-watch-hint');
    if (hint) hint.style.display = 'none';
    try {
        dirHandle = await window.showDirectoryPicker({ mode: 'read' });
        await loadFromDirectory();
    } catch (err) {
        if (err.name === 'AbortError' || err.name === 'SecurityError') return;
        console.warn('[FileWatch] showDirectoryPicker failed, falling back to file input');
        dirHandle = null;
        document.getElementById('file-upload').click();
    }
}

async function loadFromDirectory(options = {}) {
    if (!dirHandle) return;
    try {
        const jsonFiles = [];
        for await (const entry of dirHandle.values()) {
            if (entry.kind === 'file' && entry.name.toLowerCase().endsWith('.json')) jsonFiles.push(entry);
        }
        if (jsonFiles.length === 0) { alert('No JSON files found.'); return; }

        const machinesData = {};
        fileHashes.clear();
        fileSizes.clear();

        for (const entry of jsonFiles) {
            let parsed = false;
            for (let attempt = 0; attempt < 3 && !parsed; attempt++) {
                try {
                    const file = await entry.getFile();
                    const text = await file.text();
                    const raw = safeParseJSON(text, entry.name);
                    const data = normalizeMachineData(raw);
                    const machineName = entry.name.replace(/\.json$/i, '');
                    if (data) machinesData[machineName] = data;
                    const hash = await computeContentHash(text);
                    fileHashes.set(entry.name, hash);
                    fileSizes.set(entry.name, file.size);
                    parsed = true;
                } catch (e) {
                    if (attempt < 2) await new Promise(r => setTimeout(r, 60));
                    else console.warn('[FileWatch] Error loading ' + entry.name + ': ' + e.message);
                }
            }
        }

        if (Object.keys(machinesData).length > 0) {
            onAllFilesLoaded(machinesData, options);
            startFileWatching();
            dbSave('bdrDirHandle', dirHandle);
        }
    } catch (err) {
        console.error('[FileWatch] Error loading directory:', err.message);
    }
}

async function handleFileUpload(event) {
    const files = event.target.files;
    if (!files || files.length === 0) return;
    stopFileWatching();
    const jsonFiles = Array.from(files).filter(f => f.name.toLowerCase().endsWith('.json'));
    if (jsonFiles.length === 0) { alert('No JSON files found.'); event.target.value = ''; return; }
    const machinesData = {};
    fileHashes.clear();
    for (const file of jsonFiles) {
        try {
            const text = await file.text();
            const raw = JSON.parse(text);
            const data = normalizeMachineData(raw);
            const machineName = file.name.replace(/\.json$/i, '');
            if (data) machinesData[machineName] = data;
            const hash = await computeContentHash(text);
            fileHashes.set(file.name, hash);
        } catch (err) {
            console.warn('[FileWatch] Error reading ' + file.name + ': ' + err.message);
        }
    }
    if (Object.keys(machinesData).length > 0) {
        onAllFilesLoaded(machinesData);
        updateUploadLabel(jsonFiles.length + ' files loaded', 'No live watch (use Open Folder for live updates)');
    }
    event.target.value = '';
}

function startFileWatching() {
    if (fileWatchTimer) clearTimeout(fileWatchTimer);
    watchingActive = true;
    scheduleFileCheck();
}

function scheduleFileCheck() {
    if (watchingActive) fileWatchTimer = setTimeout(checkFileChanges, 200);
}

function stopFileWatching() {
    if (fileWatchTimer) { clearTimeout(fileWatchTimer); fileWatchTimer = null; }
    watchingActive = false;
    dirHandle = null;
    fileHashes.clear();
    fileSizes.clear();
}

async function checkFileChanges() {
    if (!dirHandle || !watchingActive) { if (watchingActive) scheduleFileCheck(); return; }
    try {
        const currentFiles = new Set();
        const changed = [];
        for await (const entry of dirHandle.values()) {
            if (entry.kind === 'file' && entry.name.toLowerCase().endsWith('.json')) {
                currentFiles.add(entry.name);
                try {
                    const file = await entry.getFile();
                    const oldSize = fileSizes.get(entry.name);
                    if (oldSize === undefined || file.size !== oldSize) {
                        const text = await file.text();
                        if (text.trim()) {
                            const h = await computeContentHash(text);
                            if (h !== fileHashes.get(entry.name)) {
                                fileSizes.set(entry.name, file.size);
                                fileHashes.set(entry.name, h);
                                changed.push(entry.name);
                            }
                        }
                    }
                } catch (e) { console.warn('[FileWatch] Error checking ' + entry.name + ': ' + e.message); }
            }
        }
        const deleted = [];
        for (const [fileName] of fileHashes) {
            if (!currentFiles.has(fileName)) {
                fileHashes.delete(fileName);
                fileSizes.delete(fileName);
                deleted.push(fileName);
            }
        }
        if (changed.length > 0 || deleted.length > 0) {
            await new Promise(r => setTimeout(r, 80));
            await loadFromDirectory({ preserveUi: true, suppressAlert: true, preferredMachine: CURRENT_MACHINE });
        }
    } catch (e) { console.warn('[FileWatch] Error:', e.message); }
    if (watchingActive) { clearTimeout(fileWatchTimer); scheduleFileCheck(); }
}

function updateUploadLabel(main, sub) {
    const label = document.getElementById('upload-label');
    const sublabel = document.getElementById('upload-sublabel');
    if (label) label.textContent = main;
    if (sublabel) sublabel.textContent = sub;
}

function onAllFilesLoaded(machinesData, options = {}) {
    // Remove loading indicator once live data arrives
    const loadingEl = document.getElementById('live-loading');
    if (loadingEl) loadingEl.remove();

    // Preserve full machine list (before filtering out machines with no valid slots)
    if (ALL_MACHINE_NAMES.length === 0) ALL_MACHINE_NAMES = Object.keys(machinesData);

    const preferredMachine = options.preferredMachine || CURRENT_MACHINE;

    // Filter out machines with zero valid slots
    const filtered = {};
    Object.entries(machinesData).forEach(([name, md]) => {
        if (hasValidSlots(md)) filtered[name] = md;
    });
    ALL_MACHINE_DATA = filtered;

    const machineNames = getAqcMachineNames();
    if (machineNames.length === 0) {
        if (!options.suppressAlert) alert('No valid machine data loaded from the folder.');
        return;
    }

    const kpiCountEl = document.getElementById('kpi-aqc-count');
    if (kpiCountEl) kpiCountEl.textContent = machineNames.length;

    // Compute serial statistics across all uploaded machines and update KPIs immediately
    try {
        const stats = computeSerialStats(machinesData);
        
        // 1. Total Serials
        const rawEl = document.getElementById('kpi-serials-raw');
        setBdrKpiValue(rawEl, stats.totalRaw);
        
        // 2. Total Slots (Active)
        const kpiTotalEl = document.getElementById('kpi-total');
        setBdrKpiValue(kpiTotalEl, stats.totalSlots);
        
        // 3. Avg Battery
        const kpiBattEl = document.getElementById('kpi-batt');
        setBdrKpiValue(kpiBattEl, stats.avgBattery.toFixed(1) + "%");
        
        // 4. Avg Fleet BDR
        const kpiAnomEl = document.getElementById('kpi-anom');
        setBdrKpiValue(kpiAnomEl, stats.avgBdr.toFixed(2));

        const dupEl = document.getElementById('kpi-serials-dup');
        const dupCount = Math.max(0, stats.totalRaw - stats.uniqueCount);
        setBdrKpiValue(dupEl, dupCount);
        renderDuplicates(stats.duplicates);
    } catch (e) {
        console.warn('Failed to compute fleet KPIs on load', e);
    }

    buildMachineSelector(machineNames);

    if (preferredMachine && machinesData[preferredMachine]) {
        CURRENT_MACHINE = preferredMachine;
    } else {
        CURRENT_MACHINE = machineNames[0];
    }
    SESSION_DATA = ALL_MACHINE_DATA[CURRENT_MACHINE];
    updateMachineSelectorUI();
    highlightCrossMachineDups();
    init();
    updateQualifiedCount();
    updateMachineSelectorUI();
    const fpPanel = document.getElementById('floorplan-panel');
    if (fpPanel && fpPanel.classList.contains('visible')) renderFloorplan();
    dbSave('allMachineData', { data: machinesData, savedAt: Date.now(), currentMachine: CURRENT_MACHINE });
}

const BDR_API = '/api/bdr';
const RINGS_API = '/api/rings';

let bdrPollTimer = null;
let ringsPollTimer = null;
let lastBdrFingerprint = null;
let lastRingsFingerprint = null;
let pendingRingsFingerprint = null;
let pendingRingsStableReads = 0;
let committedBdrMachineCount = Number(localStorage.getItem('committedBdrMachineCount') || 0);
let committedBdrSerialCount = Number(localStorage.getItem('committedBdrSerialCount') || 0);
let committedRingsMachineCount = Number(localStorage.getItem('committedRingsMachineCount') || 0);
let committedRingsSlotCount = Number(localStorage.getItem('committedRingsSlotCount') || 0);
let committedRingsSerialCount = Number(localStorage.getItem('committedRingsSerialCount') || 0);
let pendingBdrLowerKey = null;
let pendingBdrLowerStableReads = 0;
let pendingRingsLowerKey = null;
let pendingRingsLowerStableReads = 0;
let bdrFetchInFlight = false;
let ringsFetchInFlight = false;

async function fetchWithTimeout(url, options = {}, timeoutMs = 20000) {
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), timeoutMs);
    try {
        const response = await fetch(url, { ...options, signal: controller.signal });
        return response;
    } catch (error) {
        if (error.name === 'AbortError') {
            console.warn(`Request timed out for ${url}`);
        }
        throw error;
    } finally {
        clearTimeout(timer);
    }
}

async function loadSessionFilesFromServer() {
    if (bdrFetchInFlight) return;
    bdrFetchInFlight = true;
    try {
        const response = await fetchWithTimeout(BDR_API + '?ts=' + Date.now(), { cache: 'no-store' });
        if (response.status === 503) {
            console.warn('BDR Service Unavailable: Check backend data availability (DB or JSON files may be stale).');
            return;
        }
        if (!response.ok) throw new Error('BDR API returned ' + response.status);

        const payload = await response.json();
        let machineNames = [];
        let machinesData = {};
        let hadMachineFetchFailures = false;

        if (Array.isArray(payload)) {
            machineNames = payload.filter(v => typeof v === 'string');
            if (machineNames.length === 0 && payload.every(v => v && typeof v === 'object')) {
                payload.forEach(v => {
                    const name = v.name || v.machine || v.machine_name;
                    if (name) {
                        machineNames.push(String(name).trim());
                        const norm = normalizeMachineData(v);
                        if (norm) machinesData[String(name).trim()] = norm;
                    }
                });
            }
        } else if (typeof payload === 'object' && payload !== null) {
            machineNames = Object.keys(payload);
            const firstVal = payload[machineNames[0]];
            if (firstVal && typeof firstVal === 'object' && normalizeMachineData(firstVal)) {
                machinesData = machineNames.reduce((acc, name) => {
                    const norm = normalizeMachineData(payload[name]);
                    if (norm) acc[name] = norm;
                    return acc;
                }, {});
            }
        }
        if (machineNames.length === 0) return;

        if (Object.keys(machinesData).length === 0) {
            const results = await Promise.allSettled(
                machineNames.map(async (name) => {
                    const cleanName = String(name).trim();
                    const res = await fetchWithTimeout(BDR_API + '/' + encodeURIComponent(cleanName) + '?ts=' + Date.now(), { cache: 'no-store' });
                    if (!res.ok) throw new Error('Machine ' + cleanName + ' returned ' + res.status);
                    const data = await res.json();
                    return { name: cleanName, data: normalizeMachineData(data) };
                })
            );

            results.forEach(r => {
                if (r.status === 'fulfilled' && r.value.data) {
                    machinesData[r.value.name] = r.value.data;
                } else if (r.status === 'rejected') {
                    hadMachineFetchFailures = true;
                    console.warn('BDR: Failed to fetch machine:', r.reason);
                }
            });
        }

        if (Object.keys(machinesData).length === 0) return;

        const fp = JSON.stringify(
            Object.keys(machinesData).sort().map(name => {
                const md = machinesData[name];
                const savedAt = md.saved_at || '';
                const slots = md.slots || {};
                return name + '|' + savedAt + '|' + Object.keys(slots).sort().map(k => {
                    const s = slots[k];
                    return k + ':' + (s.serial_number || '') + ':' + (s.firmware_version || '') + ':' + (s.ring_mac || '') + ':' + (s.state || '') + ':' + (s.battery_current ?? '') + ':' + (s.dead_state || '') + ':' + ((s.bdr_state?.completed_cycles || []).length);
                }).join(',');
            })
        );
        lastDataFetchTime = Date.now();
        updateLastUpdated();
        if (fp === lastBdrFingerprint) return;

        lastBdrFingerprint = fp;

        if (machineNames.length > 0) ALL_MACHINE_NAMES = [...machineNames];

        onAllFilesLoaded(machinesData, {
            preferredMachine: CURRENT_MACHINE,
            suppressAlert: true,
        });
    } catch (error) {
        console.warn('BDR API fetch failed:', error);
    } finally {
        bdrFetchInFlight = false;
    }
}

async function loadAssignedTimes() {
    try {
        const res = await fetchWithTimeout('/api/rings/assigned-times?ts=' + Date.now(), { cache: 'no-store' });
        if (!res.ok) return;
        const data = await res.json();
        if (data && typeof data === 'object') ringsAssignedTimes = data;
    } catch (e) {
        console.warn('Could not load assigned times:', e);
    }
}

function captureAssignedTimes() {
    const changes = [];
    (ringsData || []).forEach(d => {
        const sn = (d.serial_number || '').toString().trim();
        if (!sn || sn === '--' || sn === 'N/A') return;
        if ((d.state || '').toUpperCase() !== 'ASSIGNED') return;
        if (!ringsAssignedTimes[d.file]) ringsAssignedTimes[d.file] = {};
        const e = ringsAssignedTimes[d.file][d.slot];
        if (!e || e.serial !== sn) {
            const ts = new Date().toISOString();
            ringsAssignedTimes[d.file][d.slot] = { serial: sn, ts };
            changes.push({ machine: d.file, slot: d.slot, serial: sn, ts });
        }
    });
    if (changes.length === 0) return;
    fetch('/api/rings/assigned-times', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ entries: changes })
    }).catch(err => console.warn('Could not persist assigned times:', err));
}

async function loadRingsFromAPI() {
    if (ringsFetchInFlight) return;
    ringsFetchInFlight = true;
    try {
        const res = await fetchWithTimeout(RINGS_API + '?ts=' + Date.now(), { cache: 'no-store' });
        if (res.status === 503) {
            console.warn('Rings Service Unavailable: Check backend data availability (DB or JSON files may be stale).');
            return;
        }
        if (!res.ok) throw new Error('Rings API returned ' + res.status);
        const payload = await res.json();

        let machineNames = [];
        let allSlots = [];
        let hadMachineFetchFailures = false;

        if (Array.isArray(payload)) {
            machineNames = payload.filter(v => typeof v === 'string');
            if (machineNames.length === 0 && payload.every(v => v && typeof v === 'object')) {
                payload.forEach(v => {
                    const name = v.name || v.machine || v.machine_name;
                    if (name && v.slots && typeof v.slots === 'object') {
                        machineNames.push(String(name).trim());
                        Object.entries(v.slots).forEach(([slotId, s]) => {
                            if (String(slotId).startsWith('_')) return;
                            if (s && typeof s === 'object') {
                                allSlots.push({
                                    slot: slotId,
                                    file: String(name).trim(),
                                    serial_number: s.serial_number || '--',
                                    ring_mac: s.ring_mac || '--',
                                    ring_name: s.ring_name || '--',
                                    state: s.state || '--',
                                    firmware_version: s.firmware_version || '--',
                                    dead_state: s.dead_state || null,
                                    discharge_connect_failures: s.discharge_connect_failures || 0,
                                    hardware_version: s.hardware_version || null,
                                    step_statuses: s.step_statuses || {},
                                    queued_at: s.queued_at || null
                                });
                            }
                        });
                    }
                });
            }
        } else if (typeof payload === 'object' && payload !== null) {
            machineNames = Object.keys(payload);
            const firstVal = payload[machineNames[0]];
            if (firstVal && typeof firstVal === 'object') {
                const firstEntry = Object.values(firstVal)[0];
                if (firstEntry && typeof firstEntry === 'object' && (firstEntry.serial_number || firstEntry.ring_mac || firstEntry.state)) {
                    allSlots = machineNames.flatMap(name =>
                        Object.entries(payload[name] || {})
                            .filter(([slotId]) => !String(slotId).startsWith('_'))
                            .map(([slotId, s]) => ({
                            slot: slotId,
                            file: name,
                            serial_number: s.serial_number || '--',
                            ring_mac: s.ring_mac || '--',
                            ring_name: s.ring_name || '--',
                            state: s.state || '--',
                            firmware_version: s.firmware_version || '--',
                            dead_state: s.dead_state || null,
                            discharge_connect_failures: s.discharge_connect_failures || 0,
                            hardware_version: s.hardware_version || null,
                            step_statuses: s.step_statuses || {},
                            queued_at: s.queued_at || null
                        }))
                    );
                    allSlots = allSlots.filter(s => s);
                }
            }
        }
        if (machineNames.length === 0) { return; }

        if (allSlots.length === 0) {
            const results = await Promise.allSettled(
                machineNames.map(async (name) => {
                    const cleanName = String(name).trim();
                    const r = await fetchWithTimeout(RINGS_API + '/' + encodeURIComponent(cleanName) + '?ts=' + Date.now(), { cache: 'no-store' });
                    if (!r.ok) throw new Error('Rings machine ' + cleanName + ' returned ' + r.status);
                    const machineData = await r.json();
                    return { name: cleanName, machineData };
                })
            );

            results.forEach(r => {
                if (r.status === 'fulfilled') {
                    const { name, machineData } = r.value;
                    if (machineData && typeof machineData === 'object') {
                        Object.entries(machineData).forEach(([slotId, s]) => {
                            if (String(slotId).startsWith('_')) return;
                            if (s && typeof s === 'object') {
                                allSlots.push({
                                    slot: slotId,
                                    file: name,
                                    serial_number: s.serial_number || '--',
                                    ring_mac: s.ring_mac || '--',
                                    ring_name: s.ring_name || '--',
                                    state: s.state || '--',
                                    firmware_version: s.firmware_version || '--',
                                    dead_state: s.dead_state || null,
                                    discharge_connect_failures: s.discharge_connect_failures || 0,
                                    hardware_version: s.hardware_version || null,
                                    step_statuses: s.step_statuses || {},
                                    queued_at: s.queued_at || null
                                });
                            }
                        });
                    }
                } else {
                    hadMachineFetchFailures = true;
                    console.warn('Rings: Failed to fetch machine:', r.reason);
                }
            });
        }

        if (allSlots.length === 0) return;

        allSlots.sort((a, b) => {
            const fileCompare = String(a.file).localeCompare(String(b.file), undefined, { numeric: true });
            if (fileCompare !== 0) return fileCompare;
            return String(a.slot).localeCompare(String(b.slot), undefined, { numeric: true });
        });

        const fp = JSON.stringify(allSlots.map(s => [
            s.file,
            s.slot,
            s.serial_number || '',
            s.ring_mac || '',
            s.state || '',
            s.firmware_version || '',
            s.dead_state || '',
            s.discharge_connect_failures || 0,
            s.hardware_version || '',
            s.queued_at || ''
        ]));
        lastDataFetchTime = Date.now();
        updateLastUpdated();
        if (fp === lastRingsFingerprint) return;

        lastRingsFingerprint = fp;

        const loadingEl = document.getElementById('live-loading');
        if (loadingEl) loadingEl.remove();

        ringsData = allSlots;
        ringsFetchCompleted = true;
        captureAssignedTimes();
        try {
            populateRingsFilter();
            ringsRenderGrid();
            // Re-render BDR dashboard to sync occupancy if it's the active view
            if (currentView === 'bdr') init();
            const fpPanel = document.getElementById('floorplan-panel');
            if (fpPanel && fpPanel.classList.contains('visible')) renderFloorplan();
        } catch (e) { console.warn('Error rendering rings data:', e); }
        if (currentView === 'data-viz') renderDataViz();
    } catch (error) {
        console.warn('Rings API fetch failed:', error);
    } finally {
        ringsFetchInFlight = false;
    }
}

const API_POLL_MS = 5000;

function startApiPolling() {
    if (bdrPollTimer && ringsPollTimer) return;
    if (bdrPollTimer) { clearInterval(bdrPollTimer); bdrPollTimer = null; }
    if (ringsPollTimer) { clearInterval(ringsPollTimer); ringsPollTimer = null; }
    bdrFetchInFlight = false;
    ringsFetchInFlight = false;
    // Initial fetches are done by startAutoSessionRefresh before calling this; only set up intervals here
    bdrPollTimer = setInterval(() => {
        loadSessionFilesFromServer().catch(err => console.warn('BDR poll error:', err));
    }, API_POLL_MS);
    ringsPollTimer = setInterval(() => {
        loadRemovedSlotsConfig();
        loadRingsFromAPI().catch(err => console.warn('Rings poll error:', err));
    }, API_POLL_MS);
}

function stopApiPolling() {
    if (bdrPollTimer) { clearInterval(bdrPollTimer); bdrPollTimer = null; }
    if (ringsPollTimer) { clearInterval(ringsPollTimer); ringsPollTimer = null; }
    bdrFetchInFlight = false;
    ringsFetchInFlight = false;
}

async function startAutoSessionRefresh() {
    loadRemovedSlotsConfig();
    loadAssignedTimes();
    loadSessionFilesFromServer().catch(err => console.warn('BDR initial fetch error:', err));
    loadRingsFromAPI().catch(err => console.warn('Rings initial fetch error:', err));
    startApiPolling();
}

function buildMachineSelector(names) {
    const container = document.getElementById('machine-buttons');
    container.innerHTML = '';

    // Precompute serial count per machine
    const serialCounts = {};
    Object.entries(ALL_MACHINE_DATA).forEach(([m, md]) => {
        let count = 0;
        const slots = md.slots || {};
        Object.values(slots).forEach(s => {
            const sn = (s.serial_number || '').toString().trim();
            if (sn && sn !== '--' && sn !== 'N/A') count++;
        });
        serialCounts[m] = count;
    });

    names.forEach(name => {
        if ((serialCounts[name] || 0) === 0) return;
        const btn = document.createElement('button');
        btn.className = 'heatmap-filter machine-btn';
        btn.dataset.machine = name;
        btn.innerHTML = `<span class="machine-name">${name}</span><span class="machine-count">${serialCounts[name] || 0}</span>`;
        btn.onclick = function() {
            switchMachine(name);
        };
        container.appendChild(btn);
    });
}

function updateMachineSelectorUI() {
    document.querySelectorAll('#machine-buttons .heatmap-filter').forEach(btn => {
        const isActive = btn.dataset.machine === CURRENT_MACHINE;
        btn.classList.toggle('active', isActive);
        btn.classList.toggle('machine-active-glow', isActive);
    });
    const fleetLabel = document.getElementById('fleet-heatmap-machine');
    const fleetRow = document.getElementById('fleet-heatmap-machine-row');
    if (fleetLabel && fleetRow) {
        if (CURRENT_MACHINE) {
            fleetLabel.textContent = CURRENT_MACHINE.toUpperCase();
            fleetLabel.style.display = 'inline-block';
        } else {
            fleetLabel.textContent = '';
            fleetLabel.style.display = 'none';
        }
    }
    updateBdrBulkChargerControls();
}

function highlightCrossMachineDups() {
    try {
        const stats = computeSerialStats(ALL_MACHINE_DATA);
        // Build adjacency: machines connected by a shared duplicate serial
        const adj = {};
        stats.duplicates.forEach(d => {
            const machines = [...new Set(d.locations.map(l => l.machine))];
            if (machines.length > 1) {
                for (let i = 0; i < machines.length; i++) {
                    for (let j = i + 1; j < machines.length; j++) {
                        if (!adj[machines[i]]) adj[machines[i]] = new Set();
                        if (!adj[machines[j]]) adj[machines[j]] = new Set();
                        adj[machines[i]].add(machines[j]);
                        adj[machines[j]].add(machines[i]);
                    }
                }
            }
        });
        // Find connected components (groups of machines sharing duplicates)
        const visited = new Set();
        const groups = [];
        Object.keys(adj).forEach(m => {
            if (visited.has(m)) return;
            const group = [];
            const queue = [m];
            while (queue.length > 0) {
                const node = queue.shift();
                if (visited.has(node)) continue;
                visited.add(node);
                group.push(node);
                (adj[node] || []).forEach(neighbor => {
                    if (!visited.has(neighbor)) queue.push(neighbor);
                });
            }
            if (group.length > 0) groups.push(group);
        });
        // Distinct colors per group
        const colors = ['#F59E0B', '#8B5CF6', '#EC4899', '#06B6D4', '#84CC16', '#F97316', '#6366F1', '#14B8A6'];
        const machineColor = {};
        groups.forEach((group, i) => {
            const color = colors[i % colors.length];
            group.forEach(m => { machineColor[m] = color; });
        });
        // Apply to machine buttons
        document.querySelectorAll('#machine-buttons .heatmap-filter').forEach(btn => {
            const machine = btn.dataset.machine;
            const color = machineColor[machine];
            btn.classList.remove('machine-dup-group');
            btn.style.boxShadow = '';
            btn.style.borderColor = '';
            btn.title = '';
            if (color) {
                btn.classList.add('machine-dup-group');
                btn.style.boxShadow = `0 0 0 2px ${color}`;
                btn.style.borderColor = color;
                const group = groups.find(g => g.includes(machine));
                if (group) btn.title = `Shared duplicate group: ${group.join(', ')}`;
            }
        });
    } catch (e) {
        console.warn('highlightCrossMachineDups error', e);
    }
}

function switchMachine(name, openSlotId) {
    if (!ALL_MACHINE_DATA[name] || name === CURRENT_MACHINE) return;

    if (!openSlotId) currentSlotPanel = null;
    CURRENT_MACHINE = name;
    SESSION_DATA = ALL_MACHINE_DATA[name];
    updateMachineSelectorUI();
    init();
    setTimeout(() => {
        const hmGrid = document.getElementById('heatmap-grid');
        if (hmGrid) hmGrid.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    }, 50);
    // refresh floorplan active state if visible
    const fpPanel = document.getElementById('floorplan-panel');
    if (fpPanel && fpPanel.classList.contains('visible')) renderFloorplan();
    if (openSlotId) {
        setTimeout(() => {
            const hm = globalHeatmapData.find(h => String(h.id) === String(openSlotId));
            if (hm) {
                const el = document.querySelector(`.slot-cell[data-id="${openSlotId}"]`);
                if (el) {
                    document.querySelectorAll('.slot-cell').forEach(c => c.classList.remove('active'));
                    el.classList.add('active');
                    openDetailPanel(hm);
                }
            }
        }, 50);
    }
}

function searchSerialNumber(serial) {
    if (!serial || Object.keys(ALL_MACHINE_DATA).length === 0) return;
    const q = serial.trim().toLowerCase();
    if (!q) return;
    for (const [machineName, machineData] of Object.entries(ALL_MACHINE_DATA)) {
        const slots = machineData.slots || {};
        for (const [slotId, slotData] of Object.entries(slots)) {
            const sn = (slotData.serial_number || '').toLowerCase();
            if (sn === q || sn.includes(q)) {
                if (machineName === CURRENT_MACHINE) {
                    const hm = globalHeatmapData.find(h => String(h.id) === String(slotId));
                    if (hm) {
                        const el = document.querySelector(`.slot-cell[data-id="${slotId}"]`);
                        if (el) {
                            document.querySelectorAll('.slot-cell').forEach(c => c.classList.remove('active'));
                            el.classList.add('active');
                            openDetailPanel(hm);
                        }
                    }
                } else {
                    switchMachine(machineName, slotId);
                }
                document.getElementById('serial-search').value = '';
                return;
            }
        }
    }
    alert('Serial number not found in any machine.');
}

// ── Old Data Archive Search ─────────────────────────────────────────

let oldDataBulkSerials = null;

function getOldDataSearchInputs() {
    return [
        document.getElementById('od-search-input'),
        document.getElementById('od-search-input-2')
    ].filter(Boolean);
}

function getOldDataSearchValue() {
    const inputs = getOldDataSearchInputs();
    const populated = inputs.find(input => input.value && input.value.trim());
    return populated ? populated.value : (inputs[0] ? inputs[0].value : '');
}

function setOldDataSearchValue(value) {
    getOldDataSearchInputs().forEach(input => {
        input.value = value;
    });
}

function syncOldDataSearchInputs(source) {
    setOldDataSearchValue(source ? source.value : '');
}

function oldDataHandleKeydown(event) {
    if (event.ctrlKey && (event.key === 'c' || event.key === 'C')) {
        event.preventDefault();
        clearOldDataSearch();
        return;
    }
    if (event.key === 'Enter' && !event.shiftKey) {
        event.preventDefault();
        searchOldData();
    }
}

function oldDataHandleCopy(event) {
    event.preventDefault();
    clearOldDataSearch();
}

function resetOldDataSearchView() {
    const empty = document.getElementById('od-empty');
    const content = document.getElementById('od-content');
    const results = document.getElementById('od-results');
    const countEl = document.getElementById('od-result-count');
    const indexStatus = document.getElementById('od-index-status');
    const searchTime = document.getElementById('od-search-time');

    if (empty) empty.style.display = 'flex';
    if (content) content.style.display = 'none';
    if (countEl) countEl.textContent = '';
    if (indexStatus) {
        indexStatus.textContent = '';
        indexStatus.style.color = 'var(--muted)';
    }
    if (searchTime) searchTime.textContent = '';
    if (results) {
        results.innerHTML = '<div style="text-align:center;padding:20px;color:var(--muted);font-size:13px;" id="od-loading">Searching...</div>';
    }
}

function clearOldDataSearch() {
    oldDataBulkSerials = null;
    setOldDataSearchValue('');
    resetOldDataSearchView();
    const input = document.getElementById('od-search-input');
    if (input) input.focus();
}

function parseOldDataSerials(rawValue) {
    const seen = new Set();
    return String(rawValue || '')
        .split(/[\n,;]+/)
        .map(value => value.trim())
        .filter(Boolean)
        .filter(value => {
            const key = value.toLowerCase();
            if (seen.has(key)) return false;
            seen.add(key);
            return true;
        });
}

function formatOldDataSerialSummary(serials) {
    if (!serials || serials.length === 0) return '';
    if (serials.length === 1) return '<strong>' + escapeHtml(serials[0]) + '</strong>';
    const preview = serials
        .slice(0, 3)
        .map(serial => '<strong>' + escapeHtml(serial) + '</strong>')
        .join(', ');
    return preview + (serials.length > 3 ? ' and <strong>' + (serials.length - 3) + '</strong> more' : '');
}

async function searchOldData(bulkSerials) {
    let isBulk = Array.isArray(bulkSerials) && bulkSerials.length > 0;

    let rawSearch;
    if (isBulk) {
        rawSearch = bulkSerials.join(', ');
    } else {
        const inputVal = String(getOldDataSearchValue() || '').trim();
        if (/^\[Bulk Search: \d+ Serials\]$/.test(inputVal) &&
            Array.isArray(oldDataBulkSerials) && oldDataBulkSerials.length > 0) {
            isBulk = true;
            bulkSerials = oldDataBulkSerials;
            rawSearch = bulkSerials.join(', ');
        } else {
            rawSearch = inputVal;
        }
    }
    if (!rawSearch || !rawSearch.trim()) return;

    const serials = isBulk ? bulkSerials : parseOldDataSerials(rawSearch);
    if (!serials.length) {
        clearOldDataSearch();
        return;
    }

    if (!isBulk) setOldDataSearchValue(rawSearch.trim());

    const empty = document.getElementById('od-empty');
    const content = document.getElementById('od-content');
    const loading = document.getElementById('od-loading');
    const results = document.getElementById('od-results');
    const countEl = document.getElementById('od-result-count');
    const indexStatus = document.getElementById('od-index-status');
    const searchTime = document.getElementById('od-search-time');

    if (empty) empty.style.display = 'none';
    if (content) content.style.display = 'flex';

    if (loading) loading.style.display = 'block';
    if (results) {
        const queryLabel = serials.length === 1
            ? formatOldDataSerialSummary(serials)
            : '<strong>' + serials.length + '</strong> serial numbers (' + formatOldDataSerialSummary(serials) + ')';
        results.innerHTML = '<div id="od-loading" style="text-align:center;padding:20px;color:var(--muted);font-size:13px;">Searching archive for ' + queryLabel + '...</div>';
    }

    const startTime = Date.now();

    try {
        const resp = serials.length === 1
            ? await fetch('/api/old-data/search/' + encodeURIComponent(serials[0]))
            : await fetch('/api/old-data/search', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ serials })
            });
        const data = await resp.json();

        const elapsed = ((Date.now() - startTime) / 1000).toFixed(1);

        if (data && data.ok) {
            if (indexStatus) {
                const source = data.index_source || (data.indexed ? 'rebuilt' : 'direct_scan');
                const sourceLabelMap = {
                    cache: 'Indexed search (cache)',
                    rebuilt: 'Indexed search',
                    warming: 'Archive index warming',
                    direct_scan: 'Direct scan fallback',
                    missing: 'Archive unavailable',
                    error: 'Index error',
                    merged: 'Full archive scan'
                };
                indexStatus.textContent = sourceLabelMap[source] || (data.indexed ? 'Indexed search' : 'Direct scan fallback');
                indexStatus.style.color = (source === 'direct_scan' || source === 'warming' || source === 'error') ? 'var(--warn)' : 'var(--ok)';
            }
            if (searchTime) searchTime.textContent = elapsed + 's';

            let rows = data.results || [];
            if (isBulk && serials.length > 1) {
                const bulkLookup = serials.map(s => String(s).trim().toLowerCase());
                rows = rows.filter(row => {
                    const rowSerial = String(row && (row.query_serial || row.serial_number || '')).trim().toLowerCase();
                    return rowSerial && bulkLookup.includes(rowSerial);
                });
            }
            const showSerialColumn = Boolean(data.multi_serial || serials.length > 1);

            if (rows.length === 0) {
                if (countEl) countEl.textContent = showSerialColumn ? '0 result(s)' : '0 machine(s)';
                if (results) {
                    results.innerHTML = '<div style="text-align:center;padding:40px 20px;color:var(--muted);font-size:14px;">No archived data found for ' + formatOldDataSerialSummary(serials) + '</div>';
                }
            } else {
                const getArchiveSortTime = value => {
                    const ts = new Date(value || 0).getTime();
                    return Number.isFinite(ts) ? ts : 0;
                };
                const latestByMachine = new Map();
                rows.forEach(record => {
                    if (!record || typeof record !== 'object') return;
                    const machineName = String(record.machine || 'Unknown');
                    const serialKey = showSerialColumn
                        ? String(record.query_serial || record.serial_number || '').toLowerCase()
                        : '';
                    const resultKey = showSerialColumn ? (serialKey + '::' + machineName) : machineName;
                    const previous = latestByMachine.get(resultKey);
                    const recordTime = getArchiveSortTime(record.last_update);
                    const previousTime = previous ? getArchiveSortTime(previous.last_update) : -Infinity;
                    if (!previous || recordTime > previousTime) {
                        latestByMachine.set(resultKey, record);
                    }
                });
                const groupedRows = [...latestByMachine.values()].sort((a, b) => {
                    const ta = getArchiveSortTime(a.last_update);
                    const tb = getArchiveSortTime(b.last_update);
                    return tb - ta;
                });
                if (countEl) {
                    countEl.textContent = showSerialColumn
                        ? groupedRows.length + ' result(s) across ' + serials.length + ' serial(s)' + (data.truncated ? ' (showing first 500)' : '')
                        : groupedRows.length + ' machine(s)' + (data.truncated ? ' (showing first 500)' : '');
                }

                let html = '<table><thead><tr>' +
                    (showSerialColumn ? '<th>Serial Number</th>' : '') +
                    '<th>Machine</th>' +
                    '<th>Slot</th>' +
                    '<th>Status</th>' +
                    '<th>Avg BDR</th>' +
                    '<th>Completed Cycles</th>' +
                    '<th>First Seen</th>' +
                    '<th>Last Update</th>' +
                    '</tr></thead><tbody>';
                groupedRows.forEach(r => {
                    const querySerial = r.query_serial || r.serial_number || '--';
                    const avgBdrValue = r.machine_avg_bdr;
                    const avgBdr = avgBdrValue != null && avgBdrValue !== ''
                        ? (typeof avgBdrValue === 'number' ? avgBdrValue.toFixed(2) : escapeHtml(String(avgBdrValue)))
                        : 'N/A';
                    const staleIndicator = r.avg_bdr_is_stale
                        ? ' <span title="Latest snapshot had 0.0; showing last known value" style="font-size:10px;color:var(--warn);cursor:help;">&#9888;</span>'
                        : '';
                    const startTime = r.start_time != null ? _fmtUnix(r.start_time) : '--';
                    const lastUpdate = r.last_update ? _fmtTime(r.last_update) : '--';
                    const completedCycles = r.completed_cycles != null ? r.completed_cycles : (r.total_cycles != null ? r.total_cycles : 0);
                    const avgBdrNumeric = Number(avgBdrValue);
                    const bdrClass = Number.isFinite(avgBdrNumeric)
                        ? (Math.abs(avgBdrNumeric) > 12 ? 'od-bdr-danger' : (Math.abs(avgBdrNumeric) > 5 ? 'od-bdr-warn' : 'od-bdr-ok'))
                        : '';
                    // Determine status display
                    const status = r.state || '--';
                    let statusClass = 'badge neutral';
                    let statusText = status;
                    const statusLower = String(status).toLowerCase();
                    if (statusLower.includes('pass')) {
                        statusClass = 'badge ok';
                        statusText = 'Passed';
                    } else if (statusLower.includes('fail')) {
                        statusClass = 'badge danger';
                        statusText = 'Failed';
                    } else if (statusLower.includes('bdr')) {
                        statusClass = 'badge blue';
                        statusText = 'Running';
                    } else if (statusLower.includes('assigned')) {
                        statusClass = 'badge warn';
                        statusText = 'Assigned';
                    }
                    
                    html += '<tr>' +
                        (showSerialColumn ? '<td class="od-serial">' + escapeHtml(String(querySerial)) + '</td>' : '') +
                        '<td class="od-machine"><strong>' + escapeHtml(r.machine || 'Unknown') + '</strong></td>' +
                        '<td class="od-slot">' + escapeHtml(r.slot != null ? String(r.slot) : '--') + '</td>' +
                        '<td><span class="' + statusClass + '">' + escapeHtml(statusText) + '</span></td>' +
                        '<td class="' + bdrClass + '">' + avgBdr + staleIndicator + '</td>' +
                        '<td>' + escapeHtml(String(completedCycles)) + '</td>' +
                        '<td>' + escapeHtml(startTime) + '</td>' +
                        '<td>' + escapeHtml(lastUpdate) + '</td>' +
                        '</tr>';
                });
                html += '</tbody></table>';
                if (results) results.innerHTML = html;
            }
        } else {
            console.error('Old Data Search Error:', data);
            const errorMsg = data.error || 'Unknown error';
            const traceback = data.traceback ? `<div style="margin-top:10px;font-family:monospace;font-size:10px;color:var(--muted);text-align:left;max-height:200px;overflow-y:auto;background:var(--surface);padding:10px;border-radius:4px;border:1px solid var(--border);">` + escapeHtml(data.traceback) + `</div>` : '';
            if (results) results.innerHTML = '<div style="text-align:center;padding:40px 20px;color:var(--danger);font-size:14px;">Error: ' + escapeHtml(errorMsg) + traceback + '</div>';
        }
    } catch (e) {
        console.error('Old Data Search Exception:', e);
        if (results) results.innerHTML = '<div style="text-align:center;padding:40px 20px;color:var(--danger);font-size:14px;">Failed to search archive: ' + escapeHtml(e.message) + '</div>';
    } finally {
        const ld = document.getElementById('od-loading');
        if (ld) ld.style.display = 'none';
    }
}

/* ── Old Data Bulk Paste (Excel column) ───────────────────────────────
   Single-line inputs strip newlines on paste, so intercept the clipboard
   natively and split strictly by line breaks (commas ignored). */

function setupOldDataBulkPaste() {
    const inputs = [
        document.getElementById('od-search-input'),
        document.getElementById('od-search-input-2')
    ].filter(Boolean);

    inputs.forEach(searchInput => {
        searchInput.addEventListener('paste', (e) => {
            e.preventDefault();
            const pasteData = (e.clipboardData || window.clipboardData).getData('text');
            if (!pasteData || !pasteData.trim()) return;

            const serialArray = pasteData.split(/\r?\n/).map(s => s.trim()).filter(s => s.length > 0);
            if (serialArray.length === 0) return;

            oldDataBulkSerials = serialArray;
            searchInput.value = '[Bulk Search: ' + serialArray.length + ' Serials]';
            searchOldData(serialArray);
        });
    });
}

setupOldDataBulkPaste();

function exportOldDataCSV() {
    const table = document.querySelector('#od-results table');
    if (!table) return;
    const ths = table.querySelectorAll('thead th');
    const trs = table.querySelectorAll('tbody tr');
    if (!ths.length || !trs.length) return;
    let headers = [];
    ths.forEach(th => headers.push(th.textContent.trim()));
    let csv = headers.map(h => '"' + h.replace(/"/g, '""') + '"').join(',') + '\n';
    trs.forEach(tr => {
        const row = [];
        tr.querySelectorAll('td').forEach(td => {
            const text = td.textContent.trim().replace(/"/g, '""');
            row.push('"' + text + '"');
        });
        if (row.length) csv += row.join(',') + '\n';
    });
    downloadCSV(csv, 'Old_Data_Search.csv');
}

function escapeHtml(str) {
    const div = document.createElement('div');
    div.textContent = str;
    return div.innerHTML;
}

function _fmtTime(ts) {
    if (!ts) return '';
    try {
        const d = new Date(ts);
        if (!isNaN(d.getTime())) {
            const y = d.getFullYear();
            const m = String(d.getMonth() + 1).padStart(2, '0');
            const day = String(d.getDate()).padStart(2, '0');
            const h = String(d.getHours()).padStart(2, '0');
            const min = String(d.getMinutes()).padStart(2, '0');
            return y + '-' + m + '-' + day + ' ' + h + ':' + min;
        }
    } catch (e) {}
    return ts.substring(0, 19);
}

function _fmtUnix(ts) {
    if (ts == null) return 'N/A';
    try {
        const d = new Date(Number(ts) * 1000);
        if (!isNaN(d.getTime())) {
            const y = d.getFullYear();
            const m = String(d.getMonth() + 1).padStart(2, '0');
            const day = String(d.getDate()).padStart(2, '0');
            const h = String(d.getHours()).padStart(2, '0');
            const min = String(d.getMinutes()).padStart(2, '0');
            return y + '-' + m + '-' + day + ' ' + h + ':' + min;
        }
    } catch (e) {}
    return String(ts);
}

function exportSerialNumbers() {
    const names = getAqcMachineNames();
    if (names.length === 0) return;
    let csv = "AQC,Slot,Serial Number,MAC ID,Total Workouts,Avg BDR,Avg Current,Battery %\n";
    names.forEach(name => {
        const slots = ALL_MACHINE_DATA[name].slots || {};
        const slotKeys = Object.keys(slots).sort((a, b) => parseInt(a) - parseInt(b));
        slotKeys.forEach(slotId => {
            const s = slots[slotId];
            const sn = (s.serial_number || '--').replace(/"/g, '""');
            const mac = (s.ring_mac || '--').replace(/"/g, '""');

            let completed = calculateCompletedCycleWorkouts(s);
            const avgBdr = getSlotAvgBdr(s, completed).toFixed(2);

            const sParts = (s.serial_number || '').split('-');
            let capacity = 24;
            if (sParts.length >= 4) {
                if (sParts[3] === 'WB') capacity = 32;
            }
            const totalWorkouts = completed.length;
            const avgBdrNum = parseFloat(avgBdr);
            const avgCurrent = avgBdrNum > 0 ? ((avgBdrNum / 100) * capacity).toFixed(2) : '0.00';

            const batt = s.battery_current != null ? s.battery_current : '--';
            csv += `${name},"${slotId}","${sn}","${mac}","${totalWorkouts}","${avgBdr}","${avgCurrent}","${batt}"\n`;
        });
    });
    downloadCSV(csv, 'All_Serial_Numbers.csv');
}

let _machineBuffer = '';
let _machineBufferTimer = null;
document.addEventListener('keydown', (e) => {
    if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA') return;

    if (e.ctrlKey && (e.key === 'ArrowLeft' || e.key === 'ArrowRight')) {
        e.preventDefault();
        if (currentView === 'rings' && ringsData.length > 0) {
            const names = [...new Set(ringsData.map(d => d.file))].sort();
            const idx = names.indexOf(ringsSelectedMachine);
            if (idx === -1 && names.length > 0) {
                ringsSelectedMachine = names[0];
            } else {
                const nextIdx = e.key === 'ArrowLeft'
                    ? (idx - 1 + names.length) % names.length
                    : (idx + 1) % names.length;
                ringsSelectedMachine = names[nextIdx];
            }
            ringsKpiFilter = '';
            ringsStatusFilter = '';
            populateRingsFilter();
            ringsRenderGrid();
            setTimeout(() => {
                const rg = document.getElementById('rings-grid');
                if (rg) rg.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
            }, 100);
            return;
        }
        const names = getAqcMachineNames();
        if (names.length === 0) return;
        const idx = names.indexOf(CURRENT_MACHINE);
        if (idx === -1) return;
        const nextIdx = e.key === 'ArrowLeft'
            ? (idx - 1 + names.length) % names.length
            : (idx + 1) % names.length;
        const nextMachine = names[nextIdx];
        switchMachine(nextMachine);
        setTimeout(() => {
            const hmGrid = document.getElementById('heatmap-grid');
            if (hmGrid) hmGrid.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
        }, 100);
        return;
    }

    if (e.key >= '0' && e.key <= '9') {
        _machineBuffer += e.key;
        clearTimeout(_machineBufferTimer);
        _machineBufferTimer = setTimeout(() => { _machineBuffer = ''; }, 1500);
        e.preventDefault();
    } else if (e.key === 'Enter' && _machineBuffer.length > 0) {
        const num = _machineBuffer;
        _machineBuffer = '';

        if (currentView === 'rings' && ringsData.length > 0) {
            const names = [...new Set(ringsData.map(d => d.file))].sort();
            const match = names.find(name => {
                const m = name.match(/(\d+)/);
                return m && (m[1] === num || parseInt(m[1]) === parseInt(num));
            });
            if (match) {
                ringsSelectedMachine = match;
                ringsKpiFilter = '';
                ringsStatusFilter = '';
                populateRingsFilter();
                ringsRenderGrid();
                setTimeout(() => {
                    const rg = document.getElementById('rings-grid');
                    if (rg) rg.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
                }, 50);
            }
            return;
        }

        const names = getAqcMachineNames();
        if (names.length > 0) {
            const match = names.find(name => {
                const m = name.match(/(\d+)$/);
                return m && (m[1] === num || parseInt(m[1]) === parseInt(num));
            });
            if (match) switchMachine(match);
        }
    } else {
        _machineBuffer = '';
        clearTimeout(_machineBufferTimer);
    }
});

let removedSlotsByMachine = {};
async function loadRemovedSlotsConfig() {
    try {
        const res = await fetch('/api/machines/config');
        if (!res.ok) return;
        const data = await res.json();
        const next = {};
        (data.machines || []).forEach(m => {
            if (m && m.name && Array.isArray(m.removed_slots) && m.removed_slots.length) {
                next[normalizeAqcMachineName(m.name)] = new Set(m.removed_slots.map(String));
            }
        });
        removedSlotsByMachine = next;
    } catch (e) {
        console.warn('Could not load removed slots config:', e);
    }
}

const dtFormatter = new Intl.DateTimeFormat('en-US', { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' });

let chartA, chartB, detailLineChart, currentSlotPanel = null;
let globalHeatmapData = [];
let globalFwVersion = "--";
function setBdrKpiValue(el, value, options = {}) {
    if (!el) return;
    const text = String(value);
    const numeric = parseFloat(text.replace(/,/g, ''));
    const suffix = options.suffix ?? (text.trim().endsWith('%') ? '%' : '');
    const decimals = options.decimals ?? (Number.isFinite(numeric) && text.includes('.') ? text.split('.')[1].replace(/[^0-9].*$/, '').length : 0);
    const target = Number.isFinite(numeric) ? numeric : null;

    if (target === null || el.dataset.kpiAnimated === 'true') {
        el.textContent = text;
        return;
    }

    el.dataset.kpiAnimated = 'true';
    const duration = 820;
    const start = performance.now();
    const easeOut = t => 1 - Math.pow(1 - t, 3);

    function frame(now) {
        const progress = Math.min((now - start) / duration, 1);
        const current = target * easeOut(progress);
        el.textContent = current.toFixed(decimals) + suffix;
        if (progress < 1) requestAnimationFrame(frame);
        else el.textContent = text;
    }
    requestAnimationFrame(frame);
}
function calculateWorkoutsFromBdrCycles(cycles) {
    let workouts = [];
    if (!cycles || cycles.length === 0) return workouts;
    for (let i = 0; i < cycles.length; i++) {
        let curr = cycles[i];
        let drop, hours;
        if (i < cycles.length - 1) {
            let next = cycles[i + 1];
            drop = curr.start_pct - next.start_pct;
            if (drop <= 0) continue;
        } else {
            drop = curr.start_pct - curr.end_pct;
        }
        hours = curr.duration_min / 60;
        let bdr = hours > 0 ? drop / hours : 0;
        workouts.push({
            workout_num: workouts.length + 1,
            start_pct: curr.start_pct,
            end_pct: i < cycles.length - 1 ? cycles[i + 1].start_pct : curr.end_pct,
            duration_min: curr.duration_min,
            bdr: parseFloat(bdr.toFixed(2)),
            died: i < cycles.length - 1 ? cycles[i + 1].start_pct === 0 && curr.start_pct > 0 : curr.end_pct === 0 && curr.start_pct > 0,
            readings: curr.readings || 0
        });
    }
    return workouts;
}

function calculateWorkoutsFromCycles(completedCycles) {
    let workouts = [];
    if (!completedCycles || completedCycles.length < 2) return workouts;

    let groups = [];
    let currentGroup = [completedCycles[0]];

    for (let i = 1; i < completedCycles.length; i++) {
        if (completedCycles[i].cycle === 1 && completedCycles[i - 1].cycle > 1) {
            groups.push(currentGroup);
            currentGroup = [completedCycles[i]];
        } else {
            currentGroup.push(completedCycles[i]);
        }
    }
    if (currentGroup.length > 0) groups.push(currentGroup);

    groups.forEach(group => {
        for (let i = 0; i < group.length - 1; i++) {
            let curr = group[i];
            let next = group[i + 1];
            let drop = curr.start_pct - next.start_pct;
            if (drop <= 0) continue;
            let hours = curr.duration_min / 60;
            let bdr = hours > 0 ? drop / hours : 0;
            workouts.push({
                workout_num: workouts.length + 1,
                start_pct: curr.start_pct,
                end_pct: next.start_pct,
                duration_min: curr.duration_min,
                bdr: parseFloat(bdr.toFixed(2)),
                died: next.start_pct === 0 && curr.start_pct > 0,
                readings: curr.readings || 0
            });
        }
    });

    return workouts;
}

function calculateCompletedCycleWorkouts(slotData) {
    if (slotData?.bdr_data?.cycles?.length >= 1) {
        return calculateWorkoutsFromBdrCycles(slotData.bdr_data.cycles);
    }
    return calculateWorkoutsFromCycles(slotData?.bdr_state?.completed_cycles || []);
}

function getSlotAvgBdr(slotData, completedWorkouts) {
    if (slotData?.bdr_data?.avg_bdr != null) {
        return parseFloat(slotData.bdr_data.avg_bdr);
    }
    if (completedWorkouts && completedWorkouts.length > 0) {
        const sum = completedWorkouts.reduce((s, w) => s + parseFloat(w.bdr), 0);
        return parseFloat((sum / completedWorkouts.length).toFixed(2));
    }
    return 0;
}

function getApexGrid(style) {
    const isDark = document.documentElement.getAttribute('data-theme') === 'dark';
    if (style === 'detail') {
        return { borderColor: '#1e293b', strokeDashArray: 2 };
    }
    return { borderColor: isDark ? '#1e293b' : '#f0f0f0', strokeDashArray: isDark ? 4 : 0 };
}

function isFlatBatteryGraph(history) {
    if (!Array.isArray(history) || history.length < 2) return false;
    const firstLevel = Number(history[0]?.[1]);
    if (!Number.isFinite(firstLevel)) return false;
    if (firstLevel >= 90) return false;
    const startTime = new Date(history[0]?.[0]).getTime();
    const endTime = new Date(history[history.length - 1]?.[0]).getTime();
    if (!Number.isFinite(startTime) || !Number.isFinite(endTime)) return false;
    if (endTime - startTime <= 120 * 60 * 1000) return false;
    return history.every(point => {
        const level = Number(point?.[1]);
        return Number.isFinite(level) && Math.abs(level - firstLevel) <= 0.1;
    });
}

function computeSerialStats(machinesData, ringsArr = ringsData) {
    const counts = Object.create(null);
    const locations = Object.create(null);
    let totalRaw = 0;
    let totalSlots = 0;
    let totalBdrSum = 0;
    let bdrCount = 0;
    let totalBattSum = 0;
    let battCount = 0;
    const dataSrc = machinesData || ALL_MACHINE_DATA || {};
    
    // Create a map of machine occupancy from Rings data to cross-reference
    const ringsOccupancy = Object.create(null);
    if (Array.isArray(ringsArr)) {
        ringsArr.forEach(r => {
            const mn = String(r.file || '').trim().toLowerCase();
            if (isOccupiedRingSlotRecord(r)) {
                if (!ringsOccupancy[mn]) ringsOccupancy[mn] = new Set();
                ringsOccupancy[mn].add(String(r.slot));
            }
        });
    }

    Object.entries(dataSrc).forEach(([machineName, md]) => {
        const mnKey = machineName.trim().toLowerCase();

        // CROSS-REFERENCE: If Rings data exists for this machine and it shows 0 serials, 
        // trust the Rings view (which the user says is correct) and treat this BDR data as stale/empty.
        if (ringsArr && ringsArr.length > 0) {
            if (!ringsOccupancy[mnKey] || ringsOccupancy[mnKey].size === 0) {
                return; // SKIP machine because it is empty in the live Rings view
            }
        }

        const slots = md.slots || {};
        Object.entries(slots).forEach(([slotId, s]) => {
            const sn = (s.serial_number || '').toString().trim();
            
            // Further cross-reference at slot level if possible
            const isOccupiedInRings = ringsOccupancy[mnKey] && ringsOccupancy[mnKey].has(String(slotId));
            const isEmptyInBdr = !isOccupiedRingSlotRecord({ serial_number: sn });
            
            // If BDR says it has a serial but Rings says it's empty, treat as empty (stale BDR data)
            if (!isEmptyInBdr && ringsArr && ringsArr.length > 0 && !isOccupiedInRings) {
                return; 
            }

            if (!isEmptyInBdr) {
                totalRaw += 1;
                counts[sn] = (counts[sn] || 0) + 1;
                if (!locations[sn]) locations[sn] = [];
                locations[sn].push({ machine: machineName, slot: slotId });
                totalSlots++;
            }

            if (s.battery_current != null) {
                totalBattSum += s.battery_current;
                battCount++;
            }

            const completed = calculateCompletedCycleWorkouts(s);
            if (completed && completed.length > 0) {
                const bdr = getSlotAvgBdr(s, completed);
                totalBdrSum += bdr;
                bdrCount++;
            }
        });
    });
    
    const uniqueCount = Object.keys(counts).length;
    const duplicates = Object.keys(counts).filter(k => counts[k] > 1).map(k => ({ serial: k, count: counts[k], locations: locations[k] }));
    duplicates.sort((a,b) => b.count - a.count);
    
    const fleetAvgBatt = battCount > 0 ? (totalBattSum / battCount) : 0;
    const fleetAvgBdr = bdrCount > 0 ? (totalBdrSum / bdrCount) : 0;
    
    return { 
        totalRaw, 
        uniqueCount, 
        duplicates, 
        counts, 
        locations, 
        totalSlots,
        avgBattery: fleetAvgBatt,
        avgBdr: fleetAvgBdr
    };
}

function renderDuplicates(duplicates) {
    const panel = document.getElementById('duplicates-panel');
    if (!panel) return;
    if (!duplicates || duplicates.length === 0) {
        panel.innerHTML = '<div style="color:var(--muted); font-size:13px;">No duplicate serials detected</div>';
        return;
    }
    let html = '<div style="max-height:220px; overflow:auto; width:100%;">';
    html += '<table style="width:100%; border-collapse:collapse; font-size:13px;">';
    html += '<thead><tr><th style="text-align:left; padding:6px; color:var(--muted)">Serial</th><th style="text-align:right; padding:6px; color:var(--muted)">Count</th><th style="text-align:left; padding:6px; color:var(--muted)">Locations</th></tr></thead>';
    html += '<tbody>';
    duplicates.forEach(d => {
        const locs = d.locations.map(l => `${l.machine}:${l.slot}`).join(', ');
        html += `<tr><td style="padding:6px; border-top:1px solid var(--border);">${d.serial}</td><td style="padding:6px; border-top:1px solid var(--border); text-align:right;">${d.count}</td><td style="padding:6px; border-top:1px solid var(--border);">${locs}</td></tr>`;
    });
    html += '</tbody></table></div>';
    panel.innerHTML = html;
}

function init() {
  try {
    if (!SESSION_DATA || !SESSION_DATA.slots) {
      const emptyState = document.getElementById('empty-state');
      const dashboardContent = document.getElementById('dashboard-content');
      if (emptyState) emptyState.style.display = 'flex';
      if (dashboardContent) dashboardContent.style.display = 'none';
      let exportBtn = document.getElementById('export-report-btn');
      if (exportBtn) exportBtn.style.display = 'none';
      let exportAllBtn = document.getElementById('export-all-workouts-btn');
      if (exportAllBtn) exportAllBtn.style.display = 'none';
      let exportSerialBtn = document.getElementById('export-serial-btn');
      if (exportSerialBtn) exportSerialBtn.style.display = 'none';
      let logsBtn = document.getElementById('logs-btn');
      if (logsBtn) logsBtn.style.display = 'none';
      return;
    }
    
    const emptyState = document.getElementById('empty-state');
    const dashboardContent = document.getElementById('dashboard-content');
    if (emptyState) emptyState.style.display = 'none';
    if (dashboardContent) dashboardContent.style.display = 'flex';
    switchView(currentView);
    let exportBtn = document.getElementById('export-report-btn');
    if (exportBtn) exportBtn.style.display = 'inline-flex';
    let exportAllBtn = document.getElementById('export-all-workouts-btn');
    if (exportAllBtn) exportAllBtn.style.display = 'inline-flex';
    let exportSerialBtn = document.getElementById('export-serial-btn');
    if (exportSerialBtn) exportSerialBtn.style.display = 'inline-flex';
    let logsBtn = document.getElementById('logs-btn');
    if (logsBtn) logsBtn.style.display = 'inline-flex';
    
    let detailPanel = document.getElementById('detail-panel');
    // Hide panel if no slot is selected; otherwise keep it for refresh restoration
    if (detailPanel && !currentSlotPanel) detailPanel.classList.remove('visible');

    if (chartA) chartA.destroy();
    if (chartB) chartB.destroy();
    document.getElementById('chart-a').innerHTML = '';
    document.getElementById('chart-b').innerHTML = '';

    if (detailLineChart) detailLineChart.destroy();

    document.getElementById('line-chart').innerHTML = '';

    const ringStateBySlot = {};
    if (ringsData && ringsData.length > 0 && CURRENT_MACHINE) {
        ringsData.forEach(r => {
            if (r.file === CURRENT_MACHINE) {
                ringStateBySlot[r.slot] = r.state;
            }
        });
    }
    
    const totalSlots = 64;
    const removedSet = (CURRENT_MACHINE ? removedSlotsByMachine[normalizeAqcMachineName(CURRENT_MACHINE)] : null) || new Set();
    
    // Cross-reference with Rings occupancy to mask stale BDR data
    const currentMachineNorm = normalizeAqcMachineName(CURRENT_MACHINE);
    const machineRingsData = ringsData.filter(rd => normalizeAqcMachineName(rd.file) === currentMachineNorm);
    const occupiedInRings = new Set(machineRingsData.filter(rd => rd.serial_number && rd.serial_number !== '--' && rd.serial_number !== 'N/A').map(rd => String(rd.slot)));

    const slots = [];
    for (let i = 1; i <= totalSlots; i++) {
        const slotKey = String(i);
        const sData = SESSION_DATA.slots[slotKey] || {
            ring_name: "--",
            serial_number: "--",
            battery_current: null,
            bdr_state: { phase: "UNKNOWN", completed_cycles: [], consecutive_failures: 0 },
            bdr_battery_history: [],
            firmware_version: "--"
        };

        // Mask stale BDR data if Rings (source of truth for occupancy) says it's empty
        if (ringsFetchCompleted && !occupiedInRings.has(slotKey)) {
            sData.serial_number = "--";
            sData.ring_name = "--";
            sData.battery_current = null;
            sData.bdr_state = { phase: "UNKNOWN", completed_cycles: [], consecutive_failures: 0 };
            sData.bdr_battery_history = [];
            sData.firmware_version = "--";
        }

        // Force removed slots to appear as empty
        if (removedSet.has(slotKey)) {
            sData.serial_number = "--";
            sData.ring_name = "--";
            sData.battery_current = null;
            sData.bdr_state = { phase: "UNKNOWN", completed_cycles: [], consecutive_failures: 0 };
            sData.bdr_battery_history = [];
            sData.firmware_version = "--";
        }
        slots.push({ slot_id: slotKey, ...sData });
    }

    let avgBattSum = 0;
    let validBattCount = 0;
    
    let phaseCount = { "DISCHARGING": 0, "WAIT_DISCHARGE": 0, "INITIAL_CHARGE": 0 };
    let battBins = new Array(10).fill(0);
    

    let totalFleetBdr = 0;
    let slotsWithBdr = 0;
    let validSlotCount = 0;
    
    globalHeatmapData = [];
    let heatmapData = globalHeatmapData;

    let anomalies = [];
    let spotlightAnomalies = [];
    globalFwVersion = "--";
    let fwSet = new Set();

    slots.forEach(s => {
        if (s.firmware_version) {
            fwSet.add(s.firmware_version);
            globalFwVersion = s.firmware_version;
        }
        if (s.battery_current != null) {
            avgBattSum += s.battery_current;
            validBattCount++;
            let bin = Math.min(Math.floor(s.battery_current / 10), 9);
            battBins[bin]++;
        }
        
        let phase = s.bdr_state?.phase || "OTHER";
        if (phaseCount[phase] !== undefined) phaseCount[phase]++;
        
        let diedHere = false;
        let highestBdrPos = 0;
        let highestBdrNeg = 0;
        let anomCycle = "-";
        let anomDur = "-";
        let anomBdrValue = 0;
        
        let completed = calculateCompletedCycleWorkouts(s);
        
        let history = s.bdr_battery_history || [];
        let isSensorIssue = isFlatBatteryGraph(history);

        // Strict died detection: battery < 3% OR last segment flat > 3 hr OR data stale > 3 hr
        const THREE_HOURS = 180 * 60 * 1000;
        if (s.battery_current !== null && s.battery_current < 3) {
            diedHere = true;
        }
        if (!diedHere && history.length >= 2) {
            const lastBatt = history[history.length - 1][1];
            let flatStartIdx = history.length - 1;
            for (let j = history.length - 2; j >= 0; j--) {
                if (Math.abs(history[j][1] - lastBatt) <= 1) {
                    flatStartIdx = j;
                } else {
                    break;
                }
            }
            if (flatStartIdx < history.length - 1) {
                var t1 = new Date(history[history.length - 1][0]).getTime();
                var t2 = new Date(history[flatStartIdx][0]).getTime();
                if (t1 - t2 > THREE_HOURS) {
                    diedHere = true;
                }
            }
        }
        if (!diedHere && history.length >= 1) {
            var lastTs = new Date(history[history.length - 1][0]).getTime();
            if (Date.now() - lastTs > THREE_HOURS) {
                diedHere = true;
            }
        }
        s.diedHere = diedHere;

        completed.forEach(c => {
            if (c.bdr > highestBdrPos) { highestBdrPos = c.bdr; anomBdrValue = c.bdr; anomCycle = c.workout_num; anomDur = c.duration_min; }
            if (c.bdr < highestBdrNeg) { highestBdrNeg = c.bdr; anomBdrValue = c.bdr; anomCycle = c.workout_num; anomDur = c.duration_min; }
        });

        let avgSlotBdr = getSlotAvgBdr(s, completed);
        if (avgSlotBdr > 0) {
            totalFleetBdr += avgSlotBdr;
            slotsWithBdr++;
        }

        let sn = s.serial_number || '';
        const slotRange = getSlotBdrRange(s);
        const isPro = slotRange.product === 'PRO';

        let fails = s.bdr_state?.consecutive_failures || 0;

        let issues = [];
        
        let peakIdx = history.length - 1;
        if (history.length > 0) {
            let maxVal = history[history.length - 1][1];
            for (let i = history.length - 2; i >= 0; i--) {
                if (history[i][1] >= maxVal) {
                    maxVal = history[i][1];
                    peakIdx = i;
                } else {
                    break;
                }
            }
        }
        let trueActiveDischarge = history.slice(peakIdx);

        // Find the "last part" - tail after the final workout drop
        // Slanting is only evaluated on this tail, not the full discharge
        let dischargeTail = trueActiveDischarge;
        if (trueActiveDischarge.length >= 4) {
            let tailStart = 0;
            for (let i = trueActiveDischarge.length - 1; i >= 1; i--) {
                let drop = trueActiveDischarge[i-1][1] - trueActiveDischarge[i][1];
                if (drop > 3) {
                    tailStart = i;
                    break;
                }
            }
            if (tailStart > 0) {
                dischargeTail = trueActiveDischarge.slice(tailStart);
            }
        }

        // 3. SLANTING LEAK - only on the tail after the last workout drop (disabled for PRO)
        let currentDrop = 0;
        let currentDurMins = 0;
        let isSlantingLeak = false;
        if (!isPro && dischargeTail.length >= 2) {
            let startT = new Date(dischargeTail[0][0]);
            let endT = new Date(dischargeTail[dischargeTail.length - 1][0]);
            currentDurMins = Math.round((endT - startT) / 60000);
            currentDrop = dischargeTail[0][1] - dischargeTail[dischargeTail.length - 1][1];
            
            if (currentDurMins > 180 && currentDrop > 1) {
                // If it's a slanting leak (shallow drop over long time) OR if it hasn't hit a 5% drop yet
                if (currentDrop < 5 || (currentDrop / (currentDurMins / 60) < 2)) {
                    isSlantingLeak = true;
                    anomDur = currentDurMins; // Ensure duration is passed to report
                    issues.push({ 
                        type: 'WARNING', 
                        priority: 15, 
                        title: 'Gradual Drop (Slanting Leak)', 
                        message: `Tail slanting > 3h (${currentDurMins}m) - Drop (${currentDrop.toFixed(1)}%)` 
                    });
                }
            }
        }

        let latestCycle = history;
        if (history.length > 0) {
            let lastHikeStart = 0;
            for (let i = history.length - 1; i > 0; i--) {
                if (history[i][1] > history[i-1][1]) {
                    let start = i - 1;
                    while (start > 0 && history[start][1] >= history[start-1][1]) {
                        start--;
                    }
                    lastHikeStart = start;
                    break;
                }
            }
            latestCycle = history.slice(lastHikeStart);
        }

        let latestWorkout = latestCycle;
        if (latestCycle.length > 0) {
            let lastDropStart = latestCycle.length - 1;
            for (let i = latestCycle.length - 1; i > 0; i--) {
                if (latestCycle[i][1] > latestCycle[i-1][1]) {
                    lastDropStart = i;
                    break;
                }
            }
            latestWorkout = latestCycle.slice(lastDropStart);
        }

        // NOTE: Died detection is handled below by strict logic:
        // battery < 3% OR last segment flat > 3 hours (at low battery level)
        
        let peakIndex = 0;
        let peakValue = latestCycle.length > 0 ? latestCycle[0][1] : 0;
        for (let i = 1; i < latestCycle.length; i++) {
            if (latestCycle[i][1] >= peakValue) {
                peakValue = latestCycle[i][1];
                peakIndex = i;
            } else {
                break;
            }
        }
        let dischargePhase = latestCycle.slice(peakIndex);

        // 3a. Full charge (0→100) before slanting leak → CRITICAL
        if (isSlantingLeak && latestCycle.length > 0) {
            let chargePortion = latestCycle.slice(0, peakIndex);
            if (chargePortion.length >= 2) {
                let minCharge = Math.min(...chargePortion.map(d => d[1]));
                let maxCharge = Math.max(...chargePortion.map(d => d[1]));
                if (minCharge <= 5 && maxCharge >= 95) {
                    issues.push({
                        type: 'CRITICAL',
                        priority: 20,
                        title: 'Critical Slanting Leak (Post Full Charge)',
                        message: `Full charge (${minCharge.toFixed(1)}→${maxCharge.toFixed(1)}%) then slanting ${currentDurMins}m`
                    });
                }
            }
        }

        // 3. Unexpected Charging
        let unexpectedSpikes = 0;
        for(let i = 1; i < dischargePhase.length; i++) {
            if (dischargePhase[i][1] > dischargePhase[i-1][1]) unexpectedSpikes++;
        }
        if (unexpectedSpikes > 0 && s.bdr_state?.phase === 'DISCHARGING') {
            issues.push({ type: 'WARNING', priority: 8, title: `Unexpected Charge`, message: `Unexpected charge during discharge` });
        }

        // 4. Irregular discharge / thresholds
        let zigzags = 0;
        for(let i = 2; i < dischargePhase.length; i++) {
            let diff1 = dischargePhase[i-1][1] - dischargePhase[i-2][1];
            let diff2 = dischargePhase[i][1] - dischargePhase[i-1][1];
            if (diff1 * diff2 < 0 && Math.abs(diff1) > 2 && Math.abs(diff2) > 2) zigzags++;
        }
        if (zigzags >= 2) {
            issues.push({ type: 'WARNING', priority: 7, title: `Irregular pattern`, message: `Unstable battery behavior` });
        }

        // 5. High failure count
        if (fails >= 10) {
            issues.push({ type: 'WARNING', priority: 6, title: `${fails} failures`, message: `WAIT_DISCHARGE, stuck at ${s.battery_current || 0}%` });
        }

        // 6. (DEPRECATED) 2.5-Hour Slanting Leak Rule (Moved to top as short-circuit)
        
        // 7. Minimum Steps Rule (Legacy Slant Anomaly)
        let distinctSteps = 0;
        let inFlatStasis = false;
        let accumulatedDrop = 0;

        for (let i = 1; i < trueActiveDischarge.length; i++) {
            let diff = trueActiveDischarge[i][1] - trueActiveDischarge[i-1][1];
            if (diff === 0) {
                if (accumulatedDrop <= -3) {
                    distinctSteps++;
                }
                accumulatedDrop = 0;
                inFlatStasis = true;
            } else if (diff < 0) {
                if (inFlatStasis) {
                    accumulatedDrop = 0;
                    inFlatStasis = false;
                }
                accumulatedDrop += diff;
            } else if (diff > 0) {
                distinctSteps = 0;
                inFlatStasis = false;
                accumulatedDrop = 0;
            }
        }

        let currentVal = dischargeTail.length > 0 ? dischargeTail[dischargeTail.length - 1][1] : 0;
        let peakVal = dischargeTail.length > 0 ? dischargeTail[0][1] : 0;

        if (currentDurMins > 180 && peakVal - currentVal > 5 && distinctSteps < 4 && !isPro) {
            issues.push({ type: 'WARNING', priority: 7.5, title: 'Gradual Drop (Slanting Leak)', message: `Missing macro-steps (Only ${distinctSteps} valid steps)` });
        }

        let hmClass = 'slot-ok';
        let topIssue = null;
        
        // 1. BDR HEALTH LOGIC
        const BDR_MIN = slotRange.min, BDR_MAX = slotRange.max;

        let bdrOutOfRange = avgSlotBdr > 0 && (avgSlotBdr < BDR_MIN || avgSlotBdr > BDR_MAX);
        let highAvgBdr = avgSlotBdr > BDR_MAX;

        if (highAvgBdr) {
            issues.push({ 
                type: 'WARNING', 
                priority: 5.8, 
                title: 'High Avg BDR', 
                message: `Average BDR (${avgSlotBdr.toFixed(2)}) is above ${BDR_MAX}` 
            });
        } else if (bdrOutOfRange) {
            issues.push({ 
                type: 'WARNING', 
                priority: 5.6, 
                title: 'BDR Out of Range', 
                message: `Average BDR (${avgSlotBdr.toFixed(2)}) is outside target range (${BDR_MIN}-${BDR_MAX})` 
            });
        }

        // Handle empty slots
        const isEmpty = s.serial_number === "--" || s.serial_number === "N/A" || !s.serial_number;
        if (isEmpty) {
            hmClass = 'slot-empty';
        } else {
            validSlotCount++;
            // Check for no graph data (N/A)
            const hasGraphData = s.bdr_battery_history && s.bdr_battery_history.length > 0;
            if (!hasGraphData) {
                hmClass = 'slot-na';
            } else if (isSensorIssue) {
                hmClass = 'slot-sensor-issue';
                topIssue = {
                    type: 'WARNING',
                    priority: 16,
                    title: 'Sensor Issue',
                    message: 'Battery graph is flat from start to end'
                };
            } else {
            // PASS: >= 6 workouts AND avg BDR in category range
            let isPass = !diedHere && !isSlantingLeak && completed.length >= 6 && avgSlotBdr >= BDR_MIN && avgSlotBdr <= BDR_MAX;
            if (isPass) {
                hmClass = 'slot-pass';
            } else {
            let lowAvgBdr = avgSlotBdr > 0 && avgSlotBdr < BDR_MIN;
            if (lowAvgBdr) hmClass = 'slot-low-bdr';
            else if (fails >= 3) hmClass = 'slot-warn';
            if (diedHere) hmClass = 'slot-dead';

            // BDR OUT-OF-RANGE OVERRIDE
            if (bdrOutOfRange) {
                if (hmClass === 'slot-ok') hmClass = 'slot-warn'; // out of range -> WARNING (Orange)
            }
            
            if (issues.length > 0) {
                issues.sort((a,b) => b.priority - a.priority);
                topIssue = issues[0];
                if (topIssue.type === 'CRITICAL') hmClass = 'slot-dead';
                else if (topIssue.type === 'WARNING' && hmClass !== 'slot-low-bdr') {
                    if (hmClass === 'slot-ok') hmClass = 'slot-warn';
                }
            }
            // Force Slanting Leak Warning
            if (isSlantingLeak) {
                if (hmClass === 'slot-ok') hmClass = 'slot-warn';
            }
            if (highAvgBdr) {
                hmClass = 'slot-high-bdr';
            }
            }
            }
        }

        // Ring state override: if ring slot has a known state, reflect in BDR dashboard
        const ringState = ringStateBySlot[s.slot_id];
        if (ringState === 'PASSED' || ringState === 'PASS') {
            hmClass = 'slot-pass';
        } else if (ringState === 'FAILED' || ringState === 'FAIL') {
            hmClass = 'slot-danger';
        }

        // Determine warning reason for slot-warn cells
        let warnReason = '';
        if (hmClass === 'slot-warn') {
            if (fails >= 3) {
                warnReason = `${fails} consecutive failures`;
            } else if (isSlantingLeak) {
                warnReason = 'Slanting leak detected';
            } else if (bdrOutOfRange) {
                warnReason = `BDR ${avgSlotBdr.toFixed(2)} out of range (${BDR_MIN}-${BDR_MAX})`;
            } else if (topIssue && topIssue.type === 'WARNING') {
                warnReason = topIssue.title;
            }
        }

        const slotFw = s.firmware_version || 'N/A';
        heatmapData.push({ id: s.slot_id, cls: hmClass, raw: s, fw: slotFw, latestCycle, dischargePhase, trueActiveDischarge, topIssue, completed, avgSlotBdr, isSlantingLeak, isSensorIssue, bdrOutOfRange, highAvgBdr, fails, warnReason });

        if (highestBdrPos > 5 || highestBdrNeg < -5 || topIssue) {
            if (topIssue) {
                let sev = topIssue.type === 'CRITICAL' ? 'CRITICAL' : (topIssue.type === 'FAIL' ? 'HIGH' : 'MEDIUM');
                let sevNum = topIssue.priority;
                let desc = topIssue.title;
                if (desc === 'Gradual Drop (Slanting Leak)') desc = 'Gradual Drop (Slanting Leak) - Active for > 3h';
                anomalies.push({ slot: s.slot_id, mac: s.ring_mac || "--", sn: s.serial_number, sev, sevNum, desc, bdr: avgSlotBdr ? avgSlotBdr.toFixed(2) : '-', cycle: anomCycle || '-', dur: anomDur });
            } else {
                let sev = (highestBdrPos > 5 || highestBdrNeg < -5) ? 'HIGH' : 'MEDIUM';
                let desc = highestBdrPos > 5 ? 'High Positive BDR' : 'High Negative BDR';
                anomalies.push({ slot: s.slot_id, mac: s.ring_mac || "--", sn: s.serial_number, sev, sevNum: sev==='HIGH'?8:5, desc, bdr: avgSlotBdr.toFixed(2), cycle: anomCycle, dur: anomDur });
            }
        }

        if (topIssue) {
            spotlightAnomalies.push({
                slot_id: s.slot_id,
                type: topIssue.type,
                priority: topIssue.priority,
                title: topIssue.title,
                message: topIssue.message
            });
        }
    });

    let avgBatt = validBattCount ? (avgBattSum / validBattCount) : 0;
    
    let hSessionTimeEl = document.getElementById('h-session-time');
    if (hSessionTimeEl) {
        try {
            hSessionTimeEl.innerText = SESSION_DATA.saved_at ? new Date(SESSION_DATA.saved_at).toLocaleString() : '--';
        } catch (e) {
            hSessionTimeEl.innerText = '--';
        }
    }

    // Compute fleet-wide statistics for top KPI cards
    let fleetStats = { totalSlots: 0, avgBattery: 0, avgBdr: 0, totalRaw: 0, uniqueCount: 0 };
    try {
        fleetStats = computeSerialStats(ALL_MACHINE_DATA);
    } catch (e) {
        console.warn('Error computing fleet stats in init', e);
    }

    let hSlotsEl = document.getElementById('h-slots');
    if (hSlotsEl) hSlotsEl.innerText = validSlotCount + " / " + totalSlots + " SLOTS (Machine)";
    
    // 1. Total Slots (Fleet-wide active)
    let kpiTotalEl = document.getElementById('kpi-total');
    setBdrKpiValue(kpiTotalEl, fleetStats.totalSlots);
    
    // 2. Avg Battery (Fleet-wide)
    let kpiBattEl = document.getElementById('kpi-batt');
    if (kpiBattEl) {
        setBdrKpiValue(kpiBattEl, fleetStats.avgBattery.toFixed(1) + "%", { decimals: 1, suffix: "%" });
        kpiBattEl.dataset.status = fleetStats.avgBattery > 60 ? "ok" : fleetStats.avgBattery >= 30 ? "warn" : "danger";
    }
    
    // 3. Avg Fleet BDR (Fleet-wide)
    let kpiAnomEl = document.getElementById('kpi-anom');
    setBdrKpiValue(kpiAnomEl, fleetStats.avgBdr.toFixed(2), { decimals: 2 });

    // 4. Total Serials (Fleet-wide)
    try {
        const rawEl = document.getElementById('kpi-serials-raw');
        const dupEl = document.getElementById('kpi-serials-dup');
        setBdrKpiValue(rawEl, fleetStats.totalRaw);
        const dupCount = Math.max(0, fleetStats.totalRaw - fleetStats.uniqueCount);
        setBdrKpiValue(dupEl, dupCount);
    } catch (e) {
        console.warn('Error updating serial KPIs in init', e);
    }

    const savedAt = SESSION_DATA.saved_at;
    const sessionDate = savedAt ? new Date(savedAt) : null;
    document.getElementById('f-session').innerText = "Session: " + (sessionDate && !isNaN(sessionDate.getTime()) ? sessionDate.toISOString().replace('T', ' ').replace(/\..+/, ' UTC') : '--');
    document.getElementById('f-fw').innerText = "FW: " + (fwSet.size ? [...fwSet].join(', ') : '--');
    document.getElementById('f-slots').innerText = "Total Records: " + validSlotCount;

    let hmGrid = document.getElementById('heatmap-grid');
    if (hmGrid) hmGrid.innerHTML = '';
    
    let spotlightSec = document.getElementById('spotlight-section');
    let spotlightGrid = document.getElementById('spotlight-grid');
    if (spotlightSec && spotlightGrid) {
        if (spotlightAnomalies.length > 0) {
            spotlightAnomalies.sort((a,b) => b.priority - a.priority);
            spotlightSec.style.display = 'flex';
            const spotlightInsight = document.getElementById('spotlight-insight');
            if (spotlightInsight) spotlightInsight.innerText = `${spotlightAnomalies.length} anomalies detected across ${validSlotCount} active slots`;
            
            let existingToggle = document.getElementById('spotlight-toggle-btn');
            if (existingToggle) existingToggle.remove();

            let visibleSpotlights = spotlightAnomalies.slice(0, 6);
            let renderSpotlights = (items) => {
                spotlightGrid.innerHTML = items.map(a => `
                    <div class="spotlight-card ${a.type}">
                        <div class="spotlight-slot">Slot ${a.slot_id}</div>
                        <div class="spotlight-title">${a.title}</div>
                        <div class="spotlight-msg">${a.message}</div>
                    </div>
                `).join('');
            };
            renderSpotlights(visibleSpotlights);

            if (spotlightAnomalies.length > 6) {
                let toggleBtn = document.createElement('button');
                toggleBtn.id = 'spotlight-toggle-btn';
                toggleBtn.className = 'upload-btn';
                toggleBtn.style.alignSelf = 'flex-start';
                toggleBtn.style.marginTop = '4px';
                toggleBtn.innerText = 'View All ' + spotlightAnomalies.length + ' Anomalies';
                let isExpanded = false;
                toggleBtn.onclick = () => {
                    isExpanded = !isExpanded;
                    renderSpotlights(isExpanded ? spotlightAnomalies : visibleSpotlights);
                    toggleBtn.innerText = isExpanded ? 'Show Less' : 'View All ' + spotlightAnomalies.length + ' Anomalies';
                };
                spotlightSec.appendChild(toggleBtn);
            }
        } else {
            spotlightSec.style.display = 'none';
            spotlightGrid.innerHTML = '';
            let existingToggle = document.getElementById('spotlight-toggle-btn');
            if (existingToggle) existingToggle.remove();
        }
    }
    
    anomalies.sort((a,b) => b.sevNum - a.sevNum);
    let anomTb = document.getElementById('anomaly-tbody');
    anomTb.innerHTML = anomalies.length ? anomalies.map(a => `
        <tr class="anomaly-row-${a.sev.toLowerCase()}">
            <td class="mono">${a.slot}</td>
            <td class="mono">${a.mac}</td>
            <td class="mono">${a.sn}</td>
            <td><span class="badge ${a.sev === 'CRITICAL' ? 'critical' : (a.sev === 'HIGH' ? 'danger' : 'warn')}">${a.sev}</span></td>
            <td>${a.desc}</td>
            <td>${typeof a.bdr === 'number' ? a.bdr.toFixed(2) : a.bdr}</td>
            <td>${a.cycle}</td>
            <td>${a.dur}</td>
        </tr>
    `).join('') : `<tr><td colspan="8" style="text-align:center; color: var(--muted)">No anomalies detected</td></tr>`;



    chartA = new ApexCharts(document.getElementById('chart-a'), {
            chart: { type: 'bar', height: 180, toolbar: { show: false } },
            plotOptions: { bar: { horizontal: true, borderRadius: 4, distributed: true } },
            colors: ['#10B981', '#F59E0B', '#3B82F6'],
            series: [{ name: 'Slots', data: [phaseCount["DISCHARGING"], phaseCount["WAIT_DISCHARGE"], phaseCount["INITIAL_CHARGE"]] }],
            xaxis: { categories: ['DISCHARGING', 'WAIT_DISCHARGE', 'INITIAL_CHARGE'] },
            legend: { show: false },
            grid: getApexGrid()
        });
        chartA.render();

        chartB = new ApexCharts(document.getElementById('chart-b'), {
            chart: { type: 'bar', height: 180, toolbar: { show: false } },
            plotOptions: { bar: { borderRadius: 4 } },
            colors: ['#3B82F6'],
            series: [{ name: 'Slots', data: battBins }],
            xaxis: { categories: ['0-10%','10-20%','20-30%','30-40%','40-50%','50-60%','60-70%','70-80%','80-90%','90-100%'] },
            grid: getApexGrid()
        });
        chartB.render();



    // Detect duplicate serial numbers across all machines for highlighting
    const dupSerials = new Set();
    try {
        const dupStats = computeSerialStats(ALL_MACHINE_DATA);
        dupStats.duplicates.forEach(d => { dupSerials.add(d.serial); });
    } catch (e) { /* ignore */ }

    heatmapData.sort((a,b) => parseInt(a.id) - parseInt(b.id));

    const existingCells = hmGrid.children;
    const isRefresh = !!window.__preservingUi;
    heatmapData.forEach((hm, idx) => {
        let cls = hm.cls;
        const sn = (hm.raw.serial_number || '').toString().trim();
        if (dupSerials.has(sn)) cls += ' slot-dup';
        const badgeHtml = slotBadgeHtml(sn);
        if (isRefresh && idx < existingCells.length) {
            const el = existingCells[idx];
            el.className = `slot-cell ${cls}`;
            el.dataset.id = hm.id;
            el.dataset.cls = hm.cls;
            el.dataset.fw = hm.fw;
            el.dataset.wc = hm.completed.length;
            el.innerHTML = hm.id + badgeHtml;
        } else {
            let el = document.createElement('div');
            el.className = `slot-cell ${cls}`;
            el.dataset.id = hm.id;
            el.dataset.cls = hm.cls;
            el.dataset.fw = hm.fw;
            el.dataset.wc = hm.completed.length;
            el.innerHTML = hm.id + badgeHtml;
            hmGrid.appendChild(el);
        }
    });
    while (isRefresh && hmGrid.children.length > heatmapData.length) {
        hmGrid.removeChild(hmGrid.lastChild);
    }
    // Re-attach click handlers for all cells to capture updated hm references
    for (let i = 0; i < heatmapData.length; i++) {
        const hm = heatmapData[i];
        const el = hmGrid.children[i];
        el.onclick = () => {
            document.querySelectorAll('.slot-cell').forEach(c => c.classList.remove('active'));
            if (currentSlotPanel === hm.id) {
                detailPanel.classList.remove('visible');
                currentSlotPanel = null;
            } else {
                el.classList.add('active');
                openDetailPanel(hm);
            }
        };
    }

    const fwVersions = [...new Set(heatmapData.map(h => h.fw).filter(f => f !== 'N/A'))].sort();
    const fwContainer = document.getElementById('firmware-filters');
    fwContainer.innerHTML = '<span style="font-size:10px;text-transform:uppercase;letter-spacing:0.05em;color:var(--muted);font-weight:600;margin-right:8px;">FW:</span>';
    fwVersions.forEach(fw => {
        const btn = document.createElement('button');
        btn.className = 'heatmap-filter';
        btn.dataset.fw = fw;
        btn.textContent = fw;
        btn.onclick = () => {
            if (!window.firmwareFilterActive) window.firmwareFilterActive = new Set();
            const active = window.firmwareFilterActive;
            if (active.has(fw)) { active.delete(fw); btn.classList.remove('active'); }
            else { active.add(fw); btn.classList.add('active'); }
            if (active.size === 0) window.firmwareFilterActive = null;
            applyHeatmapFilter();
        };
        fwContainer.appendChild(btn);
    });
    const fwClear = document.createElement('button');
    fwClear.className = 'heatmap-filter';
    fwClear.textContent = 'Clear';
    fwClear.style.marginLeft = '8px';
    fwClear.onclick = () => {
        window.firmwareFilterActive = null;
        fwContainer.querySelectorAll('.heatmap-filter').forEach(b => b.classList.remove('active'));
        applyHeatmapFilter();
    };
    if (fwVersions.length > 0) fwContainer.appendChild(fwClear);

    resetHeatmapColors();
    applyCustomColors();
    applyHeatmapFilter();
    highlightCrossMachineDups();
    
    function navigateSlot(direction) {
        if (!currentSlotPanel) return;
        let active = window.heatmapFilterActive;
        let hasFilter = active && active.size > 0;
        let activeSlots = globalHeatmapData.filter(h => {
            if (h.cls === 'slot-empty') return false;
            if (hasFilter && !active.has(h.cls)) return false;
            return true;
        });
        if (activeSlots.length === 0) return;
        
        let activeIdx = activeSlots.findIndex(h => h.id === currentSlotPanel);
        if (activeIdx === -1) {
            activeIdx = direction > 0 ? -1 : 0;
        }
        
        let newIdx = activeIdx + direction;
        if (newIdx < 0) newIdx = activeSlots.length - 1;
        if (newIdx >= activeSlots.length) newIdx = 0;
        
        let newHm = activeSlots[newIdx];
        document.querySelectorAll('.slot-cell').forEach(c => {
            c.classList.remove('active');
            if (c.dataset.id === String(newHm.id)) c.classList.add('active');
        });
        openDetailPanel(newHm);
    }
    
    window.navigateSlotGlobal = navigateSlot;

    document.getElementById('dt-prev').onclick = () => navigateSlot(-1);
    document.getElementById('dt-next').onclick = () => navigateSlot(1);

    const freezeBtn = document.getElementById('dt-freeze-btn');
    if (freezeBtn) {
        freezeBtn.onclick = () => {
            window.__isGraphLocked = !window.__isGraphLocked;
            const statusDot = document.getElementById('dt-freeze-status');
            const statusText = document.getElementById('dt-freeze-text');
            if (window.__isGraphLocked) {
                freezeBtn.style.background = 'rgba(220, 38, 38, 0.1)';
                freezeBtn.style.color = '#DC2626';
                if (statusDot) statusDot.style.background = '#DC2626';
                if (statusText) statusText.innerText = 'FROZEN';
            } else {
                freezeBtn.style.background = 'rgba(16, 185, 129, 0.1)';
                freezeBtn.style.color = '#10b981';
                if (statusDot) statusDot.style.background = '#10b981';
                if (statusText) statusText.innerText = 'LIVE';
                // Trigger an immediate update if unfreezing
                if (currentSlotPanel) {
                    const hm = globalHeatmapData.find(h => String(h.id) === String(currentSlotPanel));
                    if (hm) openDetailPanel(hm);
                }
            }
        };
    }

    // Only add listener if it hasn't been added yet (or handle it globally but check condition)
    if (!window.slotKeyboardListenerAdded) {
        document.addEventListener('keydown', (e) => {
            let detailPanel = document.getElementById('detail-panel');
            if (detailPanel && detailPanel.classList.contains('visible')) {
                if (e.key === 'ArrowRight' && window.navigateSlotGlobal) {
                    window.navigateSlotGlobal(1);
                } else if (e.key === 'ArrowLeft' && window.navigateSlotGlobal) {
                    window.navigateSlotGlobal(-1);
                }
            }
        });
        window.slotKeyboardListenerAdded = true;
    }
    
    function openDetailPanel(hm) {
        if (window.__isGraphLocked && window.__lastOpenedSlotId === hm.id) return;
        window.__lastOpenedSlotId = hm.id;

        currentSlotPanel = hm.id;
        let s = hm.raw;
        detailPanel.classList.add('visible');
        
        document.getElementById('dt-machine-name').innerText = (CURRENT_MACHINE || '--').toUpperCase();
        document.getElementById('dt-id').innerText = hm.id;
        document.getElementById('dt-mac').innerText = s.ring_mac || '--';
        document.getElementById('dt-sn-card').innerText = s.serial_number || '--';
        const isEmptySlot = hm.cls === 'slot-empty';
        renderChargerControls('dt-charger-controls', CURRENT_MACHINE, hm.id, !isEmptySlot);
        renderAWMControls('dt-awm-controls', CURRENT_MACHINE, hm.id, !isEmptySlot);
        const fwEl = document.getElementById('dt-firmware');
        if (isEmptySlot) {
            fwEl.innerText = '--';
            fwEl.parentElement.style.display = 'none';
        } else {
            fwEl.innerText = s.firmware_version || '--';
            fwEl.parentElement.style.display = '';
        }
        
        let phs = s.bdr_state?.phase || "UNKNOWN";
        document.getElementById('dt-phase').innerText = phs;
        document.getElementById('dt-phase').className = `badge ${phs === 'DISCHARGING' ? 'ok' : (phs==='WAIT_DISCHARGE' ? 'warn' : 'blue')}`;
        
        const statusText = {
            'slot-high-bdr': 'HIGH AVG BDR',
            'slot-low-bdr': 'LOW AVG BDR',
            'slot-sensor-issue': 'SENSOR ISSUE',
            'slot-na': 'N/A'
        }[hm.cls] || hm.cls.replace('slot-','').toUpperCase();
        document.getElementById('dt-status').innerText = statusText;
        document.getElementById('dt-status').className = `badge ${hm.cls.replace('slot-','')}`;

        // Show warning reason above the graph for warning slots
        let warnReasonEl = document.getElementById('dt-warn-reason');
        if (hm.cls === 'slot-warn' && hm.warnReason) {
            warnReasonEl.innerText = '⚠ ' + hm.warnReason;
        } else {
            warnReasonEl.innerText = '';
        }
        
        // Slanting Leak Badge
        let existingSlantBadge = document.getElementById('dt-slant-badge');
        if (existingSlantBadge) existingSlantBadge.remove();
        if (hm.isSlantingLeak) {
            let slantBadge = document.createElement('span');
            slantBadge.id = 'dt-slant-badge';
            slantBadge.className = 'badge warn';
            slantBadge.style.marginRight = '8px';
            slantBadge.style.background = '#ff9800'; // Force Orange
            slantBadge.style.color = '#fff';
            slantBadge.innerText = 'Slanting Leak Detected';
            document.querySelector('.detail-header-right').prepend(slantBadge);
            
            // Force status badge to Warning/Orange if it's a Slanting Leak
            let statusBadge = document.getElementById('dt-status');
            statusBadge.innerText = 'WARNING';
            statusBadge.className = 'badge warn';
            statusBadge.style.background = '#ff9800';
            statusBadge.style.color = '#fff';
        }
        
        document.getElementById('dt-batt').innerText = s.battery_current != null ? s.battery_current + '%' : '--';
        document.getElementById('dt-phs').innerText = phs;
        
        // AVG BDR Range Highlighting
        let avgSlotBdr = hm.avgSlotBdr || 0;
        let avgBdrEl = document.getElementById('dt-avg-bdr');
        avgBdrEl.innerText = avgSlotBdr.toFixed(2);
        const sr = getSlotBdrRange(s);
        if (avgSlotBdr > 0 && (avgSlotBdr < sr.min || avgSlotBdr > sr.max)) {
            avgBdrEl.style.color = '#DC2626';
            avgBdrEl.style.fontWeight = '700';
        } else {
            avgBdrEl.style.color = '';
            avgBdrEl.style.fontWeight = '';
        }
        
        let totalRunningTimeEl = document.getElementById('dt-total-running-time');
        let batteryHistory = s.bdr_battery_history || [];
        if (totalRunningTimeEl && batteryHistory.length >= 2) {
            let startTs = new Date(batteryHistory[0][0]);
            let endTs = new Date(batteryHistory[batteryHistory.length - 1][0]);
            let hours = ((endTs - startTs) / (1000 * 60 * 60)).toFixed(2);
            totalRunningTimeEl.innerText = `${hours} Hours`;
            totalRunningTimeEl.style.color = 'rgb(248, 250, 252)';
            totalRunningTimeEl.style.fontSize = '20px';
        } else if (totalRunningTimeEl) {
            totalRunningTimeEl.innerText = '--';
        }

        let rangeInfoEl = document.getElementById('dt-range-info');
        if (rangeInfoEl) {
            const sr = getSlotBdrRange(s);
            if (hm.bdrOutOfRange) {
                rangeInfoEl.innerText = `Out of Range (Target BDR: ${sr.min}-${sr.max})`;
                rangeInfoEl.style.color = '#DC2626';
                rangeInfoEl.style.fontWeight = '600';
            } else {
                rangeInfoEl.innerText = `Target Range - BDR: ${sr.min}-${sr.max}`;
                rangeInfoEl.style.color = 'var(--muted)';
                rangeInfoEl.style.fontWeight = '400';
            }
        }

        // Calculate Total Cycles and Workouts
        let histForKpi = s.bdr_battery_history || [];
        
        let lastUpdateTime = '--';
        if (histForKpi.length > 0) {
            let lastPt = histForKpi[histForKpi.length - 1];
            lastUpdateTime = dtFormatter.format(new Date(lastPt[0]));
        }
        document.getElementById('dt-last-update').innerText = lastUpdateTime;
        
        let completed = hm.completed || [];
        let totalWorkouts = completed.length;
        
        document.getElementById('dt-workouts').innerText = totalWorkouts;
        
        let cycTb = document.getElementById('dt-cycles');

        let workoutsWithRange = completed.map((c, idx) => {
            // Finding approximate timestamps for each workout
            // We'll reuse the history mapping logic
            let startT = null;
            let endT = null;
            // Workout calculation starts from history[i-1] to history[i]
            // But 'completed' is an array of workout objects. We need to find them in hist.
            // Let's just store the start/end timestamps during the calculation if we can,
            // or perform a simple search here.
            for (let i = 1; i < histForKpi.length; i++) {
                let sP = histForKpi[i-1];
                let eP = histForKpi[i];
                if (sP[1] === c.start_pct && eP[1] === c.end_pct) {
                    startT = sP[0];
                    endT = eP[0];
                }
            }
            return { ...c, startT, endT, id: idx + 1 };
        });

        let cycHTML = "";
        let lc = hm.trueActiveDischarge;
        let activeWkRange = null;
        if (lc && lc.length > 0) {
            let startPct = lc[0][1];
            let endPct = lc[lc.length-1][1];
            let diff = startPct - endPct;
            
            if (diff >= 5 || (hm.isSlantingLeak && diff > 1)) {
                let startT = lc[0][0];
                let endT = lc[lc.length-1][0];
                activeWkRange = { startT, endT };
                let dur = Math.round((new Date(endT) - new Date(startT)) / 60000);
                let liveBDR = (diff / 2).toFixed(2);
                let stat = hm.isSlantingLeak ? 'LEAK' : (hm.topIssue ? hm.topIssue.title : (phs === 'DISCHARGING' ? 'DISC.' : 'OK'));
                
                cycHTML += `
                <tr id="row-wk-cur" class="workout-row" data-start="${startT}" data-end="${endT}" style="background:var(--bg); border-left:3px solid ${hm.isSlantingLeak ? '#ff9800' : 'var(--blue)'}">
                    <td><b>${completed.length + 1} (Cur)</b></td>
                    <td><b>${startPct}%</b></td>
                    <td><b>${endPct}%</b></td>
                    <td><b>${dur}</b></td>
                    <td><b>${liveBDR}</b></td>
                    <td><b>—</b></td>
                    <td><span style="font-size:10px" class="badge ${hm.isSlantingLeak ? 'warn' : (hm.topIssue ? (hm.topIssue.type === 'CRITICAL'?'dead':(hm.topIssue.type === 'FAIL'?'danger':'warn')) : 'blue')}">${stat}</span></td>
                </tr>`;
                // Slanting leak badge style fix is handled below
            }
        }

        cycHTML += workoutsWithRange.length ? workoutsWithRange.map((c) => `
            <tr id="row-wk-${c.id}" class="workout-row ${c.died ? 'table-row-dead' : (Math.abs(c.bdr||0) > 5 ? 'table-row-warn' : '')}" data-start="${c.startT}" data-end="${c.endT}">
                <td>${c.id}</td>
                <td>${c.start_pct}%</td>
                <td>${c.end_pct}%</td>
                <td>${c.duration_min}</td>
                <td>${c.bdr !== null ? c.bdr : '-'}</td>
                <td>${c.readings || '—'}</td>
                <td>${c.died ? 'Yes' : 'No'}</td>
            </tr>
        `).join('') : ``;
        
        if (!cycHTML) cycHTML = `<tr><td colspan="7" style="text-align:center; color: var(--muted)">No workouts</td></tr>`;
        
        cycTb.innerHTML = cycHTML;
        
        if (detailLineChart) detailLineChart.destroy();
        document.getElementById('line-chart').innerHTML = '';
        
        let categories = [];
        let battSeries = [];
        let currentSeries = [];
        let rawTimestamps = [];
        
        let hist = s.bdr_battery_history || [];
        if (hist.length > 0) {
            hist.forEach(h => {
                let d = new Date(h[0]);
                categories.push(dtFormatter.format(d));
                battSeries.push(h[1]);
                currentSeries.push(h[2] || 0);
                rawTimestamps.push(h[0]);
            });
        }
        
        detailLineChart = new ApexCharts(document.getElementById('line-chart'), {
            series: [
                { name: 'Battery %', type: 'area', data: battSeries },
                { name: 'Current (mA)', type: 'line', data: currentSeries }
            ],
            chart: {
                animations: { enabled: false },
                height: 400,
                type: 'line',
                toolbar: { 
                    show: true,
                    autoSelected: 'zoom',
                    tools: {
                        zoom: true,
                        zoomin: true,
                        zoomout: true,
                        pan: true,
                        reset: true,
                        download: false,
                        selection: true
                    }
                },
                zoom: {
                    enabled: true,
                    type: 'x',
                    autoScaleYaxis: true,
                    allowMouseWheelZoom: false
                },
                zoomedArea: {
                    fill: {
                        color: "#3b82f6",
                        opacity: 0.24
                    }
                },
                events: {
                        mouseMove: function(event, chartContext, config) {
                            const idx = config.dataPointIndex;
                            if (idx === -1) return;
                            const ts = new Date(rawTimestamps[idx]).getTime();
                            const isDark = document.documentElement.getAttribute('data-theme') === 'dark';
                            
                            document.querySelectorAll('.workout-row').forEach(row => {
                                const start = new Date(row.dataset.start).getTime();
                                const end = new Date(row.dataset.end).getTime();
                                if (ts >= start && ts <= end) {
                                    row.style.backgroundColor = isDark ? '#1a1a2e' : '#ecfeff';
                                    row.style.borderLeft = isDark ? '4px solid #60a5fa' : '4px solid #0891b2';
                                } else {
                                    row.style.backgroundColor = '';
                                    row.style.borderLeft = '';
                                }
                            });
                        },
                    mouseLeave: function() {
                        document.querySelectorAll('.workout-row').forEach(row => {
                            row.style.backgroundColor = '';
                            row.style.borderLeft = '';
                        });
                    }
                }
            },
            colors: ['#10b981', '#3b82f6'],
            stroke: { curve: 'smooth', width: [3, 2], dashArray: [0, 8] },
            fill: {
                type: 'gradient',
                gradient: {
                    shadeIntensity: 1,
                    opacityFrom: 0.4,
                    opacityTo: 0.1,
                    stops: [0, 90, 100],
                    colorStops: [
                        [
                            { offset: 0, color: '#10b981', opacity: 0.4 },
                            { offset: 100, color: '#10b981', opacity: 0 }
                        ],
                        [] // Line doesn't need gradient stops defined this way usually
                    ]
                }
            },
            grid: getApexGrid('detail'),
            xaxis: { categories: categories, labels: { show: true, maxTicksLimit: 10, rotate: -15 }, axisBorder: { show: false } },
            yaxis: [
                { title: { text: "Battery %" }, min: 0, max: 100, labels: { style: { colors: '#5a5a56' } } },
                { opposite: true, title: { text: "Current (mA)" }, labels: { style: { colors: '#3b82f6' } } }
            ],
            tooltip: {
                shared: true,
                intersect: false,
                theme: 'dark',
                custom: function({ series, seriesIndex, dataPointIndex, w }) {
                    const batt = series[0][dataPointIndex];
                    const curr = series[1][dataPointIndex];
                    const ts = categories[dataPointIndex];
                    const isDark = document.documentElement.getAttribute('data-theme') === 'dark';
                    const bg = isDark ? '#1e293b' : '#334155';
                    return `
                        <div style="padding: 12px; background: ${bg}; border-radius: 8px; font-size: 11px;">
                            <div style="font-weight: 600; margin-bottom: 8px; border-bottom: 1px solid rgba(255,255,255,0.1); padding-bottom: 4px;">${ts}</div>
                            <div style="display: flex; gap: 16px;">
                                <span>Batt: <strong style="color: #10b981">${batt}%</strong></span>
                                <span>Curr: <strong style="color: #3b82f6">${curr.toFixed(2)} mA</strong></span>
                            </div>
                        </div>
                    `;
                }
            }
        });
        detailLineChart.render();
        
        if (!window.__suppressDetailAutoScroll) {
            const yOffset = -20;
            const y = detailPanel.getBoundingClientRect().top + window.pageYOffset + yOffset;
            window.scrollTo({ top: y, behavior: 'smooth' });
        }
    }
    window.openDetailPanel = openDetailPanel;
    
    // Restore detail panel if a slot was previously selected (e.g., after auto-refresh)
    if (currentSlotPanel) {
        const hm = globalHeatmapData.find(h => String(h.id) === String(currentSlotPanel));
        if (hm) {
            window.__suppressDetailAutoScroll = true;
            openDetailPanel(hm);
            const el = document.querySelector(`.slot-cell[data-id="${currentSlotPanel}"]`);
            if (el) el.classList.add('active');
            window.__suppressDetailAutoScroll = false;
        } else {
            // Slot no longer exists or is invalid for current machine/data
            currentSlotPanel = null;
            if (detailPanel) detailPanel.classList.remove('visible');
        }
    }
  } catch (e) {
    console.error('Error initializing dashboard:', e);
  }
}

function downloadCSV(csvContent, filename) {
    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    setTimeout(() => {
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
    }, 200);
}

function applyHeatmapFilter() {
    let healthActive = window.heatmapFilterActive;
    let hasHealthFilter = healthActive && healthActive.size > 0;
    let fwActive = window.firmwareFilterActive;
    let hasFwFilter = fwActive && fwActive.size > 0;
    document.querySelectorAll('.slot-cell').forEach(el => {
        let cls = el.dataset.cls || 'slot-empty';
        let fw = el.dataset.fw || '';
        let healthMatch = !hasHealthFilter || healthActive.has(cls);
        let fwMatch = !hasFwFilter || fwActive.has(fw);
        if (healthMatch && fwMatch) {
            el.classList.remove('slot-dimmed');
        } else {
            el.classList.add('slot-dimmed');
        }
    });
    updateBdrBulkChargerControls();
}

function setHeatmapClassColor(cls, color) {
    if (!cls || !color) return;
    const rootStyle = document.documentElement.style;
    rootStyle.setProperty(`--${cls}-color`, color);
    rootStyle.setProperty(`--${cls}-bg`, `color-mix(in srgb, ${color} 18%, transparent)`);
}

const DEFAULT_HEATMAP_COLORS = {
    'slot-pass': '#12f202',
    'slot-ok': '#02f2ba',
    'slot-low-bdr': '#0EA5E9',
    'slot-high-bdr': '#EC4899',
    'slot-sensor-issue': '#14B8A6',
    'slot-warn': '#F59E0B',
    'slot-danger': '#DC2626',
    'slot-dead': '#4F46E5',
    'slot-empty': '#9CA3AF',
    'slot-na': '#A0765F'
};

function resetHeatmapColors() {
    document.querySelectorAll('.color-picker').forEach(picker => {
        const cls = picker.dataset.target;
        const defaultColor = DEFAULT_HEATMAP_COLORS[cls];
        if (defaultColor) {
            picker.value = defaultColor;
            picker.dispatchEvent(new Event('input', { bubbles: true }));
        }
    });
}

function applyCustomColors() {
    document.querySelectorAll('.color-picker').forEach(picker => {
        let color = picker.value;
        let cls = picker.dataset.target;
        let btn = picker.closest('.heatmap-filter');
        btn.querySelector('.fdot').style.background = color;
        setHeatmapClassColor(cls, color);

        let legendDots = document.querySelectorAll('.heatmap-legend .legend-dot');
        let idx = ['slot-pass','slot-ok','slot-low-bdr','slot-high-bdr','slot-sensor-issue','slot-warn','slot-danger','slot-dead','slot-empty','slot-na'].indexOf(cls);
        if (idx >= 0 && legendDots[idx]) legendDots[idx].style.background = color;
    });
}

function formatDuration(totalMinutes) {
    if (totalMinutes == null || isNaN(totalMinutes)) return '--';
    if (totalMinutes < 60) {
        return Math.round(totalMinutes) + ' min';
    } else if (totalMinutes < 1440) {
        return (totalMinutes / 60).toFixed(1) + ' hr';
    } else {
        return (totalMinutes / 1440).toFixed(1) + ' days';
    }
}

function exportSlotHistory() {
    if (!currentSlotPanel) return;

    let hm = globalHeatmapData.find(h => String(h.id) === String(currentSlotPanel));
    if (!hm) return;
    let completed = hm.completed || [];

    let csv = "Workout,Start %,End %,Duration,BDR,Readings,Died?\n";

    completed.forEach(c => {
        csv += `"${c.workout_num}","${c.start_pct}%","${c.end_pct}%","${formatDuration(c.duration_min)}","${c.bdr}","${c.readings || 0}","${c.died ? 'Yes' : 'No'}"\n`;
    });

    let lc = hm.trueActiveDischarge;
    if (lc && lc.length >= 2) {
        let startPct = lc[0][1];
        let endPct = lc[lc.length - 1][1];
        let diff = startPct - endPct;
        if (diff >= 5 || (hm.isSlantingLeak && diff > 1)) {
            let startT = new Date(lc[0][0]);
            let endT = new Date(lc[lc.length - 1][0]);
            let dur = Math.round((endT - startT) / 60000);
            let liveBdr = (diff / 2).toFixed(2);
            csv += `"${completed.length + 1}","${startPct}%","${endPct}%","${formatDuration(dur)}","${liveBdr}","—","${endPct === 0 && startPct > 0 ? 'Yes' : 'No'}"\n`;
        }
    }

    if (csv === "Workout,Start %,End %,Duration,BDR,Readings,Died?\n") {
        alert("No workouts to export.");
        return;
    }

    downloadCSV(csv, `Slot_${currentSlotPanel}_Workout_History.csv`);
}

function isSlotDeadOrDied(s) {
  if (s.dead_state && String(s.dead_state).trim() !== '') return true;
  if (s.battery_current !== null && s.battery_current < 3) return true;
  const _history = s.bdr_battery_history || [];
  const THREE_HOURS = 180 * 60 * 1000;
  if (_history.length >= 2) {
    const _lastBatt = _history[_history.length - 1][1];
    let _flatStartIdx = _history.length - 1;
    for (let _j = _history.length - 2; _j >= 0; _j--) {
      if (Math.abs(_history[_j][1] - _lastBatt) <= 1) { _flatStartIdx = _j; }
      else break;
    }
    if (_flatStartIdx < _history.length - 1) {
      const _t1 = new Date(_history[_history.length - 1][0]).getTime();
      const _t2 = new Date(_history[_flatStartIdx][0]).getTime();
      if (_t1 - _t2 > THREE_HOURS) return true;
    }
  }
  if (_history.length >= 1) {
    const _lastTs = new Date(_history[_history.length - 1][0]).getTime();
    if (Date.now() - _lastTs > THREE_HOURS) return true;
  }
  return false;
}

function classifyExportSlot(s) {
    let sn = s.serial_number || "--";
    let mac = s.ring_mac || "--";
    let fw = s.firmware_version || "--";
    let history = s.bdr_battery_history || [];
    let isSensorIssue = isFlatBatteryGraph(history);
    var slotRange = getSlotBdrRange(s);
    var isPro = slotRange.product === 'PRO';

    let completed = calculateCompletedCycleWorkouts(s);

    let diedHere = false;
    const THREE_HOURS = 180 * 60 * 1000;
    if (s.battery_current !== null && s.battery_current < 3) {
        diedHere = true;
    }
    if (!diedHere && history.length >= 2) {
        var lastBatt = history[history.length - 1][1];
        var flatStartIdx = history.length - 1;
        for (var j = history.length - 2; j >= 0; j--) {
            if (Math.abs(history[j][1] - lastBatt) <= 1) {
                flatStartIdx = j;
            } else {
                break;
            }
        }
        if (flatStartIdx < history.length - 1) {
            var t1 = new Date(history[history.length - 1][0]).getTime();
            var t2 = new Date(history[flatStartIdx][0]).getTime();
            if (t1 - t2 > THREE_HOURS) {
                diedHere = true;
            }
        }
    }
    if (!diedHere && history.length >= 1) {
        var lastTs = new Date(history[history.length - 1][0]).getTime();
        if (Date.now() - lastTs > THREE_HOURS) {
            diedHere = true;
        }
    }

    var highestBdrPos = 0;
    var highestBdrNeg = 0;
    completed.forEach(c => {
        if (c.bdr > highestBdrPos) highestBdrPos = c.bdr;
        if (c.bdr < highestBdrNeg) highestBdrNeg = c.bdr;
    });

    var avgSlotBdr = getSlotAvgBdr(s, completed);

    var fails = s.bdr_state?.consecutive_failures || 0;

    var peakIdx = history.length - 1;
    if (history.length > 0) {
        var maxVal = history[history.length - 1][1];
        for (var i = history.length - 2; i >= 0; i--) {
            if (history[i][1] >= maxVal) {
                maxVal = history[i][1];
                peakIdx = i;
            } else {
                break;
            }
        }
    }
    var trueActiveDischarge = history.slice(peakIdx);

    var isSlantingLeak = false;
    if (!isPro && trueActiveDischarge.length >= 2) {
        var startT = new Date(trueActiveDischarge[0][0]);
        var endT = new Date(trueActiveDischarge[trueActiveDischarge.length - 1][0]);
        var currentDurMins = Math.round((endT - startT) / 60000);
        var currentDrop = trueActiveDischarge[0][1] - trueActiveDischarge[trueActiveDischarge.length - 1][1];
        if (currentDurMins > 180 && currentDrop > 1) {
            if (currentDrop < 5 || (currentDrop / (currentDurMins / 60) < 2)) {
                isSlantingLeak = true;
            }
        }
    }

    var latestCycle = history;
    if (history.length > 0) {
        var lastHikeStart = 0;
        for (var i = history.length - 1; i > 0; i--) {
            if (history[i][1] > history[i - 1][1]) {
                var start = i - 1;
                while (start > 0 && history[start][1] >= history[start - 1][1]) start--;
                lastHikeStart = start;
                break;
            }
        }
        latestCycle = history.slice(lastHikeStart);
    }

    var issues = [];
    var topIssue = null;
    var hmClass = 'slot-ok';

    var isEmpty = sn === "--" || sn === "N/A" || !s.serial_number;
    if (isEmpty) {
        hmClass = 'slot-empty';
    } else {
        var hasGraphData = history.length > 0;
        if (!hasGraphData) {
            hmClass = 'slot-na';
        } else if (isSensorIssue) {
            hmClass = 'slot-sensor-issue';
            topIssue = { type: 'WARNING', priority: 16, title: 'Sensor Issue', message: 'Battery graph is flat from start to end' };
        } else {
            var BDR_MIN = slotRange.min, BDR_MAX = slotRange.max;
            // PASS: >= 6 workouts AND avg BDR in category range
            var isPass = !diedHere && !isSlantingLeak && completed.length >= 6 && avgSlotBdr >= BDR_MIN && avgSlotBdr <= BDR_MAX;
            if (isPass) {
                hmClass = 'slot-pass';
            } else {
            var lowAvgBdr = avgSlotBdr > 0 && avgSlotBdr < BDR_MIN;
            if (lowAvgBdr) hmClass = 'slot-low-bdr';
            else if (fails >= 3) hmClass = 'slot-warn';
            if (diedHere) hmClass = 'slot-dead';

            var bdrOutOfRange = avgSlotBdr > 0 && (avgSlotBdr < BDR_MIN || avgSlotBdr > BDR_MAX);
            var highAvgBdr = avgSlotBdr > BDR_MAX;

            if (bdrOutOfRange || highAvgBdr) {
                issues.push({
                    type: highAvgBdr ? 'WARNING' : 'WARNING',
                    priority: highAvgBdr ? 5.8 : 5.6,
                    title: highAvgBdr ? 'High Avg BDR' : 'BDR Out of Range',
                    message: (highAvgBdr ? 'Avg BDR above ' + BDR_MAX : 'Avg BDR outside ' + BDR_MIN + '-' + BDR_MAX)
                });
            }

            if (bdrOutOfRange) {
                if (hmClass === 'slot-ok') hmClass = 'slot-warn';
            }

            if (isSlantingLeak) {
                issues.push({ type: 'WARNING', priority: 15, title: 'Gradual Drop (Slanting Leak)', message: 'Active > 3h continuous drop' });
                if (hmClass === 'slot-ok') hmClass = 'slot-warn';
            }

            if (highAvgBdr) {
                hmClass = 'slot-high-bdr';
            }

            if (issues.length > 0) {
                issues.sort(function (a, b) { return b.priority - a.priority; });
                topIssue = issues[0];
                if (topIssue.type === 'CRITICAL') hmClass = 'slot-dead';
                else if (topIssue.type === 'WARNING' && hmClass === 'slot-ok') hmClass = 'slot-warn';
            }
            }
        }
    }

    var workoutCount = completed.length;

    var statusMap = {
        'slot-pass': 'Pass',
        'slot-ok': 'Normal',
        'slot-low-bdr': 'Low Avg BDR',
        'slot-high-bdr': 'High Avg BDR',
        'slot-sensor-issue': 'Sensor Issue',
        'slot-warn': 'Warning',
        'slot-danger': 'Failure',
        'slot-dead': 'Died',
        'slot-na': 'N/A',
        'slot-empty': 'Empty'
    };
    var status = statusMap[hmClass] || hmClass;

    return {
        cls: hmClass,
        fw: fw,
        sn: sn,
        mac: mac,
        completed: completed,
        avgSlotBdr: avgSlotBdr,
        workoutCount: workoutCount,
        status: status,
        topIssue: topIssue,
        isSlantingLeak: isSlantingLeak,
        isSensorIssue: isSensorIssue,
        latestCycle: latestCycle
    };
}

function exportFleetSummary() {
    if (!ALL_MACHINE_DATA || Object.keys(ALL_MACHINE_DATA).length === 0) return;
    
    var healthActive = window.heatmapFilterActive;
    var hasHealthFilter = healthActive && healthActive.size > 0;
    var fwActive = window.firmwareFilterActive;
    var hasFwFilter = fwActive && fwActive.size > 0;

    var csv = "Date,Machine,Slot,Serial Number,MAC Address,Firmware Version,Total Workouts,Avg BDR,Status\n";

    var machines = Object.keys(ALL_MACHINE_DATA).sort();
    machines.forEach(function (machine) {
        var md = ALL_MACHINE_DATA[machine];
        if (!md || !md.slots) return;
        var slotKeys = Object.keys(md.slots).sort(function (a, b) { return parseInt(a) - parseInt(b); });
        slotKeys.forEach(function (slotId) {
            var s = md.slots[slotId];
            if (!s) return;
            var r = classifyExportSlot(s);

            // Ring state override for report
            if (ringsData && ringsData.length > 0) {
                var ringEntry = ringsData.find(function(rd) {
                    return rd.file === machine && rd.slot === slotId;
                });
                if (ringEntry) {
                    var rs = (ringEntry.state || '').toUpperCase();
                    if (rs === 'PASSED' || rs === 'PASS') {
                        r.cls = 'slot-pass';
                        r.status = 'Pass';
                    } else if (rs === 'FAILED' || rs === 'FAIL') {
                        r.cls = 'slot-danger';
                        r.status = 'Failure';
                    }
                }
            }

            if (hasHealthFilter && !healthActive.has(r.cls)) return;
            if (hasFwFilter && !fwActive.has(r.fw)) return;

            var avgBdrStr = r.avgSlotBdr ? r.avgSlotBdr.toFixed(2) : "0.00";

            var history = s.bdr_battery_history || [];
            var startDate = history.length > 0 ? new Date(history[0][0]) : null;
            var dateStr = startDate ? startDate.toISOString().replace('T', ' ').replace(/\..+/, '') : '--';

            var row = [ dateStr, machine, slotId, r.sn, r.mac, r.fw, r.workoutCount, avgBdrStr, r.status ];
            var rowData = row.map(function (v) { return '"' + String(v).replace(/"/g, '""') + '"'; });
            csv += rowData.join(",") + "\n";
        });
    });

    if (csv.split("\n").length <= 1) {
        alert("No data to export.");
        return;
    }

    downloadCSV(csv, "Master_Fleet_Summary.csv");
}

function countQualifiedSlots() {
    if (!ALL_MACHINE_DATA) return 0;
    let count = 0;
    Object.values(ALL_MACHINE_DATA).forEach(md => {
        if (!md || !md.slots) return;
        Object.values(md.slots).forEach(s => {
            let sn = s.serial_number || '';
            if (!sn || sn === '--' || sn === 'N/A') return;
            let completed = calculateCompletedCycleWorkouts(s);
            if (completed.length < 6) return;
            let avgBdr = getSlotAvgBdr(s, completed);
            if (avgBdr < 5 || avgBdr > 12) return;
            count++;
        });
    });
    return count;
}

function updateQualifiedCount() {
    const el = document.getElementById('qualified-count');
    if (!el) return;
    const count = countQualifiedSlots();
    el.textContent = count;
    el.style.display = count > 0 ? 'inline-flex' : 'none';
}

function exportQualifiedSlots() {
    if (!ALL_MACHINE_DATA || Object.keys(ALL_MACHINE_DATA).length === 0) return;
    let csv = "Machine,Slot,Serial Number,Total Workouts,Avg BDR\n";
    Object.entries(ALL_MACHINE_DATA).forEach(([machine, md]) => {
        if (!md || !md.slots) return;
        Object.entries(md.slots).forEach(([slotId, s]) => {
            let sn = s.serial_number || '';
            if (!sn || sn === '--' || sn === 'N/A') return;
            let completed = calculateCompletedCycleWorkouts(s);
            let workoutCount = completed.length;
            if (workoutCount < 6) return;
            let avgBdr = getSlotAvgBdr(s, completed);
            if (avgBdr < 5 || avgBdr > 12) return;
            let row = [machine, slotId, sn, workoutCount, avgBdr.toFixed(2)].map(v => `"${String(v).replace(/"/g, '""')}"`);
            csv += row.join(",") + "\n";
        });
    });
    if (csv.split("\n").length <= 1) {
        alert("No qualified slots found.");
        return;
    }
    downloadCSV(csv, "Qualified_Slots.csv");
}

// ── Floorplan ──
// All 42 fixed AQC machine positions matching the reference floorplan
const FP_ALL_MACHINES = [
  // Zone A — row 1
  { zone:'A', name:'AQC-47', x:10,  y:278, w:52, h:52 },
  { zone:'A', name:'AQC-45', x:66,  y:278, w:52, h:52 },
  { zone:'A', name:'AQC-43', x:122, y:278, w:52, h:52 },
  { zone:'A', name:'AQC-41', x:178, y:278, w:52, h:52 },
  { zone:'A', name:'AQC-38', x:234, y:278, w:52, h:52 },
  { zone:'A', name:'AQC-36', x:290, y:278, w:52, h:52 },
  { zone:'A', name:'AQC-34', x:346, y:278, w:52, h:52 },
  { zone:'A', name:'AQC-30', x:402, y:278, w:52, h:52 },
  { zone:'A', name:'AQC-28', x:458, y:278, w:52, h:52 },
  { zone:'A', name:'AQC-26', x:514, y:278, w:52, h:52 },
  { zone:'A', name:'AQC-24', x:570, y:278, w:52, h:52 },
  // Zone A — row 2
  { zone:'A', name:'AQC-46', x:10,  y:334, w:52, h:52 },
  { zone:'A', name:'AQC-44', x:66,  y:334, w:52, h:52 },
  { zone:'A', name:'AQC-42', x:122, y:334, w:52, h:52 },
  { zone:'A', name:'AQC-40', x:178, y:334, w:52, h:52 },
  { zone:'A', name:'AQC-37', x:234, y:334, w:52, h:52 },
  { zone:'A', name:'AQC-35', x:290, y:334, w:52, h:52 },
  { zone:'A', name:'AQC-31', x:346, y:334, w:52, h:52 },
  { zone:'A', name:'AQC-29', x:402, y:334, w:52, h:52 },
  { zone:'A', name:'AQC-27', x:458, y:334, w:52, h:52 },
  { zone:'A', name:'AQC-25', x:514, y:334, w:52, h:52 },
  { zone:'A', name:'AQC-23', x:570, y:334, w:52, h:52 },
  // Zone B
  { zone:'B', name:'AQC-22', x:290, y:158, w:52, h:52 },
  { zone:'B', name:'AQC-21', x:346, y:158, w:52, h:52 },
  { zone:'B', name:'AQC-20', x:402, y:158, w:52, h:52 },
  { zone:'B', name:'AQC-19', x:458, y:158, w:52, h:52 },
  { zone:'B', name:'AQC-18', x:514, y:158, w:52, h:52 },
  { zone:'B', name:'AQC-17', x:570, y:158, w:52, h:52 },
  { zone:'B', name:'AQC-16', x:626, y:158, w:52, h:52 },
  { zone:'B', name:'AQC-15', x:682, y:158, w:52, h:52 },
  // Zone C — row 1
  { zone:'C', name:'AQC-14', x:674, y:298, w:52, h:52 },
  { zone:'C', name:'AQC-12', x:730, y:298, w:52, h:52 },
  { zone:'C', name:'AQC-10', x:786, y:298, w:52, h:52 },
  // Zone C — row 2
  { zone:'C', name:'AQC-13', x:674, y:354, w:52, h:52 },
  { zone:'C', name:'AQC-11', x:730, y:354, w:52, h:52 },
  { zone:'C', name:'AQC-09', x:786, y:354, w:52, h:52 },
  // Zone D — row 1
  { zone:'D', name:'AQC-08', x:686, y:30,  w:52, h:52 },
  { zone:'D', name:'AQC-06', x:742, y:30,  w:52, h:52 },
  { zone:'D', name:'AQC-04', x:798, y:30,  w:52, h:52 },
  // Zone D — row 2
  { zone:'D', name:'AQC-07', x:686, y:86,  w:52, h:52 },
  { zone:'D', name:'AQC-05', x:742, y:86,  w:52, h:52 },
  { zone:'D', name:'AQC-03', x:798, y:86,  w:52, h:52 },
];

const FP_ZONE_STYLES = {
  A: { labelColor:'#185FA5', rectFill:'#E6F1FB', rectStroke:'#378ADD', label:'Zone A', labelX:10, labelY:268 },
  B: { labelColor:'#0F6E56', rectFill:'#E1F5EE', rectStroke:'#1D9E75', label:'Zone B', labelX:290, labelY:148 },
  C: { labelColor:'#993C1D', rectFill:'#FAECE7', rectStroke:'#D85A30', label:'Zone C', labelX:674, labelY:288 },
  D: { labelColor:'#534AB7', rectFill:'#EEEDFE', rectStroke:'#7F77DD', label:'Zone D', labelX:686, labelY:20 },
};

const FP_CUSTOM_NAMES_KEY = 'bdr_fp_names';
const FP_BLANK = '__NONE__';

function normalizeSlotData(slot) {
    if (!slot || typeof slot !== 'object') return;
    if (slot.bdr_data && !slot.bdr_state) {
        const bd = slot.bdr_data;
        const cycles = Array.isArray(bd.cycles) ? bd.cycles.map(c => ({
            cycle: c.cycle,
            start_pct: c.start_pct,
            end_pct: c.end_pct,
            duration_min: c.duration_min,
            bdr: c.bdr != null ? c.bdr : 0,
            readings: c.readings || 0,
            warning: c.warning || false
        })) : [];
        slot.bdr_state = {
            phase: bd.phase_at_finalize || 'UNKNOWN',
            completed_cycles: cycles,
            consecutive_failures: slot.discharge_connect_failures || 0,
            death_count: bd.death_count || 0
        };
    }
    if (!slot.bdr_state) {
        slot.bdr_state = {
            phase: 'UNKNOWN',
            completed_cycles: [],
            consecutive_failures: 0
        };
    }
}

function normalizeMachineData(raw) {
    if (!raw || typeof raw !== 'object') return null;
    if (raw.slots) {
        Object.values(raw.slots).forEach(s => normalizeSlotData(s));
        return raw;
    }

    const slotKeys = Object.keys(raw).filter(k =>
        k !== 'saved_at' &&
        raw[k] && typeof raw[k] === 'object' &&
        ('serial_number' in raw[k] || 'ring_name' in raw[k] || 'bdr_state' in raw[k] || 'bdr_data' in raw[k])
    );

    if (slotKeys.length > 0) {
        const result = { slots: {} };
        slotKeys.forEach(k => {
            normalizeSlotData(raw[k]);
            result.slots[k] = raw[k];
        });
        if (raw.saved_at) result.saved_at = raw.saved_at;
        return result;
    }

    return null;
}

function hasValidSlots(md) {
    if (!md || !md.slots) return false;
    return Object.values(md.slots).some(s => {
        const sn = (s && s.serial_number || '').toString().trim();
        return sn && sn !== '--' && sn !== 'N/A';
    });
}

function fpUseRings() {
  return ringsData && ringsData.length > 0;
}

function fpGetLoadedKeys() {
  if (fpUseRings()) {
    return [...new Set(ringsData.map(d => d.file))].sort((a, b) => a.localeCompare(b, undefined, { numeric: true }));
  }
  return Object.keys(ALL_MACHINE_DATA || {});
}

function getMachineSlotCount(machineKey) {
  const norm = normalizeAqcMachineName(machineKey);
  const removed = removedSlotsByMachine[norm] || new Set();
  if (fpUseRings()) {
    return ringsData.filter(d => d.file === machineKey && d.serial_number && d.serial_number !== '--' && d.serial_number !== 'N/A' && !removed.has(String(d.slot))).length;
  }
  const md = ALL_MACHINE_DATA[machineKey];
  if (!md || !md.slots) return 0;
  let count = 0;
  Object.entries(md.slots).forEach(([slotKey, s]) => {
    if (removed.has(String(slotKey))) return;
    const sn = (s.serial_number || '').toString().trim();
    if (sn && sn !== '--' && sn !== 'N/A') count++;
  });
  return count;
}

function fpGetActiveMachine() {
  if (fpUseRings()) return ringsSelectedMachine;
  return CURRENT_MACHINE;
}

function fpJumpToMachine(name) {
  if (fpUseRings()) {
    var target = name;
    if (!ALL_MACHINE_DATA[target]) {
      var pos = FP_ALL_MACHINES.find(function(m) { return m.name.toLowerCase() === name.toLowerCase(); });
      if (pos) target = pos.name;
    }
    if (ALL_MACHINE_DATA[target]) {
      switchView('bdr');
      switchMachine(target);
      toggleFloorplan();
      return;
    }
    switchView('bdr');
    toggleFloorplan();
  } else {
    switchMachine(name);
    toggleFloorplan();
  }
}

function slotCountToColor(count) {
  const ratio = Math.min(count / 64, 1);
  let r, g, b;
  if (ratio < 0.5) {
    const t = ratio / 0.5;
    r = 180 - 60 * t;
    g = 30 + 100 * t;
    b = 30 - 15 * t;
  } else {
    const t = (ratio - 0.5) / 0.5;
    r = 120 - 70 * t;
    g = 130 + 50 * t;
    b = 15 - 10 * t;
  }
  return `rgb(${Math.round(r)},${Math.round(g)},${Math.round(b)})`;
}

function slotCountToFill(count) {
  const ratio = Math.min(count / 64, 1);
  let r, g, b;
  if (ratio < 0.5) {
    const t = ratio / 0.5;
    r = 200 - 50 * t;
    g = 60 + 100 * t;
    b = 60 - 40 * t;
  } else {
    const t = (ratio - 0.5) / 0.5;
    r = 150 - 90 * t;
    g = 160 + 35 * t;
    b = 20 - 15 * t;
  }
  return `rgb(${Math.round(r)},${Math.round(g)},${Math.round(b)})`;
}

let fpCustomNames = {};
let fpCtxMenu = null;
const FP_LAYOUT_VERSION = '2';

function fpLoadNames() {
  try {
    const saved = localStorage.getItem(FP_CUSTOM_NAMES_KEY);
    if (saved) fpCustomNames = JSON.parse(saved);
    // Clear old custom names after floorplan restructure
    if (localStorage.getItem('bdr_fp_layout_ver') !== FP_LAYOUT_VERSION) {
      fpCustomNames = {};
      localStorage.setItem('bdr_fp_layout_ver', FP_LAYOUT_VERSION);
      fpSaveNames();
    }
  } catch(e) { fpCustomNames = {}; }
}
function fpSaveNames() {
  localStorage.setItem(FP_CUSTOM_NAMES_KEY, JSON.stringify(fpCustomNames));
}

function fpCloseCtxMenu() {
  if (fpCtxMenu) { fpCtxMenu.remove(); fpCtxMenu = null; }
}

function fpShowCtxMenu(e, aqcName) {
  e.preventDefault();
  fpCloseCtxMenu();
  const menu = document.createElement('div');
  menu.className = 'fp-ctx-menu';
  menu.oncontextmenu = e => e.preventDefault();

  // position within viewport
  const pad = 10;
  let left = e.clientX;
  let top = e.clientY;
  // attach invisibly to measure, then adjust and reveal
  menu.style.visibility = 'hidden';
  menu.style.position = 'fixed';
  document.body.appendChild(menu);

  const mw = menu.offsetWidth;
  const mh = menu.offsetHeight;
  if (left + mw + pad > window.innerWidth) left = window.innerWidth - mw - pad;
  if (left < pad) left = pad;
  if (top + mh + pad > window.innerHeight) top = window.innerHeight - mh - pad;
  if (top < pad) top = pad;
  menu.style.left = left + 'px';
  menu.style.top = top + 'px';

  // Build lookup (same as renderFloorplan)
  const aqcToKey = {};
  const loadedKeys = fpGetLoadedKeys();
  loadedKeys.forEach(k => {
    const kl = k.toLowerCase().trim();
    const found = FP_ALL_MACHINES.find(m => m.name.toLowerCase() === kl);
    if (found) { aqcToKey[found.name] = k; return; }
    const m = k.match(/(\d+)$/);
    if (m) {
      const padded = m[1].padStart(2, '0');
      const aqcNameC = 'AQC-' + padded;
      if (FP_ALL_MACHINES.some(x => x.name === aqcNameC)) aqcToKey[aqcNameC] = k;
    }
  });
  const autoKey = aqcToKey[aqcName] || null;
  const isSlotBlank = fpCustomNames[aqcName] === FP_BLANK;
  const currentAssigned = isSlotBlank ? '' : (fpCustomNames[aqcName] || autoKey || '');

  // "Assign machine" header
  const header = document.createElement('div');
  header.style.cssText = 'padding:6px 14px;font-size:10px;font-weight:600;text-transform:uppercase;letter-spacing:0.05em;color:var(--muted);';
  header.textContent = 'ASSIGN TO ' + aqcName.toUpperCase();
  menu.appendChild(header);

  // always-visible blank toggle
  const blankBtn = document.createElement('button');
  blankBtn.className = 'fp-ctx-item';
  if (isSlotBlank) {
    blankBtn.innerHTML = `<span style="display:flex;align-items:center;gap:6px;flex:1;"><svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/><circle cx="12" cy="12" r="3"/></svg>Show name</span>`;
    blankBtn.onclick = () => {
      fpCloseCtxMenu();
      delete fpCustomNames[aqcName];
      fpSaveNames();
      renderFloorplan();
    };
  } else {
    blankBtn.innerHTML = `<span style="display:flex;align-items:center;gap:6px;flex:1;"><svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>Hide name</span>`;
    blankBtn.onclick = () => {
      fpCloseCtxMenu();
      fpCustomNames[aqcName] = FP_BLANK;
      fpSaveNames();
      renderFloorplan();
    };
  }
  menu.appendChild(blankBtn);
  menu.appendChild(document.createElement('hr'));

  if (loadedKeys.length === 0) {
    const empty = document.createElement('div');
    empty.style.cssText = 'padding:6px 14px;font-size:11px;color:var(--muted);font-style:italic;';
    empty.textContent = 'No machines loaded';
    menu.appendChild(empty);
  } else {
    loadedKeys.forEach(k => {
      const item = document.createElement('button');
      item.className = 'fp-ctx-item';
      const isActive = k === currentAssigned;
      item.innerHTML = `<span style="display:flex;align-items:center;gap:6px;flex:1;">${isActive ? '<span style="color:#34D399;font-size:14px;">&#10003;</span>' : '<span style="width:14px;"></span>'}${k.toUpperCase()}</span>`;
      if (isActive) item.style.background = 'rgba(52,211,153,0.08)';
      item.onclick = () => {
        fpCloseCtxMenu();
        if (!isActive) {
          fpCustomNames[aqcName] = k;
          fpSaveNames();
          renderFloorplan();
        }
      };
      menu.appendChild(item);
    });
  }

  if (currentAssigned) {
    const divider = document.createElement('div');
    divider.className = 'fp-ctx-divider';
    menu.appendChild(divider);

    const resetItem = document.createElement('button');
    resetItem.className = 'fp-ctx-item';
    resetItem.innerHTML = `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="1 4 1 10 7 10"/><path d="M3.51 15a9 9 0 1 0 2.13-9.36L1 10"/></svg> Unassign`;
    resetItem.onclick = () => {
      fpCloseCtxMenu();
      delete fpCustomNames[aqcName];
      fpSaveNames();
      renderFloorplan();
    };
    menu.appendChild(resetItem);
  }

  fpCtxMenu = menu;
  menu.style.visibility = 'visible';

  setTimeout(() => {
    document.addEventListener('click', fpCloseCtxMenu, { once: true });
  }, 10);
}

function fpMachineKey(name) {
  return name.replace(/[^a-zA-Z0-9]/g, '_');
}

function renderFloorplan() {
    const container = document.getElementById('floorplan-content');
    if (!container) return;

    // Build lookup: AQC name -> actual loaded key, and actual key -> AQC name
    const aqcToKey = {};
    const keyToAqc = {};
    const loadedKeys = fpGetLoadedKeys();
    loadedKeys.forEach(k => {
      const kl = k.toLowerCase().trim();
      const found = FP_ALL_MACHINES.find(m => m.name.toLowerCase() === kl);
      if (found) {
        aqcToKey[found.name] = k;
        keyToAqc[k] = found.name;
        return;
      }
      const m = k.match(/(\d+)$/);
      if (m) {
        const padded = m[1].padStart(2, '0');
        const aqcName = 'AQC-' + padded;
        if (FP_ALL_MACHINES.some(x => x.name === aqcName)) {
          aqcToKey[aqcName] = k;
          keyToAqc[k] = aqcName;
          return;
        }
      }
    });

    fpLoadNames();
    let availableCount = 0;
    let isDark = document.documentElement.getAttribute('data-theme') === 'dark';

    let zoneLabelsRendered = new Set();
    let rects = '';
    let texts = '';
    let zoneMachineCounts = { A:0, B:0, C:0, D:0 };
    let unmatched = [];
    let assignedSet = new Set(); // track assigned keys so they don't appear as unmapped

    FP_ALL_MACHINES.forEach(m => {
      const aqcName = m.name;
      // check auto-match first, then custom assignment
      const autoKey = aqcToKey[aqcName];
      const customKeyRaw = fpCustomNames[aqcName];
      const isSlotBlank = customKeyRaw === FP_BLANK;
      const customKey = isSlotBlank ? null : (customKeyRaw || null);
      const actualKey = isSlotBlank ? null : (customKey || autoKey);
      const hasData = !!actualKey;
      const isActive = hasData && actualKey === fpGetActiveMachine();
      if (hasData) {
        availableCount++;
        zoneMachineCounts[m.zone]++;
        if (customKey) assignedSet.add(customKey);
      }
      // display: if blank show nothing, else custom key or AQC name
      const displayName = isSlotBlank ? '' : (customKey || aqcName).toUpperCase();

      const zs = FP_ZONE_STYLES[m.zone];
      const txtCx = m.x + m.w/2;
      const txtCy = m.y + m.h/2 + 4;

      if (!zoneLabelsRendered.has(m.zone)) {
        zoneLabelsRendered.add(m.zone);
        texts += `<text x="${zs.labelX}" y="${zs.labelY}" font-size="11" font-weight="500" fill="${zs.labelColor}" font-family="sans-serif">${zs.label}</text>`;
      }

      const rectId = 'fp-' + fpMachineKey(aqcName);
      if (hasData) {
        const slotCount = getMachineSlotCount(actualKey);
        const isZero = slotCount === 0;
        const fill = isZero ? (isDark ? 'rgba(255,255,255,0.04)' : '#f0f0f0') : slotCountToFill(slotCount);
        const stroke = isZero ? (isDark ? 'rgba(255,255,255,0.08)' : '#d0d0d0') : slotCountToColor(slotCount);
        const txtClr = isZero ? (isDark ? 'rgba(255,255,255,0.15)' : '#bbb') : '#fff';
        const boxCls = 'fp-machine-box' + (isActive ? ' active' : '') + (isZero ? ' empty' : '');
        rects += `<rect class="${boxCls}" id="${rectId}" x="${m.x}" y="${m.y}" width="${m.w}" height="${m.h}" rx="6" fill="${fill}" stroke="${stroke}" stroke-width="${isActive ? 3 : (isZero ? 1.5 : 2)}" data-machine="${actualKey}" data-aqc="${aqcName}" data-available="1"/>`;
        texts += `<text class="fp-machine-text" data-aqc="${aqcName}" x="${txtCx}" y="${txtCy - 2}" text-anchor="middle" dominant-baseline="middle" font-size="10" font-weight="700" fill="${txtClr}" font-family="sans-serif">${displayName}</text>`;

        // Pill-style qty badge
        const qH = 13;
        const qW = Math.max(18, String(slotCount).length * 7 + 10);
        const qX = m.x + (m.w - qW) / 2;
        const qY = m.y + m.h - qH - 3;
        const bdgClr = isZero ? (isDark ? 'rgba(255,255,255,0.08)' : 'rgba(0,0,0,0.1)') : stroke;
        const bdgTxt = isZero ? (isDark ? 'rgba(255,255,255,0.2)' : '#aaa') : '#fff';
        texts += `<rect x="${qX}" y="${qY + 0.5}" width="${qW}" height="${qH}" rx="${qH/2}" fill="rgba(0,0,0,0.12)"/>`;
        texts += `<rect x="${qX}" y="${qY}" width="${qW}" height="${qH}" rx="${qH/2}" fill="${bdgClr}"/>`;
        texts += `<text x="${txtCx}" y="${qY + qH/2 + 0.5}" text-anchor="middle" dominant-baseline="middle" font-size="7.5" font-weight="800" fill="${bdgTxt}" font-family="sans-serif">${slotCount}</text>`;
      } else if (isSlotBlank) {
        const fill = isDark ? 'rgba(255,255,255,0.03)' : '#f8f8f8';
        const stroke = isDark ? 'rgba(255,255,255,0.06)' : '#e0e0e0';
        rects += `<rect class="fp-machine-box" id="${rectId}" x="${m.x}" y="${m.y}" width="${m.w}" height="${m.h}" rx="6" fill="${fill}" stroke="${stroke}" stroke-dasharray="3,3" stroke-width="1" data-aqc="${aqcName}" data-available="0"/>`;
      } else {
        const fill = isDark ? 'rgba(255,255,255,0.03)' : '#f8f8f8';
        const stroke = isDark ? 'rgba(255,255,255,0.06)' : '#e0e0e0';
        const txtFill = isDark ? 'rgba(255,255,255,0.12)' : '#bbb';
        rects += `<rect class="fp-machine-box" id="${rectId}" x="${m.x}" y="${m.y}" width="${m.w}" height="${m.h}" rx="6" fill="${fill}" stroke="${stroke}" stroke-dasharray="4,3" stroke-width="1" data-aqc="${aqcName}" data-available="0"/>`;
        texts += `<text class="fp-machine-text" data-aqc="${aqcName}" x="${txtCx}" y="${txtCy - 2}" text-anchor="middle" dominant-baseline="middle" font-size="10" font-weight="600" fill="${txtFill}" font-family="sans-serif">${displayName}</text>`;
        // Muted dash badge for unassigned positions
        const qH = 13;
        const qW = 18;
        const qX = m.x + (m.w - qW) / 2;
        const qY = m.y + m.h - qH - 3;
        texts += `<rect x="${qX}" y="${qY}" width="${qW}" height="${qH}" rx="${qH/2}" fill="rgba(0,0,0,0.04)" stroke="rgba(0,0,0,0.06)" stroke-width="0.5"/>`;
        texts += `<text x="${txtCx}" y="${qY + qH/2 + 0.5}" text-anchor="middle" dominant-baseline="middle" font-size="6.5" font-weight="600" fill="${txtFill}" font-family="sans-serif">—</text>`;
      }
    });

    loadedKeys.forEach(k => {
      if (!keyToAqc[k] && !assignedSet.has(k)) unmatched.push(k);
    });

    const zoneOrder = ['A','B','C','D'];
    let legendHTML = '';
    zoneOrder.forEach(z => {
      const zs = FP_ZONE_STYLES[z];
      const count = zoneMachineCounts[z] || 0;
      const total = {A:20, B:8, C:8, D:6}[z];
      legendHTML += `<div class="fp-leg-item"><div class="fp-leg-dot" style="background:${zs.rectFill};border:1.5px solid ${zs.rectStroke}"></div>${zs.label} — ${count}/${total}</div>`;
    });
    legendHTML += `<div class="fp-leg-item"><div class="fp-leg-dot" style="background:rgb(200,60,60);border:1.5px solid rgb(200,60,60)"></div>0</div><div class="fp-leg-item"><div class="fp-leg-dot" style="background:rgb(150,160,20);border:1.5px solid rgb(150,160,20)"></div>32</div><div class="fp-leg-item"><div class="fp-leg-dot" style="background:rgb(60,195,5);border:1.5px solid rgb(60,195,5)"></div>64</div>`;

    let extraHTML = '';
    if (unmatched.length > 0) {
      extraHTML = `<div style="margin-top:10px;font-size:11px;color:var(--muted);display:flex;gap:6px;flex-wrap:wrap;align-items:center;"><span style="color:var(--text2);font-weight:600;">Unmapped:</span>${unmatched.map(u => `<span style="background:rgba(255,255,255,0.06);padding:2px 8px;border-radius:4px;border:1px solid var(--border);cursor:pointer;" onclick="fpJumpToMachine('${u}')">${u.toUpperCase()}</span>`).join('')}</div>`;
    }

    container.innerHTML = `
        <div style="font-size:13px;font-weight:600;color:var(--text);margin-bottom:2px;">Machine Floorplan</div>
        <div style="font-size:11px;color:var(--muted);margin-bottom:12px;">42 positions · ${availableCount} available · Right-click any position to assign a machine</div>
        <div class="fp-search"><input class="fp-search-input" id="fp-search-input" type="text" placeholder="Search machine..." oninput="fpFilterMachines(this.value)"/><span id="fp-search-count" style="font-size:11px;color:var(--muted);white-space:nowrap;"></span></div>
        <svg width="100%" viewBox="0 20 900 440" xmlns="http://www.w3.org/2000/svg">
            ${rects}
            ${texts}
        </svg>
        <div class="fp-legend">${legendHTML}</div>
        ${extraHTML}
    `;

    // delegate click on container (handles re-renders without re-attaching)
    container.onclick = function(e) {
        var el = e.target.closest('.fp-machine-box[data-available="1"]');
        if (!el) return;
        var name = el.dataset.machine;
        if (!name) return;
        if (fpUseRings()) {
            var aqcName = el.dataset.aqc;
            var target = (aqcName && ALL_MACHINE_DATA[aqcName]) ? aqcName : (ALL_MACHINE_DATA[name] ? name : null);
            if (target) {
                switchView('bdr');
                switchMachine(target);
                toggleFloorplan();
                setTimeout(function() {
                    var kpi = document.querySelector('.dashboard-kpi-grid, .kpi-grid');
                    var machineBtn = [...document.querySelectorAll('#machine-buttons .heatmap-filter')]
                        .find(function(b) { return b.dataset.machine === target; });
                    if (machineBtn) machineBtn.scrollIntoView({ behavior: 'smooth', block: 'nearest', inline: 'center' });
                    if (kpi) kpi.scrollIntoView({ behavior: 'smooth', block: 'start' });
                }, 100);
            } else {
                switchView('bdr');
                toggleFloorplan();
            }
        } else if (ALL_MACHINE_DATA[name]) {
            switchMachine(name);
            toggleFloorplan();
            setTimeout(function() {
                var kpi = document.querySelector('.dashboard-kpi-grid, .kpi-grid');
                var machineBtn = [...document.querySelectorAll('#machine-buttons .heatmap-filter')]
                    .find(function(b) { return b.dataset.machine === name; });
                if (machineBtn) machineBtn.scrollIntoView({ behavior: 'smooth', block: 'nearest', inline: 'center' });
                if (kpi) kpi.scrollIntoView({ behavior: 'smooth', block: 'start' });
            }, 100);
        }
    };

    // attach right-click context menu on ALL machine boxes
    container.querySelectorAll('.fp-machine-box').forEach(el => {
        el.addEventListener('contextmenu', (e) => {
            const aqcName = el.dataset.aqc;
            if (aqcName) fpShowCtxMenu(e, aqcName);
        });
    });
}

function fpFilterMachines(query) {
    const q = query.trim();
    const container = document.getElementById('floorplan-content');
    if (!container) return;
    const boxes = container.querySelectorAll('.fp-machine-box');
    const countEl = document.getElementById('fp-search-count');
    let matchCount = 0;
    boxes.forEach(el => {
        const aqc = (el.dataset.aqc || '').toUpperCase();
        const match = q && aqc.includes(q.toUpperCase());
        el.classList.toggle('fp-highlight', match);
        if (match) matchCount++;
    });
    // also highlight text labels
    container.querySelectorAll('.fp-machine-text').forEach(el => {
        const aqc = (el.dataset.aqc || '').toUpperCase();
        el.classList.toggle('fp-highlight', q && aqc.includes(q.toUpperCase()));
    });
    countEl.textContent = q ? matchCount + ' found' : '';
}

function toggleSerialBrowser() {
    const overlay = document.getElementById('sn-modal-overlay');
    if (overlay.classList.contains('visible')) {
        closeSerialBrowser();
    } else {
        overlay.classList.add('visible');
        _serialBrowserCategoryFilter = '';
        _serialBrowserBulkSerials = [];
        document.querySelectorAll('#sn-cat-filter button').forEach(b => b.classList.toggle('active', b.dataset.cat === ''));
        document.getElementById('sn-modal-input').value = '';
        document.getElementById('sn-modal-body').innerHTML = '<div class="sn-empty-state">Start typing a serial number or part of it above</div>';
        document.getElementById('sn-modal-count').textContent = '';
        setTimeout(() => document.getElementById('sn-modal-input').focus(), 100);
    }
}

function setSerialBrowserCategory(cat) {
    _serialBrowserCategoryFilter = cat;
    document.querySelectorAll('#sn-cat-filter button').forEach(b => b.classList.toggle('active', b.dataset.cat === cat));
    const input = document.getElementById('sn-modal-input');
    filterSerialBrowser(input ? input.value : '');
}

function toggleSerialBrowserBulk() {
    _serialBrowserBulkMode = !_serialBrowserBulkMode;
    const btn = document.getElementById('sn-bulk-toggle');
    const input = document.getElementById('sn-modal-input');
    if (btn) btn.classList.toggle('active', _serialBrowserBulkMode);
    input.placeholder = _serialBrowserBulkMode ? 'Paste serial numbers (one per line)...' : 'Type any part of serial number...';
    filterSerialBrowser(input.value);
}

function closeSerialBrowser() {
    document.getElementById('sn-modal-overlay').classList.remove('visible');
}

function exportSerialBrowserCSV() {
    const results = _serialBrowserFilteredResults;
    if (!results || results.length === 0) return;
    let csv = 'Machine,Slot,Serial Number,MAC ID,Firmware,Workouts\n';
    results.forEach(r => {
        const machine = (r.file || '--').replace(/"/g, '""');
        const sn = (r.serial || '--').replace(/"/g, '""');
        const mac = (r.mac || '--').replace(/"/g, '""');
        const fw = (r.fw || '--').replace(/"/g, '""');
        csv += `"${machine}",${r.slot},"${sn}","${mac}","${fw}",${r.workoutCount}\n`;
    });
    const query = document.getElementById('sn-modal-input')?.value?.trim() || 'serial-numbers';
    downloadCSV(csv, 'SerialBrowser_' + query.replace(/[^a-zA-Z0-9]/g, '_') + '.csv');
}

function filterSerialBrowser(query) {
    let q = query.trim();
    const labelMatch = /^\[Bulk Search: \d+ Serials\]$/.test(q);
    if (labelMatch && _serialBrowserBulkSerials.length) {
        q = _serialBrowserBulkSerials.join('\n');
    } else if (!labelMatch && _serialBrowserBulkSerials.length) {
        _serialBrowserBulkSerials = [];
    }
    const body = document.getElementById('sn-modal-body');
    const countEl = document.getElementById('sn-modal-count');
    const data = ringsData || [];

    if (!q) {
        _serialBrowserFilteredResults = [];
        body.innerHTML = '<div class="sn-empty-state">Start typing a serial number or part of it above</div>';
        countEl.textContent = '';
        return;
    }

    let terms;
    if (_serialBrowserBulkMode) {
        terms = q.split(/\r?\n/).map(t => t.trim().toLowerCase()).filter(Boolean);
        if (terms.length === 0) {
            _serialBrowserFilteredResults = [];
            body.innerHTML = '<div class="sn-empty-state">Enter at least one serial number</div>';
            countEl.textContent = '';
            return;
        }
    } else {
        terms = [q.toLowerCase()];
    }

    const results = [];

    data.forEach(r => {
        const sn = (r.serial_number || '').toString().trim();
        if (!sn || sn === '--' || sn === 'N/A') return;
        const snLower = sn.toLowerCase();
        const matched = _serialBrowserBulkMode
            ? terms.includes(snLower)
            : terms.some(t => snLower.includes(t));
        if (!matched) return;
        const cls = classifySerial(sn);
        if (_serialBrowserCategoryFilter && (!cls || cls.category !== _serialBrowserCategoryFilter)) return;
        results.push({
            file: r.file,
            slot: r.slot,
            serial: sn,
            mac: r.ring_mac || '--',
            fw: r.firmware_version || '--',
            state: (r.state || '--'),
            ring_name: r.ring_name || '--'
        });
    });

    _serialBrowserFilteredResults = results;
    countEl.textContent = results.length + ' result' + (results.length !== 1 ? 's' : '');

    if (results.length === 0) {
        const displayQ = _serialBrowserBulkMode ? terms.join(', ') : q;
        body.innerHTML = '<div class="sn-empty-state">No serial numbers contain <strong>' + escHtml(displayQ) + '</strong></div>';
        return;
    }

    function highlight(text, query) {
        const idx = text.toLowerCase().indexOf(query.toLowerCase());
        if (idx === -1) return escHtml(text);
        return escHtml(text.substring(0, idx)) + '<mark>' + escHtml(text.substring(idx, idx + query.length)) + '</mark>' + escHtml(text.substring(idx + query.length));
    }

    function highlightAll(text, termList) {
        const lower = text.toLowerCase();
        const ranges = [];
        for (const term of termList) {
            const t = term.toLowerCase();
            let idx = 0;
            while ((idx = lower.indexOf(t, idx)) !== -1) {
                ranges.push({ start: idx, end: idx + t.length });
                idx += t.length;
            }
        }
        if (ranges.length === 0) return escHtml(text);
        ranges.sort((a, b) => a.start - b.start);
        const merged = [ranges[0]];
        for (let i = 1; i < ranges.length; i++) {
            const last = merged[merged.length - 1];
            if (ranges[i].start <= last.end) {
                last.end = Math.max(last.end, ranges[i].end);
            } else {
                merged.push(ranges[i]);
            }
        }
        let result = '';
        let pos = 0;
        for (const range of merged) {
            result += escHtml(text.substring(pos, range.start));
            result += '<mark>' + escHtml(text.substring(range.start, range.end)) + '</mark>';
            pos = range.end;
        }
        result += escHtml(text.substring(pos));
        return result;
    }

    let html = '<table class="sn-table"><thead><tr>' +
        '<th>Serial Number</th><th>Machine</th><th>Slot</th><th>Status</th><th>MAC ID</th><th>Firmware</th>' +
        '</tr></thead><tbody>';

    results.forEach(r => {
        const encodedMachine = encodeURIComponent(r.file);
        const serialHtml = _serialBrowserBulkMode
            ? (terms.length <= 100 ? highlightAll(r.serial, terms) : escHtml(r.serial))
            : highlight(r.serial, q);
        html += '<tr onclick="openRingsDetailFromBrowser(\'' + encodedMachine + '\',\'' + r.slot + '\')">' +
            '<td class="sn-serial">' + serialHtml + '</td>' +
            '<td class="sn-machine" style="font-size:11px;">' + escHtml(r.file) + '</td>' +
            '<td class="sn-slot">' + escHtml(r.slot) + '</td>' +
            '<td>' + escHtml(r.state) + '</td>' +
            '<td style="font-size:11px;color:var(--muted);">' + escHtml(r.mac) + '</td>' +
            '<td style="font-size:11px;">' + escHtml(r.fw) + '</td>' +
        '</tr>';
    });

    html += '</tbody></table>';
    body.innerHTML = html;
}

/* ── Serial Browser Bulk Paste (Excel column) ─────────────────────────
   Single-line inputs strip newlines on paste, so intercept the clipboard
   natively and split strictly by line breaks (commas ignored) — same
   behavior as the Old Data bulk search. */

function setupSerialBrowserBulkPaste() {
    const searchInput = document.getElementById('sn-modal-input');
    if (!searchInput) return;

    searchInput.addEventListener('paste', (e) => {
        e.preventDefault();
        const pasteData = (e.clipboardData || window.clipboardData).getData('text');
        if (!pasteData || !pasteData.trim()) return;

        const serialArray = pasteData.split(/\r?\n/).map(s => s.trim()).filter(s => s.length > 0);
        if (serialArray.length === 0) return;

        if (!_serialBrowserBulkMode) toggleSerialBrowserBulk();
        _serialBrowserBulkSerials = serialArray;
        searchInput.value = '[Bulk Search: ' + serialArray.length + ' Serials]';
        filterSerialBrowser(serialArray.join('\n'));
    });
}

setupSerialBrowserBulkPaste();

function openRingsDetailFromBrowser(file, slot) {
    closeSerialBrowser();
    switchView('rings');
    const d = ringsData.find(r => r.file === file && r.slot === slot);
    if (!d) return;
    ringsSelectedMachine = d.file;
    populateRingsFilter();
    ringsRenderGrid();
    requestAnimationFrame(function() {
        const el = document.querySelector('#rings-grid .slot-cell[data-slot="' + d.slot + '"]');
        ringsOpenDetail(d, d.slot, el);
    });
}

function escHtml(str) {
    const div = document.createElement('div');
    div.textContent = str;
    return div.innerHTML;
}

function resetEverything() {
    if (!confirm('Reset all data and clear everything?')) return;
    stopFileWatching();
    ringsStopWatching();
    stopApiPolling();
    ALL_MACHINE_DATA = {};
    ringsData = [];
    lastBdrFingerprint = null;
    lastRingsFingerprint = null;
    pendingRingsFingerprint = null;
    pendingRingsStableReads = 0;
    committedBdrMachineCount = 0;
    committedBdrSerialCount = 0;
    committedRingsMachineCount = 0;
    committedRingsSlotCount = 0;
    committedRingsSerialCount = 0;
    pendingBdrLowerKey = null;
    pendingBdrLowerStableReads = 0;
    pendingRingsLowerKey = null;
    pendingRingsLowerStableReads = 0;
    bdrFetchInFlight = false;
    ringsFetchInFlight = false;
    localStorage.removeItem('committedBdrMachineCount');
    localStorage.removeItem('committedBdrSerialCount');
    localStorage.removeItem('committedRingsMachineCount');
    localStorage.removeItem('committedRingsSlotCount');
    localStorage.removeItem('committedRingsSerialCount');
    ringsSelectedMachine = null;
    ringsStatusFilter = '';
    ringsSelectedSlot = null;
    CURRENT_MACHINE = null;
    SESSION_DATA = null;
    globalHeatmapData = [];
    globalFwVersion = '--';
    window.heatmapFilterActive = null;
    window.firmwareFilterActive = null;
    const emptyState = document.getElementById('empty-state');
    if (emptyState) emptyState.style.display = 'flex';
    const dashboard = document.getElementById('dashboard-content');
    if (dashboard) dashboard.style.display = 'none';
    const ringsView = document.getElementById('rings-view');
    if (ringsView) ringsView.style.display = 'none';
    const detailPanel = document.getElementById('detail-panel');
    if (detailPanel) detailPanel.classList.remove('visible');
    const ringsDetail = document.getElementById('rings-detail-panel');
    if (ringsDetail) ringsDetail.classList.add('hidden');
    const statsEl = document.getElementById('rings-stats');
    if (statsEl) statsEl.style.display = 'none';
    const legend = document.getElementById('rings-legend');
    if (legend) legend.style.display = 'none';
    const ringsEmpty = document.getElementById('rings-empty');
    if (ringsEmpty) ringsEmpty.style.display = 'flex';
    const ringsGrid = document.getElementById('rings-grid');
    if (ringsGrid) ringsGrid.innerHTML = '';
    const machineButtons = document.getElementById('machine-buttons');
    if (machineButtons) machineButtons.innerHTML = '';
    const bulkChargerControls = document.getElementById('bulk-charger-controls');
    if (bulkChargerControls) bulkChargerControls.innerHTML = '';
    const ringsBulkChargerControls = document.getElementById('rings-bulk-charger-controls');
    if (ringsBulkChargerControls) ringsBulkChargerControls.innerHTML = '';
    const hmGrid = document.getElementById('heatmap-grid');
    if (hmGrid) hmGrid.innerHTML = '';
    const fwContainer = document.getElementById('firmware-filters');
    if (fwContainer) fwContainer.innerHTML = '<span style="font-size:10px;text-transform:uppercase;letter-spacing:0.05em;color:var(--muted);font-weight:600;margin-right:8px;">FW:</span>';
    const ringsWatchBadge = document.getElementById('rings-watch-badge');
    if (ringsWatchBadge) ringsWatchBadge.classList.add('hidden');
    const fleetLabel = document.getElementById('fleet-heatmap-machine');
    const fleetRow = document.getElementById('fleet-heatmap-machine-row');
    if (fleetLabel) { fleetLabel.textContent = ''; fleetLabel.style.display = 'none'; }
    const dtMachineName = document.getElementById('dt-machine-name');
    if (dtMachineName) dtMachineName.innerText = '';
    const dtId = document.getElementById('dt-id');
    if (dtId) dtId.innerText = '';
    const dtMac = document.getElementById('dt-mac');
    if (dtMac) dtMac.innerText = '';
    const dtPhase = document.getElementById('dt-phase');
    if (dtPhase) dtPhase.innerText = '';
    const dtStatus = document.getElementById('dt-status');
    if (dtStatus) dtStatus.innerText = '';
    updateUploadLabel('Open Folder', 'Watch JSON files');
    dbDelete('allMachineData');
    dbDelete('bdrDirHandle');
    dbDelete('ringsDirHandle');
}

function toggleFloorplan() {
    const panel = document.getElementById('floorplan-panel');
    const btn = document.getElementById('floorplan-toggle-btn');
    if (!panel) return;

    if (panel.classList.contains('visible')) {
        panel.classList.remove('visible');
        btn.classList.remove('active');
    } else {
        renderFloorplan();
        panel.classList.add('visible');
        btn.classList.add('active');
        setTimeout(function() {
            const top = panel.getBoundingClientRect().top + window.scrollY - 16;
            window.scrollTo({ top: Math.max(0, top), behavior: 'smooth' });
        }, 50);
    }
}

function openFloorplanSearch() {
    const panel = document.getElementById('floorplan-panel');
    const btn = document.getElementById('floorplan-toggle-btn');
    const searchInput = document.getElementById('fp-search-input');
    
    if (!panel) return;
    
    // Open floorplan if not already open
    if (!panel.classList.contains('visible')) {
        renderFloorplan();
        panel.classList.add('visible');
        btn.classList.add('active');
    }
    
    setTimeout(function() {
        const top = panel.getBoundingClientRect().top + window.scrollY - 16;
        window.scrollTo({ top: Math.max(0, top), behavior: 'smooth' });
    }, 50);
    
    // Focus on search input and clear any existing search
    if (searchInput) {
        setTimeout(() => {
            searchInput.value = '';
            fpFilterMachines('');
            searchInput.focus();
        }, 100);
    }
}

function showDuplicatesModal() {
    const stats = computeSerialStats(ALL_MACHINE_DATA);
    const overlay = document.getElementById('dups-modal-overlay');
    const content = document.getElementById('dups-modal-content');
    if (!overlay || !content) return;
    renderDuplicateModalContent(stats.duplicates);
    overlay.classList.add('visible');
    // close on overlay background click
    overlay.onclick = function(e) {
        if (e.target === overlay) closeDuplicatesModal();
    };
    // focus first button for accessibility
    setTimeout(() => {
        const firstBtn = overlay.querySelector('.dup-loc-btn');
        if (firstBtn) firstBtn.focus();
    }, 80);
}
function closeDuplicatesModal() {
    const overlay = document.getElementById('dups-modal-overlay');
    if (overlay) overlay.classList.remove('visible');
}
function renderDuplicateModalContent(duplicates) {
    const content = document.getElementById('dups-modal-content');
    if (!content) return;
    if (!duplicates || duplicates.length === 0) {
        content.innerHTML = '<div style="color:var(--muted)">No duplicate serials detected</div>';
        return;
    }
    let html = '<div class="modal-list">';
    duplicates.forEach(d => {
        const uniqueMachines = [...new Set(d.locations.map(l => l.machine))];
        const isCrossMachine = uniqueMachines.length > 1;
        const crossLabel = isCrossMachine ? ' <span style="color:#F59E0B;font-size:11px;font-weight:600;">&#9888; Cross-machine</span>' : '';
        const locs = d.locations.map(l => {
            const isOtherMachine = l.machine !== CURRENT_MACHINE;
            const cls = 'dup-loc-btn' + (isOtherMachine ? ' other-machine' : '');
            return `<button class="${cls}" data-machine="${l.machine}" data-slot="${l.slot}">${l.machine.toUpperCase()}<span class="loc-slot">Slot ${l.slot}</span></button>`;
        }).join(' ');
        html += `<div class="dup-item"><div class="dup-serial">${d.serial}</div><div class="dup-meta">${d.count} occurrences${crossLabel}</div><div class="dup-locs">${locs}</div></div>`;
    });
    html += '</div>';
    content.innerHTML = html;
    // attach handlers
    content.querySelectorAll('.dup-loc-btn').forEach(btn => {
        btn.addEventListener('click', (e) => {
            const machine = btn.dataset.machine;
            const slot = btn.dataset.slot;
            // close modal and highlight
            closeDuplicatesModal();
            highlightLocation(machine, slot);
        });
    });
}
function highlightLocation(machine, slot) {
    if (CURRENT_MACHINE !== machine) {
        // switchMachine will call init(); allow brief delay
        switchMachine(machine);
        setTimeout(() => highlightSlotById(slot), 260);
    } else {
        highlightSlotById(slot);
    }
}
function highlightSlotById(slotId) {
    try {
        // clear existing pulses
        document.querySelectorAll('.slot-cell.duplicate-pulse').forEach(el => el.classList.remove('duplicate-pulse'));
        const el = document.querySelector(`.slot-cell[data-id="${slotId}"]`);
        if (el) {
            el.classList.add('duplicate-pulse');
            el.scrollIntoView({ behavior: 'smooth', block: 'center' });
            // open detail if heatmap data is available
            const hm = globalHeatmapData.find(h => String(h.id) === String(slotId));
            if (hm) {
                document.querySelectorAll('.slot-cell').forEach(c => c.classList.remove('active'));
                el.classList.add('active');
                openDetailPanel(hm);
            }
            setTimeout(() => el.classList.remove('duplicate-pulse'), 3000);
            return;
        }
        // if element not found yet, retry shortly
        setTimeout(() => {
            const el2 = document.querySelector(`.slot-cell[data-id="${slotId}"]`);
            if (el2) { el2.classList.add('duplicate-pulse'); el2.scrollIntoView({ behavior: 'smooth', block: 'center' }); setTimeout(() => el2.classList.remove('duplicate-pulse'), 3000); }
        }, 400);
    } catch (e) {
        console.warn('highlightSlotById error', e);
    }
}

// Firmware Modal Functions
function collectFirmwareData() {
    const fwMap = {};
    Object.entries(ALL_MACHINE_DATA).forEach(([machine, md]) => {
        const slots = md.slots || {};
        Object.values(slots).forEach(s => {
            const fw = (s.firmware_version || '').toString().trim();
            if (!fw || fw === 'N/A' || fw === '--') return;
            if (!fwMap[fw]) fwMap[fw] = {};
            fwMap[fw][machine] = (fwMap[fw][machine] || 0) + 1;
        });
    });
    return fwMap;
}

function showFirmwareModal() {
    const overlay = document.getElementById('fw-modal-overlay');
    const content = document.getElementById('fw-modal-content');
    if (!overlay || !content) return;
    const fwMap = collectFirmwareData();
    const entries = Object.entries(fwMap).sort((a, b) => a[0].localeCompare(b[0]));
    if (entries.length === 0) {
        content.innerHTML = '<div style="color:var(--muted);padding:12px;">No firmware data found</div>';
    } else {
        let html = '<div class="modal-list">';
        entries.forEach(([fw, machines]) => {
            const machineList = Object.entries(machines).map(([m, count]) =>
                `<span class="fw-machine-chip" onclick="switchMachine('${m}');closeFirmwareModal();">${m.toUpperCase()}<span class="chip-count">${count}</span></span>`
            ).join('');
            html += `<div class="dup-item" style="flex-direction:column;align-items:flex-start;gap:8px;padding:12px;">
                <div style="font-weight:700;font-size:14px;letter-spacing:-0.01em;color:var(--text);background:var(--bg);padding:2px 10px;border-radius:6px;display:inline-block;">${fw}</div>
                <div style="display:flex;flex-wrap:wrap;">${machineList}</div>
            </div>`;
        });
        html += '</div>';
        content.innerHTML = html;
    }
    overlay.classList.add('visible');
    overlay.onclick = function(e) {
        if (e.target === overlay) closeFirmwareModal();
    };
}

function closeFirmwareModal() {
    const overlay = document.getElementById('fw-modal-overlay');
    if (overlay) overlay.classList.remove('visible');
}

// Logs Modal

// Theme Management
function setTheme(theme) {
    const html = document.documentElement;
    const btn = document.getElementById('theme-toggle-btn');

    // Add short-lived transition helper to enable smooth transitions across many properties
    html.classList.add('theme-transition');
    clearTimeout(window._themeTransTimer);
    window._themeTransTimer = setTimeout(() => html.classList.remove('theme-transition'), 520);

    if (theme === 'dark') {
        html.setAttribute('data-theme', 'dark');
        if (btn) btn.setAttribute('aria-pressed', 'true');
    } else {
        html.removeAttribute('data-theme');
        if (btn) btn.setAttribute('aria-pressed', 'false');
    }
    localStorage.setItem('theme', theme);
    // update charts immediately so colors feel consistent with UI
    updateChartThemes();
}
function toggleTheme() {
    const isDark = document.documentElement.getAttribute('data-theme') === 'dark';
    setTheme(isDark ? 'light' : 'dark');
}
function initTheme() {
    const saved = localStorage.getItem('theme');
    if (saved) {
        setTheme(saved);
    } else if (window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches) {
        setTheme('dark');
    } else {
        setTheme('light');
    }

    // Keyboard shortcut: T toggles theme (when not typing)
    document.addEventListener('keydown', (e) => {
        if (e.key && e.key.toLowerCase() === 't' && !['INPUT','TEXTAREA','SELECT'].includes(document.activeElement.tagName)) {
            toggleTheme();
        }
    });

    // Keyboard shortcut: F opens floorplan search (when not typing)
    document.addEventListener('keydown', (e) => {
        if (e.key && e.key.toLowerCase() === 'f' && !['INPUT','TEXTAREA','SELECT'].includes(document.activeElement.tagName)) {
            e.preventDefault();
            openFloorplanSearch();
        }
    });

    // Keyboard shortcut: C clears all filters on BDR dashboard and Ring Slots
    document.addEventListener('keydown', (e) => {
        if (e.key && e.key.toLowerCase() === 'c' && !['INPUT','TEXTAREA','SELECT'].includes(document.activeElement.tagName)) {
            e.preventDefault();
            window.heatmapFilterActive = null;
            document.querySelectorAll('.heatmap-filter').forEach(b => b.classList.remove('active', 'inactive'));
            applyHeatmapFilter();
            ringsClearAllFilters();
        }
    });

    // Keyboard shortcut: Q opens serial number browser
    document.addEventListener('keydown', (e) => {
        if (e.key && e.key.toLowerCase() === 'q' && !['INPUT','TEXTAREA','SELECT'].includes(document.activeElement.tagName)) {
            e.preventDefault();
            toggleSerialBrowser();
        }
    });
}
function updateChartThemes() {
    const grid = getApexGrid();
    [chartA, chartB].forEach(ch => {
        if (ch && typeof ch.updateOptions === 'function') {
            ch.updateOptions({ grid: { ...grid } });
        }
    });
    if (detailLineChart && typeof detailLineChart.updateOptions === 'function') {
        detailLineChart.updateOptions({ grid: getApexGrid('detail') });
    }
    // refresh floorplan if visible
    const fpPanel = document.getElementById('floorplan-panel');
    if (fpPanel && fpPanel.classList.contains('visible')) renderFloorplan();
}

function setupViewToggleListeners() {
    const views = ['bdr', 'rings', 'data-viz'];
    views.forEach(v => {
        const btn = document.getElementById('view-' + v + '-btn');
        if (btn) btn.addEventListener('click', () => switchView(v));
    });
    const diagBtn = document.getElementById('view-diag-btn');
    if (diagBtn) {
        diagBtn.addEventListener('click', () => {
            switchView('diagnostics');
            showDiagSelection();
            populateDiagMachineGrid();
        });
    }
    const oldDataBtn = document.getElementById('view-old-data-btn');
    if (oldDataBtn) {
        oldDataBtn.addEventListener('click', () => {
            switchView('old-data');
            const input1 = document.getElementById('od-search-input');
            const input2 = document.getElementById('od-search-input-2');
            if (input1) setTimeout(() => input1.focus(), 100);
            if (input2) input2.value = input1 ? input1.value : '';
        });
    }
}

document.addEventListener('DOMContentLoaded', () => {
    initTheme();
    init();
    setupViewToggleListeners();
    switchView('bdr');
    localStorage.removeItem('committedBdrMachineCount');
    localStorage.removeItem('committedRingsMachineCount');
    localStorage.removeItem('committedRingsSlotCount');

    // Show loading state while waiting for first live data
    const loadingEl = document.createElement('div');
    loadingEl.id = 'live-loading';
    loadingEl.style.cssText = 'position:fixed;top:50%;left:50%;transform:translate(-50%,-50%);text-align:center;color:var(--muted);font-size:14px;z-index:9999;background:var(--bg);padding:32px 48px;border-radius:12px;border:1px solid var(--border);box-shadow:0 4px 24px rgba(0,0,0,0.15);';
    loadingEl.innerHTML = '<div style="font-size:32px;margin-bottom:12px;">&#8987;</div><div style="font-weight:600;">Loading live data...</div><div style="font-size:11px;margin-top:6px;color:var(--muted);">Fetching from API</div>';
    document.body.appendChild(loadingEl);

    startAutoSessionRefresh();

    setTimeout(() => {
        const el = document.getElementById('live-loading');
        if (el) el.remove();
    }, 5000);

        let csvBtn = document.getElementById('dt-export-csv');
        if (csvBtn) {
            csvBtn.addEventListener('click', (e) => {
                e.stopPropagation();
                exportSlotHistory();
            });
        }

        document.getElementById('heatmap-filters').addEventListener('click', (e) => {
            let btn = e.target.closest('.heatmap-filter');
            if (!btn) return;

            if (btn.dataset.filter === 'clear') {
                window.heatmapFilterActive = null;
                document.querySelectorAll('.heatmap-filter').forEach(b => b.classList.remove('active', 'inactive'));
                applyHeatmapFilter();
                updateBdrBulkChargerControls();
                return;
            }

            if (!window.heatmapFilterActive) window.heatmapFilterActive = new Set();
            let active = window.heatmapFilterActive;
            let filter = btn.dataset.filter;

            if (active.has(filter)) {
                active.delete(filter);
                btn.classList.remove('active');
            } else {
                active.add(filter);
                btn.classList.add('active');
            }

            if (active.size === 0) window.heatmapFilterActive = null;
            applyHeatmapFilter();
            updateBdrBulkChargerControls();
        });

        document.getElementById('export-qualified-btn').addEventListener('click', exportQualifiedSlots);
        document.getElementById('serial-search').addEventListener('keydown', (e) => {
            if (e.key === 'Enter') searchSerialNumber(e.target.value);
        });
        document.getElementById('sn-scan-btn').addEventListener('click', () => {
            const input = document.getElementById('serial-search');
            if (input.value.trim()) searchSerialNumber(input.value);
        });

        document.querySelectorAll('.pick-color').forEach(dot => {
            dot.addEventListener('click', (e) => {
                e.stopPropagation();
                let btn = e.target.closest('.heatmap-filter');
                btn.querySelector('.color-picker').click();
            });
        });

        document.querySelectorAll('.color-picker').forEach(picker => {
            picker.addEventListener('input', (e) => {
                let color = e.target.value;
                let cls = e.target.dataset.target;
                let btn = e.target.closest('.heatmap-filter');
                btn.querySelector('.fdot').style.background = color;
                setHeatmapClassColor(cls, color);
                let legendDots = document.querySelectorAll('.heatmap-legend .legend-dot');
                let idx = ['slot-pass','slot-ok','slot-low-bdr','slot-high-bdr','slot-sensor-issue','slot-warn','slot-danger','slot-dead','slot-empty','slot-na'].indexOf(cls);
                if (idx >= 0 && legendDots[idx]) legendDots[idx].style.background = color;
            });
        });

        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape') {
                const ov = document.getElementById('sn-modal-overlay');
                if (ov && ov.classList.contains('visible')) { closeSerialBrowser(); return; }
                const fp = document.getElementById('floorplan-panel');
                if (fp && fp.classList.contains('visible')) {
                    fp.classList.remove('visible');
                    const btn = document.getElementById('floorplan-toggle-btn');
                    if (btn) btn.classList.remove('active');
                }
            }
            if ((e.key === 's' || e.key === 'S') && !e.ctrlKey && !e.metaKey && !e.altKey) {
                const tag = e.target.tagName;
                if (tag === 'INPUT' || tag === 'TEXTAREA' || tag === 'SELECT' || e.target.isContentEditable) return;
                e.preventDefault();
                switchView(currentView === 'bdr' ? 'rings' : 'bdr');
            }
        });
    }, 0);

    function updateClock() {
        const el = document.getElementById('live-clock');
        if (!el) return;
        const now = new Date();
        el.textContent = `${String(now.getHours()).padStart(2,'0')}:${String(now.getMinutes()).padStart(2,'0')}:${String(now.getSeconds()).padStart(2,'0')}`;
    }

    function updateLastUpdated() {
        const el = document.getElementById('last-updated');
        if (!el || !lastDataFetchTime) return;
        const diff = Date.now() - lastDataFetchTime;
        if (diff < 60000) el.textContent = `Last: ${Math.floor(diff/1000)}s ago`;
        else if (diff < 3600000) el.textContent = `Last: ${Math.floor(diff/60000)}m ago`;
        else el.textContent = `Last: ${Math.floor(diff/3600000)}h ago`;
        console.log('updateLastUpdated called', new Date(), el.textContent);
    }

    let lastDataFetchTime = 0;
    let clockIntervalId = null;
    let lastUpdatedIntervalId = null;

    function manualRefresh() {
        lastBdrFingerprint = null;
        lastRingsFingerprint = null;
        bdrFetchInFlight = false;
        ringsFetchInFlight = false;
        loadSessionFilesFromServer().catch(err => console.warn('BDR manual refresh error:', err));
        loadRingsFromAPI().catch(err => console.warn('Rings manual refresh error:', err));
    }

    setTimeout(() => {
        updateClock();
        updateLastUpdated();
        clockIntervalId = setInterval(updateClock, 1000);
        lastUpdatedIntervalId = setInterval(updateLastUpdated, 1000);

        window.addEventListener('beforeunload', () => {
            stopApiPolling();
            stopFileWatching();
            ringsStopWatching();
            if (clockIntervalId) clearInterval(clockIntervalId);
            if (lastUpdatedIntervalId) clearInterval(lastUpdatedIntervalId);
        });
    }, 0);

// Ring slots trigger (registered at script level after DOM is ready)
document.getElementById('rings-search')?.addEventListener('keydown', function(e) {
  if (e.key === 'Enter') {
    e.preventDefault();
    ringsSearchSerial(e.target.value);
  }
});

/* ── Cycle Analysis ── */

function toggleCycleAnalysis() {
  const overlay = document.getElementById('cycle-panel-overlay');
  const btn = document.getElementById('cycle-analysis-btn');
  if (!overlay) return;
  const isVisible = overlay.classList.toggle('visible');
  btn?.classList.toggle('active', isVisible);
  if (isVisible) renderCycleAnalysis();
}

function renderCycleAnalysis() {
  const body = document.getElementById('cycle-body');
  if (!body) return;
  body.innerHTML = '<div class="ar-loading"><span class="spinner"></span> Computing cycle analysis...</div>';
  setTimeout(() => {
    try {
      body.innerHTML = buildCycleAnalysisHTML();
    } catch (e) {
      body.innerHTML = '<div class="ar-empty">Error: ' + e.message + '</div>';
    }
  }, 50);
}

function buildCycleAnalysisHTML() {
  const machineNames = Object.keys(ALL_MACHINE_DATA || {});
  if (machineNames.length === 0) {
    return '<div class="ar-empty">No dashboard data loaded. Open a folder or connect to the API first.</div>';
  }

  const MAX_WORKOUT = 6;

  const machineResults = [];
  let grandTotalSlots = 0;
  let grandTotalOccupied = 0;
  const grandWorkoutBuckets = new Array(MAX_WORKOUT + 1).fill(0);

  machineNames.forEach(name => {
    const md = ALL_MACHINE_DATA[name];
    const slots = md.slots || {};
    const slotIds = Object.keys(slots);
    let occupiedSlots = 0;
    const workoutBuckets = new Array(MAX_WORKOUT + 1).fill(0);
    let slotsWithWorkouts = 0;

    slotIds.forEach(k => {
      const s = slots[k];
      const sn = (s.serial_number || '').toString().trim();
      if (!sn || sn === '--' || sn === 'N/A') return;
      occupiedSlots++;
      const completed = calculateCompletedCycleWorkouts(s);
      const wc = completed.length;
      if (wc > 0) {
        slotsWithWorkouts++;
        const idx = Math.min(wc, MAX_WORKOUT);
        workoutBuckets[idx]++;
      }
    });

    workoutBuckets[0] = occupiedSlots - slotsWithWorkouts;

    grandTotalSlots += slotIds.length;
    grandTotalOccupied += occupiedSlots;
    for (let w = 0; w <= MAX_WORKOUT; w++) {
      grandWorkoutBuckets[w] += workoutBuckets[w];
    }

    machineResults.push({ name, occupiedSlots, totalSlots: slotIds.length, buckets: workoutBuckets });
  });

  machineResults.sort((a, b) => a.name.localeCompare(b.name));

  let html = '';

  // Summary
  html += '<div class="ca-summary">';
  html += '<h3>Workout Distribution Overview</h3>';
  html += '<div class="ca-summary-grid">';
  html += '<div class="ca-stat"><span class="ca-stat-label">Total Machines</span><span class="ca-stat-value">' + machineResults.length + '</span></div>';
  html += '<div class="ca-stat"><span class="ca-stat-label">Total Slots</span><span class="ca-stat-value">' + grandTotalSlots + '</span></div>';
  html += '<div class="ca-stat"><span class="ca-stat-label">Occupied Slots</span><span class="ca-stat-value">' + grandTotalOccupied + '</span></div>';
  html += '</div></div>';

  // Overall workout distribution
  html += '<div class="ar-section">';
  html += '<div class="ar-section-title">Overall — Exact Workout Counts</div>';
  html += '<div class="ar-section-body" style="padding:0;overflow-x:auto;">';
  html += '<table class="ca-table ca-table-compact">';
  html += '<thead><tr><th>Metric</th><th>No Workout</th>';
  for (let w = 1; w <= MAX_WORKOUT; w++) html += '<th>' + ordinal(w) + ' Workout</th>';
  html += '<th>' + ordinal(MAX_WORKOUT) + '+</th>';
  html += '</tr></thead><tbody>';
  html += '<tr><td class="ca-machine-name">Slots</td>';
  html += '<td>' + grandWorkoutBuckets[0] + '</td>';
  for (let w = 1; w <= MAX_WORKOUT; w++) {
    const pct = grandTotalOccupied > 0 ? ((grandWorkoutBuckets[w] / grandTotalOccupied) * 100).toFixed(0) : 0;
    html += '<td><strong>' + grandWorkoutBuckets[w] + '</strong> <span style="color:var(--muted);font-size:10px;">(' + pct + '%)</span></td>';
  }
  html += '</tr></tbody></table>';
  html += '</div></div>';

  // Per-machine breakdown table
  html += '<div class="ar-section">';
  html += '<div class="ar-section-title">Per-Machine Exact Workout Counts</div>';
  html += '<div class="ar-section-body" style="padding:0;overflow-x:auto;">';
  html += '<table class="ca-table ca-table-compact">';
  html += '<thead><tr><th>Machine</th><th>64/Occupied</th><th>No Wk</th>';
  for (let w = 1; w <= MAX_WORKOUT; w++) html += '<th>' + ordinal(w) + '</th>';
  html += '<th>' + ordinal(MAX_WORKOUT) + '+</th>';
  html += '</tr></thead><tbody>';

  machineResults.forEach(r => {
    html += '<tr>';
    html += '<td class="ca-machine-name">' + nameToHTML(r.name) + '</td>';
    html += '<td>64/' + r.occupiedSlots + '</td>';
    html += '<td>' + r.buckets[0] + '</td>';
    for (let w = 1; w <= MAX_WORKOUT; w++) {
      html += '<td>' + r.buckets[w] + '</td>';
    }
    html += '</tr>';
  });

  html += '</tbody></table>';
  html += '</div></div>';

  // Footer
  const now = new Date();
  html += '<div style="text-align:center;padding:8px;color:var(--muted);font-size:10px;">Report generated ' + now.toLocaleString() + '</div>';

  return html;
}

function ordinal(n) {
  if (n === 1) return '1st';
  if (n === 2) return '2nd';
  if (n === 3) return '3rd';
  return n + 'th';
}

function nameToHTML(name) {
  const n = name || '';
  return n.split('_').map(w => w.charAt(0).toUpperCase() + w.slice(1)).join(' ');
}

/* ── Analysis Report ── */

function toggleAIPanel() {
  const overlay = document.getElementById('ai-panel-overlay');
  const btn = document.getElementById('ai-toggle-btn');
  if (!overlay) return;
  const isVisible = overlay.classList.toggle('visible');
  btn?.classList.toggle('active', isVisible);
  if (isVisible) generateAnalysisReport();
}

function getEffectiveSlotState(name, slotId, slot) {
  if (!ringsData || ringsData.length === 0) return slot.state || '';
  for (var i = 0; i < ringsData.length; i++) {
    var rd = ringsData[i];
    if (rd.file === name && rd.slot === slotId) {
      var rs = (rd.state || '').toUpperCase();
      if (rs === 'PASSED' || rs === 'PASS') return 'PASSED';
      if (rs === 'FAILED' || rs === 'FAIL') return 'FAILED';
      break;
    }
  }
  return slot.state || '';
}

function getIssueCount() {
  let count = 0;
  if (typeof spotlightAnomalies !== 'undefined') count += spotlightAnomalies.length;
  const names = Object.keys(ALL_MACHINE_DATA || {});
  names.forEach(name => {
    const md = ALL_MACHINE_DATA[name];
    if (!md) return;
    const slots = md.slots || {};
    const slotIds = Object.keys(slots);
    let failed = 0, dead = 0, sensorIssue = 0, highBdr = 0, na = 0, otherIssues = 0;
    slotIds.forEach(k => {
      const s = slots[k];
      const sn = (s.serial_number || '').toString().trim();
      if (!sn || sn === '--' || sn === 'N/A') { na++; return; }
      var es = getEffectiveSlotState(name, k, s);
      if (es === 'PASSED') return;
      if (es === 'FAILED') { failed++; return; }
      const bdr = s.bdr_state || {};
      if (isSlotDeadOrDied(s)) { dead++; return; }
      if ((bdr.consecutive_failures || 0) >= 3) { failed++; return; }
      if ((s.discharge_connect_failures || 0) > 3) { otherIssues++; return; }
      if (s.bdr_clock_health === 'NOK' || (s.bdr_clock_health_pct || 100) < 50) { sensorIssue++; return; }
      if (s.error && String(s.error).trim() !== '') { otherIssues++; return; }
    });
    var totalIssues = failed + dead + sensorIssue + highBdr + otherIssues;
    if (totalIssues > 15 || dead > 10 || na > 10) count += 1;
  });
  return count;
}

function updateReportBadge() {
  const badge = document.getElementById('ai-notification-badge');
  if (!badge) return;
  const count = getIssueCount();
  if (count > 0) {
    badge.textContent = count > 99 ? '99+' : count;
    badge.style.display = 'flex';
  } else {
    badge.style.display = 'none';
  }
}

function toggleAlertDetail(idx) {
  const el = document.getElementById('alert-detail-' + idx);
  const btn = el?.previousElementSibling;
  if (el) {
    el.classList.toggle('open');
    if (btn) btn.classList.toggle('open');
  }
}

function generateAnalysisReport() {
  const body = document.getElementById('ai-body');
  if (!body) return;

  body.innerHTML = '<div class="ar-loading"><span class="spinner"></span> Analyzing dashboard data...</div>';

  setTimeout(() => {
    try {
      body.innerHTML = buildReportHTML();
    } catch (e) {
      body.innerHTML = '<div class="ar-empty">Error generating report: ' + e.message + '</div>';
    }
    updateReportBadge();
  }, 100);
}

function buildReportHTML() {
  const machineNames = Object.keys(ALL_MACHINE_DATA);
  const hasData = machineNames.length > 0;

  if (!hasData) {
    return '<div class="ar-empty">No dashboard data loaded. Open a folder or connect to the API first.</div>';
  }

  // Build ring state lookup for the report
  var ringPassedSet = {};
  var ringFailedSet = {};
  if (ringsData && ringsData.length > 0) {
    ringsData.forEach(function(rd) {
      var rs = (rd.state || '').toUpperCase();
      var key = rd.file + '|' + rd.slot;
      if (rs === 'PASSED' || rs === 'PASS') ringPassedSet[key] = true;
      else if (rs === 'FAILED' || rs === 'FAIL') ringFailedSet[key] = true;
    });
  }
  function effectiveSlotState(name, slotId, slot) {
    var key = name + '|' + slotId;
    if (ringPassedSet[key]) return 'PASSED';
    if (ringFailedSet[key]) return 'FAILED';
    return slot.state || '';
  }

  let totalSlots = 0;
  let totalRunning = 0, totalPassed = 0, totalFailed = 0, totalEmpty = 0;

  machineNames.forEach(name => {
    const md = ALL_MACHINE_DATA[name];
    const slots = md.slots || {};
    const slotIds = Object.keys(slots);
    totalSlots += slotIds.length;
    totalRunning += slotIds.filter(k => effectiveSlotState(name, k, slots[k]) === 'BDR_RUNNING').length;
    totalPassed += slotIds.filter(k => effectiveSlotState(name, k, slots[k]) === 'PASSED').length;
    totalFailed += slotIds.filter(k => effectiveSlotState(name, k, slots[k]) === 'FAILED').length;
    totalEmpty += slotIds.filter(k => !slots[k].serial_number || slots[k].serial_number === '--' || slots[k].serial_number === 'N/A').length;
  });

  const allAnomalies = typeof spotlightAnomalies !== 'undefined' ? spotlightAnomalies : [];

  let html = '';

  // ── Summary Card ──
  html += '<div class="ar-summary">';
  html += '<h3>Fleet Overview</h3>';
  html += '<div class="ar-stat">Machines: <span>' + machineNames.length + '</span></div>';
  html += '<div class="ar-stat">Slots: <span>' + totalSlots + '</span></div>';
  html += '<div class="ar-stat" style="color:var(--ok)">Running: <span>' + totalRunning + '</span></div>';
  html += '<div class="ar-stat" style="color:var(--slot-pass-color)">Passed: <span>' + totalPassed + '</span></div>';
  html += '<div class="ar-stat" style="color:var(--danger)">Failed: <span>' + totalFailed + '</span></div>';
  html += '<div class="ar-stat" style="color:var(--muted)">Empty: <span>' + totalEmpty + '</span></div>';
  html += '</div>';

  // ── Alerts Section ──
  const alerts = [];

  machineNames.forEach(name => {
    const md = ALL_MACHINE_DATA[name];
    const slots = md.slots || {};
    const slotIds = Object.keys(slots);

    let failed = 0, dead = 0, sensorIssue = 0, highBdr = 0, na = 0, otherIssues = 0;
    const deadSlots = [];

    slotIds.forEach(k => {
      const s = slots[k];
      const sn = (s.serial_number || '').toString().trim();
      const effState = effectiveSlotState(name, k, s);

      if (!sn || sn === '--' || sn === 'N/A') { na++; return; }

      if (effState === 'PASSED') return; // ring passed → skip all issue counting

      if (effState === 'FAILED') { failed++; return; }

      const bdr = s.bdr_state || {};
      if (isSlotDeadOrDied(s)) {
        dead++;
        let reason = s.dead_state ? String(s.dead_state).trim() : 'Runtime died (battery < 3% or flat > 150 min)';
        deadSlots.push({ slotId: k, serial: sn, reason: reason });
        return;
      }
      if ((bdr.consecutive_failures || 0) >= 3) { failed++; return; }
      if ((s.discharge_connect_failures || 0) > 3) { otherIssues++; return; }
      if (s.bdr_clock_health === 'NOK' || (s.bdr_clock_health_pct || 100) < 50) { sensorIssue++; return; }
      if (s.error && String(s.error).trim() !== '') { otherIssues++; return; }
    });

    const totalIssues = failed + dead + sensorIssue + highBdr + otherIssues;
    const machineAlerts = [];

    if (totalIssues > 15) {
      let detail = '';
      if (failed > 0) detail += 'failed: ' + failed + ', ';
      if (dead > 0) detail += 'dead: ' + dead + ', ';
      if (sensorIssue > 0) detail += 'sensor/clock: ' + sensorIssue + ', ';
      if (otherIssues > 0) detail += 'other: ' + otherIssues + ', ';
      detail = detail.replace(/, $/, '');

      machineAlerts.push({
        iconClass: 'critical',
        text: '<strong>' + name.toUpperCase() + '</strong> — <span>' + totalIssues + ' problematic slots exceeds threshold of 15 (' + detail + ')</span>'
      });
    }

    if (dead > 10) {
      const reasonCounts = {};
      deadSlots.forEach(ds => {
        const r = ds.reason || 'UNKNOWN';
        reasonCounts[r] = (reasonCounts[r] || 0) + 1;
      });
      const deadDetailHtml = deadSlots.map(ds => 
        '<div class="ar-alert-detail-item"><strong>Slot ' + ds.slotId + '</strong> (' + ds.serial + ') — ' + ds.reason + '</div>'
      ).join('');

      machineAlerts.push({
        iconClass: 'critical',
        text: '<strong>' + name.toUpperCase() + '</strong> — <span>' + dead + ' dead/died slots exceeds threshold of 10</span>',
        detailHtml: '<div style="margin-bottom:4px;font-weight:600;">Dead/Died Slot Details:</div>' + deadDetailHtml
      });
    }

    if (na > 10) {
      machineAlerts.push({
        iconClass: 'warn',
        text: '<strong>' + name.toUpperCase() + '</strong> — <span>' + na + ' N/A slots exceeds threshold of 10</span>'
      });
    }

    if (machineAlerts.length > 0) {
      alerts.push({ machineName: name, alerts: machineAlerts });
    }
  });

  if (alerts.length > 0) {
    html += '<div class="ar-alert">';
    html += '<div class="ar-alert-title"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="width:16px;height:16px;"><path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg> ALERTS — ' + alerts.length + ' machines exceeded threshold limits</div>';
    alerts.forEach((g, gi) => {
      const hasDetail = g.alerts.some(a => a.detailHtml);
      html += '<div class="ar-alert-item ar-alert-btn' + (hasDetail ? '' : '') + '" onclick="toggleAlertDetail(' + gi + ')" data-group="' + gi + '">';
      html += '<div class="ar-alert-icon ' + g.alerts[0].iconClass + '">!</div>';
      html += '<div class="ar-alert-text">';
      html += '<strong>' + g.machineName.toUpperCase() + '</strong>';
      html += ' — <span>' + g.alerts.length + ' alert(s)</span>';
      html += '</div>';
      html += '<span class="ar-chevron">&#9660;</span>';
      html += '</div>';
      html += '<div class="ar-alert-detail" id="alert-detail-' + gi + '">';
      g.alerts.forEach(a => {
        html += '<div class="ar-alert-detail-item" style="display:flex;align-items:flex-start;gap:8px;padding:4px 0;"><span class="ar-alert-icon ' + a.iconClass + '" style="width:18px;height:18px;font-size:10px;flex-shrink:0;">!</span><div>' + a.text + '</div></div>';
        if (a.detailHtml) {
          html += '<div style="padding:4px 0 8px 26px;">' + a.detailHtml + '</div>';
        }
      });
      html += '</div>';
    });
    html += '</div>';
  } else {
    html += '<div class="ar-alert-clear">';
    html += '<div class="ar-alert-title"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="width:16px;height:16px;"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/><polyline points="22 4 12 14.01 9 11.01"/></svg> All Clear — No machines exceed threshold limits</div>';
    html += '</div>';
  }

  // ── Anomalies Section ──
  if (allAnomalies.length > 0) {
    const critical = allAnomalies.filter(a => a.sev === 'CRITICAL').length;
    const high = allAnomalies.filter(a => a.sev === 'HIGH').length;
    const medium = allAnomalies.filter(a => a.sev === 'MEDIUM').length;

    html += '<div class="ar-section">';
    html += '<div class="ar-section-title">Anomalies Detected <span style="font-weight:400;text-transform:none;letter-spacing:0;">(' + allAnomalies.length + ' total — ' + critical + ' critical, ' + high + ' high, ' + medium + ' medium)</span></div>';
    html += '<div class="ar-section-body">';
    allAnomalies.slice(0, 30).forEach(a => {
      const sevClass = a.sev === 'CRITICAL' ? 'critical' : a.sev === 'HIGH' ? 'high' : 'medium';
      html += '<div class="ar-item">';
      html += '<div class="ar-item-left">';
      html += '<span class="ar-badge ' + sevClass + '">' + a.sev + '</span>';
      html += '<span class="ar-issue-text"><strong>Slot ' + a.slot_id + '</strong>: ' + a.title + ' — ' + a.message + '</span>';
      html += '</div>';
      html += '</div>';
    });
    if (allAnomalies.length > 30) {
      html += '<div style="text-align:center;padding:8px;color:var(--muted);font-size:11px;">... and ' + (allAnomalies.length - 30) + ' more anomalies</div>';
    }
    html += '</div></div>';
  } else {
    html += '<div class="ar-section"><div class="ar-section-title">Anomalies</div><div class="ar-section-body"><div class="ar-empty" style="padding:12px;">No anomalies detected. All machines operating normally.</div></div></div>';
  }

  // ── Machine Issue Breakdown ──
  html += '<div class="ar-section">';
  html += '<div class="ar-section-title">Machine Status Breakdown</div>';
  html += '<div class="ar-section-body">';

  const sortedNames = [...machineNames].sort((a, b) => {
    const countA = getMachineIssueWeight(a);
    const countB = getMachineIssueWeight(b);
    return countB - countA;
  });

  sortedNames.forEach(name => {
    const md = ALL_MACHINE_DATA[name];
    const slots = md.slots || {};
    const slotIds = Object.keys(slots);
    const running = slotIds.filter(k => effectiveSlotState(name, k, slots[k]) === 'BDR_RUNNING').length;
    const passed = slotIds.filter(k => effectiveSlotState(name, k, slots[k]) === 'PASSED').length;
    const failed = slotIds.filter(k => effectiveSlotState(name, k, slots[k]) === 'FAILED').length;
    const empty = slotIds.filter(k => !slots[k].serial_number || slots[k].serial_number === '--' || slots[k].serial_number === 'N/A').length;
    const total = slotIds.length;

    let issueTags = '';
    if (failed > 0) issueTags += '<span class="ar-badge critical">' + failed + ' failed</span> ';
    if (empty === total) issueTags += '<span class="ar-badge medium">all empty</span> ';

    const machineAnomalies = allAnomalies.filter(a => a.machine === name || !a.machine);
    if (machineAnomalies.length > 0) issueTags += '<span class="ar-badge high">' + machineAnomalies.length + ' anomalies</span> ';

    html += '<div class="ar-item">';
    html += '<div class="ar-item-left">';
    html += '<span class="ar-machine-name">' + name.toUpperCase() + '</span>';
    html += '<span class="ar-machine-slots">' + running + '/' + total + ' running</span>';
    html += '</div>';
    html += '<div class="ar-item-right">' + issueTags + '</div>';
    html += '</div>';
  });

  html += '</div></div>';

  // ── Machines Needing Attention ──
  const attentionMachines = sortedNames.filter(name => {
    const md = ALL_MACHINE_DATA[name];
    const slots = md.slots || {};
    const slotIds = Object.keys(slots);
    const failed = slotIds.filter(k => effectiveSlotState(name, k, slots[k]) === 'FAILED').length;
    const empty = slotIds.filter(k => !slots[k].serial_number || slots[k].serial_number === '--' || slots[k].serial_number === 'N/A').length;
    const machineAnomalies = allAnomalies.filter(a => a.machine === name || !a.machine);
    return failed > 0 || (empty < slotIds.length && machineAnomalies.length > 0);
  });

  if (attentionMachines.length > 0) {
    html += '<div class="ar-section">';
    html += '<div class="ar-section-title" style="color:var(--danger);">Machines Requiring Attention</div>';
    html += '<div class="ar-section-body">';
    attentionMachines.slice(0, 10).forEach(name => {
      const md = ALL_MACHINE_DATA[name];
      const slots = md.slots || {};
      const slotIds = Object.keys(slots);
      const failed = slotIds.filter(k => effectiveSlotState(name, k, slots[k]) === 'FAILED').length;
      const machineAnomalies = allAnomalies.filter(a => a.machine === name || !a.machine);
      const reasons = [];
      if (failed > 0) reasons.push(failed + ' failed slots');
      if (machineAnomalies.length > 0) reasons.push(machineAnomalies.length + ' anomalies');

      html += '<div class="ar-item">';
      html += '<div class="ar-item-left">';
      html += '<span class="ar-badge critical">!</span>';
      html += '<span class="ar-machine-name">' + name.toUpperCase() + '</span>';
      html += '</div>';
      html += '<div class="ar-item-right" style="font-size:11px;color:var(--danger);">' + reasons.join(', ') + '</div>';
      html += '</div>';
    });
    if (attentionMachines.length > 10) {
      html += '<div style="text-align:center;padding:8px;color:var(--muted);font-size:11px;">... and ' + (attentionMachines.length - 10) + ' more</div>';
    }
    html += '</div></div>';
  }

  // ── Footer ──
  const now = new Date();
  html += '<div style="text-align:center;padding:8px;color:var(--muted);font-size:10px;">Report generated ' + now.toLocaleString() + ' &mdash; Data from BDR Dashboard</div>';

  return html;
}

function getMachineIssueWeight(name) {
  const md = ALL_MACHINE_DATA[name];
  if (!md) return 0;
  const slots = md.slots || {};
  const slotIds = Object.keys(slots);
  const anomalies = (typeof spotlightAnomalies !== 'undefined') ? spotlightAnomalies.filter(a => a.machine === name || !a.machine).length : 0;

  // Build per-function ring lookup for issue weight
  var rp = {}, rf = {};
  if (typeof ringsData !== 'undefined' && ringsData && ringsData.length > 0) {
    ringsData.forEach(function(rd) {
      var rs = (rd.state || '').toUpperCase();
      var key = rd.file + '|' + rd.slot;
      if (rs === 'PASSED' || rs === 'PASS') rp[key] = true;
      else if (rs === 'FAILED' || rs === 'FAIL') rf[key] = true;
    });
  }
  function effState(n, sid, s) {
    var key = n + '|' + sid;
    if (rp[key]) return 'PASSED';
    if (rf[key]) return 'FAILED';
    return s.state || '';
  }

  let weight = anomalies * 5;
  slotIds.forEach(k => {
    const s = slots[k];
    const sn = (s.serial_number || '').toString().trim();
    if (!sn || sn === '--' || sn === 'N/A') { weight += 1; return; }
    var es = effState(name, k, s);
    if (es === 'PASSED') return;
    if (es === 'FAILED') { weight += 10; return; }
    const bdr = s.bdr_state || {};
    if (s.dead_state && String(s.dead_state).trim() !== '') { weight += 8; return; }
    if ((bdr.consecutive_failures || 0) >= 3) { weight += 8; return; }
    if ((s.discharge_connect_failures || 0) > 3) { weight += 5; return; }
    if (s.bdr_clock_health === 'NOK' || (s.bdr_clock_health_pct || 100) < 50) { weight += 5; return; }
    if (s.error && String(s.error).trim() !== '') { weight += 3; return; }
  });
  return weight;
}

// Update badge when data changes
const _origInit = init;
init = function() {
  _origInit.apply(this, arguments);
  updateReportBadge();
};
const _origRingsRender = ringsRenderGrid;
ringsRenderGrid = function() {
  _origRingsRender.apply(this, arguments);
  updateReportBadge();
};

// ═══════════════════════════════════════════════════════════════════
//  DIAGNOSTICS VIEW
// ═══════════════════════════════════════════════════════════════════

let _diagMachine = null;
let _diagConnected = false;
let _diagMonitorTimer = null;
let _diagMonitorActive = false;

function openDiagnostics(machineName) {
  _diagMachine = machineName;
  _diagConnected = false;

  document.getElementById('diag-machine-name').textContent = machineName;
  document.getElementById('diag-connection-status').textContent = 'Not Connected';
  document.getElementById('diag-connection-status').className = 'badge neutral';
  document.getElementById('diag-connect-btn').style.display = 'inline-flex';
  document.getElementById('diag-live-dot').style.background = '#6B7280';
  document.getElementById('diag-live-label').textContent = 'Stopped';
  document.getElementById('diag-monitor-btn').textContent = 'Start';
  document.getElementById('diag-results-card').style.display = 'none';
  document.getElementById('diag-scan-summary').textContent = '';
  document.getElementById('diag-led-result').textContent = '';
  document.getElementById('diag-read-result').textContent = '';
  diagStopMonitor();
  diagStopLogMonitor();
  diagClearLiveLogs();
  renderDiagGrid([]);
  switchView('diagnostics');
  const sel = document.getElementById('diag-selection-screen');
  const ctrl = document.getElementById('diag-controls-screen');
  if (sel) sel.style.display = 'none';
  if (ctrl) ctrl.style.display = 'flex';
}

function closeDiagnostics() {
  diagStopMonitor();
  _diagMachine = null;
  switchView('bdr');
  const sel = document.getElementById('diag-selection-screen');
  const ctrl = document.getElementById('diag-controls-screen');
  if (sel) sel.style.display = 'flex';
  if (ctrl) ctrl.style.display = 'none';
}

function renderDiagGrid(data) {
  const grid = document.getElementById('diag-button-grid');
  if (grid) {
    grid.innerHTML = '';
    for (let i = 1; i <= 64; i++) {
      const cell = document.createElement('div');
      cell.className = 'slot-cell';
      cell.id = 'diag-cell-' + i;
      cell.textContent = i;
      cell.style.cssText = 'aspect-ratio:1;border-radius:4px;display:flex;align-items:center;justify-content:center;font-size:9px;font-weight:700;cursor:default;border:1px solid var(--border);background:var(--slot-empty-bg);color:var(--slot-empty-color);transition:background 0.15s;';
      grid.appendChild(cell);
    }
  }
  diagUpdateGrid(data);
}

function diagUpdateGrid(data) {
  for (let i = 1; i <= 64; i++) {
    const cell = document.getElementById('diag-cell-' + i);
    if (!cell) continue;
    const entry = data && data[i];
    if (!entry) {
      cell.style.background = 'var(--slot-empty-bg)';
      cell.style.color = 'var(--slot-empty-color)';
      cell.style.borderColor = 'var(--border)';
    } else if (entry.state === 'pressed') {
      cell.style.background = '#EF4444';
      cell.style.color = '#fff';
      cell.style.borderColor = '#DC2626';
    } else if (entry.state === 'released') {
      cell.style.background = '#22C55E';
      cell.style.color = '#fff';
      cell.style.borderColor = '#16A34A';
    } else {
      cell.style.background = '#F59E0B';
      cell.style.color = '#fff';
      cell.style.borderColor = '#D97706';
    }
  }
}

async function diagConnect() {
  const name = _diagMachine;
  if (!name) return;
  const btn = document.getElementById('diag-connect-btn');
  const statusEl = document.getElementById('diag-connection-status');
  btn.disabled = true;
  btn.textContent = 'Connecting...';
  statusEl.textContent = 'Connecting...';
  statusEl.className = 'badge warn';
  try {
    const res = await fetch('/api/machine/' + encodeURIComponent(name) + '/diagnose/connect', { method: 'POST', cache: 'no-store' });
    const data = await res.json();
    if (data && data.ok) {
      _diagConnected = true;
      statusEl.textContent = 'Connected to ' + (data.hostname || name);
      statusEl.className = 'badge ok';
      btn.style.display = 'none';
      diagQuickScan();
    } else {
      statusEl.textContent = 'Failed: ' + ((data && (data.error || data.detail)) || 'Unknown error');
      statusEl.className = 'badge danger';
    }
  } catch (err) {
    statusEl.textContent = 'Error: ' + err.message;
    statusEl.className = 'badge danger';
  } finally {
    btn.disabled = false;
    btn.textContent = 'Connect';
  }
}

async function diagQuickScan() {
  const name = _diagMachine;
  if (!name) return;
  const summary = document.getElementById('diag-scan-summary');
  summary.textContent = 'Scanning...';
  try {
    const res = await fetch('/api/machine/' + encodeURIComponent(name) + '/diagnose/scan', { method: 'POST', cache: 'no-store' });
    const data = await res.json();
    if (data && data.ok && data.grid) {
      const lookup = {};
      let pressed = 0;
      for (let m = 0; m < data.grid.length; m++) {
        const row = data.grid[m];
        for (let c = 0; c < row.length; c++) {
          const cell = row[c];
          lookup[cell.location] = cell;
          if (cell.state === 'pressed') pressed++;
        }
      }
      diagUpdateGrid(lookup);
      summary.textContent = pressed + ' pressed, ' + (64 - pressed) + ' released';
    } else {
      summary.textContent = 'Scan failed: ' + ((data && (data.error || data.detail)) || 'Unknown error');
    }
    diagShowResults(data);
  } catch (err) {
    summary.textContent = 'Error: ' + err.message;
  }
}

async function diagToggleMonitor() {
  if (_diagMonitorActive) {
    diagStopMonitor();
    return;
  }
  const name = _diagMachine;
  if (!name) return;
  _diagMonitorActive = true;
  const btn = document.getElementById('diag-monitor-btn');
  const dot = document.getElementById('diag-live-dot');
  const label = document.getElementById('diag-live-label');
  btn.textContent = 'Stop';
  dot.style.background = '#22C55E';
  label.textContent = 'Live';

  async function poll() {
    if (!_diagMonitorActive) return;
    try {
      const res = await fetch('/api/machine/' + encodeURIComponent(name) + '/diagnose/scan', { method: 'POST', cache: 'no-store' });
      const data = await res.json();
      if (data && data.ok && data.grid) {
        const lookup = {};
        for (let m = 0; m < data.grid.length; m++) {
          const row = data.grid[m];
          for (let c = 0; c < row.length; c++) {
            lookup[row[c].location] = row[c];
          }
        }
        diagUpdateGrid(lookup);
        const summary = document.getElementById('diag-scan-summary');
        if (summary) {
          const pressedCount = Object.values(lookup).filter(v => v.state === 'pressed').length;
          summary.textContent = pressedCount + ' pressed, ' + (64 - pressedCount) + ' released (live)';
        }
      }
    } catch (err) {
      console.warn('Monitor poll error:', err);
    }
    if (_diagMonitorActive) {
      _diagMonitorTimer = setTimeout(poll, 1000);
    }
  }
  poll();
}

function diagStopMonitor() {
  _diagMonitorActive = false;
  if (_diagMonitorTimer) {
    clearTimeout(_diagMonitorTimer);
    _diagMonitorTimer = null;
  }
  const btn = document.getElementById('diag-monitor-btn');
  const dot = document.getElementById('diag-live-dot');
  const label = document.getElementById('diag-live-label');
  if (btn) btn.textContent = 'Start';
  if (dot) dot.style.background = '#6B7280';
  if (label) label.textContent = 'Stopped';
}

function diagLedSet(colorName) {
  const picker = document.getElementById('diag-led-color');
  const colorMap = { red: '#ff0000', green: '#00ff00', blue: '#0000ff', yellow: '#ffff00', purple: '#800080', cyan: '#00ffff', white: '#ffffff' };
  if (colorMap[colorName]) picker.value = colorMap[colorName];
}

async function diagLedAction(action) {
  const name = _diagMachine;
  if (!name) return;
  const resultEl = document.getElementById('diag-led-result');
  resultEl.textContent = 'Sending...';
  try {
    const slot = document.getElementById('diag-led-slot').value;
    const colorHex = document.getElementById('diag-led-color').value;
    const r = parseInt(colorHex.slice(1,3), 16);
    const g = parseInt(colorHex.slice(3,5), 16);
    const b = parseInt(colorHex.slice(5,7), 16);
    const namedColors = { '255,0,0':'red','0,255,0':'green','0,0,255':'blue','255,255,0':'yellow','128,0,128':'purple','0,255,255':'cyan','255,255,255':'white','0,0,0':'off' };
    const key = r + ',' + g + ',' + b;
    const colorName = namedColors[key] || null;

    const params = new URLSearchParams();
    if (action === 'set') params.set('slot', slot);
    if (colorName) params.set('color', colorName);
    if (!colorName && (action === 'set' || action === 'fill')) {
      if (action === 'set') { params.set('r', r); params.set('g', g); params.set('b', b); }
      if (action === 'fill') { params.set('color', 'custom'); params.set('r', r); params.set('g', g); params.set('b', b); }
    }

    const url = '/api/machine/' + encodeURIComponent(name) + '/diagnose/led/' + action + (params.toString() ? '?' + params.toString() : '');
    const res = await fetch(url, { method: 'POST', cache: 'no-store' });
    const data = await res.json();
    if (data && data.ok) {
      resultEl.textContent = action + ': OK';
    } else {
      resultEl.textContent = action + ': ' + ((data && (data.error || data.detail)) || 'Failed');
    }
    diagShowResults(data);
  } catch (err) {
    resultEl.textContent = 'Error: ' + err.message;
  }
}

async function diagFullDiagnostics() {
  const name = _diagMachine;
  if (!name) return;
  diagShowResults({ status: 'running', message: 'Running full diagnostics...' });
  try {
    const res = await fetch('/api/machine/' + encodeURIComponent(name) + '/diagnose/full', { method: 'POST', cache: 'no-store' });
    const data = await res.json();
    diagShowResults(data);
  } catch (err) {
    diagShowResults({ error: err.message });
  }
}

async function diagMotorStatus() {
  const name = _diagMachine;
  if (!name) return;
  diagShowResults({ status: 'running', message: 'Checking motor status...' });
  try {
    const res = await fetch('/api/machine/' + encodeURIComponent(name) + '/diagnose/motor', { cache: 'no-store' });
    const data = await res.json();
    diagShowResults(data);
  } catch (err) {
    diagShowResults({ error: err.message });
  }
}

async function diagTroubleshoot(fix) {
  const name = _diagMachine;
  if (!name) return;
  const fixLabels = { reconfigure_mcps: 'Reconfiguring MCPs...', kill_conflicts: 'Killing conflicting processes...' };
  diagShowResults({ status: 'running', message: fixLabels[fix] || 'Running...' });
  try {
    const res = await fetch('/api/machine/' + encodeURIComponent(name) + '/diagnose/troubleshoot/' + fix, { method: 'POST', cache: 'no-store' });
    const data = await res.json();
    diagShowResults(data);
  } catch (err) {
    diagShowResults({ error: err.message });
  }
}

async function diagReadLocation() {
  const name = _diagMachine;
  if (!name) return;
  const slot = document.getElementById('diag-read-loc').value;
  const resultEl = document.getElementById('diag-read-result');
  resultEl.textContent = 'Reading...';
  try {
    const res = await fetch('/api/machine/' + encodeURIComponent(name) + '/diagnose/location/' + slot, { cache: 'no-store' });
    const data = await res.json();
    if (data && data.ok) {
      resultEl.textContent = 'Location ' + slot + ': ' + data.state.toUpperCase();
      resultEl.style.color = data.state === 'pressed' ? '#EF4444' : '#22C55E';
    } else {
      resultEl.textContent = 'Error: ' + ((data && (data.error || data.detail)) || 'Failed');
      resultEl.style.color = 'var(--muted)';
    }
    diagShowResults(data);
  } catch (err) {
    resultEl.textContent = 'Error: ' + err.message;
  }
}

function diagShowResults(data) {
  const card = document.getElementById('diag-results-card');
  const pre = document.getElementById('diag-results');
  if (!card || !pre) return;
  card.style.display = 'block';
  pre.textContent = JSON.stringify(data, null, 2);
}

function diagClearResults() {
  const card = document.getElementById('diag-results-card');
  const pre = document.getElementById('diag-results');
  if (card) card.style.display = 'none';
  if (pre) pre.textContent = '';
}

// ═══════════════════════════════════════════════════════════════════
//  DIAGNOSTICS - LIVE LOG MONITOR
// ═══════════════════════════════════════════════════════════════════

let _diagLogMonitorActive = false;
let _diagLogMonitorTimer = null;
let _diagLogEntries = []; // Array to store all log entries
const _diagLogPollInterval = 2000; // 2 seconds

async function diagToggleLogMonitor() {
  if (_diagLogMonitorActive) {
    diagStopLogMonitor();
    return;
  }
  const name = _diagMachine;
  if (!name) return;
  _diagLogMonitorActive = true;
  const btn = document.getElementById('diag-log-toggle-btn');
  const status = document.getElementById('diag-log-status');
  btn.textContent = 'Stop';
  status.textContent = 'Live';

  async function poll() {
    if (!_diagLogMonitorActive) return;
    try {
      const res = await fetch('/api/machine/' + encodeURIComponent(name) + '/diagnose/logs?lines=300', { cache: 'no-store' });
      const data = await res.json();
      if (data && data.ok && data.entries) {
        // Merge new entries with existing ones, avoiding duplicates
        const existingTimestamps = new Set(_diagLogEntries.map(e => e.timestamp + '|' + e.line));
        for (const entry of data.entries) {
          const key = entry.timestamp + '|' + entry.line;
          if (!existingTimestamps.has(key)) {
            _diagLogEntries.push(entry);
            existingTimestamps.add(key);
          }
        }
        // Sort all entries by timestamp
        _diagLogEntries.sort((a, b) => {
          if (a.timestamp === null && b.timestamp === null) return 0;
          if (a.timestamp === null) return 1;
          if (b.timestamp === null) return -1;
          return a.timestamp - b.timestamp;
        });
        // Render the logs
        diagRenderLiveLogs();
      }
    } catch (err) {
      console.warn('Live log poll error:', err);
    }
    if (_diagLogMonitorActive) {
      _diagLogMonitorTimer = setTimeout(poll, _diagLogPollInterval);
    }
  }
  poll();
}

function diagStopLogMonitor() {
  _diagLogMonitorActive = false;
  if (_diagLogMonitorTimer) {
    clearTimeout(_diagLogMonitorTimer);
    _diagLogMonitorTimer = null;
  }
  const btn = document.getElementById('diag-log-toggle-btn');
  const status = document.getElementById('diag-log-status');
  if (btn) btn.textContent = 'Start';
  if (status) status.textContent = 'Stopped';
}

function diagClearLiveLogs() {
  _diagLogEntries = [];
  diagRenderLiveLogs();
}

function diagRenderLiveLogs() {
  const container = document.getElementById('diag-live-log');
  if (!container) return;
  container.innerHTML = '';
  if (_diagLogEntries.length === 0) {
    container.innerHTML = '<div style="color:#6b7280;font-size:12px;">No log entries yet</div>';
    return;
  }
  // Render each log entry as a separate line
  for (const entry of _diagLogEntries) {
    const lineEl = document.createElement('div');
    lineEl.style.cssText = 'font-family:"JetBrains Mono","Fira Code",monospace;font-size:11px;line-height:1.6;padding:2px 0;border-bottom:1px solid rgba(255,255,255,0.05);color:#e2e8f0;word-break:break-all;';
    lineEl.textContent = entry.line;
    // Colorize based on log level if present
    const lineLower = entry.line.toLowerCase();
    if (lineLower.includes('error') || lineLower.includes('fail') || lineLower.includes('critical')) {
      lineEl.style.color = '#f87171';
    } else if (lineLower.includes('warn') || lineLower.includes('warning')) {
      lineEl.style.color = '#fbbf24';
    } else if (lineLower.includes('info')) {
      lineEl.style.color = '#60a5fa';
    } else if (lineLower.includes('debug')) {
      lineEl.style.color = '#a78bfa';
    }
    container.appendChild(lineEl);
  }
  // Only auto-scroll if user is already near the bottom
  const threshold = 50;
  const isAtBottom = (container.scrollHeight - container.scrollTop) <= (container.clientHeight + threshold);
  if (isAtBottom) {
    container.scrollTop = container.scrollHeight;
  }
}

// Make sure to stop log monitor when closing diagnostics
const _origCloseDiagnostics = closeDiagnostics;
closeDiagnostics = function() {
  diagStopLogMonitor();
  _origCloseDiagnostics.apply(this, arguments);
};

// ═══════════════════════════════════════════════════════════════════
//  DIAGNOSTICS - BLUETOOTH
// ═══════════════════════════════════════════════════════════════════

async function diagBt(action) {
  const name = _diagMachine;
  if (!name) return;
  const labels = {
    status: 'Getting Bluetooth status...',
    diagnose: 'Running Bluetooth diagnosis...',
    scan: 'Scanning for BLE devices...',
    reset: 'Resetting Bluetooth adapter...',
    'full-reset': 'Performing full Bluetooth reset...',
    recover: 'Running Bluetooth recovery...',
  };
  diagShowResults({ status: 'running', message: labels[action] || 'Running...' });
  try {
    const url = '/api/machine/' + encodeURIComponent(name) + '/diagnose/bt/' + action;
    const opts = action === 'status' ? { cache: 'no-store' } : { method: 'POST', cache: 'no-store' };
    const res = await fetch(url, opts);
    const data = await res.json();
    diagShowResults(data);
  } catch (err) {
    diagShowResults({ error: err.message });
  }
}

// ═══════════════════════════════════════════════════════════════════
//  DIAGNOSTICS - NEW FEATURES (MCP, AUDIT, BT EXTRA)
// ═══════════════════════════════════════════════════════════════════

async function diagAudit() {
  const name = _diagMachine;
  if (!name) return;
  diagShowResults({ status: 'running', message: 'Running folder audit...' });
  try {
    const res = await fetch('/api/machine/' + encodeURIComponent(name) + '/diagnose/audit', { method: 'POST', cache: 'no-store' });
    const data = await res.json();
    diagShowResults(data);
  } catch (err) {
    diagShowResults({ error: err.message });
  }
}

async function diagAuditProcesses() {
  const name = _diagMachine;
  if (!name) return;
  diagShowResults({ status: 'running', message: 'Listing processes...' });
  try {
    const res = await fetch('/api/machine/' + encodeURIComponent(name) + '/diagnose/audit/processes', { method: 'POST', cache: 'no-store' });
    const data = await res.json();
    diagShowResults(data);
  } catch (err) {
    diagShowResults({ error: err.message });
  }
}

async function diagAuditSystem() {
  const name = _diagMachine;
  if (!name) return;
  diagShowResults({ status: 'running', message: 'Checking system...' });
  try {
    const res = await fetch('/api/machine/' + encodeURIComponent(name) + '/diagnose/audit/system', { method: 'POST', cache: 'no-store' });
    const data = await res.json();
    diagShowResults(data);
  } catch (err) {
    diagShowResults({ error: err.message });
  }
}

async function diagMcpScan() {
  const name = _diagMachine;
  if (!name) return;
  diagShowResults({ status: 'running', message: 'Scanning MCP registers...' });
  try {
    const res = await fetch('/api/machine/' + encodeURIComponent(name) + '/diagnose/mcp/scan', { method: 'POST', cache: 'no-store' });
    const data = await res.json();
    diagShowResults(data);
  } catch (err) {
    diagShowResults({ error: err.message });
  }
}

async function diagMcpRepair() {
  const name = _diagMachine;
  if (!name) return;
  if (!confirm('Repair all MCP registers? This resets direction/pull-up config but preserves charger output state.')) return;
  diagShowResults({ status: 'running', message: 'Repairing MCP registers...' });
  try {
    const res = await fetch('/api/machine/' + encodeURIComponent(name) + '/diagnose/mcp/repair', { method: 'POST', cache: 'no-store' });
    const data = await res.json();
    diagShowResults(data);
  } catch (err) {
    diagShowResults({ error: err.message });
  }
}

async function diagMcpAdvancedRepair() {
  const name = _diagMachine;
  if (!name) return;
  if (!confirm('Advanced safe MCP repair: only writes registers that differ from expected values. Continue?')) return;
  diagShowResults({ status: 'running', message: 'Running advanced MCP repair...' });
  try {
    const res = await fetch('/api/machine/' + encodeURIComponent(name) + '/diagnose/mcp/advanced-repair', { method: 'POST', cache: 'no-store' });
    const data = await res.json();
    diagShowResults(data);
  } catch (err) {
    diagShowResults({ error: err.message });
  }
}

async function diagButtonAdvancedRepair() {
  const name = _diagMachine;
  if (!name) return;
  if (!confirm('Advanced safe button/MCP repair: only writes registers that differ. Continue?')) return;
  diagShowResults({ status: 'running', message: 'Running advanced button repair...' });
  try {
    const res = await fetch('/api/machine/' + encodeURIComponent(name) + '/diagnose/button/advanced-repair', { method: 'POST', cache: 'no-store' });
    const data = await res.json();
    diagShowResults(data);
  } catch (err) {
    diagShowResults({ error: err.message });
  }
}

async function diagLedRestore() {
  const name = _diagMachine;
  if (!name) return;
  const resultEl = document.getElementById('diag-led-result');
  resultEl.textContent = 'Restoring...';
  try {
    const res = await fetch('/api/machine/' + encodeURIComponent(name) + '/diagnose/led/restore', { method: 'POST', cache: 'no-store' });
    const data = await res.json();
    if (data && data.ok) {
      resultEl.textContent = 'Restore: OK (brightness=' + (data.brightness || '?') + ')';
    } else {
      resultEl.textContent = 'Restore: ' + ((data && (data.error || data.detail)) || 'Failed');
    }
    diagShowResults(data);
  } catch (err) {
    resultEl.textContent = 'Error: ' + err.message;
  }
}

async function diagLedDiagnose() {
  const name = _diagMachine;
  if (!name) return;
  const resultEl = document.getElementById('diag-led-result');
  resultEl.textContent = 'Running LED diagnosis...';
  diagShowResults({ status: 'running', message: 'Running full LED diagnosis (test + restore)...' });
  try {
    const res = await fetch('/api/machine/' + encodeURIComponent(name) + '/diagnose/led/diagnose?deep=true', { method: 'POST', cache: 'no-store' });
    const data = await res.json();
    if (data && data.ok) {
      resultEl.textContent = 'Diagnose: OK';
    } else {
      resultEl.textContent = 'Diagnose: ' + ((data && (data.error || data.detail)) || 'Failed');
    }
    diagShowResults(data);
  } catch (err) {
    resultEl.textContent = 'Error: ' + err.message;
  }
}

async function diagKillConflicts() {
  const name = _diagMachine;
  if (!name) return;
  if (!confirm('Kill conflicting processes (assembly_test_app, device_daemon)?')) return;
  diagShowResults({ status: 'running', message: 'Killing conflicting processes...' });
  try {
    const res = await fetch('/api/machine/' + encodeURIComponent(name) + '/diagnose/kill-conflicts', { method: 'POST', cache: 'no-store' });
    const data = await res.json();
    diagShowResults(data);
  } catch (err) {
    diagShowResults({ error: err.message });
  }
}

async function diagBtConnectionCheck() {
  const name = _diagMachine;
  if (!name) return;
  diagShowResults({ status: 'running', message: 'Running Bluetooth connection check...' });
  try {
    const res = await fetch('/api/machine/' + encodeURIComponent(name) + '/diagnose/bt/connection-check', { method: 'POST', cache: 'no-store' });
    const data = await res.json();
    diagShowResults(data);
  } catch (err) {
    diagShowResults({ error: err.message });
  }
}

async function diagBtLiveLog() {
  const name = _diagMachine;
  if (!name) return;
  diagShowResults({ status: 'running', message: 'Starting Bluetooth live log (streaming for 120s)...' });
  try {
    const res = await fetch('/api/machine/' + encodeURIComponent(name) + '/diagnose/bt/live-log?duration=120&lines=120', { method: 'POST', cache: 'no-store' });
    const data = await res.json();
    diagShowResults(data);
  } catch (err) {
    diagShowResults({ error: err.message });
  }
}

async function diagBtFixCrashLoop() {
  const name = _diagMachine;
  if (!name) return;
  if (!confirm('Fix Bluetooth crash-loop? This may briefly drop current BLE connections but does not modify app data.')) return;
  diagShowResults({ status: 'running', message: 'Fixing Bluetooth crash loop...' });
  try {
    const res = await fetch('/api/machine/' + encodeURIComponent(name) + '/diagnose/bt/fix-crash-loop', { method: 'POST', cache: 'no-store' });
    const data = await res.json();
    diagShowResults(data);
  } catch (err) {
    diagShowResults({ error: err.message });
  }
}

async function diagBtFixPairingPopup() {
  const name = _diagMachine;
  if (!name) return;
  if (!confirm('Fix Bluetooth pairing popup? This writes a temporary NoInputNoOutput agent under /tmp (no systemd service).')) return;
  diagShowResults({ status: 'running', message: 'Fixing pairing popup (safe)...' });
  try {
    const res = await fetch('/api/machine/' + encodeURIComponent(name) + '/diagnose/bt/fix-pairing-popup', { method: 'POST', cache: 'no-store' });
    const data = await res.json();
    diagShowResults(data);
  } catch (err) {
    diagShowResults({ error: err.message });
  }
}

async function diagBtFixPairingPopupPersistent() {
  const name = _diagMachine;
  if (!name) return;
  if (!confirm('Install persistent systemd service for NoInputNoOutput pairing agent? Only use on trusted factory machines.')) return;
  diagShowResults({ status: 'running', message: 'Installing persistent pairing agent...' });
  try {
    const res = await fetch('/api/machine/' + encodeURIComponent(name) + '/diagnose/bt/fix-pairing-popup-persistent', { method: 'POST', cache: 'no-store' });
    const data = await res.json();
    diagShowResults(data);
  } catch (err) {
    diagShowResults({ error: err.message });
  }
}

/* =========================================================================
   COMMAND PALETTE LOGIC
   ========================================================================= */

function toggleCommandPalette() {
    const overlay = document.getElementById('command-palette-overlay');
    if (!overlay) return;
    const isVisible = overlay.classList.contains('visible');
    
    if (isVisible) {
        overlay.classList.remove('visible');
    } else {
        overlay.classList.add('visible');
        const input = document.getElementById('cmd-palette-input');
        if (input) {
            input.value = '';
            setTimeout(() => input.focus(), 50);
            filterCommandPalette();
        }
    }
}

function filterCommandPalette() {
    const input = document.getElementById('cmd-palette-input');
    const resultsContainer = document.getElementById('cmd-palette-results');
    if (!input || !resultsContainer) return;
    
    const query = input.value.toLowerCase().trim();
    resultsContainer.innerHTML = '';
    
    let results = [];
    
    // Commands
    results.push({ type: 'command', title: 'Open Operations Queue', sub: 'Workspace', action: () => switchView('bdr'), icon: '<svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2"><path d="M4 6h16M4 12h16M4 18h7"/></svg>' });
    results.push({ type: 'command', title: 'Open Machine Workspace', sub: 'Workspace', action: () => switchView('rings'), icon: '<svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="3" width="7" height="7"/><rect x="14" y="3" width="7" height="7"/><rect x="14" y="14" width="7" height="7"/><rect x="3" y="14" width="7" height="7"/></svg>' });
    
    // Filter and Render
    const filtered = query ? results.filter(r => r.title.toLowerCase().includes(query) || r.sub.toLowerCase().includes(query)) : results;
    
    if (filtered.length === 0) {
        resultsContainer.innerHTML = '<div style="padding:16px; text-align:center; color:var(--muted); font-size:12px;">No results found</div>';
        return;
    }
    
    filtered.forEach((r, idx) => {
        const div = document.createElement('div');
        div.className = 'cmd-result-item' + (idx === 0 ? ' selected' : '');
        div.innerHTML = `
            <div class="cmd-result-icon">${r.icon || ''}</div>
            <div class="cmd-result-content">
                <div class="cmd-result-title">${r.title}</div>
                <div class="cmd-result-subtitle">${r.sub}</div>
            </div>
        `;
        div.onclick = () => {
            toggleCommandPalette();
            r.action();
        };
        resultsContainer.appendChild(div);
    });
}

// Global Keyboard Listeners
document.addEventListener('keydown', (e) => {
    // Ctrl+K
    if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
        e.preventDefault();
        toggleCommandPalette();
    }
    
    // ESC
    if (e.key === 'Escape') {
        const overlay = document.getElementById('command-palette-overlay');
        if (overlay && overlay.classList.contains('visible')) {
            toggleCommandPalette();
        }
    }
    
    // Enter (execute selected)
    if (e.key === 'Enter') {
        const overlay = document.getElementById('command-palette-overlay');
        if (overlay && overlay.classList.contains('visible')) {
            const selected = document.querySelector('.cmd-result-item.selected');
            if (selected) {
                selected.click();
            }
        }
    }
});
