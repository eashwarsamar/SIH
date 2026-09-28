/**
 * SIH26012 Platform - Topology Warning Center Controller
 * Manages bottom collapsible tray, severity badges, filtering, and click-to-zoom.
 */

export class WarningCenter {
  constructor(containerId, options = {}) {
    this.container = document.getElementById(containerId);
    this.onWarningClick = options.onWarningClick || (() => {});
    this.allWarnings = [];
    this.currentFilter = 'all'; // 'all' | 'synthetic' | 'real'
    this.isExpanded = false;
  }

  setWarnings(warnings) {
    this.allWarnings = warnings || [];
    this.render();
  }

  toggleExpand() {
    this.isExpanded = !this.isExpanded;
    this.render();
  }

  render() {
    const total = this.allWarnings.length;
    const synthCount = this.allWarnings.filter(w => w.source && w.source.includes('synthetic')).length;
    const realCount = total - synthCount;

    let filtered = this.allWarnings;
    if (this.currentFilter === 'synthetic') {
      filtered = this.allWarnings.filter(w => w.source && w.source.includes('synthetic'));
    } else if (this.currentFilter === 'real') {
      filtered = this.allWarnings.filter(w => !w.source || !w.source.includes('synthetic'));
    }

    this.container.innerHTML = `
      <div class="warning-tray-header" id="warning-header-toggle">
        <div class="warning-tray-title">
          <span>⚠️ Topology Warning Center</span>
          <span class="warning-counter-badge">${total} Active</span>
        </div>
        <div style="display: flex; align-items: center; gap: 8px;">
          <!-- Filter Tabs -->
          <div style="display: flex; gap: 4px; margin-right: 12px;">
            <button class="btn btn-secondary ${this.currentFilter === 'all' ? 'active' : ''}" id="filter-warn-all" style="padding: 2px 8px; font-size: 10px;">All (${total})</button>
            <button class="btn btn-secondary ${this.currentFilter === 'synthetic' ? 'active' : ''}" id="filter-warn-synth" style="padding: 2px 8px; font-size: 10px;">Synthetic Demos (${synthCount})</button>
            <button class="btn btn-secondary ${this.currentFilter === 'real' ? 'active' : ''}" id="filter-warn-real" style="padding: 2px 8px; font-size: 10px;">Real Overlaps (${realCount})</button>
          </div>
          <span style="font-size: 13px; color: var(--text-muted);">${this.isExpanded ? '▼ Hide' : '▲ Expand'}</span>
        </div>
      </div>

      ${this.isExpanded ? `
        <div class="warning-tray-body">
          ${filtered.length > 0 ? filtered.map(w => `
            <div class="warning-card severity-${w.severity}" data-wid="${w.warning_id}">
              <div class="warning-info">
                <div class="warning-title-line">
                  <span style="text-transform: capitalize;">${w.warning_type.replace(/_/g, ' ')}</span>
                  <span class="status-badge" style="background: rgba(255,255,255,0.08);">${w.severity}</span>
                  ${w.source && w.source.includes('synthetic') ? '<span class="badge-synth">DEMO FIXTURE</span>' : ''}
                </div>
                <div class="warning-desc">${w.explanation}</div>
                <div style="font-size: 10px; color: var(--text-faint); margin-top: 2px;">
                  Affected features: <strong>${w.feature_ids ? w.feature_ids.join(', ') : 'None'}</strong> | Rule: <em>${w.plain_language_rule || ''}</em>
                </div>
              </div>
              <button class="btn btn-primary btn-icon btn-zoom-warning" data-wid="${w.warning_id}">Zoom to Conflict 🔍</button>
            </div>
          `).join('') : '<div style="padding: 12px; color: var(--text-faint); text-align: center;">No warnings match this filter.</div>'}
        </div>
      ` : ''}
    `;

    // Bind event handlers
    const toggleHeader = document.getElementById('warning-header-toggle');
    if (toggleHeader) {
      toggleHeader.onclick = (e) => {
        if (e.target.closest('button')) return;
        this.toggleExpand();
      };
    }

    const btnAll = document.getElementById('filter-warn-all');
    const btnSynth = document.getElementById('filter-warn-synth');
    const btnReal = document.getElementById('filter-warn-real');

    if (btnAll) btnAll.onclick = (e) => { e.stopPropagation(); this.currentFilter = 'all'; this.isExpanded = true; this.render(); };
    if (btnSynth) btnSynth.onclick = (e) => { e.stopPropagation(); this.currentFilter = 'synthetic'; this.isExpanded = true; this.render(); };
    if (btnReal) btnReal.onclick = (e) => { e.stopPropagation(); this.currentFilter = 'real'; this.isExpanded = true; this.render(); };

    this.container.querySelectorAll('.btn-zoom-warning').forEach(btn => {
      btn.onclick = (e) => {
        e.stopPropagation();
        const wid = btn.getAttribute('data-wid');
        const warn = this.allWarnings.find(w => w.warning_id === wid);
        if (warn) this.onWarningClick(warn);
      };
    });
  }
}
