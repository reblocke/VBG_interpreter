export function createWorkerClient({ onReady, onStatus, onError }) {
  let worker = null;
  let requestId = 0;
  let failedWorker = null;
  const pendingRequests = new Map();

  function rejectPending(message) {
    for (const pending of pendingRequests.values()) {
      pending.reject(new Error(message));
    }
    pendingRequests.clear();
  }

  function requestWorker(type, payload, expectedResponseType) {
    if (!worker || worker === failedWorker) {
      return Promise.reject(new Error("The Python interpretation engine is unavailable."));
    }
    const id = ++requestId;
    return new Promise((resolve, reject) => {
      pendingRequests.set(id, { expectedResponseType, reject, resolve });
      worker.postMessage({ id, type, ...payload });
    });
  }

  function handleWorkerFailure(error, sourceWorker) {
    if (sourceWorker !== worker || failedWorker === sourceWorker) {
      return;
    }
    failedWorker = sourceWorker;
    const message =
      error instanceof Error && error.message
        ? error.message
        : "The Python interpretation engine failed.";
    rejectPending(message);
    onError(new Error(message));
  }

  function start() {
    if (worker) {
      worker.terminate();
      rejectPending("The Python interpretation engine restarted.");
    }

    failedWorker = null;
    onStatus("Loading the local Python interpretation engine.", "loading");

    let currentWorker;
    try {
      currentWorker = new Worker("./pyodide_worker.js", { type: "classic" });
    } catch (error) {
      worker = null;
      onError(error instanceof Error ? error : new Error(String(error)));
      return;
    }
    worker = currentWorker;

    currentWorker.addEventListener("message", (event) => {
      if (worker !== currentWorker || failedWorker === currentWorker) {
        return;
      }
      const { id, type, payload, error } = event.data || {};
      const pending = pendingRequests.get(id);
      if (!pending) {
        handleWorkerFailure(new Error("The worker returned an unknown response."), currentWorker);
        return;
      }
      pendingRequests.delete(id);

      if (type === "error") {
        pending.reject(new Error(error || "The worker request failed."));
        return;
      }
      if (type !== pending.expectedResponseType) {
        pending.reject(new Error("The worker returned an unexpected response."));
        handleWorkerFailure(new Error("The worker response contract failed."), currentWorker);
        return;
      }
      pending.resolve(payload);
    });

    currentWorker.addEventListener("error", (event) => {
      handleWorkerFailure(new Error(event.message || "The worker failed."), currentWorker);
    });

    requestWorker("initialize", {}, "ready")
      .then(() => {
        if (worker !== currentWorker || failedWorker === currentWorker) {
          return;
        }
        onReady();
      })
      .catch((error) => handleWorkerFailure(error, currentWorker));
  }

  function interpret(input) {
    return requestWorker("interpret", { input }, "interpretation");
  }

  return Object.freeze({ interpret, start });
}
