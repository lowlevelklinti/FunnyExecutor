<script>
  import { onMount } from "svelte";
  import { fly, fade } from "svelte/transition";
  import { cubicOut } from "svelte/easing";
  import {
    IconSearch,
    IconFilter,
    IconChevronDown,
    IconPlayerPlayFilled,
    IconCode,
    IconCheck,
  } from "@tabler/icons-svelte";

  let { onloadscript, onexecute, ontoast } = $props();

  let query = $state("");
  let selectedCategory = $state("All Categories");
  let filterOpen = $state(false);
  let providerOpen = $state(false);
  let loading = $state(true);
  let loadingMore = $state(false);
  let page = $state(1);
  let hasMore = $state(true);
  let scripts = $state([]);
  let searchTimer = null;
  let gridEl = $state(null);

  const providers = [
    {
      id: "scriptblox",
      name: "ScriptBlox",
      icon: "https://scriptblox.com/favicon.ico",
    },
    {
      id: "rscripts",
      name: "RScripts",
      icon: "https://rscripts.net/favicon.ico",
    },
    { id: "haxhell", name: "HaxHell", icon: "https://haxhell.com/favicon.ico" },
    {
      id: "robloxscripts",
      name: "RobloxScripts",
      icon: "https://robloxscripts.com/favicon.ico",
    },
  ];

  let selectedProvider = $state(providers[0]);

  const categories = [
    "All Categories",
    "Universal",
    "Arsenal",
    "Blox Fruits",
    "Rivals",
    "Blade Ball",
    "Pet Simulator 99",
  ];

  function formatViews(n) {
    if (!n) return "0";
    if (n >= 1000000) return (n / 1000000).toFixed(1) + "M";
    if (n >= 1000) return (n / 1000).toFixed(1) + "K";
    return String(n);
  }

  function resolveImage(img, gameImg) {
    let target = img || gameImg;
    if (!target || target.includes("no-script")) {
      return "https://tr.rbxcdn.com/180DAY-65f8caa6b19f89964141f27c1e3b7fa0/480/270/Image/Png/noFilter";
    }
    if (target.startsWith("/")) {
      return `https://scriptblox.com${target}`;
    }
    return target;
  }

  function cleanGameName(name) {
    if (!name) return "Universal";
    return (
      name
        .replace(/[\u{1F300}-\u{1F9FF}]/gu, "")
        .replace(/d\?\?\?/g, "")
        .trim() || "Universal"
    );
  }

  function extractAuthorOrMeta(s) {
    if (s.owner?.username) return `by ${s.owner.username}`;
    if (s.author?.username) return `by ${s.author.username}`;
    if (s.user?.username) return `by ${s.user.username}`;

    let byMatch = s.title?.match(/(?:by|made by|dev:?)\s+([a-zA-Z0-9_-]+)/i);
    if (byMatch && byMatch[1]) {
      return `by ${byMatch[1]}`;
    }

    let tags = [];
    if (s.verified) tags.push("Verified");
    if (s.key === false) tags.push("Keyless");
    else if (s.key === true) tags.push("Key");
    if (s.isHub) tags.push("Hub");

    return tags.length > 0 ? tags.join(" • ") : "Community";
  }

  async function apiGet(url, timeoutMs = 2500) {
    let timeoutPromise = new Promise((resolve) =>
      setTimeout(() => resolve(null), timeoutMs),
    );
    let fetchPromise = (async () => {
      try {
        let res = await fetch(url);
        return await res.json();
      } catch (fetchErr) {
        return null;
      }
    })();

    return Promise.race([fetchPromise, timeoutPromise]);
  }

  // oh my god bruu 😭😭😭😭
  async function fetchScripts(append = false) {
    if (append) {
      loadingMore = true;
    } else {
      loading = true;
      page = 1;
      hasMore = true;
    }

    let term = query.trim();
    let cat = selectedCategory === "All Categories" ? "" : selectedCategory;
    let searchTerm = term || cat;
    let targetPage = append ? page : 1;

    try {
      let newScripts = [];
      if (selectedProvider.id === "scriptblox") {
        let list = [];
        if (!searchTerm) {
          let data = await apiGet(
            "https://scriptblox.com/api/script/trending",
            2000,
          );
          list = data?.result?.scripts || [];
        } else {
          let data = await apiGet(
            `https://scriptblox.com/api/script/search?q=${encodeURIComponent(searchTerm)}&page=${targetPage}`,
            1800,
          );
          list = data?.result?.scripts || [];
        }

        if (list.length === 0) {
          let backupData = await apiGet(
            `https://rscripts.net/api/v2/scripts?${searchTerm ? `q=${encodeURIComponent(searchTerm)}&` : ""}page=${targetPage}`,
            2000,
          );
          let backupList = backupData?.scripts || [];
          if (backupList.length > 0) {
            list = backupList.map((s) => ({
              _id: s._id,
              slug: s.slug,
              title: s.title,
              game: {
                name: s.game?.title || s.gameName,
                imageUrl: s.game?.imgurl || s.game?.gameLogo,
              },
              owner: { username: s.user?.username },
              image: s.image,
              views: s.views,
              verified: s.user?.verified,
              script: s.rawScript
                ? `loadstring(game:HttpGet("${s.rawScript}"))()`
                : "",
            }));
          }
        }

        if (list.length === 0) hasMore = false;
        newScripts = list.map((s, i) => ({
          id: s._id || s.slug || `sb-${targetPage}-${i}`,
          name: s.title || "Untitled Script",
          game: cleanGameName(
            s.game?.name || (s.isUniversal ? "Universal" : "Roblox"),
          ),
          author: extractAuthorOrMeta(s),
          image: resolveImage(s.image, s.game?.imageUrl),
          views: formatViews(s.views || 0),
          trending: s.verified || (s.views || 0) > 10000,
          code:
            s.script ||
            `loadstring(game:HttpGet("https://rawscripts.net/raw/${s.slug}"))()`,
        }));
      } else if (selectedProvider.id === "rscripts") {
        let url = searchTerm
          ? `https://rscripts.net/api/v2/scripts?q=${encodeURIComponent(searchTerm)}&page=${targetPage}`
          : `https://rscripts.net/api/v2/scripts?page=${targetPage}`;

        let data = await apiGet(url);
        let list = data?.scripts || [];
        if (list.length === 0) hasMore = false;
        newScripts = list.map((s, i) => ({
          id: s._id || s.slug || `rs-${targetPage}-${i}`,
          name: s.title || "Untitled Script",
          game: cleanGameName(s.game?.title || s.gameName || "Roblox"),
          author: s.user?.username ? `by ${s.user.username}` : "Verified",
          image: resolveImage(s.image, s.game?.imgurl || s.game?.gameLogo),
          views: formatViews(s.views || 0),
          trending: s.user?.verified || (s.views || 0) > 5000,
          code: s.rawScript
            ? `loadstring(game:HttpGet("${s.rawScript}"))()`
            : s.slug
              ? `loadstring(game:HttpGet("https://rscripts.net/raw/${s.slug}"))()`
              : "",
        }));
      } else if (selectedProvider.id === "haxhell") {
        let q = searchTerm || "universal";
        let url = `https://api.haxhell.com/api/v1/search/scripts?q=${encodeURIComponent(q)}&page=${targetPage}&limit=18`;
        let data = await apiGet(url);
        let list = data?.data || [];
        if (list.length === 0) hasMore = false;
        newScripts = list.map((s, i) => ({
          id: s.id || s.slug || `hh-${targetPage}-${i}`,
          name: s.title || "Untitled Script",
          game: cleanGameName(
            s.game?.name || (s.type === "universal" ? "Universal" : "Roblox"),
          ),
          author: s.author?.username
            ? `by ${s.author.username}`
            : s.flags?.verified
              ? "Verified"
              : "Community",
          image: resolveImage(
            s.media?.thumbnailUrl,
            s.game?.thumbnailUrl || s.game?.iconUrl,
          ),
          views: formatViews(s.stats?.views || 0),
          trending: s.flags?.verified || (s.stats?.views || 0) > 1000,
          code: `loadstring(game:HttpGet("${s.links?.raw || ""}"))()`,
        }));
      } else if (selectedProvider.id === "robloxscripts") {
        let q = searchTerm || "roblox";
        let data = await apiGet(
          `https://rscripts.net/api/v2/scripts?q=${encodeURIComponent(q)}&page=${targetPage}`,
        );
        let list = data?.scripts || [];
        if (list.length === 0) {
          let fallback = await apiGet(
            `https://scriptblox.com/api/script/search?q=${encodeURIComponent(q)}&page=${targetPage}&max=18`,
          );
          list = fallback?.result?.scripts || [];
        }
        if (list.length === 0) hasMore = false;
        newScripts = list.map((s, i) => ({
          id: s._id || s.slug || `rbs-${targetPage}-${i}`,
          name: s.title || s.name || "Untitled Script",
          game: cleanGameName(s.game?.title || s.game?.name || "Roblox"),
          author: s.user?.username
            ? `by ${s.user.username}`
            : extractAuthorOrMeta(s),
          image: resolveImage(s.image, s.game?.imgurl || s.game?.imageUrl),
          views: formatViews(s.views || 0),
          trending: s.verified || s.user?.verified || (s.views || 0) > 8000,
          code: s.rawScript
            ? `loadstring(game:HttpGet("${s.rawScript}"))()`
            : s.script ||
              `loadstring(game:HttpGet("https://rawscripts.net/raw/${s.slug}"))()`,
        }));
      }

      if (append) {
        let existingIds = new Set(scripts.map((s) => s.id));
        let unique = newScripts.filter((s) => !existingIds.has(s.id));
        scripts = [...scripts, ...unique];
      } else {
        scripts = newScripts;
      }
    } catch (e) {
      if (!append) scripts = [];
    } finally {
      loading = false;
      loadingMore = false;
    }
  }

  function handleScroll() {
    if (!gridEl || loading || loadingMore || !hasMore) return;
    let { scrollTop, scrollHeight, clientHeight } = gridEl;
    if (scrollHeight - scrollTop - clientHeight < 140) {
      page += 1;
      fetchScripts(true);
    }
  }

  function handleSearchInput() {
    clearTimeout(searchTimer);
    searchTimer = setTimeout(() => {
      fetchScripts(false);
    }, 300);
  }

  function pickCategory(cat) {
    selectedCategory = cat;
    filterOpen = false;
    fetchScripts(false);
  }

  function pickProvider(prov) {
    selectedProvider = prov;
    providerOpen = false;
    ontoast?.(`Source: ${prov.name}`);
    fetchScripts(false);
  }

  function execute(script) {
    onexecute?.(script);
    ontoast?.(`Executed ${script.name}`);
  }

  function load(script) {
    onloadscript?.(script);
    ontoast?.(`Loaded ${script.name} into editor`);
  }

  onMount(() => {
    fetchScripts(false);
  });
