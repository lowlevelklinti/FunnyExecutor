<script>
  import { fly, fade } from "svelte/transition";
  import { cubicOut } from "svelte/easing";

  let { message = "", visible = false } = $props();
</script>

{#if visible}
  <div
    class="toast-feedback"
    in:fly={{ y: 16, duration: 220, easing: cubicOut }}
    out:fade={{ duration: 150 }}
  >
    <span>{message}</span>
  </div>
{/if}

<style>
  .toast-feedback {
    position: absolute;
    bottom: 20px;
    left: calc(50% + 28px);
    transform: translateX(-50%);
    z-index: 1000;
    background-color: #222222;
    border: 1px solid rgba(255, 255, 255, 0.08);
    color: #e5e5e5;
    font-family: 'Syne', sans-serif;
    font-size: 11.5px;
    font-weight: 400;
    padding: 6px 12px;
    border-radius: 6px;
    box-shadow: 0 6px 18px rgba(0, 0, 0, 0.45);
    pointer-events: none;
    display: inline-flex;
    align-items: center;
    white-space: nowrap;
  }
</style>
