const PYODIDE_INDEX_PATH = "./vendor/pyodide/0.29.3/";
const PACKAGE_MANIFEST_PATH = "./assets/py/package-manifest.json";
const PACKAGE_MANIFEST_SCHEMA_VERSION = "vbg_explorer_web_package_manifest/1.0";
const PYTHON_ASSET_PATH = "./assets/py";
const PYTHON_IMPORT_ROOT = "/vbg_explorer_app/assets/py";
const SAFE_PACKAGE_FILE_PATH =
  /^(?:stewartlight|vbg_interpreter)\/(?:[A-Za-z0-9_][A-Za-z0-9_.-]*\/)*[A-Za-z0-9_][A-Za-z0-9_.-]*$/;

let runtimePromise = null;

function requireSameOriginUrl(resource, label) {
  const candidate = resource?.url ?? String(resource);
  const url = new URL(candidate, self.location.href);
  if (url.origin !== self.location.origin) {
    throw new Error(`${label} must remain same-origin.`);
  }
  return url.href;
}

const PYODIDE_INDEX_URL = requireSameOriginUrl(PYODIDE_INDEX_PATH, "Pyodide index URL");
const nativeFetch = self.fetch.bind(self);
self.fetch = (resource, options) => {
  requireSameOriginUrl(resource, "Worker fetch");
  return nativeFetch(resource, options);
};

const nativeImportScripts = self.importScripts.bind(self);
self.importScripts = (...resources) => {
  const urls = resources.map((resource) => requireSameOriginUrl(resource, "Worker importScripts"));
  return nativeImportScripts(...urls);
};

const nativeXhrOpen = self.XMLHttpRequest.prototype.open;
self.XMLHttpRequest.prototype.open = function (method, resource, ...options) {
  requireSameOriginUrl(resource, "Worker XMLHttpRequest");
  return nativeXhrOpen.call(this, method, resource, ...options);
};

async function fetchText(path) {
  const response = await fetch(requireSameOriginUrl(path, "Python asset fetch"));
  if (!response.ok) {
    throw new Error("A required Python asset could not be loaded.");
  }
  return response.text();
}

async function fetchBytes(path) {
  const response = await fetch(requireSameOriginUrl(path, "Python asset fetch"));
  if (!response.ok) {
    throw new Error("A required Python asset could not be loaded.");
  }
  return new Uint8Array(await response.arrayBuffer());
}

function validatePackageManifest(manifest) {
  if (!manifest || typeof manifest !== "object" || Array.isArray(manifest)) {
    throw new Error("The Python package manifest is invalid.");
  }
  const keys = Object.keys(manifest).sort();
  if (keys.join(",") !== "files,schema_version") {
    throw new Error("The Python package manifest has an invalid shape.");
  }
  if (manifest.schema_version !== PACKAGE_MANIFEST_SCHEMA_VERSION) {
    throw new Error("The Python package manifest version is unsupported.");
  }
  if (!Array.isArray(manifest.files) || manifest.files.length === 0) {
    throw new Error("The Python package manifest has no files.");
  }

  const files = manifest.files.map((path) => {
    if (typeof path !== "string" || !SAFE_PACKAGE_FILE_PATH.test(path)) {
      throw new Error("The Python package manifest contains an unsafe path.");
    }
    return path;
  });
  for (let index = 1; index < files.length; index += 1) {
    if (files[index - 1] >= files[index]) {
      throw new Error("The Python package manifest paths must be sorted and unique.");
    }
  }
  for (const requiredEntry of ["stewartlight/__init__.py", "vbg_interpreter/__init__.py"]) {
    if (!files.includes(requiredEntry)) {
      throw new Error("The Python package manifest is missing a required package entry.");
    }
  }
  return Object.freeze(files);
}

async function fetchManifest() {
  const source = await fetchText(PACKAGE_MANIFEST_PATH);
  let manifest;
  try {
    manifest = JSON.parse(source);
  } catch {
    throw new Error("The Python package manifest is not valid JSON.");
  }
  if (`${JSON.stringify(manifest, null, 2)}\n` !== source) {
    throw new Error("The Python package manifest is not canonical JSON.");
  }
  return validatePackageManifest(manifest);
}

async function fetchPackageFiles(paths) {
  return Promise.all(
    paths.map(async (path) => ({
      path,
      bytes: await fetchBytes(`${PYTHON_ASSET_PATH}/${path}`),
    })),
  );
}

function mountPackages(pyodide, files) {
  for (const { path, bytes } of files) {
    const destination = `${PYTHON_IMPORT_ROOT}/${path}`;
    const parentDirectory = destination.slice(0, destination.lastIndexOf("/"));
    pyodide.FS.mkdirTree(parentDirectory);
    pyodide.FS.writeFile(destination, bytes);
  }

  pyodide.runPython(`
import sys

python_import_root = "${PYTHON_IMPORT_ROOT}"
if python_import_root not in sys.path:
    sys.path.insert(0, python_import_root)

from vbg_interpreter.browser_adapter import interpret_browser_request_json

if not callable(interpret_browser_request_json):
    raise RuntimeError("The Explorer browser adapter is unavailable.")
`);
}

async function initializeRuntime() {
  const packagePaths = await fetchManifest();
  const packageFiles = await fetchPackageFiles(packagePaths);
  importScripts(`${PYODIDE_INDEX_URL}pyodide.js`);
  const pyodide = await loadPyodide({ indexURL: PYODIDE_INDEX_URL });
  mountPackages(pyodide, packageFiles);
  return pyodide;
}

function getRuntime() {
  runtimePromise ||= initializeRuntime();
  return runtimePromise;
}

function sanitizeInterpretationError(error) {
  const message = error instanceof Error ? error.message : String(error);
  const lines = message
    .split("\n")
    .map((line) => line.trim())
    .filter(Boolean);
  const validationLine = [...lines]
    .reverse()
    .find((line) => /(?:ExplorerSerializationError|ExplorerInputError):/.test(line));
  if (!validationLine) {
    return "Interpretation could not be completed.";
  }
  return validationLine
    .replace(/^.*(?:ExplorerSerializationError|ExplorerInputError):\s*/, "")
    .slice(0, 320);
}

async function interpret(input) {
  const pyodide = await getRuntime();
  pyodide.globals.set("explorer_request_json", JSON.stringify(input));
  try {
    const responseJson = pyodide.runPython(`
from vbg_interpreter.browser_adapter import interpret_browser_request_json

interpret_browser_request_json(explorer_request_json)
`);
    if (typeof responseJson !== "string") {
      throw new Error("The browser adapter returned an invalid response.");
    }
    const response = JSON.parse(responseJson);
    if (!response || typeof response !== "object" || Array.isArray(response)) {
      throw new Error("The browser adapter returned an invalid result object.");
    }
    return response;
  } finally {
    pyodide.globals.delete("explorer_request_json");
  }
}

self.addEventListener("message", async (event) => {
  const { id, type, input } = event.data || {};
  try {
    if (type === "initialize") {
      await getRuntime();
      self.postMessage({ id, type: "ready", payload: { ready: true } });
      return;
    }
    if (type === "interpret") {
      const payload = await interpret(input);
      self.postMessage({ id, type: "interpretation", payload });
      return;
    }
    self.postMessage({ id, type: "error", error: "Unknown worker request." });
  } catch (error) {
    self.postMessage({
      id,
      type: "error",
      error:
        type === "interpret"
          ? sanitizeInterpretationError(error)
          : "The Python interpretation engine could not be initialized.",
    });
  }
});
