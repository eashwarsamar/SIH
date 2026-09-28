/**
 * SIH26012 Platform - AI Building Model & Benchmark Modals Controller
 */
import { ApiClient } from './api.js';

export class ModelModalController {
  constructor(options = {}) {
    this.onInferenceSuccess = options.onInferenceSuccess || (() => {});
    this.modelModal = document.getElementById('modal-ai-model');
    this.benchmarkModal = document.getElementById('modal-benchmarks');

    this.bindButtons();
  }

  bindButtons() {
    // Open inference modal button
    const btnOpenModel = document.getElementById('btn-open-model-modal');
    if (btnOpenModel) {
      btnOpenModel.onclick = () => this.openModelModal();
    }

    // Open benchmarks modal button
    const btnOpenBenchmarks = document.getElementById('btn-open-benchmark-modal');
    if (btnOpenBenchmarks) {
      btnOpenBenchmarks.onclick = () => this.openBenchmarkModal();
    }

    // Close buttons
    document.querySelectorAll('.modal-close-trigger').forEach(btn => {
      btn.onclick = () => this.closeModals();
    });

    // Run inference button
    const btnRunInference = document.getElementById('btn-run-inference');
    if (btnRunInference) {
      btnRunInference.onclick = () => this.executeInference();
    }
  }

  openModelModal() {
    this.modelModal.classList.add('active');
  }

  async openBenchmarkModal() {
    this.benchmarkModal.classList.add('active');
    const contentBox = document.getElementById('benchmark-content-area');
    if (contentBox) {
      contentBox.innerHTML = '<p>Loading registered benchmark specifications...</p>';
      try {
        const manifest = await ApiClient.getBenchmarks();
        const datasets = manifest.registered_datasets;
        contentBox.innerHTML = `
          <div style="background: rgba(245, 158, 11, 0.12); border: 1px solid rgba(245, 158, 11, 0.3); border-radius: 6px; padding: 10px; font-size: 11.5px; color: #fbbf24; margin-bottom: 12px;">
            ℹ️ ${manifest.disclaimer}
          </div>
          ${Object.entries(datasets).map(([key, d]) => `
            <div style="background: var(--bg-card); border: 1px solid var(--border-subtle); border-radius: 8px; padding: 12px; margin-bottom: 10px;">
              <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px;">
                <strong style="color: var(--accent-cyan); font-size: 13px;">${d.name}</strong>
                <span class="status-badge" style="background: rgba(244, 63, 94, 0.2); color: #fb7185;">${d.status}</span>
              </div>
              <div style="font-size: 11.5px; color: var(--text-muted); display: flex; flex-direction: column; gap: 4px;">
                <div>Resolution: <strong>${d.resolution}</strong> | Coverage: <strong>${d.coverage}</strong></div>
                <div>License: <strong>${d.license}</strong></div>
                <div>URL / Reference: <a href="${d.url}" target="_blank" style="color: var(--accent-cyan);">${d.url}</a></div>
                <div style="margin-top: 4px; background: rgba(0,0,0,0.3); padding: 6px; border-radius: 4px; font-family: var(--font-mono); font-size: 10.5px; color: #e2e8f0;">
                  ${d.download_method}
                </div>
                <div style="font-size: 10.5px; color: var(--text-faint); margin-top: 2px;">
                  <em>${d.status_details}</em>
                </div>
              </div>
            </div>
          `).join('')}
        `;
      } catch (err) {
        contentBox.innerHTML = `<p style="color: var(--accent-rose)">Failed to load benchmarks: ${err.message}</p>`;
      }
    }
  }

  closeModals() {
    this.modelModal.classList.remove('active');
    this.benchmarkModal.classList.remove('active');
  }

  async executeInference() {
    const modelSelect = document.getElementById('model-select');
    const confSlider = document.getElementById('model-conf-slider');
    const simulateFailureCheck = document.getElementById('model-simulate-failure');
    const statusBox = document.getElementById('model-inference-status');
    const btnRun = document.getElementById('btn-run-inference');

    const modelName = modelSelect ? modelSelect.value : 'Vaayu-UnetPP-Lite';
    const confThreshold = confSlider ? parseFloat(confSlider.value) : 0.5;
    const simulateFailure = simulateFailureCheck ? simulateFailureCheck.checked : false;

    btnRun.disabled = true;
    statusBox.innerHTML = `
      <div style="display: flex; align-items: center; gap: 8px; color: var(--accent-cyan);">
        <span>⚡ Executing inference forward pass (${modelName})...</span>
      </div>
    `;

    try {
      const result = await ApiClient.runModelInference(modelName, confThreshold, simulateFailure);
      statusBox.innerHTML = `
        <div style="color: var(--accent-emerald); font-weight: 500;">
          ✓ Inference Success! Extracted ${result.detected_count} building footprints.
          <div style="font-size: 11px; color: var(--text-muted); margin-top: 4px;">Features appended to active review layer with source="ai_building_model".</div>
        </div>
      `;
      btnRun.disabled = false;
      this.onInferenceSuccess(result);
    } catch (err) {
      statusBox.innerHTML = `
        <div style="color: var(--accent-rose); font-weight: 500;">
          ✕ Inference Failed (Handled Gracefully):
          <div style="font-size: 11px; margin-top: 4px;">${err.message}</div>
        </div>
      `;
      btnRun.disabled = false;
    }
  }
}
