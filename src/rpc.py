"""Discord rich presence for the executor shell.

Runs on a plain background thread - it only needs to know when a script was
executed and which game is currently open, both of which the shell already
tracks.
"""

import threading
import time

CLIENT_ID = "1553410003417960469"
DISCORD_INVITE = "https://discord.gg/e9Ru9nuSyv"
PROJECT_URL = "https://github.com/lowlevelklinti/FunnyExecutor"


def dbg(msg):
    print(f"[rpc] {msg}")


def discordPresent():
    try:
        import psutil
    except Exception:
        return False

    try:
        for proc in psutil.process_iter(["name"]):
            try:
                name = (proc.name() or "").lower()
            except Exception:
                continue
            if name.startswith("discord"):
                return True
    except Exception:
        return False
    return False


def updateRpc(rpc, gameInfo=None):
    if rpc is None:
        return
    try:
        rpc.update(
            state="Using Funny Executor",
            details="Skidding",
            large_image="logo",
            large_text="Funny Executor",
            buttons=[
                {"label": "Join Discord Server", "url": DISCORD_INVITE},
                {"label": "Download", "url": PROJECT_URL},
            ],
        )
    except Exception as e:
        dbg(f"update failed: {e}")


class RpcManager:
    def __init__(self, clientId=CLIENT_ID, pollInterval=5.0):
        self.clientId = clientId
        self.pollInterval = pollInterval
        self._running = False
        self._enabled = False
        self._connected = False
        self._rpc = None
        self._thread = None
        self._lock = threading.Lock()
        self._gameState = {}

    def setGameState(self, gameState):
        """Called by the shell whenever FAPI reports a new place."""
        with self._lock:
            self._gameState = dict(gameState or {})

    def discordPresent(self):
        return discordPresent()

    def _ensureConnection(self):
        if self._connected and self._rpc is not None:
            return True
        try:
            from pypresence import Presence

            self._rpc = Presence(self.clientId)
            self._rpc.connect()
            self._connected = True
            dbg("connected to Discord RPC")
            return True
        except Exception as e:
            dbg(f"connect failed: {e}")
            self._rpc = None
            self._connected = False
            return False

    def _disconnect(self):
        if self._rpc is not None:
            try:
                self._rpc.clear()
            except Exception:
                pass
            try:
                self._rpc.close()
            except Exception:
                pass
        self._rpc = None
        self._connected = False

    def setEnabled(self, enabled):
        if enabled and not discordPresent():
            dbg("Discord not detected, leaving RPC disabled")
            self._enabled = False
            return

        self._enabled = enabled
        try:
            from FAPI import bridge

            bridge.game_state = {}
        except Exception:
            pass

    def isEnabled(self):
        return self._enabled

    def clear(self):
        if self._rpc is not None:
            try:
                self._rpc.clear()
            except Exception:
                pass

    def start(self):
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._pollLoop, daemon=True)
        self._thread.start()

    def stop(self):
        self._running = False
        if self._thread:
            self._thread.join(timeout=self.pollInterval + 1)
        self.clear()
        self._disconnect()

    def _pollLoop(self):
        while self._running:
            try:
                if not self._enabled:
                    if self._connected:
                        self.clear()
                        self._disconnect()
                    time.sleep(1)
                    continue

                if not self._connected:
                    if not self._ensureConnection():
                        time.sleep(2)
                        continue
                    updateRpc(self._rpc, None)
            except Exception as e:
                dbg(f"poll error: {e}")

            time.sleep(self.pollInterval)