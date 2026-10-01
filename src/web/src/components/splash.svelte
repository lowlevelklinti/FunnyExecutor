<script>
  import { onMount } from "svelte";

  let { onfinish } = $props();
  let opacity = $state(1);
  let phase = $state("initial");

  onMount(() => {
    let t1 = setTimeout(() => {
      phase = "centered";
    }, 50);

    let t2 = setTimeout(() => {
      phase = "revealed";
    }, 850);

    let t3 = setTimeout(() => {
      opacity = 0;

      setTimeout(() => {
        if (onfinish) onfinish();
      }, 450);
    }, 2200);

    return () => {
      clearTimeout(t1);
      clearTimeout(t2);
      clearTimeout(t3);
    };
  });
</script>

<div class="splash-screen" style="opacity: {opacity};">
  <div class="splash-wrap {phase}">
    <div class="logo-box">
      <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 116.7 134" class="splash-logo">
        <path fill="#b51a2b" d="m97 2h-19c-9.6 0-26 10.3-32 25-2 4.9-2 13.9-2 25l-22 23h24v59h7.7l18.3-20v-37h15.9l8.1-25-24-1v-16.4c0-6.8 5.7-10.6 10.6-10.6s13.4 0.3 14.4 0v-22zm-50.3 72.8 22.3-20.9v21.1l-22.3-0.2z" />
      </svg>
    </div>

    <div class="text-wrapper">
      <span class="brand-text">Funny Executor</span>
    </div>
  </div>
</div>

<style>
  .splash-screen {
    position: absolute;
    inset: 0;
    background-color: #1a1a1a;
    display: flex;
    align-items: center;
    justify-content: center;
    transition: opacity 0.45s cubic-bezier(0.22, 1, 0.36, 1);
    z-index: 20;
    overflow: hidden;
  }

  .splash-wrap {
    position: relative;
    display: flex;
    align-items: center;
    justify-content: center;
    will-change: transform, opacity;
  }

  .splash-wrap.initial {
    transform: translateY(320px);
    opacity: 0;
  }

  .splash-wrap.centered {
    transition:
      transform 0.8s cubic-bezier(0.16, 1, 0.3, 1),
      opacity 0.6s cubic-bezier(0.22, 1, 0.36, 1);
  }

  .splash-wrap.revealed {
    transform: translateY(0);
    opacity: 1;
  }

  .logo-box {
    display: flex;
    align-items: center;
    justify-content: center;
    z-index: 2;
    transform: translateX(85px);
    transition: transform 0.75s cubic-bezier(0.16, 1, 0.3, 1);
    will-change: transform;
  }

  .splash-wrap.revealed .logo-box {
    transform: translateX(0);
  }

  .splash-logo {
    width: 50px;
    height: 57px;
    display: block;
  }

  .text-wrapper {
    display: flex;
    align-items: center;
    padding-left: 18px;
    z-index: 1;
    clip-path: inset(0 100% 0 0);
    transform: translateX(-30px);
    opacity: 0;
    transition:
      clip-path 0.75s cubic-bezier(0.16, 1, 0.3, 1),
      transform 0.75s cubic-bezier(0.16, 1, 0.3, 1),
      opacity 0.55s cubic-bezier(0.22, 1, 0.36, 1);
    will-change: clip-path, transform, opacity;
  }

  .splash-wrap.revealed .text-wrapper {
    clip-path: inset(0 0% 0 0);
    transform: translateX(0);
    opacity: 1;
  }

  .brand-text {
    font-family: 'Syne', sans-serif;
    font-size: 38px;
    font-weight: 400;
    color: #ffffff;
    letter-spacing: -0.5px;
    line-height: 1;
    white-space: nowrap;
    user-select: none;
  }
</style>
