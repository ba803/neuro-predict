/**
 * NeuroPredict — Assessment Client Controller
 * Manages 4-step user workflow, validation, Chart.js visualizations, and PDF downloads.
 */

// ===================================================================
// Backend API Configuration
// ===================================================================
// Set your production hosted backend URL here when deployed (e.g. Render, Koyeb, HF):
// Production Hosted Backend URL on Render
const BACKEND_URL = "https://neuro-predict-u43g.onrender.com";

/**
 * Dynamically resolves the API base URL:
 * 1. Checks runtime localStorage or window.API_URL overrides
 * 2. If running locally (localhost / 127.0.0.1), uses http://localhost:8000
 * 3. On production (e.g. GitHub Pages, mobile), connects to BACKEND_URL
 */
function resolveApiUrl() {
  if (typeof window !== "undefined") {
    if (window.API_URL && window.API_URL.trim() !== "") {
      return window.API_URL.replace(/\/+$/, "");
    }
    const stored = localStorage.getItem("NEURO_BACKEND_URL");
    if (stored && stored.trim() !== "") {
      return stored.replace(/\/+$/, "");
    }
  }

  // Local development check
  const hostname = window.location.hostname;
  const origin = window.location.origin;
  if (!origin || origin.startsWith("file:") || hostname === "localhost" || hostname === "127.0.0.1" || origin.includes(":3000") || origin.includes(":5500")) {
    return "http://localhost:8000";
  }

  // Production hosted backend URL
  return BACKEND_URL.replace(/\/+$/, "");
}

const API_URL = resolveApiUrl();

// Global Application State
let currentStep = 1;
let completedSteps = { 1: false, 2: false, 3: false, 4: false };
let assessmentResult = null;
let chartLikelihoodInstance = null;
let chartFactorsInstance = null;

// Preset Definitions (for quick testing only)
const TEST_PROFILES = {
  healthy: {
    Functional_Assessment_Score: 8.8,
    MMSE_Score: 28,
    ADL_Score: 9.0,
    Memory_Complaints: 0,
    Behavioral_Problems: 0
  },
  borderline: {
    Functional_Assessment_Score: 5.5,
    MMSE_Score: 22,
    ADL_Score: 5.5,
    Memory_Complaints: 1,
    Behavioral_Problems: 0
  },
  "high-risk": {
    Functional_Assessment_Score: 2.0,
    MMSE_Score: 12,
    ADL_Score: 2.2,
    Memory_Complaints: 1,
    Behavioral_Problems: 1
  }
};

// -------------------------------------------------------------------
// Initialization
// -------------------------------------------------------------------
document.addEventListener("DOMContentLoaded", () => {
  setupStepNavigation();
  setupTestProfiles();
  setupValidation();
  setupFormSubmission();
  setupReportActions();
});

// -------------------------------------------------------------------
// Step Navigation (4 Steps)
// -------------------------------------------------------------------
function setupStepNavigation() {
  // Allow clicking on completed steps in the progress bar
  document.getElementById("node-step-1").addEventListener("click", () => {
    goToStep(1);
  });

  document.getElementById("node-step-3").addEventListener("click", () => {
    if (completedSteps[3] || assessmentResult) {
      goToStep(3);
    }
  });

  document.getElementById("node-step-4").addEventListener("click", () => {
    if (completedSteps[4] || assessmentResult) {
      goToStep(4);
    }
  });

  // Edit details buttons
  const editButtons = ["btn-edit-details-1", "btn-edit-details-2", "btn-edit-details-3"];
  editButtons.forEach(id => {
    const el = document.getElementById(id);
    if (el) {
      el.addEventListener("click", () => {
        goToStep(1);
      });
    }
  });

  // Step 3 -> Step 4 navigation
  document.getElementById("btn-go-to-report").addEventListener("click", () => {
    goToStep(4);
  });

  // Step 4 -> Step 3 navigation
  document.getElementById("btn-back-to-results").addEventListener("click", () => {
    goToStep(3);
  });
}

