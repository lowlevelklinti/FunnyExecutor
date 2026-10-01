<script>
  import { IconMinus, IconX } from "@tabler/icons-svelte";
  import { windowAction } from "../lib/bridge.js";
</script>

<header class="titlebar">
  <div class="drag-region">
    <div class="brand">
      <svg viewBox="0 0 116.7 134" class="logo">
        <path fill="#b51a2b" d="m97 2h-19c-9.6 0-26 10.3-32 25-2 4.9-2 13.9-2 25l-22 23h24v59h7.7l18.3-20v-37h15.9l8.1-25-24-1v-16.4c0-6.8 5.7-10.6 10.6-10.6s13.4 0.3 14.4 0v-22zm-50.3 72.8 22.3-20.9v21.1l-22.3-0.2z" />
      </svg>
    </div>

    <span class="title">Funny Executor</span>
  </div>

  <div class="controls">
    <button class="btn" title="Minimize" onclick={() => windowAction("minimize")}>
      <IconMinus size={13} stroke={2} />
    </button>
    <button class="btn close" title="Close" onclick={() => windowAction("close")}>
      <IconX size={13} stroke={2} />
    </button>
  </div>
</header>

<style>
  .titlebar {
    position: relative;
    z-index: 50;
    display: flex;
    align-items: center;
    height: 40px;
    padding: 0 14px 0 16px;
    background: transparent;
    user-select: none;
  }

  .drag-region {
    display: flex;
    align-items: center;
    flex: 1;
    min-width: 0;
    height: 100%;
  }

  .brand {
    display: flex;
    align-items: center;
    width: 60px;
  }

  .logo {
    width: 18px;
    height: 21px;
  }

  .title {
    flex: 1;
    text-align: center;
    font-family: 'Syne', sans-serif;
    font-size: 13.5px;
    color: #dedede;
  }

  .controls {
    display: flex;
    align-items: center;
    justify-content: flex-end;
    gap: 4px;
    width: 60px;
    z-index: 60;
  }

  .btn {
    display: grid;
    place-items: center;
    width: 26px;
    height: 26px;
    border-radius: 6px;
    background: transparent;
    border: none;
    color: #888;
    cursor: pointer;
    transition: 0.15s ease;
  }

  .btn:hover {
    color: #fff;
    background: #252525;
  }

  .btn.close:hover {
    background: #b51a2b;
  }
</style>
