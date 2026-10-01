<script>
  import { fly, fade } from "svelte/transition";
  import { cubicOut } from "svelte/easing";
  import {
    IconAdjustments,
    IconCode,
    IconPlayerPlay,
    IconPalette,
    IconInfoCircle,
    IconRestore,
    IconAlertTriangle,
    IconBrandDiscord,
    IconExternalLink,
  } from "@tabler/icons-svelte";
  import {
    settings,
    set,
    resetAll,
    resetSection,
    replaySplash,
  } from "../lib/settings.svelte.js";
  import { isNative, listFiles, clearWorkspace, pathOf } from "../lib/bridge.js";

  let { ontoast } = $props();

  let activeSection = $state("general");
  let searchQuery = $state("");

  const ACCENTS = [
    { name: "Neutral", value: "#8a8a8a" },
    { name: "Slate", value: "#7f9cc0" },
    { name: "Teal", value: "#4fb3a4" },
    { name: "Olive", value: "#9aa855" },
    { name: "Sand", value: "#c2a878" },
    { name: "Violet", value: "#9d8bd0" },
  ];

  const FONT_OPTIONS = [
    { value: "jetbrains", label: "JetBrains Mono" },
    { value: "cascadia", label: "Cascadia Code" },
    { value: "consolas", label: "Consolas" },
    { value: "courier", label: "Courier New" },
    { value: "menlo", label: "Menlo" },
  ];

  const groups = {
    general: [
      {
        title: "Startup",
        rows: [
          {
            key: "splash",
            label: "Splash screen",
            desc: "Show the animated intro when the app launches",
            type: "toggle",
          },
          {
            key: "autosave",
            label: "Autosave",
            desc: "Write workspace files back a moment after you stop typing",
            type: "toggle",
          },
          {
            key: "autosaveDelay",
            label: "Autosave delay",
            desc: "How long to wait after the last keystroke",
            type: "range",
            min: 400,
            max: 5000,
            step: 100,
            unit: "ms",
          },
        ],
      },
      {
        title: "Session",
        rows: [
          {
            key: "rpcEnabled",
            label: "Discord rich presence",
            desc: "Show the current script and game status on your Discord profile",
            type: "toggle",
          },
          {
            type: "action",
            label: "Launch animation",
            desc: "Play the splash screen again without restarting",
            act: "replay",
          },
        ],
      },
    ],
    editor: [
      {
        title: "Text",
        rows: [
          {
            key: "fontFamily",
            label: "Font family",
            desc: "Monospace stack used by the code editor",
            type: "select",
            options: FONT_OPTIONS,
          },
          {
            key: "fontSize",
            label: "Font size",
            desc: "Base editor text size in pixels",
            type: "range",
            min: 10,
            max: 22,
            step: 1,
            unit: "px",
          },
          {
            key: "tabSize",
            label: "Tab size",
            desc: "Spaces inserted when you press Tab",
            type: "select",
            options: [2, 4, 8].map((n) => ({ value: n, label: String(n) })),
          },
          {
            key: "insertSpaces",
            label: "Insert spaces",
            desc: "Off means Tab inserts a real tab character",
            type: "toggle",
          },
        ],
      },
      {
        title: "Layout",
        rows: [
          {
            key: "wordWrap",
            label: "Word wrap",
            desc: "Wrap long lines instead of scrolling sideways",
            type: "select",
            options: [
              { value: "off", label: "Off" },
              { value: "on", label: "Viewport" },
              { value: "bounded", label: "Column" },
            ],
          },
          {
            key: "lineNumbers",
            label: "Line numbers",
            desc: "Gutter numbering style",
            type: "select",
            options: [
              { value: "on", label: "On" },
              { value: "off", label: "Off" },
              { value: "relative", label: "Relative" },
              { value: "interval", label: "Every 10" },
            ],
          },
          {
            key: "minimap",
            label: "Minimap",
            desc: "Overview strip on the right edge of the editor",
            type: "toggle",
          },
          {
            key: "bracketPairColorization",
            label: "Bracket pair colorization",
            desc: "Tint matching brackets the same colour",
            type: "toggle",
          },
        ],
      },
      {
        title: "Motion",
        rows: [
          {
            key: "smoothScrolling",
            label: "Smooth scrolling",
            desc: "Animate the editor scroll instead of jumping",
            type: "toggle",
          },
          {
            key: "cursorBlinking",
            label: "Cursor style",
            desc: "Blink behaviour of the text cursor",
            type: "select",
            options: [
              { value: "blink", label: "Blink" },
              { value: "smooth", label: "Smooth" },
              { value: "phase", label: "Phase" },
              { value: "expand", label: "Expand" },
              { value: "solid", label: "Solid" },
            ],
          },
          {
            key: "lineHighlight",
            label: "Line highlight",
            desc: "Shade the row the cursor sits on",
            type: "select",
            options: [
              { value: "all", label: "All lines" },
              { value: "line", label: "Current line" },
              { value: "none", label: "None" },
            ],
          },
        ],
      },
    ],
    execution: [
      {
        title: "Console",
        rows: [
          {
            key: "openConsoleOnRun",
            label: "Open console on run",
            desc: "Reveal the console drawer whenever you execute",
            type: "toggle",
          },
          {
            key: "clearConsoleOnRun",
            label: "Clear before run",
            desc: "Wipe previous output when a new run starts",
            type: "toggle",
          },
          {
            key: "timestamps",
            label: "Timestamps",
            desc: "Prefix each log line with the local time",
            type: "toggle",
          },
          {
            key: "maxLogLines",
            label: "Max log lines",
            desc: "Older lines are dropped once the buffer is full",
            type: "range",
            min: 50,
            max: 2000,
            step: 50,
            unit: "lines",
          },
        ],
      },
      {
        title: "Safety",
        rows: [
          {
            key: "confirmClear",
            label: "Confirm before clear",
            desc: "Require a second click to empty the editor",
            type: "toggle",
          },
        ],
      },
    ],
    appearance: [
      {
        title: "Accent",
        rows: [
          {
            key: "accent",
            label: "Accent colour",
            desc: "Highlights, selection and editor syntax all follow this",
            type: "color",
          },
        ],
      },
      {
        title: "Interface",
        rows: [
          {
            key: "compact",
            label: "Compact mode",
            desc: "Shorter tabs and a tighter navigation rail",
            type: "toggle",
          },
        ],
      },
    ],
    about: [],
  };

  const sections = [
    { id: "general", label: "General", icon: IconAdjustments },
    { id: "editor", label: "Editor", icon: IconCode },
    { id: "execution", label: "Execution", icon: IconPlayerPlay },
    { id: "appearance", label: "Appearance", icon: IconPalette },
    { id: "about", label: "About", icon: IconInfoCircle },
  ].map((s) => ({ ...s, groups: groups[s.id] || [] }));

  let currentLabel = $derived(
    sections.find((s) => s.id === activeSection)?.label || "General",
  );

  let searching = $derived(searchQuery.trim().length > 0);

  let sectionMatches = $derived.by(() => {
    let q = searchQuery.trim().toLowerCase();
    if (!q) return [];

    return sections
      .map((sec) => {
        let labelHit = sec.label.toLowerCase().includes(q);
        let groupsFor = sec.groups
          .map((g) => ({
            ...g,
            rows: labelHit
              ? g.rows
              : g.rows.filter((r) =>
                  `${r.label || ""} ${r.desc || ""} ${r.key || ""}`
                    .toLowerCase()
                    .includes(q),
                ),
          }))
          .filter((g) => g.rows.length > 0);

        return { ...sec, groups: groupsFor, labelHit };
      })
      .filter((sec) => sec.labelHit || sec.groups.length > 0);
  });

  let visibleSections = $derived(
    searching
      ? sectionMatches
      : sections.filter((s) => s.id === activeSection),
  );

  let hitCount = $derived(
    sectionMatches.reduce(
      (sum, s) => sum + s.groups.reduce((n, g) => n + g.rows.length, 0),
      0,
    ),
  );

  function onRange(section, key, e) {
    set(section, key, Number(e.currentTarget.value));
  }

  function resetCurrent() {
    if (activeSection === "about") return;
    resetSection(activeSection);
    ontoast?.(`Reset ${currentLabel} to defaults`);
  }

  function doResetAll() {
    resetAll();
    ontoast?.("All settings restored to defaults");
  }

  function replayIntro() {
    replaySplash();
  }

  async function wipeWorkspace() {
    let target = isNative() ? "on disk" : "in the browser";
    if (confirm(`Delete every workspace file ${target}? This cannot be undone.`)) {
      await clearWorkspace();
      fileCount = 0;
      window.dispatchEvent(new CustomEvent("funnyexecutor:workspace"));
      ontoast?.("Workspace cleared");
    }
  }

  let fileCount = $state(0);
  $effect(() => {
    listFiles()
      .then((files) => {
        fileCount = files.length;
      })
      .catch((err) => {
        console.error("[executor] failed to count workspace files", err);
        fileCount = 0;
      });
  });

  let settingsPath = $derived(
    isNative()
      ? "FunnyExecutor/settings.json"
      : `localStorage[funnyexecutor.settings.v1]`,
  );
  let settingsLocation = $derived(isNative() ? "on disk" : "browser");

  function openLink(url) {
    window.open(url, "_blank", "noopener");
  }
