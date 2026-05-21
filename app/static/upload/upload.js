const form = document.getElementById("upload-form");
const input = document.getElementById("telemetry-file");
const apiKeyInput = document.getElementById("api-key");
const message = document.getElementById("message");
const results = document.getElementById("upload-results");
const summary = document.getElementById("upload-summary");
const warnings = document.getElementById("upload-warnings");
const previewTableWrapper = document.getElementById("preview-table-wrapper");
const history = document.getElementById("upload-history");
const analyticsVehicleRegistration = document.getElementById("analytics-vehicle-registration");
const analyticsStartRecordedAt = document.getElementById("analytics-start-recorded-at");
const analyticsEndRecordedAt = document.getElementById("analytics-end-recorded-at");
const runAnalyticsButton = document.getElementById("run-analytics-button");
const analyticsSummary = document.getElementById("analytics-summary");
const prepareTransformButton = document.getElementById("prepare-transform-button");
const runTransformButton = document.getElementById("run-transform-button");
const downloadProcessedLink = document.getElementById("download-processed-link");
const duplicateDiagnosticsCard = document.getElementById("duplicate-diagnostics-card");
const duplicateDiagnosticsList = document.getElementById("duplicate-diagnostics-list");
let currentStoredFilename = "";

function canPrepareForTransform(status) {
  return status === "validated" || status === "validated_with_warnings";
}

function canRunTransform(status) {
  return status === "ready_for_transform";
}

function applyCurrentDetail(data) {
  const uploadData = data.upload ?? data;
  if (!uploadData.stored_filename) {
    return;
  }
  currentStoredFilename = uploadData.stored_filename;

  if (prepareTransformButton) {
    prepareTransformButton.dataset.storedFilename = uploadData.stored_filename;
    prepareTransformButton.hidden = !canPrepareForTransform(uploadData.status);
  }
  if (runTransformButton) {
    runTransformButton.dataset.storedFilename = uploadData.stored_filename;
    runTransformButton.hidden = !canRunTransform(uploadData.status);
  }
  if (downloadProcessedLink) {
    downloadProcessedLink.href = `/api/v1/uploads/history/${encodeURIComponent(uploadData.stored_filename)}/processed-artifact`;
    downloadProcessedLink.hidden = !uploadData.processed_path;
  }
  if (runAnalyticsButton) {
    runAnalyticsButton.disabled = !uploadData.processed_path;
  }
}

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}

function renderSummary(data) {
  const uploadData = data.upload ?? data;
  const sanitySummary = data.sanity_summary;
  const summaryRows = [
    ["Status", uploadData.status ?? "current_upload"],
    ["File", uploadData.original_filename ?? uploadData.filename],
    ["Stored as", uploadData.stored_filename],
    ["Rows", String(uploadData.row_count)],
    ["Size", `${uploadData.size_bytes} bytes`],
    ["Vehicles", String(sanitySummary.unique_vehicle_count)],
    ["Duplicates skipped", String(uploadData.duplicate_row_count ?? 0)],
    ["First timestamp", sanitySummary.first_recorded_at ?? "Not detected"],
    ["Last timestamp", sanitySummary.last_recorded_at ?? "Not detected"],
  ];

  summary.innerHTML = summaryRows
    .map(
      ([label, value]) =>
        `<dt>${escapeHtml(label)}</dt><dd>${escapeHtml(value)}</dd>`,
    )
    .join("");
}

function renderWarnings(data) {
  const sanitySummary = data.sanity_summary;
  const issueItems = sanitySummary.required_value_issues.map(
    (issue) =>
      `<div class="warning-item"><strong>${escapeHtml(issue.column)}</strong> ${
        escapeHtml(issue.issue)
      } Affected rows: ${escapeHtml(issue.affected_rows)}</div>`,
  );
  const warningItems = sanitySummary.warnings.map(
    (warning) => `<div class="warning-item">${escapeHtml(warning)}</div>`,
  );

  if (warningItems.length === 0 && issueItems.length === 0) {
    warnings.innerHTML =
      '<div class="warning-clear">No validation warnings were detected in the preview pass.</div>';
    return;
  }

  warnings.innerHTML = [...warningItems, ...issueItems].join("");
}

