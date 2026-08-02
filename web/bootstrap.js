function showApplicationFailure() {
  const runtimeStatus = document.querySelector("#runtime-status");
  const assistiveStatus = document.querySelector("#assistive-status");
  const retryButton = document.querySelector("#retry-engine");
  const formError = document.querySelector("#form-errors");

  document.querySelector("#interpret-button").disabled = true;
  runtimeStatus.textContent = "Error: the Explorer could not be initialized.";
  runtimeStatus.dataset.state = "error";
  assistiveStatus.textContent =
    "The Explorer could not be initialized. Interpretation remains disabled. Reload to retry.";
  formError.textContent = "The Explorer could not be initialized. Reload the page to retry.";
  formError.hidden = false;
  retryButton.textContent = "Reload Explorer";
  retryButton.hidden = false;
  retryButton.addEventListener("click", () => window.location.reload(), { once: true });
}

try {
  await import("./app.js");
} catch {
  showApplicationFailure();
}
