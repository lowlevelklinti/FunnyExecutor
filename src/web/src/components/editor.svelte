<script>
  import { onMount } from "svelte";
  import {
    IconPlayerPlayFilled,
    IconLink,
    IconFolderOpen,
    IconDeviceFloppy,
    IconTrash,
    IconGripVertical,
    IconTerminal2,
    IconPlus,
    IconX
  } from "@tabler/icons-svelte";
  import monaco, { applyAccent, registerLuauProviders } from "../monaco.js";
  import { invoke } from "../lib/bridge.js";
  import { settings, FONT_STACKS } from "../lib/settings.svelte.js";

  function editorOptions() {
    let e = settings.editor;
    return {
      fontSize: e.fontSize,
      fontFamily: FONT_STACKS[e.fontFamily] || FONT_STACKS.jetbrains,
      tabSize: e.tabSize,
      insertSpaces: e.insertSpaces,
      wordWrap: e.wordWrap,
      lineNumbers: e.lineNumbers,
      minimap: {
        enabled: e.minimap,
        side: "right",
        renderCharacters: true,
        showSlider: "mouseover"
      },
      smoothScrolling: e.smoothScrolling,
      cursorBlinking: e.cursorBlinking,
      renderLineHighlight: e.lineHighlight,
      bracketPairColorization: { enabled: e.bracketPairColorization }
    };
  }

  let {
    files = $bindable([]),
    onselect,
    onnew,
    ondelete,
    onmenu,
    onsave,
    onopenfile,
    onrenametab,
    showconsole = $bindable(false),
    logs = $bindable([]),
    status = $bindable({ state: "idle", injected: false, roblox: false }),
    onclearconsole,
    ontoast,
    onlog
  } = $props();

  let editorContainer = $state(null);
  let editor = $state(null);
  let editorViewEl = $state(null);
  let barEl = $state(null);
  let fileInputEl = $state(null);

  // why is this floating thing even here bro
  let barPos = $state({ x: 0, y: 0 });
  let dragging = $state(false);
  let dragStart = $state({ x: 0, y: 0 });
  let initialPos = $state({ x: 0, y: 0 });

  let renamingTabId = $state(null);
  let renameValue = $state("");

  function getActive() {
    return files.find(f => f.active) || null;
  }

  export function startRename(file, e) {
    e?.stopPropagation();
    renamingTabId = file.id;
    renameValue = file.name;
  }

  function finishRename(id) {
    if (renamingTabId === id && renameValue.trim()) {
      let finalName = renameValue.trim();
      if (!finalName.endsWith(".lua") && !finalName.endsWith(".luau") && !finalName.endsWith(".txt")) {
        finalName += ".lua";
      }
      files = files.map(f => f.id === id ? { ...f, name: finalName } : f);
      onrenametab?.(id, finalName);
    }
    renamingTabId = null;
  }

  function handleTabKey(e, id) {
    if (e.key === "Enter") finishRename(id);
    if (e.key === "Escape") renamingTabId = null;
  }

  export function init() {
    if (!editorContainer) return;
    let current = getActive();
    if (editor) {
      if (current) editor.setValue(current.content || "");
      return;
    }

    editor = monaco.editor.create(editorContainer, {
      value: current ? current.content : "",
      language: "lua",
      theme: "funnyexecutor-dark",
      ...editorOptions(),
      fontFamily: FONT_STACKS[settings.editor.fontFamily] || FONT_STACKS.jetbrains,
      automaticLayout: true,
      scrollBeyondLastLine: false,
      padding: { top: 14, bottom: 14 },
      lineNumbersMinChars: 3,
      cursorSmoothCaretAnimation: "on",
      overviewRulerBorder: false,
      hideCursorInOverviewRuler: false,
      matchBrackets: "never",
      guides: { bracketPairs: false },
      readOnly: false,
    });

    editor.onDidChangeModelContent(() => {
      let active = getActive();
      if (active) {
        active.content = editor.getValue();
        scheduleAutosave();
      }
    });
  }

  function pushLogs(list, text, type = "info") {
    let next = [
      ...list,
      {
        type,
        text,
        ts: settings.execution.timestamps ? new Date().toLocaleTimeString() : null,
      },
    ];
    let cap = Number(settings.execution.maxLogLines) || 500;
    return next.slice(-cap);
  }

  export function setValue(val) {
    if (editor) editor.setValue(val);
  }

  export function getValue() {
    return editor ? editor.getValue() : "";
  }

  export function destroy() {
    if (editor) {
      editor.dispose();
      editor = null;
    }
  }

  function startDrag(e) {
    dragging = true;
    dragStart = { x: e.clientX, y: e.clientY };
    initialPos = { ...barPos };
    e.preventDefault();
  }

  function resetDrag() {
    barPos = { x: 0, y: 0 };
    ontoast?.("Action bar reset");
  }

  function handleMouseMove(e) {
    if (!dragging) return;
    let targetX = initialPos.x + (e.clientX - dragStart.x);
    let targetY = initialPos.y + (e.clientY - dragStart.y);

    if (editorViewEl && barEl) {
      let editorRect = editorViewEl.getBoundingClientRect();
      let barRect = barEl.getBoundingClientRect();

      let defaultLeft = editorRect.width - 20 - barRect.width;
      let defaultTop = editorRect.height - 18 - barRect.height;

      let minX = -defaultLeft + 10;
      let maxX = 10;
      let minY = -defaultTop + 48;
      let maxY = 8;

      barPos = {
        x: Math.max(minX, Math.min(maxX, targetX)),
        y: Math.max(minY, Math.min(maxY, targetY))
      };
    } else {
      barPos = { x: targetX, y: targetY };
    }
  }

  function handleMouseUp() {
    dragging = false;
  }

  let clearArmed = $state(false);
  let clearTimer = null;
  let busy = $state(false);

  async function execute() {
    let active = getActive();
    if (!active || !editor) {
      ontoast?.("No active script to execute");
      return;
    }

    let source = editor.getValue();
    active.content = source;

    if (settings.execution.clearConsoleOnRun) onclearconsole?.();
    pushLogs(logs, `[executor] executing ${active.name}...`);
    if (settings.execution.openConsoleOnRun) showconsole = true;

    busy = true;
    try {
      await invoke("execute", { source });
      pushLogs(logs, `[executor] ${active.name} sent to the game`);
      ontoast?.(`Executed ${active.name}`);
    } catch (err) {
      let message = String(err?.message || err);
      pushLogs(logs, `[executor] ${message}`, "error");
      ontoast?.(message);
    } finally {
      busy = false;
    }
  }

  async function inject() {
    if (busy) return;
    busy = true;
    pushLogs(logs, "[executor] inject requested");
    try {
      let next = await invoke("inject");
      if (next?.injected) {
        pushLogs(logs, "[executor] injected");
        ontoast?.("Injected successfully");
      } else {
        pushLogs(logs, "[executor] queued, waiting for the game to load");
        ontoast?.("Inject queued - join a game first");
      }
    } catch (err) {
      let message = String(err?.message || err);
      pushLogs(logs, `[executor] ${message}`, "error");
      ontoast?.(message);
    } finally {
      busy = false;
    }
  }

  export function runExecute() {
    execute();
  }

  export function runInject() {
    inject();
  }

  function triggerOpenFile() {
    fileInputEl?.click();
  }

  function handleFilePicked(e) {
    let file = e.target.files?.[0];
    if (!file) return;
    let reader = new FileReader();
    reader.onload = (evt) => {
      let content = evt.target.result;
      onopenfile?.(file.name, content);
      e.target.value = "";
    };
    reader.readAsText(file);
  }

  function saveFile() {
    onsave?.();
  }

  function clearCode() {
    if (!editor || files.length === 0) return;

    if (settings.execution.confirmClear && !clearArmed) {
      clearArmed = true;
      ontoast?.("Click Clear again to confirm");
      clearTimeout(clearTimer);
      clearTimer = setTimeout(() => (clearArmed = false), 2000);
      return;
    }

    clearArmed = false;
    clearTimeout(clearTimer);
    editor.setValue("");
    let active = getActive();
    if (active) active.content = "";
    ontoast?.("Editor cleared");
  }

  let isDragOver = $state(false);

  function handleDragOver(e) {
    e.preventDefault();
    isDragOver = true;
  }

  function handleDragLeave(e) {
    e.preventDefault();
    isDragOver = false;
  }

  function handleDrop(e) {
    e.preventDefault();
    isDragOver = false;
    let droppedFiles = e.dataTransfer?.files;
    if (!droppedFiles || droppedFiles.length === 0) return;
    for (let file of droppedFiles) {
      let reader = new FileReader();
      reader.onload = (evt) => {
        onopenfile?.(file.name, evt.target.result);
      };
      reader.readAsText(file);
    }
  }

  let autosaveTimer = null;

  let stateLabel = $derived(
    status.state === "unavailable"
      ? "offline"
      : status.injected
        ? "injected"
        : status.state === "queued"
          ? "queued"
          : status.roblox
            ? "attached"
            : "idle",
  );

  function scheduleAutosave() {
    clearTimeout(autosaveTimer);
    if (!settings.general.autosave) return;
    autosaveTimer = setTimeout(
      () => onsave?.(true),
      Math.max(200, Number(settings.general.autosaveDelay) || 1200),
    );
  }

  $effect(() => {
    let opts = editorOptions();
    let accent = settings.appearance.accent;
    if (!editor) {
      applyAccent(accent);
      return;
    }
    editor.updateOptions(opts);
    applyAccent(accent);
  });

  onMount(() => {
    if (files.length > 0) init();

    // the native shell exposes the unc api tables, so autocomplete matches the
    // client exactly; the browser build simply gets no providers
    invoke("get_luau_api")
      .then((api) => registerLuauProviders(api))
      .catch(() => registerLuauProviders(null));

    window.addEventListener("mousemove", handleMouseMove);
    window.addEventListener("mouseup", handleMouseUp);

    return () => {
      if (autosaveTimer) {
        clearTimeout(autosaveTimer);
        autosaveTimer = null;
        if (settings.general.autosave) onsave?.(true);
      }
      destroy();
      clearTimeout(clearTimer);
      window.removeEventListener("mousemove", handleMouseMove);
      window.removeEventListener("mouseup", handleMouseUp);
    };
  });
