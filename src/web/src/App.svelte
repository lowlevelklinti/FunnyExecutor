<script>
  import { onMount, tick } from "svelte";
  import { fade } from "svelte/transition";
  import { invoke } from "./lib/bridge.js";
  import { settings, events, applyChrome, loadSettings } from "./lib/settings.svelte.js";
  import Splash from "./components/splash.svelte";
  import Titlebar from "./components/titlebar.svelte";
  import Sidebar from "./components/sidebar.svelte";
  import Workspace from "./components/workspace.svelte";
  import Editor from "./components/editor.svelte";
  import Home from "./components/home.svelte";
  import Scripthub from "./components/scripthub.svelte";
  import Settings from "./components/settings.svelte";
  import Contextmenu from "./components/contextmenu.svelte";
  import Toast from "./components/toast.svelte";

  let splash = $state(settings.general.splash);
  let tab = $state("editor");

  const defaultcode = `--[[\n  _____ _         _       _   _   _\n |  ___| |_ _ _ __| |_ ___| | | |_ _\n | |_  | __| '__/ __| __/ _ \\ | |  _|\n |  _| | |_| | | (__| || (_) || |_| |\n |_|   \\__|_|  \\___|\\___\\___/ \\__\\__|\n--]]\n\nprint("Funny Executor loaded")\n`;

  let tabs = $state([
    {
      id: 1,
      name: "Script 1.lua",
      content: defaultcode,
      active: true,
      workspaceId: null,
    },
  ]);

  let workspaceFiles = $state([]);

  let showconsole = $state(false);
  let logs = $state([{ type: "info", text: "[executor] Funny Executor has loaded!" }]);

  let menu = $state({
    visible: false,
    x: 0,
    y: 0,
    type: "workspace",
    target: null,
  });

  let toast = $state({
    message: "",
    visible: false,
    timer: null,
  });

  let editorRef = $state(null);
  let workspaceRef = $state(null);

  // executor state, refreshed from the python shell
  let status = $state({
    state: "idle",
    injected: false,
    roblox: false,
    pid: 0,
    placeId: 0,
    gameName: "",
    creator: "",
  });

  let consoleTimer = null;
  let statusTimer = null;

  function showToast(msg) {
    toast.message = msg;
    toast.visible = true;
    if (toast.timer) clearTimeout(toast.timer);
    toast.timer = setTimeout(() => {
      toast.visible = false;
    }, 2000);
  }

  function pushLog(text, type = "info") {
    let cap = Number(settings.execution.maxLogLines) || 500;
    logs = [
      ...logs,
      {
        type,
        text,
        ts: settings.execution.timestamps ? new Date().toLocaleTimeString() : null,
      },
    ].slice(-cap);
  }

  // win32 console colour ids the shell forwards -> css log types
  const COLOR_TYPES = {
    10: "info",
    14: "warn",
    12: "error",
    13: "accent",
  };

  async function pollConsole() {
    try {
      let lines = await invoke("get_console");
      if (!Array.isArray(lines) || lines.length === 0) return;
      let cap = Number(settings.execution.maxLogLines) || 500;
      let next = [...logs];
      for (let line of lines) {
        next.push({
          type: COLOR_TYPES[line.color] || "info",
          text: line.text,
          ts: settings.execution.timestamps ? new Date().toLocaleTimeString() : null,
        });
      }
      logs = next.slice(-cap);
    } catch (err) {
      // the browser build has no console buffer, nothing to poll
    }
  }

  async function pollStatus() {
    try {
      let next = await invoke("get_status");
      if (next && typeof next === "object") status = next;
    } catch (err) {
      status = { ...status, state: "unavailable" };
    }
  }

  async function clearConsoleOutput() {
    try {
      await invoke("clear_console");
    } catch (err) {}
    logs = [];
  }

  function getActiveTab() {
    return tabs.find((t) => t.active) || null;
  }

  async function selectTab(id) {
    if (editorRef) {
      let current = getActiveTab();
      if (current) current.content = editorRef.getValue();
    }

    tabs = tabs.map((t) => ({ ...t, active: t.id === id }));
    await tick();
    let target = tabs.find((t) => t.id === id);
    if (editorRef && target) {
      editorRef.setValue(target.content || "");
    }
  }

  async function addNewTab() {
    if (editorRef) {
      let current = getActiveTab();
      if (current) current.content = editorRef.getValue();
    }

    let num = tabs.length + 1;
    let name = `Script ${num}.lua`;
    let newTab = {
      id: Date.now(),
      name: name,
      content: defaultcode,
      active: true,
      workspaceId: null,
    };
    tabs = tabs.map((t) => ({ ...t, active: false })).concat(newTab);
    await tick();
    if (editorRef) {
      editorRef.init();
      editorRef.setValue(newTab.content);
    }
    closeMenu();
  }

  async function duplicateTab(targetTab) {
    if (!targetTab) return;
    if (editorRef) {
      let current = getActiveTab();
      if (current) current.content = editorRef.getValue();
    }

    let base = targetTab.name.replace(/\.lua$/, "");
    let copy = {
      id: Date.now(),
      name: `${base}_copy.lua`,
      content: targetTab.content || "",
      active: true,
      workspaceId: null,
    };
    tabs = tabs.map((t) => ({ ...t, active: false })).concat(copy);
    await tick();
    if (editorRef) {
      editorRef.init();
      editorRef.setValue(copy.content);
    }
    closeMenu();
  }

  async function deleteTab(id, e) {
    if (e) e.stopPropagation();
    tabs = tabs.filter((t) => t.id !== id);
    if (tabs.length > 0) {
      if (!tabs.some((t) => t.active)) {
        tabs[0].active = true;
      }
      let active = getActiveTab();
      await tick();
      if (editorRef && active) {
        editorRef.setValue(active.content || "");
      }
    } else {
      if (editorRef) editorRef.destroy();
    }
    closeMenu();
  }

  async function closeOtherTabs(keepId) {
    tabs = tabs.filter((t) => t.id === keepId);
    if (tabs.length > 0) {
      tabs[0].active = true;
      await tick();
      if (editorRef) {
        editorRef.setValue(tabs[0].content || "");
      }
    }
    closeMenu();
  }

  function closeAllTabs() {
    tabs = [];
    if (editorRef) editorRef.destroy();
    closeMenu();
  }

  function handleTabRenamed(id, newName) {
    let target = tabs.find((t) => t.id === id);
    if (target && target.workspaceId) {
      workspaceFiles = workspaceFiles.map((f) =>
        f.id === target.workspaceId ? { ...f, name: newName } : f,
      );
    }
  }

  async function saveActiveTab(silent = false) {
    let current = getActiveTab();
    if (!current) {
      if (!silent) showToast("Nothing to save");
      return;
    }
    if (editorRef) current.content = editorRef.getValue();

    let existingFile = current.workspaceId
      ? workspaceFiles.find((f) => f.id === current.workspaceId)
      : null;

    if (existingFile) {
      let folder = existingFile.folder || "scripts";
      workspaceFiles = workspaceFiles.map((f) =>
        f.id === current.workspaceId
          ? { ...f, name: current.name, content: current.content }
          : f,
      );
      try {
        await invoke("write_workspace_file", {
          folder,
          name: current.name,
          content: current.content,
        });
      } catch (err) {}
      if (!silent) showToast(`Saved ${current.name}`);
    } else {
      let newWsFile = {
        id: Date.now(),
        name: current.name,
        content: current.content,
        folder: "scripts",
      };
      current.workspaceId = newWsFile.id;
      workspaceFiles = [...workspaceFiles, newWsFile];
      try {
        await invoke("write_workspace_file", {
          folder: "scripts",
          name: current.name,
          content: current.content,
        });
      } catch (err) {}
      if (!silent) showToast(`Saved ${current.name} to workspace/scripts`);
    }
  }

  async function openWorkspaceFile(file) {
    let existing = tabs.find((t) => t.workspaceId === file.id);
    if (existing) {
      await selectTab(existing.id);
      return;
    }

    if (editorRef) {
      let current = getActiveTab();
      if (current) current.content = editorRef.getValue();
    }

    let newTab = {
      id: Date.now(),
      name: file.name,
      content: file.content,
      active: true,
      workspaceId: file.id,
    };
    tabs = tabs.map((t) => ({ ...t, active: false })).concat(newTab);
    await tick();
    if (editorRef) {
      editorRef.init();
      editorRef.setValue(newTab.content);
    }
    showToast(`Opened ${file.name}`);
  }

  async function openLocalFile(name, content) {
    if (editorRef) {
      let current = getActiveTab();
      if (current) current.content = editorRef.getValue();
    }

    let newTab = {
      id: Date.now(),
      name: name,
      content: content,
      active: true,
      workspaceId: null,
    };
    tabs = tabs.map((t) => ({ ...t, active: false })).concat(newTab);
    await tick();
    if (editorRef) {
      editorRef.init();
      editorRef.setValue(newTab.content);
    }
    showToast(`Opened ${name}`);
  }

  async function newWorkspaceFile(folder = "scripts") {
    let targetFolder =
      typeof folder === "string" ? folder.toLowerCase() : "scripts";
    let num =
      workspaceFiles.filter(
        (f) => (f.folder || "scripts").toLowerCase() === targetFolder,
      ).length + 1;
    let name = `script_${num}.lua`;
    let file = {
      id: Date.now(),
      name: name,
      content: defaultcode,
      folder: targetFolder,
    };
    workspaceFiles = [...workspaceFiles, file];
    try {
      await invoke("write_workspace_file", {
        folder: targetFolder,
        name,
        content: defaultcode,
      });
    } catch (err) {}
    showToast(`Created ${name} in ${targetFolder}`);
  }

  async function deleteWorkspaceFile(id) {
    let file = workspaceFiles.find((f) => f.id === id);
    if (file) {
      try {
        await invoke("remove_workspace_file", {
          folder: file.folder || "scripts",
          name: file.name,
        });
      } catch (err) {}
    }
    workspaceFiles = workspaceFiles.filter((f) => f.id !== id);
    tabs = tabs.map((t) =>
      t.workspaceId === id ? { ...t, workspaceId: null } : t,
    );
    showToast("Deleted file from workspace");
  }

  function renameWorkspaceFile(id, newName) {
    let file = workspaceFiles.find((f) => f.id === id);
    if (file) {
      let oldName = file.name;
      let folder = file.folder || "scripts";
      try {
        invoke("remove_workspace_file", { folder, name: oldName });
        invoke("write_workspace_file", {
          folder,
          name: newName,
          content: file.content,
        });
      } catch (err) {}
    }
    workspaceFiles = workspaceFiles.map((f) =>
      f.id === id ? { ...f, name: newName } : f,
    );
    tabs = tabs.map((t) =>
      t.workspaceId === id ? { ...t, name: newName } : t,
    );
  }

  async function moveWorkspaceFile(file, fromFolder, toFolder) {
    if (!file || fromFolder.toLowerCase() === toFolder.toLowerCase()) return;
    let targetFolder = toFolder.toLowerCase();
    workspaceFiles = workspaceFiles.map((f) =>
      f.id === file.id ? { ...f, folder: targetFolder } : f,
    );
    try {
      await invoke("move_workspace_file", {
        fromFolder: fromFolder.toLowerCase(),
        toFolder: targetFolder,
        name: file.name,
      });
    } catch (err) {}
    showToast(`Moved ${file.name} to ${targetFolder}/`);
  }

  async function revealFolder(folderName) {
    try {
      await invoke("reveal_folder", { folderName: folderName || "scripts" });
      showToast(`Revealed ${folderName || "scripts"} in Explorer`);
    } catch (err) {
      showToast(`Opened folder`);
    }
    closeMenu();
  }

  function startRename(target, e) {
    if (menu.type === "tab") {
      if (editorRef) editorRef.startRename(target, e);
    } else {
      if (workspaceRef) workspaceRef.startRename(target, e);
    }
    closeMenu();
  }

  function openMenu(e, target = null, type = "workspace") {
    e.preventDefault();
    menu = {
      visible: true,
      x: Math.min(e.clientX, window.innerWidth - 180),
      y: Math.min(e.clientY, window.innerHeight - 220),
      type: type,
      target: target,
    };
  }

  function closeMenu() {
    menu.visible = false;
  }

  async function setTab(next) {
    tab = next;
    if (next === "editor") {
      await tick();
      if (editorRef && tabs.length > 0) editorRef.init();
    } else if (editorRef) {
      editorRef.destroy();
    }
  }

  async function loadHubScript(script) {
    let file = {
      id: Date.now(),
      name: `${script.name.toLowerCase().replace(/\s+/g, "_")}.lua`,
      content: script.code,
      active: true,
      workspaceId: null,
    };
    tabs = tabs.map((t) => ({ ...t, active: false })).concat(file);
    tab = "editor";
    await tick();
    if (editorRef) {
      editorRef.init();
      editorRef.setValue(file.content);
    }
  }

  async function executeHubScript(script) {
    try {
      await invoke("execute", { source: script.code });
      pushLog(`Executed ${script.name}`, "info");
      showToast(`Executed ${script.name}`);
    } catch (err) {
      pushLog(String(err?.message || err), "error");
      showToast(String(err?.message || "Execution failed"));
    }
  }

  async function refreshWorkspace(showNotify = true) {
    try {
      let diskFiles = await invoke("read_workspace_files");
      if (Array.isArray(diskFiles)) {
        workspaceFiles = diskFiles;
      }
      if (showNotify) showToast("Workspace refreshed");
    } catch (err) {
      if (showNotify) showToast("Workspace refreshed");
    }
  }

  onMount(() => {
    applyChrome();
    loadSettings().then(() => {
      splash = settings.general.splash;
      applyChrome();
    });
    refreshWorkspace(false);
    pollStatus();
    pollConsole();

    // the shell keeps a status flag and a console buffer for us to pull
    statusTimer = setInterval(pollStatus, 1000);
    consoleTimer = setInterval(pollConsole, 400);

    function onGlobalClick() {
      if (menu.visible) closeMenu();
    }

    function onGlobalKey(e) {
      if (e.key === "Escape") closeMenu();
    }

    function onGlobalShortcut(e) {
      if (!(e.ctrlKey || e.metaKey)) return;
      let key = e.key.toLowerCase();
      if (key === "s") {
        e.preventDefault();
        saveActiveTab();
      } else if (key === "enter") {
        e.preventDefault();
        editorRef?.runExecute?.();
      } else if (key === "i") {
        e.preventDefault();
        editorRef?.runInject?.();
      } else if (key === "n") {
        e.preventDefault();
        addNewTab();
      }
    }

    function onWorkspaceWiped() {
      workspaceFiles = [];
      tabs = tabs.map((t) => ({ ...t, workspaceId: null }));
    }

    window.addEventListener("click", onGlobalClick);
    window.addEventListener("keydown", onGlobalKey);
    window.addEventListener("keydown", onGlobalShortcut);
    window.addEventListener("funnyexecutor:workspace", onWorkspaceWiped);

    return () => {
      window.removeEventListener("click", onGlobalClick);
      window.removeEventListener("keydown", onGlobalKey);
      window.removeEventListener("keydown", onGlobalShortcut);
      window.removeEventListener("funnyexecutor:workspace", onWorkspaceWiped);
      clearInterval(statusTimer);
      clearInterval(consoleTimer);
    };
  });

  let lastSplashTick = 0;

  $effect(() => {
    let tick = events.replaySplash;
    if (tick === 0 || tick === lastSplashTick) return;
    lastSplashTick = tick;
    splash = true;
  });
