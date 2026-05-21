const form = document.getElementById("upload-form");
const input = document.getElementById("telemetry-file");
const message = document.getElementById("message");
const result = document.getElementById("result");

if (form && input && message && result) {
  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    const file = input.files?.[0];
    if (!file) {
      message.textContent = "Choose a CSV file first.";
      message.className = "error";
      result.hidden = true;
      return;
    }

    const formData = new FormData();
    formData.append("file", file);

    message.textContent = "Uploading...";
    message.className = "status";
    result.hidden = true;

    const apiPrefix = window.telemetryUploadConfig?.apiPrefix ?? "/api/v1";
    const response = await fetch(`${apiPrefix}/uploads/telemetry`, {
      method: "POST",
      body: formData,
    });
    const data = await response.json();

    if (!response.ok) {
      message.textContent = data.detail ?? "Upload failed.";
      message.className = "error";
      result.hidden = true;
      return;
    }

    message.textContent = "Upload completed.";
    message.className = "status";
    result.textContent = JSON.stringify(data, null, 2);
    result.hidden = false;
  });
}
