const STORE_KEY = "funnyexecutor.workspace.v1";
const SETTINGS_KEY = "funnyexecutor.settings.v1";
const ROOT = "FunnyExecutor";
const FOLDERS = ["autoexec", "workspace", "scripts"];

function readStore() {
  try {
    let raw = localStorage.getItem(STORE_KEY);
    let parsed = raw ? JSON.parse(raw) : [];
    return Array.isArray(parsed) ? parsed : [];
  } catch (err) {
    console.warn("[executor] workspace store is broken, resetting", err);
    return [];
  }
}

function writeStore(files) {
  try {
    localStorage.setItem(STORE_KEY, JSON.stringify(files));
  } catch (err) {
    console.error("[executor] failed to persist workspace", err);
    throw new Error(String(err));
  }
}

export function pathOf(folder, name) {
  return name ? `${ROOT}/${folder}/${name}` : `${ROOT}/${folder}/`;
}

function log(action, target) {
  console.log(`[funnyexecutor] ${action} ${target}`);
}

function normalizeFolder(folder) {
  let f = String(folder || "scripts").toLowerCase();
  return FOLDERS.includes(f) ? f : "scripts";
}

// --- browser fallbacks -----------------------------------------------------
// the python shell answers everything properly; these keep the ui usable when
// it is opened in a plain browser (npm run dev without --native).

async function readWorkspaceFiles() {
  return readStore().map((f) => ({ ...f }));
}

async function writeWorkspaceFile({ folder, name, content }) {
  let target = normalizeFolder(folder);
  let files = readStore();
  let existing = files.find((f) => f.folder === target && f.name === name);

  if (existing) {
    existing.content = content;
  } else {
    files.push({ id: Date.now() + files.length, name, content, folder: target });
  }

  writeStore(files);
}

async function removeWorkspaceFile({ folder, name }) {
  let target = normalizeFolder(folder);
  writeStore(readStore().filter((f) => !(f.folder === target && f.name === name)));
}

async function moveWorkspaceFile({ fromFolder, toFolder, name }) {
  let from = normalizeFolder(fromFolder);
  let to = normalizeFolder(toFolder);
  if (from === to) return;

  let moved = false;
  let files = readStore().map((f) => {
    if (f.folder === from && f.name === name) {
      moved = true;
      return { ...f, folder: to };
    }
    return f;
  });

  if (!moved) throw new Error(`${pathOf(from, name)} not found`);
  writeStore(files);
}

async function revealFolder() {
  return pathOf("scripts");
}

async function openUrl({ url }) {
  let win = window.open(url, "_blank", "noopener");
  if (!win) throw new Error("popup blocked");
}

async function httpGet({ url }) {
  let res = await fetch(url);
  if (!res.ok) throw new Error(`http ${res.status}`);
  return await res.text();
}

async function excludeFromDefender() {
  log("defender", "no defender in the browser build");
}

async function readSettings() {
  try {
    let parsed = JSON.parse(localStorage.getItem(SETTINGS_KEY) || "{}");
    return parsed && typeof parsed === "object" ? parsed : {};
  } catch (err) {
    console.warn("[executor] stored settings are broken, ignoring them", err);
    return {};
  }
}

async function writeSettings({ data }) {
  try {
    localStorage.setItem(SETTINGS_KEY, JSON.stringify(data || {}));
  } catch (err) {
    console.error("[executor] failed to persist settings", err);
  }
}

// no executor in the browser: report a closed client so the ui stays honest
async function getStatus() {
  return { state: "unavailable", injected: false, roblox: false, pid: 0, placeId: 0, gameName: "" };
}

async function inject() {
  throw new Error("injection needs the Funny Executor shell");
}

async function execute() {
  throw new Error("execution needs the Funny Executor shell");
}

async function getClients() {
  return [];
}

async function getConsole() {
  return [];
}

async function clearConsole() {
  return 0;
}

async function getLuauApi() {
  return { items: [], hover: {}, signatures: {} };
}

const commands = {
  read_workspace_files: readWorkspaceFiles,
  write_workspace_file: writeWorkspaceFile,
  remove_workspace_file: removeWorkspaceFile,
  move_workspace_file: moveWorkspaceFile,
  reveal_folder: revealFolder,
  read_settings: readSettings,
  write_settings: writeSettings,
  open_url: openUrl,
  http_get: httpGet,
  exclude_from_defender: excludeFromDefender,
  get_status: getStatus,
  inject: inject,
  execute: execute,
  get_clients: getClients,
  get_console: getConsole,
  clear_console: clearConsole,
  get_luau_api: getLuauApi,
};

// the python shell serves the ui with ?native=1, so we know up front that a
// shell is behind the webview - window.pywebview itself shows up too late to
// ask about it on the first render.
const NATIVE_HINT =
  typeof location !== "undefined" &&
  new URLSearchParams(location.search).has("native");

const NATIVE_TIMEOUT = 3000;

export function isNative() {
  return NATIVE_HINT && typeof window !== "undefined" && !!window.pywebview;
}

let nativeApiPromise = null;

export function nativeApi() {
  if (!nativeApiPromise) {
    nativeApiPromise = new Promise((resolve) => {
      if (!NATIVE_HINT) {
        resolve(null);
        return;
      }

      let settled = false;
      let finish = (api) => {
        if (settled) return;
        settled = true;
        if (!api) log("native api never showed up, falling back to browser storage");
        resolve(api);
      };
      let check = () => {
        let api = window.pywebview && window.pywebview.api;
        if (api && typeof api.invoke === "function") finish(api);
        else if (!settled) setTimeout(check, 50);
      };

      window.addEventListener("pywebviewready", check, { once: true });
      setTimeout(() => finish(null), NATIVE_TIMEOUT);
      check();
    });
  }
  return nativeApiPromise;
}

export async function windowAction(action) {
  let api = await nativeApi();
  if (api && typeof api[action] === "function") {
    return api[action]();
  }
  log(`${action} is not available in the browser build`);
}

export async function invoke(cmd, args = {}) {
  let api = await nativeApi();
  if (api) {
    return api.invoke(cmd, args);
  }

  let handler = commands[cmd];
  if (!handler) {
    throw new Error(`unknown command: ${cmd}`);
  }
  return handler(args);
}

export function listFiles() {
  return nativeApi().then((api) =>
    api ? api.invoke("read_workspace_files") : readStore(),
  );
}

export function clearWorkspace() {
  return nativeApi().then(async (api) => {
    if (!api) {
      writeStore([]);
      return;
    }
    let files = await api.invoke("read_workspace_files");
    for (let file of files) {
      await api.invoke("remove_workspace_file", {
        folder: file.folder,
        name: file.name,
      });
    }
  });
}

if (typeof window !== "undefined") {
  window.funnyexecutor = {
    pathOf,
    listFiles,
    clearWorkspace,
    invoke,
    store: readStore,
    isNative,
  };
}