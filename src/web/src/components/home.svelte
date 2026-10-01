<script>
  import { onMount } from "svelte";
  import { invoke } from "../lib/bridge.js";
  import { IconPlus, IconCode } from "@tabler/icons-svelte";

  let { onnewscript, onopeneditor, ontoast } = $props();
  let version = $state("");
  let excluding = $state(false);

  async function getVersion() {
    try {
      let res = await fetch("https://weao.xyz/api/versions/current");
      if (res.ok) {
        let data = await res.json();
        if (data?.Windows) version = data.Windows;
      }
    } catch (err) {}
  }

  async function launchRoblox() {
    try {
      await invoke("open_url", { url: "roblox://" });
      ontoast?.("Launching Roblox...");
    } catch (e) {
      ontoast?.("Failed to launch Roblox");
    }
  }

  async function excludeApp() {
    if (excluding) return;
    excluding = true;
    ontoast?.("Adding Defender exclusion...");
    try {
      await invoke("exclude_from_defender");
      ontoast?.("Funny Executor excluded from Windows Defender");
    } catch (e) {
      ontoast?.("Exclusion cancelled or failed");
    }
    excluding = false;
  }

  async function handleDiscord() {
    try {
      await invoke("open_url", { url: "https://discord.gg/e9Ru9nuSyv" });
      ontoast?.("Joining Discord server...");
    } catch (e) {
      ontoast?.("Failed to open Discord");
    }
  }

  onMount(() => {
    getVersion();
  });
</script>