</script>

<section class="settings-view">
  <div class="settings-main">
    <div class="settings-header">
      {#key activeSection}
        <div
          class="title-anim-wrapper"
          in:fly={{ y: 8, duration: 180, easing: cubicOut }}
          out:fade={{ duration: 80 }}
        >
          <h2 class="settings-title">{currentLabel}</h2>
        </div>
      {/key}
      <div class="header-actions">
        {#if activeSection !== "about"}
          <button class="ghost-btn" title="Reset this section" onclick={resetCurrent}>
            <IconRestore size={13} stroke={1.8} />
            <span>Reset</span>
          </button>
        {/if}
      </div>
    </div>

    <div class="settings-body">
      {#if searching && hitCount > 0}
        <p class="search-summary">
          {hitCount} {hitCount === 1 ? "setting" : "settings"} found
        </p>
      {/if}

      {#each visibleSections as sec (sec.id)}
        <div class="section-block">
          {#if sec.groups.length === 0 && sec.id === "about"}
            <div class="group">
              <div class="group-title">Funny Executor</div>
              <div class="about-head">
                <svg viewBox="0 0 116.7 134" class="about-logo">
                  <path
                    fill="var(--accent)"
                    d="m97 2h-19c-9.6 0-26 10.3-32 25-2 4.9-2 13.9-2 25l-22 23h24v59h7.7l18.3-20v-37h15.9l8.1-25-24-1v-16.4c0-6.8 5.7-10.6 10.6-10.6s13.4 0.3 14.4 0v-22zm-50.3 72.8 22.3-20.9v21.1l-22.3-0.2z"
                  />
                </svg>
                <div class="about-text">
                  <div class="about-name">Funny Executor</div>
                  <div class="about-ver">version {APP_VERSION}</div>
                  <div class="about-mode">
                    {isNative() ? "native shell" : "browser build"} &middot;
                    root {pathOf("")}
                  </div>
                </div>
              </div>

              <div class="rows">
                <div class="row static">
                  <div class="row-text">
                    <span class="row-label">Stored files</span>
                    <span class="row-desc">Scripts currently held in the {isNative() ? "workspace folders on disk" : "browser workspace"}</span>
                  </div>
                  <span class="row-static">{fileCount}</span>
                </div>

                <div class="row static">
                  <div class="row-text">
                    <span class="row-label">Settings file</span>
                    <span class="row-desc">{settingsPath}</span>
                  </div>
                  <span class="row-static">{settingsLocation}</span>
                </div>

                <div class="row">
                  <div class="row-text">
                    <span class="row-label">Community</span>
                    <span class="row-desc">Discord server for scripts and help</span>
                  </div>
                  <button class="link-btn" onclick={() => openLink("https://discord.gg/e9Ru9nuSyv")}>
                    <IconBrandDiscord size={14} stroke={1.8} />
                    <span>Open</span>
                  </button>
                </div>

                <div class="row">
                  <div class="row-text">
                    <span class="row-label">Website</span>
                    <span class="row-desc">github.com/lowlevelklinti/FunnyExecutor</span>
                  </div>
                  <button class="link-btn" onclick={() => openLink("https://github.com/lowlevelklinti/FunnyExecutor")}>
                    <IconExternalLink size={14} stroke={1.8} />
                    <span>Open</span>
                  </button>
                </div>
              </div>
            </div>

            <div class="group">
              <div class="group-title danger">Danger zone</div>
              <div class="rows">
                <div class="row">
                  <div class="row-text">
                    <span class="row-label">Clear workspace</span>
                    <span class="row-desc">Delete all {fileCount} stored script files</span>
                  </div>
                  <button class="danger-btn" onclick={wipeWorkspace}>
                    <IconAlertTriangle size={13} stroke={1.8} />
                    <span>Clear files</span>
                  </button>
                </div>

                <div class="row">
                  <div class="row-text">
                    <span class="row-label">Reset all settings</span>
                    <span class="row-desc">Put every option back to its default value</span>
                  </div>
                  <button class="danger-btn" onclick={doResetAll}>
                    <IconRestore size={13} stroke={1.8} />
                    <span>Reset all</span>
                  </button>
                </div>
              </div>
            </div>
          {/if}

          {#each sec.groups as group (group.title)}
            <div class="group">
              <div class="group-title">{group.title}</div>
              <div class="rows">
                {#each group.rows as row (row.key || row.label)}
                  <div class="row">
                    <div class="row-text">
                      <span class="row-label">{row.label}</span>
                      {#if row.desc}<span class="row-desc">{row.desc}</span>{/if}
                    </div>
                    <div class="row-control">
                      {#if row.type === "toggle"}
                        <button
                          class="switch"
                          class:on={settings[sec.id][row.key]}
                          role="switch"
                          aria-checked={settings[sec.id][row.key]}
                          aria-label={row.label}
                          onclick={() => set(sec.id, row.key, !settings[sec.id][row.key])}
                        >
                          <span class="knob"></span>
                        </button>
                      {:else if row.type === "select"}
                        <div class="select-wrap">
                          <select
                            value={settings[sec.id][row.key]}
                            onchange={(e) => set(sec.id, row.key, e.currentTarget.value)}
                          >
                            {#each row.options as opt (opt.value)}
                              <option value={opt.value}>{opt.label}</option>
                            {/each}
                          </select>
                        </div>
                      {:else if row.type === "range"}
                        <div class="range-wrap">
                          <input
                            type="range"
                            min={row.min}
                            max={row.max}
                            step={row.step}
                            value={settings[sec.id][row.key]}
                            oninput={(e) => onRange(sec.id, row.key, e)}
                          />
                          <span class="range-val">
                            {settings[sec.id][row.key]}{row.unit === "%" ? "%" : ""}
                            {#if row.unit && row.unit !== "%"}<i>{row.unit}</i>{/if}
                          </span>
                        </div>
                      {:else if row.type === "color"}
                        <div class="color-wrap">
                          {#each ACCENTS as sw (sw.value)}
                            <button
                              class="swatch"
                              class:active={settings[sec.id][row.key] === sw.value}
                              style="background: {sw.value};"
                              title={sw.name}
                              aria-label={sw.name}
                              onclick={() => set(sec.id, row.key, sw.value)}
                            ></button>
                          {/each}
                          <input
                            type="color"
                            class="color-input"
                            value={settings[sec.id][row.key]}
                            oninput={(e) => set(sec.id, row.key, e.currentTarget.value)}
                          />
                        </div>
                      {:else if row.type === "action"}
                        <button class="link-btn" onclick={replayIntro}>
                          <IconPlayerPlay size={13} stroke={1.8} />
                          <span>Replay</span>
                        </button>
                      {/if}
                    </div>
                  </div>
                {/each}
              </div>
            </div>
          {/each}
        </div>
      {/each}

      {#if searching && visibleSections.length === 0}
        <div class="no-results">Nothing matches "{searchQuery.trim()}"</div>
      {/if}
    </div>
  </div>

  <aside class="settings-sidebar">
    <div class="search-wrap">
      <input
        type="text"
        placeholder="Search..."
        bind:value={searchQuery}
        class="search-input"
      />
    </div>

    <div class="sidebar-nav">
      {#each sections as sec (sec.id)}
        {@const ItemIcon = sec.icon}
        <button
          class="sidebar-item"
          class:active={activeSection === sec.id && !searching}
          onclick={() => {
            activeSection = sec.id;
            searchQuery = "";
          }}
        >
          <ItemIcon size={14} stroke={1.8} />
          <span>{sec.label}</span>
        </button>
      {/each}
    </div>
  </aside>
</section>

<style>
  .settings-view {
    display: flex;
    width: 100%;
    height: 100%;
    background-color: #1a1a1a;
    overflow: hidden;
    user-select: none;
  }

  .settings-main {
    flex: 1;
    height: 100%;
    padding: 6px 24px 14px 24px;
    box-sizing: border-box;
    display: flex;
    flex-direction: column;
    overflow-y: auto;
  }

  .settings-header {
    position: relative;
    height: 38px;
    display: flex;
    align-items: center;
    margin-bottom: 16px;
    flex-shrink: 0;
  }

  .title-anim-wrapper {
    position: absolute;
    top: 0;
    left: 0;
    height: 100%;
    display: flex;
    align-items: center;
  }

  .settings-title {
    margin: 0;
    font-size: 20px;
    font-weight: 600;
    color: #fff;
    font-family: "Syne", sans-serif;
    letter-spacing: -0.2px;
    line-height: 1;
  }

  .header-actions {
    margin-left: auto;
    display: flex;
    gap: 6px;
  }

  .settings-body {
    display: flex;
    flex-direction: column;
    gap: 10px;
    padding-bottom: 24px;
  }

  .search-summary {
    margin: 0 0 4px;
    font-size: 11px;
    color: #666;
    font-style: italic;
  }

  .section-block {
    display: flex;
    flex-direction: column;
    gap: 10px;
  }

  .group {
    background: #151515;
    border: 1px solid rgba(255, 255, 255, 0.04);
    border-radius: 8px;
    overflow: hidden;
  }

  .group-title {
    padding: 9px 14px;
    font-size: 10.5px;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.6px;
    color: #6f6f6f;
    background: #131313;
    border-bottom: 1px solid rgba(255, 255, 255, 0.04);
  }

  .group-title.danger {
    color: #9a8a8a;
  }

  .rows {
    display: flex;
    flex-direction: column;
  }

  .row {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 20px;
    padding: 11px 14px;
    border-bottom: 1px solid rgba(255, 255, 255, 0.03);
  }

  .row:last-child {
    border-bottom: none;
  }

  .row-text {
    display: flex;
    flex-direction: column;
    gap: 2px;
    min-width: 0;
  }

  .row-label {
    font-size: 12px;
    color: #e2e2e2;
    font-family: "Syne", sans-serif;
  }

  .row-desc {
    font-size: 10.5px;
    color: #6a6a6a;
    line-height: 1.35;
  }

  .row-control {
    flex-shrink: 0;
    display: flex;
    align-items: center;
  }

  .row-static {
    font-size: 12px;
    color: #8a8a8a;
    font-variant-numeric: tabular-nums;
  }

  .switch {
    position: relative;
    width: 34px;
    height: 19px;
    border-radius: 10px;
    background: #242424;
    border: 1px solid rgba(255, 255, 255, 0.07);
    cursor: pointer;
    padding: 0;
    outline: none;
    transition: 0.15s ease;
  }

  .switch .knob {
    position: absolute;
    top: 2px;
    left: 2px;
    width: 13px;
    height: 13px;
    border-radius: 50%;
    background: #777;
    transition: 0.15s cubic-bezier(0.16, 1, 0.3, 1);
  }

  .switch.on {
    background: rgba(var(--accent-rgb), 0.32);
    border-color: rgba(var(--accent-rgb), 0.55);
  }

  .switch.on .knob {
    left: 17px;
    background: var(--accent);
  }

  .select-wrap {
    position: relative;
  }

  .select-wrap::after {
    content: "";
    position: absolute;
    right: 10px;
    top: 50%;
    width: 5px;
    height: 5px;
    border-right: 1.5px solid #777;
    border-bottom: 1.5px solid #777;
    transform: translateY(-70%) rotate(45deg);
    pointer-events: none;
  }

  .select-wrap select {
    appearance: none;
    height: 27px;
    min-width: 130px;
    background: #1a1a1a;
    border: 1px solid rgba(255, 255, 255, 0.07);
    border-radius: 6px;
    padding: 0 26px 0 10px;
    color: #dedede;
    font-family: "Syne", sans-serif;
    font-size: 11.5px;
    cursor: pointer;
    outline: none;
    transition: 0.15s ease;
  }

  .select-wrap select:hover {
    border-color: rgba(255, 255, 255, 0.14);
  }

  .select-wrap select:focus {
    border-color: rgba(var(--accent-rgb), 0.6);
  }

  .range-wrap {
    display: flex;
    align-items: center;
    gap: 10px;
  }

  .range-wrap input[type="range"] {
    appearance: none;
    width: 130px;
    height: 3px;
    border-radius: 2px;
    background: #2a2a2a;
    outline: none;
    cursor: pointer;
  }

  .range-wrap input[type="range"]::-webkit-slider-thumb {
    appearance: none;
    width: 12px;
    height: 12px;
    border-radius: 50%;
    background: var(--accent);
    border: none;
    cursor: pointer;
  }

  .range-wrap input[type="range"]::-moz-range-thumb {
    width: 12px;
    height: 12px;
    border-radius: 50%;
    background: var(--accent);
    border: none;
    cursor: pointer;
  }

  .range-val {
    min-width: 46px;
    text-align: right;
    font-size: 11px;
    color: #b0b0b0;
    font-variant-numeric: tabular-nums;
  }

  .range-val i {
    font-style: normal;
    color: #666;
    font-size: 9.5px;
  }

  .color-wrap {
    display: flex;
    align-items: center;
    gap: 6px;
  }

  .swatch {
    width: 18px;
    height: 18px;
    border-radius: 5px;
    border: 1px solid rgba(255, 255, 255, 0.12);
    cursor: pointer;
    padding: 0;
    outline: none;
    transition: 0.12s ease;
  }

  .swatch:hover {
    transform: scale(1.12);
  }

  .swatch.active {
    box-shadow: 0 0 0 2px #1a1a1a, 0 0 0 3.5px var(--accent);
  }

  .color-input {
    width: 24px;
    height: 22px;
    padding: 0;
    border: 1px solid rgba(255, 255, 255, 0.1);
    border-radius: 5px;
    background: transparent;
    cursor: pointer;
  }

  .color-input::-webkit-color-swatch-wrapper {
    padding: 2px;
  }

  .color-input::-webkit-color-swatch {
    border: none;
    border-radius: 3px;
  }

  .ghost-btn,
  .link-btn,
  .danger-btn {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    height: 27px;
    padding: 0 10px;
    border-radius: 6px;
    font-family: "Syne", sans-serif;
    font-size: 11px;
    font-weight: 500;
    cursor: pointer;
    outline: none;
    transition: 0.12s ease;
  }

  .ghost-btn {
    background: #1a1a1a;
    border: 1px solid rgba(255, 255, 255, 0.07);
    color: #9a9a9a;
  }

  .ghost-btn:hover {
    color: #fff;
    border-color: rgba(255, 255, 255, 0.16);
  }

  .link-btn {
    background: transparent;
    border: 1px solid rgba(255, 255, 255, 0.08);
    color: #c4c4c4;
  }

  .link-btn:hover {
    background: rgba(var(--accent-rgb), 0.14);
    border-color: rgba(var(--accent-rgb), 0.4);
    color: #fff;
  }

  .danger-btn {
    background: transparent;
    border: 1px solid rgba(255, 255, 255, 0.08);
    color: #b09a9a;
  }

  .danger-btn:hover {
    background: rgba(var(--accent-rgb), 0.16);
    border-color: rgba(var(--accent-rgb), 0.45);
    color: #fff;
  }

  .about-head {
    display: flex;
    align-items: center;
    gap: 14px;
    padding: 14px;
    border-bottom: 1px solid rgba(255, 255, 255, 0.03);
  }

  .about-logo {
    width: 30px;
    height: 34px;
    flex-shrink: 0;
  }

  .about-text {
    display: flex;
    flex-direction: column;
    gap: 2px;
  }

  .about-name {
    font-size: 14px;
    color: #fff;
    font-family: "Syne", sans-serif;
  }

  .about-ver,
  .about-mode {
    font-size: 10.5px;
    color: #6a6a6a;
  }

  .no-results {
    padding: 24px 4px;
    font-size: 11.5px;
    color: #555;
    font-style: italic;
    text-align: center;
  }

  .settings-sidebar {
    width: 200px;
    height: 100%;
    background-color: #151515;
    border-left: 1px solid rgba(255, 255, 255, 0.04);
    display: flex;
    flex-direction: column;
    padding: 6px 10px 14px 10px;
    box-sizing: border-box;
    flex-shrink: 0;
  }

  .search-wrap {
    height: 38px;
    display: flex;
    align-items: center;
    margin-bottom: 16px;
    padding: 0;
    box-sizing: border-box;
    flex-shrink: 0;
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
    font-family: "Syne", sans-serif;
    outline: none;
    transition: 0.15s ease;
  }

  .search-input:focus {
    border-color: rgba(var(--accent-rgb), 0.5);
    background: #1e1e1e;
  }

  .search-input::placeholder {
    color: #666;
  }

  .sidebar-nav {
    display: flex;
    flex-direction: column;
    gap: 3px;
    padding: 0;
    overflow-y: auto;
  }

  .sidebar-item {
    display: flex;
    align-items: center;
    gap: 8px;
    height: 30px;
    padding: 0 10px;
    background: transparent;
    border: 1px solid transparent;
    border-radius: 6px;
    color: #888;
    font-family: "Syne", sans-serif;
    font-size: 11.5px;
    font-weight: 500;
    cursor: pointer;
    text-align: left;
    outline: none;
    transition: 0.12s ease;
  }

  .sidebar-item:hover {
    background: #1b1b1b;
    color: #ccc;
  }

  .sidebar-item.active {
    background: rgba(var(--accent-rgb), 0.12);
    border-color: rgba(var(--accent-rgb), 0.25);
    color: #fff;
  }
</style>