function renderPreviewTable(data) {
  const sanitySummary = data.sanity_summary;
  const headerCells = sanitySummary.preview_columns
    .map((column) => `<th>${escapeHtml(column)}</th>`)
    .join("");

  const bodyRows = sanitySummary.preview_rows
    .map((row) => {
      const cells = sanitySummary.preview_columns
        .map((column) => `<td>${escapeHtml(row.values[column] ?? "")}</td>`)
        .join("");
      return `<tr><td>${escapeHtml(row.row_number)}</td>${cells}</tr>`;
    })
    .join("");

  previewTableWrapper.innerHTML = `
    <div class="table-scroll">
      <table class="preview-table">
        <thead>
          <tr>
            <th>Row</th>
            ${headerCells}
          </tr>
        </thead>
        <tbody>
          ${bodyRows}
        </tbody>
      </table>
    </div>
  `;
}

function renderDuplicateDiagnostics(data) {
  if (!duplicateDiagnosticsCard || !duplicateDiagnosticsList) {
    return;
  }

  const duplicateDiagnostics = data.duplicate_diagnostics ?? [];
  if (duplicateDiagnostics.length === 0) {
    duplicateDiagnosticsCard.hidden = true;
    duplicateDiagnosticsList.innerHTML = "";
    return;
  }

  duplicateDiagnosticsCard.hidden = false;
  duplicateDiagnosticsList.innerHTML = duplicateDiagnostics
    .map(
      (item) => `
        <article class="diagnostic-item">
          <div class="diagnostic-topline">
            <strong>Row ${escapeHtml(item.row_number)}</strong>
            <span>Duplicate of row ${escapeHtml(item.duplicate_of_row_number)}</span>
          </div>
          <div><strong>Key:</strong> ${escapeHtml(item.duplicate_key)}</div>
          <div><strong>Vehicle:</strong> ${escapeHtml(item.vehicle_registration || "Not provided")}</div>
          <div><strong>IMEI:</strong> ${escapeHtml(item.device_imei || "Not provided")}</div>
          <div><strong>Recorded at:</strong> ${escapeHtml(item.recorded_at || "Not provided")}</div>
          <div class="schema-note">${escapeHtml(item.reason)}</div>
        </article>
      `,
    )
    .join("");
}

function renderHistory(items) {
  if (!history) {
    return;
  }

  if (items.length === 0) {
    history.innerHTML =
      '<div class="history-empty">No uploads have been recorded yet.</div>';
    return;
  }

  history.innerHTML = items
    .map((item) => {
      const statusMarkup =
        item.warning_count > 0
          ? `<div class="history-warning">${escapeHtml(item.warning_count)} warning(s): ${
              item.warnings.map((warning) => escapeHtml(warning)).join(" | ")
            }</div>`
          : '<div class="history-clear">No warnings recorded.</div>';

      return `
        <article class="history-card">
          <button class="history-button" type="button" data-stored-filename="${escapeHtml(item.stored_filename)}">
            <div class="status-pill ${escapeHtml(item.status)}">${escapeHtml(item.status)}</div>
            <h3>${escapeHtml(item.original_filename)}</h3>
            <div class="history-meta">
              <div>Uploaded: ${escapeHtml(item.created_at)}</div>
              <div>Rows: ${escapeHtml(item.row_count)} | Vehicles: ${escapeHtml(item.unique_vehicle_count)}</div>
              <div>Stored as: ${escapeHtml(item.stored_filename)}</div>
              <div>Transformed rows: ${escapeHtml(item.transformed_row_count ?? "Not transformed")}</div>
              <div>Duplicates skipped: ${escapeHtml(item.duplicate_row_count ?? 0)}</div>
            </div>
            ${statusMarkup}
          </button>
        </article>
      `;
    })
    .join("");
}