</script>

<main class="window-container">
  {#if splash}
    <Splash onfinish={() => (splash = false)} />
  {:else}
    <div class="app-layout">
      <Titlebar />

      <div class="main-body">
        <Sidebar {tab} onchange={setTab} />

        <div class="content-wrapper">
          {#key tab}
            <div
              class="page-transition-container"
              in:fade={{ duration: 180 }}
              out:fade={{ duration: 120 }}
            >
              {#if tab === "editor"}
                <Workspace
                  bind:this={workspaceRef}
                  bind:files={workspaceFiles}
                  bind:showconsole
                  {status}
                  onopenfile={openWorkspaceFile}
                  onnewfile={newWorkspaceFile}
                  ondeletefile={deleteWorkspaceFile}
                  onrenamefile={renameWorkspaceFile}
                  onmovefile={moveWorkspaceFile}
                  onrefresh={() => refreshWorkspace(true)}
                  onmenu={openMenu}
                  ontoggleconsole={() => (showconsole = !showconsole)}
                  ontoast={showToast}
                />

                <Editor
                  bind:this={editorRef}
                  bind:files={tabs}
                  bind:showconsole
                  bind:logs
                  {status}
                  onselect={selectTab}
                  onnew={addNewTab}
                  ondelete={deleteTab}
                  onmenu={openMenu}
                  onsave={saveActiveTab}
                  onopenfile={openLocalFile}
                  onrenametab={handleTabRenamed}
                  onclearconsole={clearConsoleOutput}
                  ontoast={showToast}
                  onlog={pushLog}
                />
              {:else if tab === "home"}
                <Home
                  {status}
                  onnewscript={() => {
                    addNewTab();
                    setTab("editor");
                  }}
                  onopeneditor={() => setTab("editor")}
                  ontoast={showToast}
                />
              {:else if tab === "scripthub"}
                <Scripthub
                  {status}
                  onloadscript={loadHubScript}
                  onexecute={executeHubScript}
                  ontoast={showToast}
                />
              {:else if tab === "settings"}
                <Settings ontoast={showToast} />
              {/if}
            </div>
          {/key}
        </div>
      </div>

      <Contextmenu
        {menu}
        onnew={menu.type === "tab"
          ? addNewTab
          : (folder) =>
              newWorkspaceFile(typeof folder === "string" ? folder : "scripts")}
        onrename={startRename}
        onduplicate={menu.type === "tab" ? duplicateTab : () => {}}
        ondelete={menu.type === "tab" ? deleteTab : deleteWorkspaceFile}
        oncloseothers={closeOtherTabs}
        oncloseall={closeAllTabs}
        onopenfile={openWorkspaceFile}
        onrevealfolder={revealFolder}
      />

      <Toast message={toast.message} visible={toast.visible} />
    </div>
  {/if}
</main>

<style>
  /* inspired by israel maybe*/
  :global(:root) {
    --accent: #8a8a8a;
    --accent-rgb: 138, 138, 138;
    --nav-size: 38px;
    --nav-rail: 58px;
    --tab-h: 28px;
  }

  :global(html),
  :global(body) {
    margin: 0;
    padding: 0;
    width: 100%;
    height: 100%;
    background-color: #1a1a1a;
    overflow: hidden;
    font-family:
      "Syne",
      -apple-system,
      BlinkMacSystemFont,
      "Segoe UI",
      Roboto,
      sans-serif;
    font-weight: 400;
  }

  /* no scrollbar-width / scrollbar-color here on purpose: in Chromium they
     switch off the ::-webkit-scrollbar pseudo-elements entirely */
  :global(*::-webkit-scrollbar) {
    width: 12px;
    height: 12px;
  }

  :global(*::-webkit-scrollbar-track) {
    background: transparent;
  }

  :global(*::-webkit-scrollbar-thumb) {
    background: #303030;
    border-radius: 6px;
    border: 4px solid transparent;
    background-clip: padding-box;
  }

  :global(*::-webkit-scrollbar-thumb:hover) {
    background: #474747;
    background-clip: padding-box;
  }

  :global(*::-webkit-scrollbar-thumb:active) {
    background: #5a5a5a;
    background-clip: padding-box;
  }

  :global(*::-webkit-scrollbar-corner) {
    background: transparent;
  }

  .window-container {
    position: relative;
    width: 100%;
    height: 100%;
    box-sizing: border-box;
    background-color: #1a1a1a;
    display: flex;
    flex-direction: column;
    user-select: none;
    font-family: "Syne", sans-serif;
    font-weight: 400;
  }

  .app-layout {
    position: relative;
    display: flex;
    flex-direction: column;
    width: 100%;
    height: 100%;
    min-height: 0;
    background-color: #1a1a1a;
    overflow: hidden;
  }

  .main-body {
    display: flex;
    flex: 1;
    min-height: 0;
    overflow: hidden;
  }

  .content-wrapper {
    position: relative;
    flex: 1;
    height: 100%;
    overflow: hidden;
  }

  .page-transition-container {
    position: absolute;
    inset: 0;
    display: flex;
    width: 100%;
    height: 100%;
  }

</style>
