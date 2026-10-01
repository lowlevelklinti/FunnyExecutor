import { nativeApi, invoke } from "./bridge.js";

const KEY = "funnyexecutor.settings.v1";

export const DEFAULTS = {
  general: {
    splash: true,
    autosave: false,
    autosaveDelay: 1200,
    rpcEnabled: false,
  },
  editor: {
    fontSize: 13,
    fontFamily: "jetbrains",
    tabSize: 4,
    insertSpaces: true,
    wordWrap: "off",
    lineNumbers: "on",
    minimap: true,
    smoothScrolling: true,
    cursorBlinking: "smooth",
    lineHighlight: "all",
    bracketPairColorization: false,
  },
  execution: {
    clearConsoleOnRun: true,
    openConsoleOnRun: false,
    timestamps: true,
    maxLogLines: 500,
    confirmClear: false,
  },
  appearance: {
    accent: "#8a8a8a",
    compact: false,
  },
};

export const FONT_STACKS = {
  jetbrains:
    "'JetBrains Mono', 'Cascadia Code', Consolas, 'Courier New', monospace",
  cascadia: "'Cascadia Code', Consolas, 'Courier New', monospace",
  consolas: "Consolas, 'Courier New', monospace",
  courier: "'Courier New', monospace",
  menlo: "Menlo, Consolas, 'Courier New', monospace",
};

function clone(value) {
  return JSON.parse(JSON.stringify(value));
}

// controls hand back strings (and legacy blobs stored 0/1 for booleans),
// so normalise anything to the type declared in DEFAULTS
function coerce(defaultValue, value) {
  if (typeof defaultValue === "number" && typeof value === "string" && value.trim() !== "") {
    let num = Number(value);
    if (!Number.isNaN(num)) return num;
  }
  if (typeof defaultValue === "boolean" && typeof value !== "boolean") {
    return value === true || value === "true" || value === 1 || value === "1";
  }
  return value;
}

function merge(base, saved) {
  let out = clone(base);
  if (!saved || typeof saved !== "object") return out;
  for (let key of Object.keys(out)) {
    if (saved[key] === undefined || saved[key] === null) continue;
    if (typeof out[key] === "object" && !Array.isArray(out[key])) {
      out[key] = merge(out[key], saved[key]);
    } else {
      out[key] = coerce(out[key], saved[key]);
    }
  }
  return out;
}

function read() {
  try {
    return merge(DEFAULTS, JSON.parse(localStorage.getItem(KEY) || "{}"));
  } catch (err) {
    console.warn("[executor] settings are broken, falling back to defaults", err);
    return clone(DEFAULTS);
  }
}

export const settings = $state(read());

export const events = $state({ replaySplash: 0 });

// the python shell keeps settings in FunnyExecutor/settings.json, so localStorage
// is only the browser fallback. resolved once in loadSettings().
let backend = "browser";
let loaded = false;

function replace(next) {
  for (let section of Object.keys(settings)) delete settings[section];
  Object.assign(settings, next);
  applyChrome();
}

function persist() {
  let snapshot = clone(settings);
  if (backend === "file") {
    invoke("write_settings", { data: snapshot }).catch((err) => {
      console.error("[executor] failed to save settings.json", err);
    });
    return;
  }
  try {
    localStorage.setItem(KEY, JSON.stringify(snapshot));
  } catch (err) {
    console.error("[executor] failed to persist settings", err);
  }
}

// async because the shell answers with the file contents, so the ui paints
// with defaults (or the browser copy) first and re-applies once loaded
export async function loadSettings() {
  let api = await nativeApi();
  backend = api ? "file" : "browser";

  if (api) {
    let stored = {};
    try {
      stored = await invoke("read_settings");
    } catch (err) {
      console.error("[executor] failed to read settings.json", err);
    }
    if (stored && typeof stored === "object" && Object.keys(stored).length > 0) {
      replace(merge(DEFAULTS, stored));
    } else {
      // no file yet, drop the current state into one
      persist();
    }
  }

  loaded = true;
  applyChrome();
  return settings;
}

export function settingsLoaded() {
  return loaded;
}

function hexToRgb(hex) {
  let h = String(hex).replace("#", "");
  if (h.length === 3) h = h.split("").map((c) => c + c).join("");
  let n = parseInt(h, 16);
  if (Number.isNaN(n)) return "138, 138, 138";
  return `${(n >> 16) & 255}, ${(n >> 8) & 255}, ${n & 255}`;
}

export function applyChrome() {
  if (typeof document === "undefined") return;
  let root = document.documentElement;
  root.style.setProperty("--accent", settings.appearance.accent);
  root.style.setProperty("--accent-rgb", hexToRgb(settings.appearance.accent));
  root.style.setProperty("--nav-size", settings.appearance.compact ? "32px" : "38px");
  root.style.setProperty("--nav-rail", settings.appearance.compact ? "50px" : "58px");
  root.style.setProperty("--tab-h", settings.appearance.compact ? "24px" : "28px");
  root.classList.toggle("compact", settings.appearance.compact);
}

// discord presence lives in the python process, so it has to be told directly
// instead of relying on the settings file being re-read
function syncSideEffects(section, key) {
  if (section !== "general" || key !== "rpcEnabled") return;
  invoke("set_rpc", { enabled: !!settings.general.rpcEnabled }).catch((err) => {
    console.error("[executor] failed to update discord rpc", err);
  });
}

export function set(section, key, value) {
  settings[section][key] = coerce(DEFAULTS[section]?.[key], value);
  persist();
  applyChrome();
  syncSideEffects(section, key);
}

export function resetAll() {
  for (let section of Object.keys(DEFAULTS)) {
    let next = clone(DEFAULTS[section]);
    for (let key of Object.keys(settings[section])) delete settings[section][key];
    Object.assign(settings[section], next);
  }
  persist();
  applyChrome();
  syncSideEffects("general", "rpcEnabled");
}

export function resetSection(section) {
  Object.assign(settings[section], clone(DEFAULTS[section]));
  persist();
  applyChrome();
  syncSideEffects(section, "rpcEnabled");
}

export function replaySplash() {
  events.replaySplash += 1;
}

applyChrome();