<section class="home-view">
  <div class="home-container">
    <div class="hero-card">
      <div class="hero-left">
        <h1 class="hero-title">
          Welcome
        </h1>
        <div class="hero-meta">
          <span
            >roblox version: <span class="mono-id"
              >{version || "fetching..."}</span
            ></span
          >
        </div>

        <div class="hero-actions">
          <button class="btn primary" onclick={onnewscript}>
            <IconPlus size={13} stroke={2.5} />
            <span>new script</span>
          </button>

          <button class="btn secondary" onclick={onopeneditor}>
            <IconCode size={13} stroke={2} />
            <span>open editor</span>
          </button>
        </div>
      </div>

      <div class="hero-right">
      </div>
    </div>

    <div class="grid">
      <div class="card log-card">
        <div class="card-head">
          <span class="card-title">update log</span>
          <span class="badge">v1.2.0</span>
        </div>

        <div class="log-list">
          <div class="log-item">
            <div class="log-meta">
              <span class="log-ver">v1.2.0</span>
              <span class="log-date">Today</span>
            </div>
            <div class="log-text">
              + complete ui rewrite on monaco + svelte
            </div>
          </div>

          <div class="log-item">
            <div class="log-meta">
              <span class="log-ver">v1.1.8</span>
              <span class="log-date">Today</span>
            </div>
            <div class="log-text">
              + script output now lands in the built-in console
            </div>
          </div>

          <div class="log-item">
            <div class="log-meta">
              <span class="log-ver">v1.1.5</span>
              <span class="log-date">Today</span>
            </div>
            <div class="log-text">
              + workspace explorer, tabs and drag between folders
            </div>
          </div>

          <div class="log-item">
            <div class="log-meta">
              <span class="log-ver">v1.1.0</span>
              <span class="log-date">Today</span>
            </div>
            <div class="log-text">
              + multi-provider script hub with live search
            </div>
          </div>

          <div class="log-item">
            <div class="log-meta">
              <span class="log-ver">v1.0.8</span>
              <span class="log-date">Today</span>
            </div>
            <div class="log-text">+ luau autocomplete, hovers and signature help</div>
          </div>
        </div>
      </div>

      <div class="right-col">
        <button class="action-card roblox-card" onclick={launchRoblox}>
          <div class="action-content">
            <span class="action-title">launch roblox</span>
            <span class="action-desc">launch roblox and use funny executor!</span>
          </div>
          <div class="action-watermark-wrap roblox-wrap">
            <svg
              role="img"
              viewBox="0 0 24 24"
              xmlns="http://www.w3.org/2000/svg"
              class="action-watermark roblox-wm"
              fill="currentColor"
            >
              <path
                d="M18.926 23.998 0 18.892 5.075.002 24 5.108ZM15.348 10.09l-5.282-1.453-1.414 5.273 5.282 1.453z"
              />
            </svg>
          </div>
        </button>

        <button class="action-card discord-card" onclick={handleDiscord}>
          <div class="action-content">
            <span class="action-title">join our discord</span>
            <span class="action-desc"
              >join our discord for support and to stay updated!</span
            >
          </div>
          <div class="action-watermark-wrap discord-wrap">
            <svg
              role="img"
              viewBox="0 0 24 24"
              xmlns="http://www.w3.org/2000/svg"
              class="action-watermark discord-wm"
              fill="currentColor"
            >
              <title>Discord</title>
              <path
                d="M20.317 4.3698a19.7913 19.7913 0 00-4.8851-1.5152.0741.0741 0 00-.0785.0371c-.211.3753-.4447.8648-.6083 1.2495-1.8447-.2762-3.68-.2762-5.4868 0-.1636-.3933-.4058-.8742-.6177-1.2495a.077.077 0 00-.0785-.037 19.7363 19.7363 0 00-4.8852 1.515.0699.0699 0 00-.0321.0277C.5334 9.0458-.319 13.5799.0992 18.0578a.0824.0824 0 00.0312.0561c2.0528 1.5076 4.0413 2.4228 5.9929 3.0294a.0777.0777 0 00.0842-.0276c.4616-.6304.8731-1.2952 1.226-1.9942a.076.076 0 00-.0416-.1057c-.6528-.2476-1.2743-.5495-1.8722-.8923a.077.077 0 01-.0076-.1277c.1258-.0943.2517-.1923.3718-.2914a.0743.0743 0 01.0776-.0105c3.9278 1.7933 8.18 1.7933 12.0614 0a.0739.0739 0 01.0785.0095c.1202.099.246.1981.3728.2924a.077.077 0 01-.0066.1276 12.2986 12.2986 0 01-1.873.8914.0766.0766 0 00-.0407.1067c.3604.698.7719 1.3628 1.225 1.9932a.076.076 0 00.0842.0286c1.961-.6067 3.9495-1.5219 6.0023-3.0294a.0777.0777 0 00.0313-.0552c.5004-5.177-.8382-9.6739-3.5485-13.6604a.061.061 0 00-.0312-.0286zM8.02 15.3312c-1.1825 0-2.1569-1.0857-2.1569-2.419 0-1.3332.9555-2.4189 2.157-2.4189 1.2108 0 2.1757 1.0952 2.1568 2.419 0 1.3332-.9555 2.4189-2.1569 2.4189zm7.9748 0c-1.1825 0-2.1569-1.0857-2.1569-2.419 0-1.3332.9554-2.4189 2.1569-2.4189 1.2108 0 2.1757 1.0952 2.1568 2.419 0 1.3332-.946 2.4189-2.1568 2.4189Z"
              />
            </svg>
          </div>
        </button>

        <button class="action-card defender-card" onclick={excludeApp}>
          <div class="action-content">
            <span class="action-title">exclude funny executor</span>
            <span class="action-desc">exclude from windows defender</span>
          </div>
          <div class="action-watermark-wrap defender-wrap">
            <svg
              viewBox="0 0 24 24"
              class="action-watermark defender-wm"
              fill="currentColor"
            >
              <path
                d="M12 1L3 5v6c0 5.55 3.84 10.74 9 12 5.16-1.26 9-6.45 9-12V5l-9-4zm0 2.18l7 3.12v4.7c0 4.54-3.08 8.78-7 9.88-3.92-1.1-7-5.34-7-9.88V6.3l7-3.12z"
              />
            </svg>
          </div>
        </button>
      </div>
    </div>
  </div>
</section>

