<script>
  import { scale } from "svelte/transition";
  import {
    IconPlus,
    IconPencil,
    IconCopy,
    IconX,
    IconTrash,
    IconFolderOpen,
    IconFileCode,
  } from "@tabler/icons-svelte";

  let {
    menu,
    onnew,
    onrename,
    onduplicate,
    ondelete,
    oncloseothers,
    oncloseall,
    onopenfile,
    onrevealfolder,
  } = $props();
</script>

{#if menu.visible}
  <!-- menu anims and other thingies -->
  <div
    class="ctx-menu"
    role="menu"
    tabindex="-1"
    style="top: {menu.y}px; left: {menu.x}px;"
    transition:scale={{ start: 0.95, duration: 120 }}
    onclick={(e) => e.stopPropagation()}
    onkeydown={() => {}}
  >
    {#if menu.type === "tab"}
      <button class="ctx-item" onclick={onnew}>
        <IconPlus size={13} stroke={2} />
        <span>New Tab</span>
      </button>

      {#if menu.target}
        <button class="ctx-item" onclick={(e) => onrename(menu.target, e)}>
          <IconPencil size={13} stroke={2} />
          <span>Rename</span>
        </button>

        <button class="ctx-item" onclick={() => onduplicate(menu.target)}>
          <IconCopy size={13} stroke={2} />
          <span>Duplicate</span>
        </button>

        <div class="divider"></div>

        <button class="ctx-item" onclick={() => ondelete(menu.target.id)}>
          <IconX size={13} stroke={2} />
          <span>Close</span>
        </button>

        <button class="ctx-item" onclick={() => oncloseothers(menu.target.id)}>
          <IconX size={13} stroke={2} />
          <span>Close Others</span>
        </button>
      {/if}

      <button class="ctx-item danger" onclick={oncloseall}>
        <IconTrash size={13} stroke={2} />
        <span>Close All</span>
      </button>
    {:else if menu.type === "folder"}
      <button
        class="ctx-item"
        onclick={() => onnew(menu.target?.name || "scripts")}
      >
        <IconPlus size={13} stroke={2} />
        <span>New File in {menu.target?.name || "Folder"}</span>
      </button>

      <div class="divider"></div>

      <button
        class="ctx-item"
        onclick={() => onrevealfolder(menu.target?.name || "scripts")}
      >
        <IconFolderOpen size={13} stroke={2} />
        <span>Reveal in File Explorer</span>
      </button>
    {:else if menu.target}
      <button class="ctx-item" onclick={() => onopenfile(menu.target)}>
        <IconFileCode size={13} stroke={2} />
        <span>Open in Editor</span>
      </button>

      <button class="ctx-item" onclick={(e) => onrename(menu.target, e)}>
        <IconPencil size={13} stroke={2} />
        <span>Rename</span>
      </button>

      <button class="ctx-item" onclick={() => onduplicate(menu.target)}>
        <IconCopy size={13} stroke={2} />
        <span>Duplicate</span>
      </button>

      <div class="divider"></div>

      <button class="ctx-item danger" onclick={() => ondelete(menu.target.id)}>
        <IconTrash size={13} stroke={2} />
        <span>Delete</span>
      </button>
    {:else}
      <button class="ctx-item" onclick={() => onnew("scripts")}>
        <IconPlus size={13} stroke={2} />
        <span>New File</span>
      </button>
    {/if}
  </div>
{/if}

<style>
  .ctx-menu {
    position: fixed;
    z-index: 100;
    width: 175px;
    background: #1c1c1c;
    border: 1px solid rgba(255, 255, 255, 0.08);
    border-radius: 8px;
    padding: 4px;
    display: flex;
    flex-direction: column;
    gap: 2px;
    box-shadow: 0 8px 24px rgba(0, 0, 0, 0.5);
  }

  .divider {
    height: 1px;
    background: rgba(255, 255, 255, 0.06);
    margin: 3px 0;
  }

  .ctx-item {
    display: flex;
    align-items: center;
    gap: 8px;
    width: 100%;
    height: 26px;
    padding: 0 8px;
    border-radius: 5px;
    background: transparent;
    border: none;
    color: #ccc;
    font-family: "Syne", sans-serif;
    font-size: 11px;
    cursor: pointer;
    text-align: left;
    transition: 0.12s ease;
    box-sizing: border-box;
  }

  .ctx-item:hover {
    background: #252525;
    color: #fff;
  }

  .ctx-item.danger {
    color: #ff5252;
  }

  .ctx-item.danger:hover {
    background: rgba(255, 82, 82, 0.12);
    color: #ff6b6b;
  }
</style>
