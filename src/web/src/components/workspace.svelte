<script>
  import { onMount } from "svelte";
  import { fly } from "svelte/transition";
  import {
    IconPlus,
    IconRefresh,
    IconChevronDown,
    IconChevronRight,
    IconFolder,
    IconFolderFilled,
    IconFileCode,
    IconX,
    IconTerminal2,
    IconDeviceDesktop
  } from "@tabler/icons-svelte";
  import { invoke } from "../lib/bridge.js";

  let {
    files = $bindable([]),
    onopenfile,
    onnewfile,
    ondeletefile,
    onrenamefile,
    onmovefile,
    onrefresh,
    onmenu,
    showconsole = $bindable(false),
    ontoggleconsole,
    ontoast,
    status = $bindable({ roblox: false, injected: false })
  } = $props();

  let query = $state("");
  let renamingId = $state(null);
  let renameName = $state("");

  // bullshit
  let dragFile = $state(null);
  let isDragging = $state(false);
  let dragGhostX = $state(0);
  let dragGhostY = $state(0);
  let dropTarget = $state(null);
  let mouseStartX = 0;
  let mouseStartY = 0;
  let dragThreshold = 5;

  let openFolders = $state({
    autoexec: true,
    Workspace: true,
    scripts: true
  });

  const folders = ["autoexec", "Workspace", "scripts"];

  let folderEls = {};

  let showClients = $state(false);
  let selectedClientId = $state(0);
  let clients = $state([]);

  async function refreshClients() {
    try {
      let list = await invoke("get_clients");
      clients = Array.isArray(list) ? list : [];
      if (selectedClientId && !clients.some((c) => c.id === selectedClientId)) {
        selectedClientId = 0;
      }
      if (!selectedClientId && clients.length) {
        selectedClientId = clients[0].id;
      }
    } catch (err) {
      clients = [];
    }
  }

  $effect(() => {
    if (!showClients) return;
    refreshClients();
    let timer = setInterval(refreshClients, 1500);
    return () => clearInterval(timer);
  });

  function toggleFolder(f) {
    openFolders[f] = !openFolders[f];
  }

  function pickClient(client) {
    selectedClientId = client.id;
    ontoast?.(`Selected ${client.displayName} (PID: ${client.pid})`);
  }

  function onFileMouseDown(e, file) {
    if (e.button !== 0) return;
    if (e.target.closest('.del-btn') || e.target.closest('.rename-input')) return;
    e.preventDefault();
    dragFile = file;
    mouseStartX = e.clientX;
    mouseStartY = e.clientY;
    isDragging = false;
  }

  function onGlobalMouseMove(e) {
    if (!dragFile) return;

    let dx = e.clientX - mouseStartX;
    let dy = e.clientY - mouseStartY;

    if (!isDragging && Math.abs(dx) + Math.abs(dy) > dragThreshold) {
      isDragging = true;
    }

    if (isDragging) {
      dragGhostX = e.clientX;
      dragGhostY = e.clientY;

      let hit = null;
      for (let f of folders) {
        let el = folderEls[f];
        if (el) {
          let rect = el.getBoundingClientRect();
          if (e.clientX >= rect.left && e.clientX <= rect.right &&
              e.clientY >= rect.top && e.clientY <= rect.bottom) {
            hit = f;
            break;
          }
        }
      }
      dropTarget = hit;
    }
  }

  function onGlobalMouseUp(e) {
    if (!dragFile) return;

    if (isDragging && dropTarget) {
      let fromFolder = (dragFile.folder || "scripts").toLowerCase();
      let toFolder = dropTarget.toLowerCase();
      if (fromFolder !== toFolder) {
        onmovefile?.(dragFile, fromFolder, toFolder);
      }
    }

    dragFile = null;
    isDragging = false;
    dropTarget = null;
  }

  onMount(() => {
    window.addEventListener("mousemove", onGlobalMouseMove);
    window.addEventListener("mouseup", onGlobalMouseUp);
    return () => {
      window.removeEventListener("mousemove", onGlobalMouseMove);
      window.removeEventListener("mouseup", onGlobalMouseUp);
    };
  });

  export function startRename(file, e) {
    e?.stopPropagation();
    renamingId = file.id;
    renameName = file.name;
  }

  function saveRename(id) {
    if (renameName.trim()) {
      let finalName = renameName.trim();
      if (!finalName.endsWith(".lua") && !finalName.endsWith(".luau") && !finalName.endsWith(".txt")) {
        finalName += ".lua";
      }
      files = files.map(f => f.id === id ? { ...f, name: finalName } : f);
      onrenamefile?.(id, finalName);
    }
    renamingId = null;
  }

  function handleKey(e, id) {
    if (e.key === "Enter") saveRename(id);
    if (e.key === "Escape") renamingId = null;
  }

  function getFolderFiles(f) {
    let q = query.trim().toLowerCase();
    return files.filter(file => {
      let matchFolder = (file.folder || "scripts").toLowerCase() === f.toLowerCase();
      let matchQuery = !q || file.name.toLowerCase().includes(q) || (file.content && file.content.toLowerCase().includes(q));
      return matchFolder && matchQuery;
    });
  }