async function loadHistory(apiPrefix) {
  if (!history) {
    return;
  }

  const response = await fetch(`${apiPrefix}/uploads/history`);
  if (!response.ok) {
    history.innerHTML =
      '<div class="history-empty">Upload history is temporarily unavailable.</div>';
    return;
  }

  const data = await response.json();
  renderHistory(data.uploads ?? []);
}

async function loadUploadDetail(apiPrefix, storedFilename) {
  const response = await fetch(
    `${apiPrefix}/uploads/history/${encodeURIComponent(storedFilename)}`,
  );
  if (!response.ok) {
    message.textContent = "Could not load the selected upload detail.";
    message.className = "error";
    return;
  }

  const data = await response.json();
  renderSummary(data);
  renderWarnings(data);
  renderPreviewTable(data);
  renderDuplicateDiagnostics(data);
  applyCurrentDetail(data);
  if (data.upload?.processed_path) {
    void runDuckDbSummary();
  } else if (analyticsSummary) {
    analyticsSummary.innerHTML = "";
  }
  results.hidden = false;
  message.textContent = "Loaded a previous ingestion run for review.";
  message.className = "status";
}

function renderAnalyticsSummary(data) {
  if (!analyticsSummary) {
    return;
  }

  const rows = [
    ["Rows", String(data.row_count)],
    ["Vehicles", String(data.distinct_vehicle_count)],
    ["First", data.first_recorded_at ?? "Not detected"],
    ["Last", data.last_recorded_at ?? "Not detected"],
    ["Filter", data.vehicle_registration ?? "All vehicles"],
  ];

  analyticsSummary.innerHTML = rows
    .map(
      ([label, value]) =>
        `<dt>${escapeHtml(label)}</dt><dd>${escapeHtml(value)}</dd>`,
    )
    .join("");
}

async function runDuckDbSummary() {
  if (!runAnalyticsButton || !analyticsSummary || !currentStoredFilename) {
    return;
  }

  const apiPrefix = window.telemetryUploadConfig?.apiPrefix ?? "/api/v1";
  const params = new URLSearchParams();

  const vehicleRegistration =
    analyticsVehicleRegistration instanceof HTMLInputElement
      ? analyticsVehicleRegistration.value.trim()
      : "";
  const startRecordedAt =
    analyticsStartRecordedAt instanceof HTMLInputElement
      ? analyticsStartRecordedAt.value
      : "";
  const endRecordedAt =
    analyticsEndRecordedAt instanceof HTMLInputElement
      ? analyticsEndRecordedAt.value
      : "";

  if (vehicleRegistration) {
    params.set("vehicle_registration", vehicleRegistration);
  }
  if (startRecordedAt) {
    params.set("start_recorded_at", startRecordedAt);
  }
  if (endRecordedAt) {
    params.set("end_recorded_at", endRecordedAt);
  }

  runAnalyticsButton.disabled = true;
  const response = await fetch(
    `${apiPrefix}/analytics/telemetry/${encodeURIComponent(currentStoredFilename)}/summary?${params.toString()}`,
  );
  const data = await response.json();
  runAnalyticsButton.disabled = false;

  if (!response.ok) {
    message.textContent = data.detail ?? "DuckDB summary failed.";
    message.className = "error";
    return;
  }

  renderAnalyticsSummary(data);
  message.textContent = "DuckDB summary loaded.";
  message.className = "status";
}