function goToStep(step) {
  currentStep = step;

  // 1. Toggle Views
  document.querySelectorAll(".step-view").forEach(view => view.classList.add("hidden"));
  const activeView = document.getElementById(`view-step-${step}`);
  if (activeView) {
    activeView.classList.remove("hidden");
  }

  // 2. Update Progress Bar Nodes
  updateProgressTracker(step);

  // 3. Scroll to top of main container smoothly
  window.scrollTo({ top: 0, behavior: "smooth" });
}

function updateProgressTracker(activeStep) {
  for (let s = 1; s <= 4; s++) {
    const node = document.getElementById(`node-step-${s}`);
    if (!node) continue;

    node.classList.remove("active", "completed");

    if (s < activeStep || (completedSteps[s] && s !== activeStep)) {
      node.classList.add("completed");
      node.disabled = false;
    } else if (s === activeStep) {
      node.classList.add("active");
      node.disabled = false;
    } else {
      node.disabled = !completedSteps[s];
    }
  }

  // Connectors
  updateConnector("conn-1-2", completedSteps[1]);
  updateConnector("conn-2-3", completedSteps[2]);
  updateConnector("conn-3-4", completedSteps[3]);
}

function updateConnector(connId, isCompleted) {
  const conn = document.getElementById(connId);
  if (conn) {
    if (isCompleted) conn.classList.add("completed");
    else conn.classList.remove("completed");
  }
}

// -------------------------------------------------------------------
// Quick Test Profiles
// -------------------------------------------------------------------
function setupTestProfiles() {
  document.querySelectorAll(".btn-profile").forEach(btn => {
    btn.addEventListener("click", () => {
      const profileKey = btn.getAttribute("data-profile");
      const profileData = TEST_PROFILES[profileKey];
      if (!profileData) return;

      document.getElementById("input-fas").value = profileData.Functional_Assessment_Score;
      document.getElementById("input-mmse").value = profileData.MMSE_Score;
      document.getElementById("input-adl").value = profileData.ADL_Score;

      const memRadio = document.querySelector(`input[name="Memory_Complaints"][value="${profileData.Memory_Complaints}"]`);
      if (memRadio) memRadio.checked = true;

      const behRadio = document.querySelector(`input[name="Behavioral_Problems"][value="${profileData.Behavioral_Problems}"]`);
      if (behRadio) behRadio.checked = true;

      clearAllValidationErrors();
      showFeedback(`Filled "${btn.textContent}". Click "Continue Assessment" when ready.`, "success");
    });
  });
}

// -------------------------------------------------------------------
// Input Validation
// -------------------------------------------------------------------
function setupValidation() {
  const fasInput = document.getElementById("input-fas");
  const mmseInput = document.getElementById("input-mmse");
  const adlInput = document.getElementById("input-adl");

  fasInput.addEventListener("input", () => validateNumberField(fasInput, 0, 10, "error-fas", "Score must be between 0 and 10"));
  mmseInput.addEventListener("input", () => validateNumberField(mmseInput, 0, 30, "error-mmse", "MMSE Score must be between 0 and 30"));
  adlInput.addEventListener("input", () => validateNumberField(adlInput, 0, 10, "error-adl", "Score must be between 0 and 10"));

  document.getElementById("btn-clear-form").addEventListener("click", () => {
    document.getElementById("assessment-form").reset();
    clearAllValidationErrors();
    showFeedback("Form has been cleared.", "success");
  });

  const feedbackClose = document.getElementById("feedback-close");
  if (feedbackClose) {
    feedbackClose.addEventListener("click", () => {
      document.getElementById("feedback-banner").classList.add("hidden");
    });
  }
}

function validateNumberField(inputEl, minVal, maxVal, errorId, errorMsg) {
  const errorEl = document.getElementById(errorId);
  const raw = inputEl.value.trim();
  const val = parseFloat(raw);

  if (raw === "" || isNaN(val)) {
    inputEl.classList.add("is-invalid");
    if (errorEl) errorEl.textContent = "Please enter a value.";
    return false;
  }

  if (val < minVal || val > maxVal) {
    inputEl.classList.add("is-invalid");
    if (errorEl) errorEl.textContent = errorMsg;
    return false;
  }

  inputEl.classList.remove("is-invalid");
  if (errorEl) errorEl.textContent = "";
  return true;
}