</script>

<input
  type="file"
  bind:this={fileInputEl}
  accept=".lua,.luau,.txt"
  onchange={handleFilePicked}
  style="display: none;"
/>

<section
  class="editor-view"
  bind:this={editorViewEl}
  ondragover={handleDragOver}
  ondragleave={handleDragLeave}
  ondrop={handleDrop}
>
  {#if isDragOver}
    <div class="drag-overlay">
      <IconFolderOpen size={36} stroke={1.8} />
      <span class="drag-text">Drop scripts here to open</span>
    </div>
  {/if}

  <div class="tabs-bar">
    <div class="tabs-row">
      {#each files as file (file.id)}
        <div
          class="tab"
          class:active={file.active}
          oncontextmenu={(e) => onmenu(e, file, 'tab')}
        >
          {#if renamingTabId === file.id}
            <input
              type="text"
              bind:value={renameValue}
              class="tab-rename-input"
              onblur={() => finishRename(file.id)}
              onkeydown={(e) => handleTabKey(e, file.id)}
              onclick={(e) => e.stopPropagation()}
            />
          {:else}
            <button class="tab-btn" onclick={() => onselect(file.id)} ondblclick={(e) => startRename(file, e)}>
              <span class="tab-title">{file.name}</span>
            </button>
          {/if}
          
          <button class="tab-close" title="Close" onclick={(e) => ondelete(file.id, e)}>
            <IconX size={10} stroke={2.5} />
          </button>
        </div>
      {/each}
    </div>

    <button class="add-btn" title="New Tab" onclick={onnew}>
      <IconPlus size={13} stroke={2.2} />
    </button>
  </div>

  {#if files.length === 0}
    <div class="empty-view">
      <button class="empty-btn" onclick={onnew}>
        <svg viewBox="0 0 116.7 134" class="empty-logo">
          <path fill="#404040" d="m97 2h-19c-9.6 0-26 10.3-32 25-2 4.9-2 13.9-2 25l-22 23h24v59h7.7l18.3-20v-37h15.9l8.1-25-24-1v-16.4c0-6.8 5.7-10.6 10.6-10.6s13.4 0.3 14.4 0v-22zm-50.3 72.8 22.3-20.9v21.1l-22.3-0.2z" />
        </svg>
        <span class="empty-text">Make a new script!</span>
      </button>
    </div>
  {:else}
    <div class="monaco-box" bind:this={editorContainer}></div>
  {/if}

  <div
    class="action-bar"
    bind:this={barEl}
    style="transform: translate({barPos.x}px, {barPos.y - (showconsole ? 180 : 0)}px); transition: {dragging ? 'none' : 'transform 0.24s cubic-bezier(0.16, 1, 0.3, 1)'};"
  >
    <button class="bar-btn exec" onclick={execute} disabled={busy} title="Execute (Ctrl+Enter)">
      <IconPlayerPlayFilled size={12} />
      <span>Execute</span>
    </button>

    <button
      class="bar-btn"
      class:armed={status.injected}
      onclick={inject}
      disabled={busy}
      title="Inject (Ctrl+I)"
    >
      <IconLink size={13} stroke={2} />
      <span>{status.injected ? "Injected" : "Inject"}</span>
    </button>

    <button class="bar-btn" onclick={triggerOpenFile} title="Open File">
      <IconFolderOpen size={13} stroke={2} />
      <span>Open</span>
    </button>

    <button class="bar-btn" onclick={saveFile} title="Save to Workspace (Ctrl+S)">
      <IconDeviceFloppy size={13} stroke={2} />
      <span>Save</span>
    </button>

    <button class="bar-btn" class:armed={clearArmed} onclick={clearCode} title="Clear">
      <IconTrash size={13} stroke={2} />
      <span>Clear</span>
    </button>

    <div class="status-pip" class:live={status.injected} title="Client status">
      <span class="dot"></span>
      <span class="state">{stateLabel}</span>
    </div>

    <div
      class="grip"
      title="Drag to reposition (Double click to reset)"
      onmousedown={startDrag}
      ondblclick={resetDrag}
      role="button"
      tabindex="0"
    >
      <IconGripVertical size={14} stroke={1.5} />
    </div>
  </div>

  <div class="console-drawer" class:open={showconsole}>
    <div class="console-head">
      <div class="console-left">
        <IconTerminal2 size={14} stroke={2} class="console-icon" />
        <span class="console-title">Console</span>
      </div>

      <div class="console-right">
        <button class="icon-btn" title="Clear" onclick={onclearconsole}>
          <IconTrash size={12} stroke={2} />
        </button>
        <button class="icon-btn" title="Close" onclick={() => showconsole = false}>
          <IconX size={11} stroke={2.5} />
        </button>
      </div>
    </div>

    <div class="console-content">
      {#if logs.length === 0}
        <div class="empty-logs">Console output is empty</div>
      {:else}
        <div class="log-lines">
          {#each logs as log}
            <div class="log-row {log.type}">
              {#if log.ts}<span class="ts">{log.ts}</span>{/if}
              {#if log.text.startsWith('[executor]')}
                <span class="tag">[executor]</span>
                <span class="msg">{log.text.slice(9)}</span>
              {:else}
                <span class="msg">{log.text}</span>
              {/if}
            </div>
          {/each}
        </div>
      {/if}
    </div>
  </div>
</section>

<style>
  .editor-view {
    display: flex;
    flex-direction: column;
    width: 100%;
    height: 100%;
    background: #1a1a1a;
    position: relative;
    overflow: hidden;
  }

  .drag-overlay {
    position: absolute;
    inset: 0;
    z-index: 50;
    background: rgba(20, 20, 20, 0.88);
    backdrop-filter: blur(4px);
    border: 2px dashed rgba(var(--accent-rgb), 0.6);
    border-radius: 8px;
    margin: 8px;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    gap: 12px;
    pointer-events: none;
    color: var(--accent);
  }

  .drag-text {
    font-size: 13px;
    font-family: 'Syne', sans-serif;
    color: #fff;
    font-weight: 500;
  }

  .tabs-bar {
    display: flex;
    align-items: center;
    justify-content: space-between;
    height: 42px;
    background: #161616;
    border-bottom: 1px solid rgba(255, 255, 255, 0.04);
    padding: 0 10px;
    box-sizing: border-box;
    flex-shrink: 0;
    gap: 6px;
  }

  .tabs-row {
    display: flex;
    align-items: center;
    gap: 6px;
    flex: 1;
    overflow-x: auto;
    scrollbar-width: none;
  }

  .tabs-row::-webkit-scrollbar {
    display: none;
  }

  .tab {
    display: flex;
    align-items: center;
    height: var(--tab-h, 28px);
    padding: 0 8px 0 10px;
    border-radius: 6px;
    background: #1f1f1f;
    color: #888;
    gap: 8px;
    flex-shrink: 0;
    transition: 0.12s ease;
  }

  .tab:hover {
    background: #242424;
    color: #d1d1d1;
  }

  .tab.active {
    background: #282828;
    color: #fff;
  }

  .tab-btn {
    display: flex;
    align-items: center;
    background: transparent;
    border: none;
    color: inherit;
    font-family: 'Syne', sans-serif;
    font-size: 11.5px;
    cursor: pointer;
    padding: 0;
    outline: none;
  }

  .tab-title {
    white-space: nowrap;
  }

  .tab-rename-input {
    background: #141414;
    border: 1px solid var(--accent);
    border-radius: 4px;
    color: #fff;
    font-family: 'Syne', sans-serif;
    font-size: 11.5px;
    padding: 1px 5px;
    width: 80px;
    outline: none;
  }

  .tab-close {
    display: grid;
    place-items: center;
    width: 18px;
    height: 18px;
    border-radius: 4px;
    background: transparent;
    border: none;
    color: #777;
    cursor: pointer;
    padding: 0;
    transition: 0.12s ease;
  }

  .tab-close:hover {
    background: rgba(255, 255, 255, 0.1);
    color: #fff;
  }

  .add-btn {
    display: grid;
    place-items: center;
    width: 28px;
    height: 28px;
    border-radius: 6px;
    background: transparent;
    border: none;
    color: #888;
    cursor: pointer;
    transition: 0.15s ease;
    padding: 0;
  }

  .add-btn:hover {
    background: #242424;
    color: #fff;
  }

  .empty-view {
    flex: 1;
    display: grid;
    place-items: center;
    width: 100%;
    height: 100%;
  }

  .empty-btn {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 14px;
    background: transparent;
    border: none;
    cursor: pointer;
    padding: 20px;
  }

  .empty-logo {
    width: 44px;
    height: 50px;
  }

  .empty-text {
    font-family: 'Syne', sans-serif;
    font-size: 13.5px;
    color: #555;
    transition: 0.15s ease;
  }

  .empty-btn:hover .empty-text {
    color: #888;
  }

  .monaco-box {
    flex: 1;
    width: 100%;
    height: 100%;
    overflow: hidden;
  }

  .action-bar {
    position: absolute;
    bottom: 18px;
    right: 20px;
    z-index: 10;
    display: inline-flex;
    align-items: center;
    height: 36px;
    gap: 2px;
    background: #171717;
    border: 1px solid rgba(255, 255, 255, 0.08);
    border-radius: 8px;
    padding: 0 4px;
    box-shadow: 0 8px 24px rgba(0, 0, 0, 0.5);
    user-select: none;
    box-sizing: border-box;
  }

  .bar-btn {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    gap: 6px;
    height: 28px;
    padding: 0 9px;
    font-family: 'Syne', sans-serif;
    font-size: 11.5px;
    cursor: pointer;
    transition: 0.15s ease;
    border: none;
    border-radius: 6px;
    background: transparent;
    color: #888;
  }

  .bar-btn:hover {
    color: #fff;
    background: rgba(255, 255, 255, 0.04);
  }

  .bar-btn.exec {
    background: #322A45;
    color: #fff;
    padding: 0 10px;
  }

  .bar-btn.exec:hover {
    background: radial-gradient(ellipse 90% 100% at 50% 50%, rgba(var(--accent-rgb), 0.42) 0%, #191919 85%);
  }

  .bar-btn.armed {
    color: #fff;
    background: rgba(var(--accent-rgb), 0.25);
  }

  .bar-btn:disabled {
    opacity: 0.45;
    cursor: not-allowed;
  }

  .status-pip {
    display: inline-flex;
    align-items: center;
    gap: 5px;
    height: 28px;
    padding: 0 8px 0 7px;
    margin-left: 4px;
    font-family: 'Syne', sans-serif;
    font-size: 10px;
    color: #666;
    border-left: 1px solid rgba(255, 255, 255, 0.06);
  }

  .status-pip .dot {
    width: 6px;
    height: 6px;
    border-radius: 50%;
    background: #c83232;
  }

  .status-pip.live .dot {
    background: #32c85a;
    box-shadow: 0 0 6px rgba(50, 200, 90, 0.8);
  }

  .status-pip.live .state {
    color: #32c85a;
  }

  .grip {
    display: grid;
    place-items: center;
    width: 16px;
    height: 28px;
    cursor: grab;
    color: #4a4a4a;
    transition: 0.15s ease;
    border-radius: 4px;
    margin: 0 2px 0 1px;
  }

  .grip:hover, .grip:active {
    color: #999;
    cursor: grabbing;
    background: rgba(255, 255, 255, 0.04);
  }

  .console-drawer {
    position: absolute;
    bottom: 0;
    left: 0;
    right: 0;
    height: 175px;
    background: #141414;
    border-top: 1px solid rgba(255, 255, 255, 0.08);
    display: flex;
    flex-direction: column;
    z-index: 9;
    transform: translateY(100%);
    transition: transform 0.24s cubic-bezier(0.16, 1, 0.3, 1);
    box-shadow: 0 -4px 16px rgba(0, 0, 0, 0.5);
  }

  .console-drawer.open {
    transform: translateY(0);
  }

  .console-head {
    display: flex;
    align-items: center;
    justify-content: space-between;
    height: 26px;
    padding: 0 10px;
    background: #181818;
    border-bottom: 1px solid rgba(255, 255, 255, 0.04);
    flex-shrink: 0;
  }

  .console-left {
    display: flex;
    align-items: center;
    gap: 6px;
  }

  .console-icon {
    color: var(--accent);
  }

  .console-title {
    font-family: 'Syne', sans-serif;
    font-size: 11px;
    color: #fff;
  }

  .console-right {
    display: flex;
    align-items: center;
    gap: 4px;
  }

  .icon-btn {
    display: grid;
    place-items: center;
    width: 20px;
    height: 20px;
    background: transparent;
    border: none;
    color: #777;
    cursor: pointer;
    border-radius: 4px;
    transition: 0.15s ease;
  }

  .icon-btn:hover {
    color: #fff;
    background: #242424;
  }

  .console-content {
    flex: 1;
    padding: 8px 12px;
    overflow-y: auto;
    font-family: 'JetBrains Mono', monospace;
    font-size: 11.5px;
    background: #121212;
  }

  .empty-logs {
    color: #666;
    font-size: 11px;
    font-style: italic;
  }

  .log-lines {
    display: flex;
    flex-direction: column;
    gap: 4px;
  }

  .log-row {
    display: flex;
    align-items: flex-start;
    gap: 6px;
    line-height: 1.4;
    word-break: break-all;
  }

  .tag {
    color: var(--accent);
  }

  .ts {
    color: #555;
    font-variant-numeric: tabular-nums;
  }

  .msg {
    color: #fff;
  }

  .log-row.error .msg {
    color: #ff3b5c;
  }

  .log-row.warn .msg {
    color: #ffa83c;
  }

  .log-row.accent .msg {
    color: var(--accent);
  }
</style>