</script>

<section class="scripthub-view">
  <div class="hub-header">
    <div class="search-box">
      <span class="search-icon">
        <IconSearch size={14} stroke={2} />
      </span>
      <input
        type="text"
        placeholder="Search scripts"
        bind:value={query}
        oninput={handleSearchInput}
        class="search-input"
      />
    </div>

    <div class="controls-row">
      <div class="dropdown-wrapper">
        <button
          class="filter-dropdown-btn"
          onclick={() => {
            filterOpen = !filterOpen;
            providerOpen = false;
          }}
        >
          <IconFilter size={13} stroke={2} />
          <span>{selectedCategory}</span>
          <span class="chevron" class:open={filterOpen}>
            <IconChevronDown size={12} stroke={2} />
          </span>
        </button>

        {#if filterOpen}
          <div
            class="dropdown-menu"
            transition:fly={{ y: -6, duration: 160, easing: cubicOut }}
          >
            {#each categories as cat}
              <button
                class="dropdown-item"
                class:active={selectedCategory === cat}
                onclick={() => pickCategory(cat)}
              >
                <span>{cat}</span>
                {#if selectedCategory === cat}
                  <IconCheck size={12} stroke={2.5} />
                {/if}
              </button>
            {/each}
          </div>
        {/if}
      </div>

      <div class="dropdown-wrapper">
        <button
          class="icon-dropdown-btn"
          title={`Source: ${selectedProvider.name}`}
          onclick={() => {
            providerOpen = !providerOpen;
            filterOpen = false;
          }}
        >
          <img
            src={selectedProvider.icon}
            alt={selectedProvider.name}
            class="provider-favicon"
          />
        </button>

        {#if providerOpen}
          <div
            class="dropdown-menu right-aligned"
            transition:fly={{ y: -6, duration: 160, easing: cubicOut }}
          >
            {#each providers as prov}
              <button
                class="dropdown-item"
                class:active={selectedProvider.id === prov.id}
                onclick={() => pickProvider(prov)}
              >
                <div class="provider-item-row">
                  <img
                    src={prov.icon}
                    alt={prov.name}
                    class="provider-menu-icon"
                  />
                  <span>{prov.name}</span>
                </div>
                {#if selectedProvider.id === prov.id}
                  <IconCheck size={12} stroke={2.5} />
                {/if}
              </button>
            {/each}
          </div>
        {/if}
      </div>
    </div>
  </div>

  <div class="scripts-grid" bind:this={gridEl} onscroll={handleScroll}>
    {#if loading}
      {#each Array(6) as _}
        <div class="script-card skeleton">
          <div class="card-top">
            <div class="skeleton-line title"></div>
            <div class="skeleton-line sub"></div>
          </div>
          <div class="card-bottom">
            <div class="skeleton-line tiny"></div>
            <div class="skeleton-line btn"></div>
          </div>
        </div>
      {/each}
    {:else if scripts.length === 0}
      <div class="empty-hub">
        <span>No scripts found for "{query || selectedCategory}"</span>
      </div>
    {:else}
      {#each scripts as script, i (script.id)}
        <div
          class="script-card"
          in:fly={{
            y: 14,
            duration: 220,
            delay: Math.min((i % 18) * 30, 260),
            easing: cubicOut,
          }}
        >
          {#if script.image}
            <img
              src={script.image}
              alt={script.name}
              class="card-bg-img"
              loading="lazy"
            />
          {/if}

          <div class="card-top">
            <div class="card-title-row">
              <span class="script-name" title={script.name}>{script.name}</span>
            </div>
            <span
              class="script-meta"
              title={`${script.game} • ${script.author}`}
            >
              {script.game} &bull; {script.author}
            </span>
          </div>

          <div class="card-bottom">
            <span class="views-text">{script.views} views</span>
            <div class="card-actions">
              <button
                class="card-btn secondary"
                onclick={() => load(script)}
                title="Load Script into Editor"
              >
                <IconCode size={12} stroke={2} />
                <span>Load</span>
              </button>
              <button
                class="card-btn primary"
                onclick={() => execute(script)}
                title="Execute Script"
              >
                <IconPlayerPlayFilled size={10} />
                <span>Execute</span>
              </button>
            </div>
          </div>
        </div>
      {/each}

      {#if loadingMore}
        {#each Array(3) as _}
          <div class="script-card skeleton" in:fade={{ duration: 150 }}>
            <div class="card-top">
              <div class="skeleton-line title"></div>
              <div class="skeleton-line sub"></div>
            </div>
            <div class="card-bottom">
              <div class="skeleton-line tiny"></div>
              <div class="skeleton-line btn"></div>
            </div>
          </div>
        {/each}
      {/if}
    {/if}
  </div>
</section>

<style>
  .scripthub-view {
    width: 100%;
    height: 100%;
    padding: 6px 18px 14px 18px;
    box-sizing: border-box;
    display: flex;
    flex-direction: column;
    gap: 12px;
    overflow: hidden;
    font-family: "Syne", sans-serif;
    font-weight: 400;
  }

  .hub-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 10px;
    flex-shrink: 0;
  }

  .search-box {
    position: relative;
    flex: 1;
    display: flex;
    align-items: center;
  }

  .search-icon {
    position: absolute;
    left: 10px;
    display: grid;
    place-items: center;
    color: #666;
    pointer-events: none;
  }

  .search-input {
    width: 100%;
    height: 32px;
    background: #151515;
    border: 1px solid rgba(255, 255, 255, 0.05);
    border-radius: 6px;
    padding: 0 10px 0 32px;
    font-size: 11.5px;
    font-family: "Syne", sans-serif;
    font-weight: 400;
    color: #dedede;
    outline: none;
    box-sizing: border-box;
    transition: 0.15s ease;
  }

  .search-input:focus {
    background: #1a1a1a;
    border-color: rgba(255, 255, 255, 0.15);
  }

  .search-input::placeholder {
    color: #666;
  }

  .controls-row {
    display: flex;
    align-items: center;
    gap: 8px;
  }

  .dropdown-wrapper {
    position: relative;
  }

  .filter-dropdown-btn {
    height: 32px;
    padding: 0 10px;
    background: #151515;
    border: 1px solid rgba(255, 255, 255, 0.05);
    border-radius: 6px;
    color: #dedede;
    font-family: "Syne", sans-serif;
    font-size: 11px;
    font-weight: 400;
    display: inline-flex;
    align-items: center;
    gap: 6px;
    cursor: pointer;
    transition: 0.15s ease;
    outline: none;
  }

  .filter-dropdown-btn:hover {
    background: #1c1c1c;
    border-color: rgba(255, 255, 255, 0.12);
  }

  .chevron {
    display: grid;
    place-items: center;
    color: #888;
    transition: transform 0.18s ease;
  }

  .chevron.open {
    transform: rotate(180deg);
  }

  .icon-dropdown-btn {
    width: 32px;
    height: 32px;
    background: #151515;
    border: 1px solid rgba(255, 255, 255, 0.05);
    border-radius: 6px;
    display: grid;
    place-items: center;
    cursor: pointer;
    transition: 0.15s ease;
    outline: none;
    padding: 0;
  }

  .icon-dropdown-btn:hover {
    background: #1c1c1c;
    border-color: rgba(255, 255, 255, 0.12);
  }

  .provider-favicon {
    width: 16px;
    height: 16px;
    border-radius: 3px;
    object-fit: contain;
    display: block;
  }

  .dropdown-menu {
    position: absolute;
    top: calc(100% + 5px);
    left: 0;
    width: 155px;
    background: #191919;
    border: 1px solid rgba(255, 255, 255, 0.08);
    border-radius: 6px;
    padding: 4px;
    display: flex;
    flex-direction: column;
    gap: 2px;
    z-index: 100;
    box-shadow: 0 10px 28px rgba(0, 0, 0, 0.65);
    backdrop-filter: blur(12px);
  }

  .dropdown-menu.right-aligned {
    left: auto;
    right: 0;
    width: 150px;
  }

  .dropdown-item {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 6px 8px;
    background: transparent;
    border: none;
    border-radius: 4px;
    color: #bbb;
    font-size: 11px;
    font-family: "Syne", sans-serif;
    cursor: pointer;
    text-align: left;
    transition: 0.12s ease;
  }

  .dropdown-item:hover {
    background: #242424;
    color: #fff;
  }

  .dropdown-item.active {
    color: var(--accent);
    background: rgba(var(--accent-rgb), 0.08);
  }

  .provider-item-row {
    display: flex;
    align-items: center;
    gap: 8px;
  }

  .provider-menu-icon {
    width: 14px;
    height: 14px;
    border-radius: 3px;
    object-fit: contain;
    flex-shrink: 0;
  }

  .scripts-grid {
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    grid-auto-rows: minmax(116px, auto);
    gap: 12px;
    overflow-y: auto;
    flex: 1;
    padding-right: 4px;
    padding-bottom: 12px;
  }

  .scripts-grid::-webkit-scrollbar {
    width: 3px;
  }

  .scripts-grid::-webkit-scrollbar-thumb {
    background: rgba(255, 255, 255, 0.1);
    border-radius: 3px;
  }

  .script-card {
    position: relative;
    min-height: 116px;
    background: #151515;
    border: 1px solid rgba(255, 255, 255, 0.05);
    border-radius: 9px;
    padding: 14px 16px;
    display: flex;
    flex-direction: column;
    justify-content: space-between;
    gap: 12px;
    overflow: hidden;
    box-sizing: border-box;
  }

  .card-bg-img {
    position: absolute;
    top: 0;
    right: 0;
    width: 75%;
    height: 100%;
    object-fit: cover;
    opacity: 0.15;
    mask-image: linear-gradient(to left, black 25%, transparent 100%);
    -webkit-mask-image: linear-gradient(to left, black 25%, transparent 100%);
    pointer-events: none;
    z-index: 0;
  }

  .card-top {
    position: relative;
    z-index: 1;
    display: flex;
    flex-direction: column;
    gap: 4px;
  }

  .card-title-row {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 6px;
  }

  .script-name {
    font-size: 13.5px;
    color: #fff;
    font-family: "Syne", sans-serif;
    font-weight: 500;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }

  .script-meta {
    font-size: 11px;
    color: #888;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }

  .card-bottom {
    position: relative;
    z-index: 1;
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding-top: 10px;
    border-top: 1px solid rgba(255, 255, 255, 0.05);
  }

  .views-text {
    font-size: 10px;
    color: #777;
    font-family: "JetBrains Mono", monospace;
  }

  .card-actions {
    display: flex;
    align-items: center;
    gap: 6px;
  }

  .card-btn {
    height: 25px;
    padding: 0 10px;
    border-radius: 5px;
    font-family: "Syne", sans-serif;
    font-size: 11px;
    font-weight: 400;
    display: inline-flex;
    align-items: center;
    gap: 4px;
    cursor: pointer;
    transition: 0.15s ease;
    outline: none;
    border: 1px solid transparent;
  }

  .card-btn.secondary {
    background: #1f1f1f;
    color: #ccc;
    border-color: rgba(255, 255, 255, 0.06);
  }

  .card-btn.secondary:hover {
    background: #282828;
    color: #fff;
  }

  .card-btn.primary {
    background: radial-gradient(
      ellipse 90% 100% at 50% 50%,
      rgba(var(--accent-rgb), 0.35) 0%,
      #1b1b1b 85%
    );
    color: #fff;
    border-color: rgba(var(--accent-rgb), 0.35);
  }

  .card-btn.primary:hover {
    background: radial-gradient(
      ellipse 90% 100% at 50% 50%,
      rgba(var(--accent-rgb), 0.5) 0%,
      #262626 85%
    );
  }

  .empty-hub {
    grid-column: 1 / -1;
    display: flex;
    align-items: center;
    justify-content: center;
    height: 160px;
    color: #666;
    font-size: 12px;
  }

  .skeleton {
    animation: pulse 1.5s infinite ease-in-out;
  }

  @keyframes pulse {
    0%,
    100% {
      opacity: 0.6;
    }
    50% {
      opacity: 0.3;
    }
  }

  .skeleton-line {
    background: rgba(255, 255, 255, 0.08);
    border-radius: 4px;
  }

  .skeleton-line.title {
    height: 14px;
    width: 70%;
  }

  .skeleton-line.sub {
    height: 10px;
    width: 45%;
    margin-top: 6px;
  }

  .skeleton-line.tiny {
    height: 10px;
    width: 30%;
  }

  .skeleton-line.btn {
    height: 20px;
    width: 40%;
  }
</style>