function clearAllValidationErrors() {
  document.querySelectorAll(".custom-input").forEach(el => el.classList.remove("is-invalid"));
  document.querySelectorAll(".field-error-msg").forEach(el => el.textContent = "");
  document.getElementById("feedback-banner").classList.add("hidden");
}

function validateEntireForm() {
  const fasInput = document.getElementById("input-fas");
  const mmseInput = document.getElementById("input-mmse");
  const adlInput = document.getElementById("input-adl");

  const v1 = validateNumberField(fasInput, 0, 10, "error-fas", "Score must be between 0 and 10");
  const v2 = validateNumberField(mmseInput, 0, 30, "error-mmse", "MMSE Score must be between 0 and 30");
  const v3 = validateNumberField(adlInput, 0, 10, "error-adl", "Score must be between 0 and 10");

  const memChecked = document.querySelector('input[name="Memory_Complaints"]:checked');
  const behChecked = document.querySelector('input[name="Behavioral_Problems"]:checked');

  return v1 && v2 && v3 && !!memChecked && !!behChecked;
}

// -------------------------------------------------------------------
// Form Submission & Progressive Assessment Workflow
// -------------------------------------------------------------------
function setupFormSubmission() {
  const form = document.getElementById("assessment-form");

  form.addEventListener("submit", async (e) => {
    e.preventDefault();

    if (!validateEntireForm()) {
      showFeedback("Please fill all required scores with valid numbers before continuing.", "error");
      return;
    }

    // Read values
    const payload = {
      Functional_Assessment_Score: parseFloat(document.getElementById("input-fas").value),
      MMSE_Score: parseFloat(document.getElementById("input-mmse").value),
      ADL_Score: parseFloat(document.getElementById("input-adl").value),
      Memory_Complaints: parseInt(document.querySelector('input[name="Memory_Complaints"]:checked').value, 10),
      Behavioral_Problems: parseInt(document.querySelector('input[name="Behavioral_Problems"]:checked').value, 10)
    };

    if (!API_URL) {
      showFeedback(
        "The live cloud backend is not connected yet. Please deploy the backend on Render to enable live assessments on mobile and public devices.",
        "error"
      );
      return;
    }

    // Step A: Mark Step 1 complete
    completedSteps[1] = true;

    // Step B: Move user to Step 2 (Assessment / Circular Loading Screen)
    goToStep(2);

    try {
      const response = await fetch(`${API_URL}/predict`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json"
        },
        body: JSON.stringify(payload)
      });

      if (!response.ok) {
        let errMessage = "The assessment request could not be completed.";
        try {
          const errData = await response.json();
          if (errData && errData.detail) errMessage = errData.detail;
        } catch (_) {}
        throw new Error(errMessage);
      }

      const result = await response.json();
      assessmentResult = result;

      // Mark Steps 2 and 3 complete
      completedSteps[2] = true;
      completedSteps[3] = true;

      // Automatically transition to Step 3, then render results & report
      goToStep(3);
      renderResultsView(result);
      renderReportView(result);

    } catch (err) {
      console.error("Assessment Error:", err);
      let msg = err.message || "Unable to reach server.";
      if (msg === "Failed to fetch") {
        msg = "Unable to connect to the backend server. Please verify that your cloud backend is active.";
      }
      showFeedback(`Assessment failed: ${msg}`, "error");
      // Return to Step 1 on error
      goToStep(1);
    }
  });
}