if (form && input && message && results && summary && warnings && previewTableWrapper) {
  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    const file = input.files?.[0];
    if (!file) {
      message.textContent = "Choose a CSV file first.";
      message.className = "error";
      results.hidden = true;
      return;
    }

    const formData = new FormData();
    formData.append("file", file);

    message.textContent = "Uploading...";
    message.className = "status";
    results.hidden = true;

    const apiPrefix = window.telemetryUploadConfig?.apiPrefix ?? "/api/v1";
    const apiKey = apiKeyInput instanceof HTMLInputElement ? apiKeyInput.value.trim() : "";
    const uploadHeaders = {};
    if (apiKey) {
      uploadHeaders["X-API-Key"] = apiKey;
    }
    const response = await fetch(`${apiPrefix}/uploads/telemetry`, {
      method: "POST",
      headers: uploadHeaders,
      body: formData,
    });
    const data = await response.json();

    if (!response.ok) {
      message.textContent = data.detail ?? "Upload failed.";
      message.className = "error";
      results.hidden = true;
      return;
    }

    renderSummary(data);
    renderWarnings(data);
    renderPreviewTable(data);
    renderDuplicateDiagnostics(data);
    applyCurrentDetail(data);
    if (data.upload?.processed_path) {
      void runDuckDbSummary();
    } else if (analyticsSummary) {
      analyticsSummary.innerHTML = "";
    }
    await loadHistory(apiPrefix);

    message.textContent = "Upload completed. Review the sanity check before you ingest more data.";
    message.className = "status";
    results.hidden = false;
  });

  const apiPrefix = window.telemetryUploadConfig?.apiPrefix ?? "/api/v1";
  void loadHistory(apiPrefix);
  history?.addEventListener("click", async (event) => {
    const trigger = event.target.closest("[data-stored-filename]");
    if (!(trigger instanceof HTMLElement)) {
      return;
    }
    const storedFilename = trigger.dataset.storedFilename;
    if (!storedFilename) {
      return;
    }
    await loadUploadDetail(apiPrefix, storedFilename);
  });
  prepareTransformButton?.addEventListener("click", async () => {
    const storedFilename = prepareTransformButton.dataset.storedFilename;
    if (!storedFilename) {
      return;
    }
    message.textContent = "Marking upload ready for transform...";
    message.className = "status";
    const response = await fetch(
      `${apiPrefix}/uploads/history/${encodeURIComponent(storedFilename)}/prepare-transform`,
      { method: "POST" },
    );
    const data = await response.json();
    if (!response.ok) {
      message.textContent = data.detail ?? "Could not update upload status.";
      message.className = "error";
      return;
    }
    renderSummary(data);
    renderWarnings(data);
    renderPreviewTable(data);
    renderDuplicateDiagnostics(data);
    applyCurrentDetail(data);
    await loadHistory(apiPrefix);
    message.textContent = "Upload marked ready for transform.";
    message.className = "status";
  });
  runTransformButton?.addEventListener("click", async () => {
    const storedFilename = runTransformButton.dataset.storedFilename;
    if (!storedFilename) {
      return;
    }
    message.textContent = "Running transform...";
    message.className = "status";
    const response = await fetch(
      `${apiPrefix}/uploads/history/${encodeURIComponent(storedFilename)}/run-transform`,
      { method: "POST" },
    );
    const data = await response.json();
    if (!response.ok) {
      message.textContent = data.detail ?? "Could not run transform.";
      message.className = "error";
      return;
    }
    renderSummary(data);
    renderWarnings(data);
    renderPreviewTable(data);
    renderDuplicateDiagnostics(data);
    applyCurrentDetail(data);
    await loadHistory(apiPrefix);
    if (data.upload?.processed_path) {
      void runDuckDbSummary();
    }
    message.textContent = "Transform completed and curated output was recorded.";
    message.className = "status";
  });
  runAnalyticsButton?.addEventListener("click", async () => {
    await runDuckDbSummary();
  });
  analyticsVehicleRegistration?.addEventListener("keydown", (event) => {
    if (event.key === "Enter") {
      event.preventDefault();
      void runDuckDbSummary();
    }
  });
}
