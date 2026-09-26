import time
import threading
import requests
from pathlib import Path

DEBUG = True

DISCORD_INVITE = "https://discord.gg/fmTJvVmnA2"
GAME_PAGE_URL = "https://www.roblox.com/games/"
THUMBNAIL_API = "https://thumbnails.roblox.com/v1/games/icons?universeIds={}&size=512x512&format=Png&isCircular=false"

_thumbnail_cache = {}
_universe_cache = {}

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
    'Accept': 'application/json',
}


def dbg(msg):
    if DEBUG:
        print(f"[RPC] {msg}")


def get_universe_id(place_id):
    if place_id in _universe_cache:
        return _universe_cache[place_id]
    try:
        resp = requests.get(
            f"https://apis.roblox.com/universes/v1/places/{place_id}/universe",
            headers=HEADERS, timeout=5
        )
        if resp.status_code == 200:
            data = resp.json()
            universe_id = data.get('universeId')
            if universe_id:
                _universe_cache[place_id] = universe_id
                return universe_id
    except Exception as e:
        dbg(f"universeId fetch failed: {e}")
    return None


def get_game_thumbnail(place_id):
    if place_id in _thumbnail_cache:
        return _thumbnail_cache[place_id]
    universe_id = get_universe_id(place_id)
    if not universe_id:
        return None
    try:
        resp = requests.get(
            THUMBNAIL_API.format(universe_id),
            headers=HEADERS, timeout=5
        )
        if resp.status_code == 200:
            data = resp.json()
            if data.get('data') and len(data['data']) > 0:
                url = data['data'][0].get('imageUrl')
                if url:
                    _thumbnail_cache[place_id] = url
                    return url
    except Exception as e:
        dbg(f"thumbnail fetch failed: {e}")
    return None


def get_game_from_bridge():
    try:
        from FAPI import bridge
        state = bridge.game_state
        if not state:
            return None
        if time.time() - state.get('timestamp', 0) > 30:
            return None
        place_id = state.get('placeId')
        if not place_id:
            return None
        return {
            'place_id': place_id,
            'name': state.get('gameName', 'Unknown Game'),
            'creator': state.get('creator', 'Unknown'),
        }
    except Exception:
        return None


def run_game_info_script(worker):
    try:
        if worker is None or worker.executor is None:
            return False
        if not worker.executor.injected:
            return False
        script_path = Path(__file__).parent / 'game_info_script.lua'
        if not script_path.exists():
            return False
        with open(script_path, 'r', encoding='utf-8') as f:
            script = f.read()
        worker.executor.execute(script)
        return True
    except Exception as e:
        dbg(f"script execution failed: {e}")
    return False


def update_rpc(rpc, game_info=None):
    try:
        if game_info:
            thumb_url = get_game_thumbnail(game_info['place_id'])
            rpc.update(
                state=f"Playing {game_info['name']}",
                details=f"by {game_info['creator']}",
                large_image="logo",
                large_text="Funny Executor",
                small_image=thumb_url or "roblox",
                small_text=game_info['name'],
                buttons=[
                    {"label": "See Game Page", "url": f"{GAME_PAGE_URL}{game_info['place_id']}"},
                    {"label": "Join Discord Server", "url": DISCORD_INVITE},
                ],
            )
        else:
            rpc.update(
                state="In Funny Executor",
                details="Idling",
                large_image="logo",
                large_text="Funny Executor",
                buttons=[
                    {"label": "Join Discord Server", "url": DISCORD_INVITE},
                    {"label": "Download", "url": "https://github.com"},
                ],
            )
    except Exception as e:
        dbg(f"rpc update failed: {e}")


class RpcManager:
    def __init__(self, rpc, poll_interval=5.0):
        self.rpc = rpc
        self.poll_interval = poll_interval
        self._running = False
        self._enabled = True
        self._thread = None
        self._last_game_id = None
        self._script_executed = False
        self._worker = None

    def setExecutor(self, worker):
        self._worker = worker

    def setEnabled(self, enabled):
        self._enabled = enabled
        if not enabled:
            self.clear()
        else:
            self._script_executed = False
            self._last_game_id = None
            from FAPI import bridge
            bridge.game_state = {}
            update_rpc(self.rpc, None)

    def isEnabled(self):
        return self._enabled

    def clear(self):
        try:
            self.rpc.clear()
        except Exception:
            pass

    def start(self):
        if self._running:
            return
        self._running = True
        if self._enabled:
            update_rpc(self.rpc, None)
        self._thread = threading.Thread(target=self._poll_loop, daemon=True)
        self._thread.start()

    def stop(self):
        self._running = False
        if self._thread:
            self._thread.join(timeout=self.poll_interval + 1)
        self.clear()

    def _poll_loop(self):
        while self._running:
            try:
                if not self._enabled:
                    time.sleep(2)
                    continue

                import psutil
                rbx_running = False
                for proc in psutil.process_iter(['name']):
                    try:
                        if proc.name().lower() == 'robloxplayerbeta.exe':
                            rbx_running = True
                            break
                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                        pass

                if not rbx_running:
                    if self._script_executed:
                        self._script_executed = False
                        self._last_game_id = None
                        from FAPI import bridge
                        bridge.game_state = {}
                        update_rpc(self.rpc, None)
                    time.sleep(2)
                    continue

                if self._worker is None or self._worker.executor is None:
                    time.sleep(2)
                    continue

                if not self._worker.executor.injected:
                    if self._script_executed or self._last_game_id is not None:
                        self._script_executed = False
                        self._last_game_id = None
                        from FAPI import bridge
                        bridge.game_state = {}
                        update_rpc(self.rpc, None)
                    time.sleep(2)
                    continue

                if not self._script_executed:
                    if run_game_info_script(self._worker):
                        self._script_executed = True
                    else:
                        time.sleep(2)
                        continue

                game = get_game_from_bridge()
                current_id = game.get('place_id') if game else None

                if current_id != self._last_game_id:
                    self._last_game_id = current_id
                    update_rpc(self.rpc, game)
            except Exception as e:
                dbg(f"poll error: {e}")

            time.sleep(self.poll_interval)