// -------------------------------------------------------------------
// Render Step 3: Results View
// -------------------------------------------------------------------
function renderResultsView(data) {
  const pScores = data.patient_scores;
  const isHighRisk = data.risk_level === "Higher Risk";

  // 1. Compact Step 1 Summary
  document.getElementById("summary-fas").textContent = pScores.functional.display;
  document.getElementById("summary-mmse").textContent = pScores.mmse.display;
  document.getElementById("summary-adl").textContent = pScores.adl.display;

  const summaryMem = document.getElementById("summary-memory");
  summaryMem.textContent = pScores.memory.display;
  summaryMem.className = pScores.memory.value === 1 ? "c-val-badge" : "c-val-badge";

  const summaryBeh = document.getElementById("summary-behavior");
  summaryBeh.textContent = pScores.behavior.display;
  summaryBeh.className = pScores.behavior.value === 1 ? "c-val-badge" : "c-val-badge";

  // 2. Main Result Card
  const resultCard = document.getElementById("main-result-card");
  resultCard.className = `card result-card ${isHighRisk ? 'higher-risk' : 'lower-risk'}`;

  const resBadge = document.getElementById("res-badge");
  resBadge.textContent = data.result_headline;

  document.getElementById("res-explanation").textContent = data.explanation;

  const probAd = data.alzheimers_likelihood;
  const probOther = data.other_likelihood;

  document.getElementById("res-prob-ad").textContent = `${probAd.toFixed(1)}%`;
  document.getElementById("res-prob-other").textContent = `${probOther.toFixed(1)}%`;

  // 3. Likelihood Donut Chart
  renderLikelihoodChart(probAd, probOther, isHighRisk);

  // 4. Key Factors Horizontal Bar Chart
  renderKeyFactorsChart(data.key_factors);

  // 5. Your Assessment Scores (Numeric Progress Bars)
  document.getElementById("meter-val-fas").textContent = pScores.functional.display;
  document.getElementById("meter-fill-fas").style.width = `${pScores.functional.percent}%`;
  document.getElementById("meter-meaning-fas").textContent = pScores.functional.meaning;

  document.getElementById("meter-val-mmse").textContent = pScores.mmse.display;
  document.getElementById("meter-fill-mmse").style.width = `${pScores.mmse.percent}%`;
  document.getElementById("meter-meaning-mmse").textContent = pScores.mmse.meaning;

  document.getElementById("meter-val-adl").textContent = pScores.adl.display;
  document.getElementById("meter-fill-adl").style.width = `${pScores.adl.percent}%`;
  document.getElementById("meter-meaning-adl").textContent = pScores.adl.meaning;

  // Status Cards (Memory & Behavior)
  const badgeMem = document.getElementById("status-badge-memory");
  badgeMem.textContent = pScores.memory.value === 1 ? "Yes (Reported)" : "No (None reported)";
  badgeMem.className = `sic-badge ${pScores.memory.value === 1 ? 'reported' : 'unreported'}`;

  const badgeBeh = document.getElementById("status-badge-behavior");
  badgeBeh.textContent = pScores.behavior.value === 1 ? "Yes (Observed)" : "No (None observed)";
  badgeBeh.className = `sic-badge ${pScores.behavior.value === 1 ? 'reported' : 'unreported'}`;

  // 6. Simplified Factors Table
  const tableBody = document.getElementById("table-factors-body");
  tableBody.innerHTML = data.factors_table.map(row => `
    <tr>
      <td><strong>${row.factor}</strong></td>
      <td class="td-val">${row.value}</td>
      <td>${row.meaning}</td>
    </tr>
  `).join("");
}