<style>
  .home-view {
    width: 100%;
    height: 100%;
    padding: 6px 18px 14px 18px;
    box-sizing: border-box;
    overflow: hidden;
    display: flex;
    flex-direction: column;
  }

  .home-container {
    display: flex;
    flex-direction: column;
    width: 100%;
    height: 100%;
    gap: 12px;
  }

  .hero-card {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 16px 20px;
    background: #151515;
    border: 1px solid rgba(255, 255, 255, 0.05);
    border-radius: 8px;
  }

  .hero-left {
    display: flex;
    flex-direction: column;
  }

  .hero-title {
    font-size: 20px;
    font-weight: 400;
    color: #fff;
    margin: 0;
    font-family: "Syne", sans-serif;
  }

  .hero-name {
    color: #fff;
  }

  .hero-meta {
    font-size: 11px;
    color: #777;
    margin: 4px 0 12px;
    font-family: "Syne", sans-serif;
  }

  .mono-id {
    font-family: "JetBrains Mono", monospace;
    color: #a0a0a0;
  }

  .hero-actions {
    display: flex;
    align-items: center;
    gap: 8px;
  }

  .btn {
    height: 28px;
    padding: 0 12px;
    border-radius: 6px;
    font-family: "Syne", sans-serif;
    font-size: 11px;
    display: inline-flex;
    align-items: center;
    gap: 6px;
    cursor: pointer;
    border: 1px solid rgba(255, 255, 255, 0.06);
    background: #1c1c1c;
    color: #dedede;
    transition: 0.15s ease;
  }

  .btn:hover {
    background: #242424;
    color: #fff;
    border-color: rgba(255, 255, 255, 0.12);
  }

  .btn.secondary {
    background: #1a1a1a;
  }

  .avatar-wrap {
    width: 74px;
    height: 74px;
    border-radius: 50%;
    border: 1px solid rgba(255, 255, 255, 0.08);
    overflow: hidden;
    background: #1a1a1a;
  }

  .avatar {
    width: 100%;
    height: 100%;
    object-fit: cover;
  }

  .grid {
    display: grid;
    grid-template-columns: 1.15fr 1fr;
    gap: 12px;
    flex: 1;
    min-height: 0;
  }

  .right-col {
    display: flex;
    flex-direction: column;
    gap: 10px;
    height: 100%;
    min-height: 0;
    justify-content: space-between;
  }

  .card {
    background: #151515;
    border: 1px solid rgba(255, 255, 255, 0.05);
    border-radius: 8px;
    padding: 14px 16px;
    display: flex;
    flex-direction: column;
    box-sizing: border-box;
  }

  .log-card {
    justify-content: space-between;
  }

  .action-card {
    position: relative;
    flex: 1;
    min-height: 0;
    background: #151515;
    border: 1px solid rgba(255, 255, 255, 0.05);
    border-radius: 8px;
    padding: 14px 16px;
    display: flex;
    align-items: center;
    justify-content: space-between;
    box-sizing: border-box;
    cursor: pointer;
    overflow: hidden;
    text-align: left;
    outline: none;
    transition: 0.15s ease;
  }

  .action-card:hover {
    background: #191919;
    border-color: rgba(255, 255, 255, 0.12);
  }

  .action-content {
    display: flex;
    flex-direction: column;
    gap: 3px;
    z-index: 1;
    position: relative;
  }

  .action-title {
    font-size: 13px;
    font-weight: 500;
    color: #fff;
    font-family: "Syne", sans-serif;
    text-transform: lowercase;
  }

  .action-desc {
    font-size: 11px;
    color: #777;
    font-family: "Syne", sans-serif;
    text-transform: lowercase;
  }

  .action-watermark-wrap {
    position: absolute;
    right: -18px;
    top: 74%;
    transform: translateY(-50%);
    display: grid;
    place-items: center;
    pointer-events: none;
    z-index: 0;
  }

  .action-watermark {
    width: 96px;
    height: 96px;
    color: #ffffff;
    opacity: 0.2;
    transform: rotate(14deg);
    transition:
      color 0.2s ease,
      opacity 0.2s ease;
  }

  .action-card:hover .action-watermark {
    color: var(--accent);
    opacity: 0.35;
  }

  .card-head {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 12px;
  }

  .card-title {
    font-size: 13px;
    color: #fff;
    font-family: "Syne", sans-serif;
    line-height: 1.8;
  }

  .badge {
    font-size: 10px;
    color: #666;
    border: 1px solid rgba(255, 255, 255, 0.05);
    padding: 1px 6px;
    border-radius: 4px;
    background: #1a1a1a;
    font-family: "Syne", sans-serif;
  }

  .log-list {
    display: flex;
    flex-direction: column;
    gap: 9px;
    overflow-y: auto;
    flex: 1;
    padding-right: 4px;
  }

  .log-item {
    display: flex;
    flex-direction: column;
    gap: 2px;
  }

  .log-meta {
    display: flex;
    align-items: center;
    justify-content: space-between;
  }

  .log-ver {
    font-size: 11.5px;
    color: var(--accent);
    font-family: "Syne", sans-serif;
  }

  .log-date {
    font-size: 10px;
    color: #555;
    font-family: "Syne", sans-serif;
  }

  .log-text {
    font-size: 10.5px;
    color: #888;
    font-family: "Syne", sans-serif;
    line-height: 1.35;
  }
</style>