</script>

{#if isDragging && dragFile}
  <div class="drag-ghost" style="left:{dragGhostX + 12}px;top:{dragGhostY - 10}px;">
    <IconFileCode size={12} stroke={1.8} />
    <span>{dragFile.name}</span>
  </div>
{/if}

<aside class="workspace" oncontextmenu={(e) => onmenu(e, null, 'workspace')}>
  <div class="search-wrap">
    <input
      type="text"
      placeholder="Search files..."
      bind:value={query}
      class="search-input"
    />
  </div>

  <div class="explorer">
    <div class="header-row">
      <span class="heading">Workspace</span>
      <div class="actions">
        <button class="icon-btn" title="New File" onclick={() => onnewfile?.("scripts")}>
          <IconPlus size={13} stroke={2.2} />
        </button>
        <button class="icon-btn" title="Refresh Workspace" onclick={onrefresh}>
          <IconRefresh size={13} stroke={2} />
        </button>
      </div>
    </div>

    <div class="folder-tree">
      {#each folders as f}
        <div class="folder-group">
          <div
            class="folder-header"
            class:drag-target={isDragging && dropTarget === f}
            bind:this={folderEls[f]}
            onclick={() => { if (!isDragging) toggleFolder(f); }}
            onkeydown={(e) => { if (e.key === 'Enter' || e.key === ' ') toggleFolder(f); }}
            oncontextmenu={(e) => { e.stopPropagation(); onmenu(e, { isFolder: true, name: f.toLowerCase() }, 'folder'); }}
            role="button"
            tabindex="0"
          >
            <span class="chevron" class:open={openFolders[f]}>
              <IconChevronRight size={11} stroke={2.5} />
            </span>
            {#if openFolders[f]}
              <IconFolderFilled size={13} class="folder-icon open" />
            {:else}
              <IconFolder size={13} stroke={1.8} class="folder-icon" />
            {/if}
            <span class="folder-name">{f}</span>
            <span class="folder-count">{getFolderFiles(f).length}</span>
          </div>

          {#if openFolders[f]}
            <div class="folder-contents" transition:fly={{ y: -4, duration: 120 }}>
              {#each getFolderFiles(f) as file (file.id)}
                <div
                  class="file-row"
                  class:is-dragging={isDragging && dragFile?.id === file.id}
                  onmousedown={(e) => onFileMouseDown(e, file)}
                  oncontextmenu={(e) => onmenu(e, file, 'workspace')}
                  onclick={() => { if (!isDragging) onopenfile?.(file); }}
                  ondblclick={(e) => startRename(file, e)}
                  role="button"
                  tabindex="0"
                  onkeydown={(e) => { if (e.key === 'Enter') onopenfile?.(file); }}
                >
                  <div class="file-btn">
                    <IconFileCode size={13} stroke={1.8} class="file-icon" />
                    {#if renamingId === file.id}
                      <input
                        type="text"
                        bind:value={renameName}
                        class="rename-input"
                        onblur={() => saveRename(file.id)}
                        onkeydown={(e) => handleKey(e, file.id)}
                        onclick={(e) => e.stopPropagation()}
                      />
                    {:else}
                      <span class="name">{file.name}</span>
                    {/if}
                  </div>

                  <button class="del-btn" title="Delete" onclick={(e) => { e.stopPropagation(); ondeletefile?.(file.id); }}>
                    <IconX size={11} stroke={2.5} />
                  </button>
                </div>
              {/each}

              {#if getFolderFiles(f).length === 0}
                <div class="empty-folder-hint">empty</div>
              {/if}
            </div>
          {/if}
        </div>
      {/each}
    </div>
  </div>

  {#if showClients}
    <div class="clients-drawer" transition:fly={{ y: 20, duration: 180 }}>
      <div class="drawer-header">
        <span>Attached Clients ({clients.length})</span>
        <button class="icon-btn" onclick={() => (showClients = false)}>
          <IconX size={12} stroke={2.2} />
        </button>
      </div>

      {#if clients.length === 0}
        <p class="clients-empty">No Roblox client found. Launch Roblox to attach.</p>
      {:else}
        <div class="clients-list">
          {#each clients as client (client.id)}
            <button
              class="client-row"
              class:selected={selectedClientId === client.id}
              onclick={() => pickClient(client)}
            >
              <div class="client-mark" class:live={status.injected}>
                <IconDeviceDesktop size={14} stroke={1.8} />
              </div>
              <div class="client-info">
                <span class="client-name">{client.displayName}</span>
                <span class="client-sub">
                  PID {client.pid}{status.injected ? " · injected" : ""}
                </span>
              </div>
            </button>
          {/each}
        </div>
      {/if}
    </div>
  {/if}

  <div class="footer">
    <button class="footer-btn" class:active={showconsole} onclick={ontoggleconsole}>
      <IconTerminal2 size={13} stroke={2} />
      <span>Console</span>
    </button>

    <button class="footer-btn" class:active={showClients} onclick={() => showClients = !showClients}>
      <IconDeviceDesktop size={13} stroke={2} />
      <span>Clients</span>
    </button>
  </div>
</aside>

<style>
  .drag-ghost {
    position: fixed;
    z-index: 9999;
    pointer-events: none;
    display: flex;
    align-items: center;
    gap: 5px;
    background: rgba(var(--accent-rgb), 0.15);
    border: 1px solid rgba(var(--accent-rgb), 0.5);
    border-radius: 5px;
    padding: 3px 8px;
    color: #fff;
    font-family: 'Syne', sans-serif;
    font-size: 10.5px;
    white-space: nowrap;
    backdrop-filter: blur(6px);
  }

  .workspace {
    width: 220px;
    height: 100%;
    background-color: #151515;
    border-right: 1px solid rgba(255, 255, 255, 0.04);
    display: flex;
    flex-direction: column;
    box-sizing: border-box;
    position: relative;
    user-select: none;
  }

  .search-wrap {
    padding: 10px 12px 6px;
  }

  .search-input {
    width: 100%;
    height: 28px;
    background: #1a1a1a;
    border: 1px solid rgba(255, 255, 255, 0.06);
    border-radius: 6px;
    padding: 0 10px;
    box-sizing: border-box;
    color: #dedede;
    font-size: 11px;
    font-family: 'Syne', sans-serif;
    outline: none;
    transition: 0.15s ease;
  }

  .search-input:focus {
    border-color: rgba(255, 255, 255, 0.15);
    background: #1e1e1e;
  }

  .search-input::placeholder {
    color: #666;
  }

  .explorer {
    display: flex;
    flex-direction: column;
    flex: 1;
    overflow: hidden;
    padding: 6px 8px;
  }

  .header-row {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 4px 6px 8px;
  }

  .heading {
    font-size: 11.5px;
    color: #888;
    font-weight: 500;
    font-family: 'Syne', sans-serif;
  }

  .actions {
    display: flex;
    align-items: center;
    gap: 4px;
  }

  .icon-btn {
    display: grid;
    place-items: center;
    width: 20px;
    height: 20px;
    border-radius: 4px;
    background: transparent;
    border: none;
    color: #777;
    cursor: pointer;
    transition: 0.12s ease;
  }

  .icon-btn:hover {
    background: #202020;
    color: #fff;
  }

  .folder-tree {
    display: flex;
    flex-direction: column;
    gap: 3px;
    overflow-y: auto;
    flex: 1;
  }

  .folder-group {
    display: flex;
    flex-direction: column;
  }

  .folder-header {
    display: flex;
    align-items: center;
    gap: 6px;
    height: 26px;
    padding: 0 6px;
    background: transparent;
    border: none;
    border-radius: 5px;
    color: #aaa;
    font-family: 'Syne', sans-serif;
    font-size: 11px;
    cursor: pointer;
    text-align: left;
    transition: 0.12s ease;
  }

  .folder-header:hover {
    background: #1b1b1b;
    color: #fff;
  }

  .folder-header.drag-target {
    background: rgba(var(--accent-rgb), 0.12);
    border: 1px dashed rgba(var(--accent-rgb), 0.6);
    color: #fff;
  }

  .chevron {
    display: grid;
    place-items: center;
    color: #666;
    transition: transform 0.15s ease;
  }

  .chevron.open {
    transform: rotate(90deg);
  }

  :global(.folder-icon) {
    color: #888;
  }

  :global(.folder-icon.open) {
    color: #d4a373;
  }

  .folder-name {
    flex: 1;
    font-weight: 500;
  }

  .folder-count {
    font-size: 9.5px;
    color: #555;
    background: #1a1a1a;
    padding: 1px 5px;
    border-radius: 4px;
  }

  .folder-contents {
    display: flex;
    flex-direction: column;
    gap: 1px;
    padding-left: 14px;
    margin-top: 1px;
  }

  .empty-folder-hint {
    padding: 3px 18px;
    font-size: 10px;
    color: #4a4a4a;
    font-style: italic;
  }

  .folder-header * {
    pointer-events: none;
  }

  .file-row {
    display: flex;
    align-items: center;
    justify-content: space-between;
    height: 24px;
    padding: 0 6px;
    border-radius: 5px;
    color: #888;
    cursor: grab;
    user-select: none;
    -webkit-user-select: none;
    transition: 0.12s ease;
  }

  .file-row * {
    pointer-events: none;
  }

  .file-row .rename-input,
  .file-row .del-btn {
    pointer-events: auto;
  }

  .file-row.is-dragging {
    opacity: 0.35;
    pointer-events: none;
  }

  .file-row:active {
    cursor: grabbing;
  }

  .file-row:hover {
    background: #1c1c1c;
    color: #ccc;
  }

  .file-btn {
    display: flex;
    align-items: center;
    gap: 6px;
    background: transparent;
    border: none;
    color: inherit;
    font-family: 'Syne', sans-serif;
    font-size: 11px;
    cursor: pointer;
    flex: 1;
    min-width: 0;
    padding: 0;
    text-align: left;
  }

  :global(.file-icon) {
    color: #666;
    flex-shrink: 0;
  }

  .name {
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .rename-input {
    background: #111;
    border: 1px solid var(--accent);
    border-radius: 4px;
    color: #fff;
    font-family: 'Syne', sans-serif;
    font-size: 10.5px;
    padding: 1px 4px;
    width: 100%;
    outline: none;
  }

  .del-btn {
    display: none;
    place-items: center;
    width: 16px;
    height: 16px;
    border-radius: 3px;
    background: transparent;
    border: none;
    color: #666;
    cursor: pointer;
    padding: 0;
  }

  .file-row:hover .del-btn {
    display: grid;
  }

  .del-btn:hover {
    color: var(--accent);
  }

  .footer {
    display: flex;
    align-items: center;
    gap: 6px;
    padding: 8px 10px;
    border-top: 1px solid rgba(255, 255, 255, 0.04);
    background: #141414;
  }

  .footer-btn {
    flex: 1;
    height: 26px;
    border-radius: 5px;
    border: 1px solid rgba(255, 255, 255, 0.05);
    background: #1a1a1a;
    color: #888;
    font-family: 'Syne', sans-serif;
    font-size: 10.5px;
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 5px;
    cursor: pointer;
    transition: 0.12s ease;
  }

  .footer-btn:hover {
    background: #222;
    color: #fff;
  }

  .footer-btn.active {
    background: #252525;
    color: #fff;
    border-color: rgba(255, 255, 255, 0.15);
  }

  .clients-drawer {
    position: absolute;
    bottom: 45px;
    left: 8px;
    right: 8px;
    background: #1c1c1c;
    border: 1px solid rgba(255, 255, 255, 0.08);
    border-radius: 8px;
    padding: 8px;
    display: flex;
    flex-direction: column;
    gap: 6px;
    box-shadow: 0 8px 24px rgba(0, 0, 0, 0.5);
    z-index: 20;
  }

  .drawer-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    font-size: 10.5px;
    color: #888;
    font-family: 'Syne', sans-serif;
    padding: 0 2px;
  }

  .clients-list {
    display: flex;
    flex-direction: column;
    gap: 4px;
  }

  .client-row {
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 6px;
    border-radius: 6px;
    background: #161616;
    border: 1px solid rgba(255, 255, 255, 0.04);
    cursor: pointer;
    text-align: left;
    transition: 0.12s ease;
  }

  .client-row:hover {
    background: #202020;
    border-color: rgba(255, 255, 255, 0.1);
  }

  .client-row.selected {
    border-color: var(--accent);
    background: #212121;
  }

  .client-pfp {
    width: 26px;
    height: 26px;
    border-radius: 50%;
  }

  .client-mark {
    display: grid;
    place-items: center;
    width: 26px;
    height: 26px;
    border-radius: 50%;
    background: #1a1a1a;
    border: 1px solid rgba(255, 255, 255, 0.06);
    color: #777;
    flex-shrink: 0;
  }

  .client-mark.live {
    color: #32c85a;
    border-color: rgba(50, 200, 90, 0.4);
  }

  .clients-empty {
    margin: 0;
    padding: 6px 2px;
    font-size: 10.5px;
    color: #666;
    font-style: italic;
    line-height: 1.4;
  }

  .client-info {
    display: flex;
    flex-direction: column;
  }

  .client-name {
    font-size: 11px;
    color: #fff;
  }

  .client-sub {
    font-size: 9.5px;
    color: #777;
  }
</style>