// -------------------------------------------------------------------
// Render Likelihood Donut Chart
// -------------------------------------------------------------------
function renderLikelihoodChart(probAd, probOther, isHighRisk) {
  const canvas = document.getElementById("chart-likelihood-canvas");
  if (!canvas) return;

  if (chartLikelihoodInstance) {
    chartLikelihoodInstance.destroy();
  }

  // Update center metric
  document.getElementById("center-donut-pct").textContent = `${probAd.toFixed(1)}%`;
  document.getElementById("center-donut-label").textContent = isHighRisk ? "Higher Risk" : "Lower Risk";
  document.getElementById("center-donut-pct").style.color = isHighRisk ? "#dc2626" : "#059669";

  // Update legend
  document.getElementById("legend-text-ad").textContent = `Higher Risk: ${probAd.toFixed(1)}%`;
  document.getElementById("legend-text-other").textContent = `Lower Risk: ${probOther.toFixed(1)}%`;

  const ctx = canvas.getContext("2d");
  chartLikelihoodInstance = new Chart(ctx, {
    type: "doughnut",
    data: {
      labels: ["Higher Risk", "Lower Risk"],
      datasets: [{
        data: [probAd, probOther],
        backgroundColor: ["#ef4444", "#10b981"],
        hoverBackgroundColor: ["#dc2626", "#059669"],
        borderWidth: 2,
        borderColor: "#ffffff"
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      cutout: "75%",
      plugins: {
        legend: { display: false },
        tooltip: {
          callbacks: {
            label: function(context) {
              return ` ${context.label}: ${context.raw.toFixed(1)}%`;
            }
          }
        }
      }
    }
  });
}

// -------------------------------------------------------------------
// Render Key Factors Chart
// -------------------------------------------------------------------
function renderKeyFactorsChart(keyFactors) {
  const canvas = document.getElementById("chart-factors-canvas");
  if (!canvas || !keyFactors) return;

  if (chartFactorsInstance) {
    chartFactorsInstance.destroy();
  }

  // Reverse copy so highest factor is at top of horizontal bar
  const sorted = [...keyFactors].reverse();
  const labels = sorted.map(item => item.factor);
  const values = sorted.map(item => item.weight);

  const ctx = canvas.getContext("2d");
  chartFactorsInstance = new Chart(ctx, {
    type: "bar",
    data: {
      labels: labels,
      datasets: [{
        label: "Relevance Weight (%)",
        data: values,
        backgroundColor: "#0284c7",
        hoverBackgroundColor: "#0369a1",
        borderRadius: 6,
        barThickness: 16
      }]
    },
    options: {
      indexAxis: "y",
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { display: false },
        tooltip: {
          callbacks: {
            label: function(context) {
              return ` Relevance: ${context.raw.toFixed(1)}%`;
            }
          }
        }
      },
      scales: {
        x: {
          beginAtZero: true,
          grid: { color: "#e2e8f0" },
          ticks: {
            color: "#64748b",
            callback: value => `${value}%`
          }
        },
        y: {
          grid: { display: false },
          ticks: {
            color: "#0f172a",
            font: { family: "'Plus Jakarta Sans', sans-serif", size: 11, weight: 600 }
          }
        }
      }
    }
  });
}

// -------------------------------------------------------------------
// Render Step 4: Report View
// -------------------------------------------------------------------
function renderReportView(data) {
  document.getElementById("rep-date").textContent = data.timestamp_formatted;
  document.getElementById("rep-ref").textContent = data.assessment_id;

  const isHighRisk = data.risk_level === "Higher Risk";
  const badge = document.getElementById("rep-badge");
  badge.textContent = data.result_headline;
  badge.className = `result-badge ${isHighRisk ? 'badge-high' : 'badge-low'}`;
  badge.style.backgroundColor = isHighRisk ? '#fee2e2' : '#d1fae5';
  badge.style.color = isHighRisk ? '#b91c1c' : '#047857';
  badge.style.border = isHighRisk ? '1px solid #fecaca' : '1px solid #a7f3d0';

  document.getElementById("rep-pct-ad").textContent = `${data.alzheimers_likelihood.toFixed(1)}%`;
  document.getElementById("rep-pct-other").textContent = `${data.other_likelihood.toFixed(1)}%`;
  document.getElementById("rep-summary-p").textContent = data.summary;

  // 5 Info boxes
  const pScores = data.patient_scores;
  document.getElementById("rep-info-grid").innerHTML = `
    <div class="rep-info-box">
      <span class="rib-label">Functional Assessment</span>
      <span class="rib-value">${pScores.functional.display}</span>
    </div>
    <div class="rep-info-box">
      <span class="rib-label">MMSE Score</span>
      <span class="rib-value">${pScores.mmse.display}</span>
    </div>
    <div class="rep-info-box">
      <span class="rib-label">ADL Score</span>
      <span class="rib-value">${pScores.adl.display}</span>
    </div>
    <div class="rep-info-box">
      <span class="rib-label">Memory Complaints</span>
      <span class="rib-value">${pScores.memory.display}</span>
    </div>
    <div class="rep-info-box">
      <span class="rib-label">Behavioral Problems</span>
      <span class="rib-value">${pScores.behavior.display}</span>
    </div>
  `;

  // Table
  document.getElementById("rep-factors-table-body").innerHTML = data.factors_table.map(row => `
    <tr>
      <td><strong>${row.factor}</strong></td>
      <td class="td-val">${row.value}</td>
      <td>${row.meaning}</td>
    </tr>
  `).join("");

  // Guidance Cards
  document.getElementById("rep-personalized-guidance").innerHTML = data.helpful_guidance.map(item => `
    <div class="guidance-item-card">
      <svg class="guidance-icon" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
        <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"></path>
        <polyline points="22 4 12 14.01 9 11.01"></polyline>
      </svg>
      <span>${item}</span>
    </div>
  `).join("");
}

// -------------------------------------------------------------------
// Report Actions (PDF Download & Print)
// -------------------------------------------------------------------
function setupReportActions() {
  const btnDownloadPdf = document.getElementById("btn-download-pdf");
  const spinner = document.getElementById("pdf-spinner");
  const btnPrint = document.getElementById("btn-print-report");

  if (btnDownloadPdf) {
    btnDownloadPdf.addEventListener("click", async () => {
      if (!assessmentResult) {
        showFeedback("Please complete the assessment before downloading the report.", "error");
        return;
      }

      btnDownloadPdf.disabled = true;
      if (spinner) spinner.classList.remove("hidden");

      try {
        const response = await fetch(`${API_URL}/download-report`, {
          method: "POST",
          headers: {
            "Content-Type": "application/json"
          },
          body: JSON.stringify(assessmentResult)
        });

        if (!response.ok) {
          throw new Error("Report generation failed on the server.");
        }

        const blob = await response.blob();
        const downloadUrl = window.URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.style.display = "none";
        a.href = downloadUrl;
        a.download = `NeuroPredict_Report_${assessmentResult.assessment_id || 'ALZ'}.pdf`;
        document.body.appendChild(a);
        a.click();
        window.URL.revokeObjectURL(downloadUrl);
        a.remove();

        showFeedback("PDF report downloaded successfully.", "success");
      } catch (err) {
        console.error("PDF Download error:", err);
        showFeedback(`Failed to download report: ${err.message}`, "error");
      } finally {
        btnDownloadPdf.disabled = false;
        if (spinner) spinner.classList.add("hidden");
      }
    });
  }

  if (btnPrint) {
    btnPrint.addEventListener("click", () => {
      window.print();
    });
  }
}

// -------------------------------------------------------------------
// Reset Assessment
// -------------------------------------------------------------------
function handleResetAssessment() {
  if (assessmentResult) {
    const confirmed = confirm("Are you sure you want to start a new assessment? The current result will be cleared.");
    if (!confirmed) return;
  }

  assessmentResult = null;
  completedSteps = { 1: false, 2: false, 3: false, 4: false };

  document.getElementById("assessment-form").reset();
  clearAllValidationErrors();

  if (chartLikelihoodInstance) {
    chartLikelihoodInstance.destroy();
    chartLikelihoodInstance = null;
  }
  if (chartFactorsInstance) {
    chartFactorsInstance.destroy();
    chartFactorsInstance = null;
  }

  goToStep(1);
  showFeedback("Started a new assessment. Please enter patient details.", "success");
}

// -------------------------------------------------------------------
// Feedback Banner
// -------------------------------------------------------------------
function showFeedback(msg, type = "error") {
  const banner = document.getElementById("feedback-banner");
  const textEl = document.getElementById("feedback-text");
  if (!banner || !textEl) return;

  banner.className = `feedback-banner feedback-${type}`;
  textEl.textContent = msg;
  banner.classList.remove("hidden");
}
