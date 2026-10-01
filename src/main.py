"""Funny Executor desktop shell.

Hosts the svelte UI (web/) inside a frameless WebView2 window (pywebview) and
gives it a native backend:

  * workspace files on disk (%APPDATA%\\FunnyExecutor)
  * the FAPI executor - inject / execute / client list
  * the console buffer the injected roblox scripts print into
  * settings.json, os.startfile, real window controls

    python src/main.py            # build/serve web/dist and open the window
    python src/main.py --dev      # load the vite dev server instead (hot reload)
    python src/main.py --debug    # open devtools
"""

from __future__ import annotations

import argparse
import ctypes
import functools
import json
import os
import shutil
import subprocess
import sys
import threading
import time
import urllib.request
from ctypes import wintypes
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import webview

sys.path.insert(0, str(Path(__file__).resolve().parent))

import FAPI
from FAPI import bridge
from luau_api import comp
from rpc import RpcManager

FOLDERS = ("autoexec", "workspace", "scripts")
SETTINGS_FILE = "settings.json"
DEV_URL = "http://localhost:5173/?native=1"
DEFAULT_SIZE = (1080, 680)
BROWSER_UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/152.0.0.0 Safari/537.36"
CREATE_NO_WINDOW = 0x08000000

# win32 bits used to get the stock windows minimize/restore animation on a
# frameless window: without a system menu DWM just makes the window vanish.
GWL_STYLE = -16
GWL_WNDPROC = -4
WS_POPUP = 0x80000000
WS_OVERLAPPEDWINDOW = 0x00CF0000
WS_CLIPSIBLINGS = 0x04000000
WS_CLIPCHILDREN = 0x02000000
SWP_NOSIZE = 0x0001
SWP_NOMOVE = 0x0002
SWP_NOZORDER = 0x0004
SWP_NOACTIVATE = 0x0010
SWP_FRAMECHANGED = 0x0020
WM_NCCALCSIZE = 0x0083
WM_NCHITTEST = 0x0084
WM_SYSCOMMAND = 0x0112
SC_MINIMIZE = 0xF020
SC_RESTORE = 0xF120
HTCLIENT = 1
DWMWA_BORDER_COLOR = 34
DWMWA_COLOR_NONE = 0xFFFFFFFE
LRESULT = ctypes.c_ssize_t
WNDPROC = ctypes.WINFUNCTYPE(
    LRESULT, wintypes.HWND, ctypes.c_uint, wintypes.WPARAM, wintypes.LPARAM
)

user32 = ctypes.WinDLL("user32", use_last_error=True)
_get_window_long = getattr(user32, "GetWindowLongPtrW", user32.GetWindowLongW)
_get_window_long.restype = ctypes.c_longlong
_get_window_long.argtypes = [wintypes.HWND, ctypes.c_int]
_set_window_long = getattr(user32, "SetWindowLongPtrW", user32.SetWindowLongW)
_set_window_long.restype = ctypes.c_longlong
_set_window_long.argtypes = [wintypes.HWND, ctypes.c_int, ctypes.c_longlong]
_call_window_proc = user32.CallWindowProcW
_call_window_proc.restype = LRESULT
_call_window_proc.argtypes = [
    ctypes.c_longlong,
    wintypes.HWND,
    ctypes.c_uint,
    wintypes.WPARAM,
    wintypes.LPARAM,
]
_wndproc_keepalive: list[object] = []
_framed_windows: set[int] = set()


def log(*parts: object) -> None:
    print("[funnyexecutor]", *parts, flush=True)


def hwnd_of(window: webview.Window | None) -> int:
    handle = getattr(getattr(window, "native", None), "Handle", None)
    if handle is None:
        return 0
    return int(handle.ToInt64()) if hasattr(handle, "ToInt64") else int(handle)


def enable_window_animations(window: webview.Window | None) -> bool:
    """DWM only animates minimize/restore for windows that still own a caption.

    A WS_POPUP frameless window just blinks out, so we put the standard
    overlapped bits back and swallow the non-client area ourselves:
    WM_NCCALCSIZE -> 0 makes the client area cover the frame (no visible
    caption), while DWM keeps treating the window as a normal one and
    animates the taskbar transitions.
    """
    hwnd = hwnd_of(window)
    if not hwnd:
        return False

    def apply() -> None:
        rect = wintypes.RECT()
        user32.GetWindowRect(hwnd, ctypes.byref(rect))
        width = rect.right - rect.left
        height = rect.bottom - rect.top

        if hwnd not in _framed_windows:
            box: dict[str, int] = {"proc": _get_window_long(hwnd, GWL_WNDPROC)}

            def wndproc(hwnd, msg, wparam, lparam):
                if msg == WM_NCCALCSIZE and wparam:
                    return 0
                if msg == WM_NCHITTEST:
                    return HTCLIENT
                return _call_window_proc(box["proc"], hwnd, msg, wparam, lparam)

            proc = WNDPROC(wndproc)
            _wndproc_keepalive.append(proc)
            _set_window_long(
                hwnd, GWL_WNDPROC, ctypes.cast(proc, ctypes.c_void_p).value
            )
            _framed_windows.add(hwnd)

        style = _get_window_long(hwnd, GWL_STYLE)
        wanted = (
            (style & ~WS_POPUP) | WS_OVERLAPPEDWINDOW | WS_CLIPSIBLINGS | WS_CLIPCHILDREN
        )
        if wanted != style:
            _set_window_long(hwnd, GWL_STYLE, wanted)

        user32.SetWindowPos(
            hwnd,
            None,
            rect.left,
            rect.top,
            width,
            height,
            SWP_FRAMECHANGED | SWP_NOZORDER | SWP_NOACTIVATE,
        )

        # winforms subtracts the frame it just gained, so hand the original
        # size back through the form itself - otherwise we end up 16x39 short.
        form = getattr(window, "native", None)
        if form is not None:
            try:
                current = form.Size
                if current.Width != width or current.Height != height:
                    form.Size = type(current)(width, height)
            except Exception as err:  # pragma: no cover - interop hiccup
                log("could not restore the window size:", err)

        border = ctypes.c_int(DWMWA_COLOR_NONE)
        ctypes.windll.dwmapi.DwmSetWindowAttribute(
            wintypes.HWND(hwnd), DWMWA_BORDER_COLOR, ctypes.byref(border), ctypes.sizeof(border)
        )

    # pywebview raises shown from its own thread; SetWindowPos and a one shot
    # form.Size write are both safe from here.
    apply()
    return True


def app_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent


def workspace_root() -> Path:
    """Same folder FAPI uses for its file api, so scripts and games agree."""
    base = Path(os.environ["APPDATA"]) / "FunnyExecutor"
    base.mkdir(parents=True, exist_ok=True)
    for folder in FOLDERS:
        (base / folder).mkdir(exist_ok=True)
    return base


def frontend_candidates() -> list[Path]:
    candidates = []
    env = os.environ.get("FE_FRONTEND")
    if env:
        candidates.append(Path(env))
    here = app_dir()
    candidates += [
        here.parent / "web" / "dist",
        here / "web" / "dist",
        here / "dist",
    ]
    return candidates


def resolve_frontend() -> Path:
    candidates = frontend_candidates()
    for path in candidates:
        if (path / "index.html").is_file():
            log("frontend:", path)
            return path

    for path in candidates:
        parent = path.parent
        if (parent / "package.json").is_file() and shutil.which("npm"):
            log("frontend missing, building:", parent)
            result = subprocess.run(
                ["npm", "run", "build"],
                cwd=parent,
                creationflags=CREATE_NO_WINDOW,
            )
            if result.returncode == 0 and (path / "index.html").is_file():
                log("frontend built:", path)
                return path

    raise SystemExit(
        "web/dist not found. build it first:\n  cd web && npm install && npm run build"
    )


class Handler(SimpleHTTPRequestHandler):
    def log_message(self, fmt: str, *args: object) -> None:
        if os.environ.get("FE_HTTP_LOG"):
            log("http", fmt % args)

    def end_headers(self) -> None:
        self.send_header("Cache-Control", "no-store")
        super().end_headers()


def start_server(directory: Path) -> tuple[ThreadingHTTPServer, str]:
    handler = functools.partial(Handler, directory=str(directory))
    httpd = ThreadingHTTPServer(("127.0.0.1", 0), handler)
    httpd.daemon_threads = True
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    # the ?native=1 flag tells the frontend a python shell is on the other side
    return httpd, f"http://127.0.0.1:{httpd.server_address[1]}/?native=1"


class Executor:
    """Threaded Roblox session - owns the FAPI executor and its state.

    The ui talks to this through invoke("inject"/"execute"/"get_status"), it
    never touches FAPI directly.
    """

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._executor = None
        self._sdk = None
        self._queued = False
        self._injecting = False
        self._lastInjectTry = 0.0
        self._state = "idle"
        self._clients: dict[int, dict] = {}
        self._running = True
        self._lastGameKey = None
        self._rpc = None

        self._thread = threading.Thread(target=self._poll, daemon=True)
        self._thread.start()

    # --- lifecycle ------------------------------------------------------

    def stop(self) -> None:
        self._running = False
        if self._thread.is_alive():
            self._thread.join(timeout=2.0)

    def _setState(self, state: str) -> None:
        with self._lock:
            self._state = state

    def status(self) -> dict[str, object]:
        with self._lock:
            injected = False
            roblox = False
            if self._executor is not None:
                try:
                    injected = bool(self._executor.injected)
                except Exception:
                    injected = False
            try:
                roblox = bool(FAPI.robloxOpen())
            except Exception:
                roblox = False

            game = bridge.game_state or {}
            clients = list(self._clients.values())

            return {
                "state": self._state,
                "injected": injected,
                "roblox": roblox,
                "pid": clients[0]["pid"] if clients else 0,
                "placeId": int(game.get("placeId") or 0),
                "gameName": str(game.get("gameName") or ""),
                "creator": str(game.get("creator") or ""),
            }

    def clients(self) -> list[dict]:
        with self._lock:
            return list(self._clients.values())

    # --- worker ---------------------------------------------------------

    def _ensureExecutor(self) -> bool:
        with self._lock:
            if self._executor is not None and self._sdk is not None:
                try:
                    import psutil

                    if psutil.pid_exists(self._sdk.mem.process_id):
                        return True
                except Exception:
                    pass
                self._executor = None
                self._sdk = None

        try:
            if not FAPI.robloxOpen():
                with self._lock:
                    self._executor = None
                    self._sdk = None
                return False
        except Exception:
            return False

        try:
            executor = FAPI.Executor()
            with self._lock:
                self._executor = executor
                self._sdk = executor.sdk
            return True
        except Exception:
            with self._lock:
                self._executor = None
                self._sdk = None
            return False

    def _refreshClients(self) -> None:
        try:
            import psutil
        except Exception:
            return

        found: dict[int, dict] = {}
        try:
            for proc in psutil.process_iter(["name", "exe"]):
                try:
                    if (proc.info.get("name") or "").lower() != "robloxplayerbeta.exe":
                        continue
                except Exception:
                    continue
                pid = proc.info.get("pid") or proc.pid
                found[pid] = {
                    "id": pid,
                    "pid": pid,
                    "username": "roblox",
                    "displayName": proc.info.get("name") or "RobloxPlayerBeta",
                    "path": proc.info.get("exe") or "",
                }
        except Exception:
            return

        game = bridge.game_state or {}
        placeId = game.get("placeId")

        sdkPid = 0
        with self._lock:
            if self._sdk is not None:
                sdkPid = getattr(self._sdk.mem, "process_id", 0) or 0

        for pid, entry in found.items():
            if pid == sdkPid:
                # only the process we actually attached to has a known game
                entry["displayName"] = game.get("gameName") or entry["displayName"]
                entry["creator"] = game.get("creator") or ""
                entry["placeId"] = game.get("placeId") or 0

        with self._lock:
            if set(found) != set(self._clients):
                self._clients = found
            elif self._clients:
                for pid, entry in found.items():
                    if pid in self._clients:
                        self._clients[pid] = entry

            key = (placeId, game.get("gameName"), game.get("creator"))
            if key != self._lastGameKey:
                self._lastGameKey = key
                if self._rpc is not None:
                    self._rpc.setGameState(game)

    def _tryInject(self) -> None:
        if self._injecting:
            return

        with self._lock:
            executor = self._executor
            if executor is None:
                return
            if self._state == "injected":
                return

        try:
            if executor.injected:
                return
            dm = executor.sdk.datamodel
            if not dm or dm.name != "Ugc" or not dm.address:
                return
            if dm.address in executor._handledDms:
                return
            players = dm.findFirstChild("Players")
            if not players or not players.getChildren():
                return
        except Exception:
            return

        if time.time() - self._lastInjectTry < 1.0:
            return

        self._lastInjectTry = time.time()
        self._injecting = True
        try:
            executor.inject()
        except Exception as err:
            bridge.consolePush(f"inject failed: {err}", 12)
        finally:
            self._injecting = False

    def _poll(self) -> None:
        while self._running:
            try:
                self._refreshClients()

                if not self._ensureExecutor():
                    self._queued = False
                    self._setState("idle")
                    time.sleep(0.5)
                    continue

                try:
                    injected = bool(self._executor.injected)
                except Exception:
                    injected = False

                if injected:
                    self._setState("injected")
                elif self._queued:
                    self._setState("queued")
                    self._tryInject()
                else:
                    self._setState("idle")
            except Exception:
                self._setState("idle")
            time.sleep(0.25)

    # --- ui facing ------------------------------------------------------

    def inject(self) -> dict[str, object]:
        if not self._ensureExecutor():
            raise RuntimeError("Open Roblox before injecting")

        try:
            if self._executor.injected:
                raise RuntimeError("Already injected")
        except RuntimeError:
            raise
        except Exception:
            pass

        self._queued = True
        self._tryInject()

        status = self.status()
        if not status["injected"]:
            bridge.consolePush("inject queued, waiting for the game to load...", 14)
        return status

    def execute(self, source: str) -> dict[str, object]:
        with self._lock:
            executor = self._executor

        if executor is None:
            raise RuntimeError("Inject before executing")

        try:
            ready = bool(executor.injected)
        except Exception:
            ready = False

        if not ready:
            raise RuntimeError("You must inject before executing")

        try:
            executor.execute(str(source))
        except FAPI.ExecutionError as err:
            raise RuntimeError(str(err)) from err
        except Exception as err:
            bridge.consolePush(f"execute failed: {err}", 12)
            raise RuntimeError(str(err)) from err

        return {"ok": True}

    def setRpc(self, rpc) -> None:
        self._rpc = rpc


class Shell:
    """Everything the web layer can ask the shell to do."""

    def __init__(self, window: webview.Window | None = None) -> None:
        self.window = window
        self.root = workspace_root()
        self._lock = threading.Lock()
        self.executor = Executor()
        self.rpc = RpcManager()
        self.executor.setRpc(self.rpc)
        log("workspace root:", self.root)

        settings = self.read_settings()
        discord = self.rpc.discordPresent()
        general = settings.get("general") if isinstance(settings.get("general"), dict) else {}
        enabled = bool(general.get("rpcEnabled", settings.get("rpcEnabled", False))) and discord
        self.rpc.setEnabled(enabled)
        self.rpc.start()
        log("discord rpc:", "on" if enabled else "off")

    # --- workspace ------------------------------------------------------

    def _resolve(self, folder: str = "scripts", name: str | None = None) -> Path:
        target = str(folder or "scripts").lower()
        if target not in FOLDERS:
            target = "scripts"
        path = self.root / target
        if name is not None:
            raw = str(name)
            safe = Path(raw).name
            if not safe or safe != raw or safe in (".", ".."):
                raise ValueError(f"bad file name: {raw!r}")
            path = path / safe
        return path

    def read_workspace_files(self) -> list[dict[str, object]]:
        files: list[dict[str, object]] = []
        with self._lock:
            counter = 100
            for folder in FOLDERS:
                for path in sorted((self.root / folder).iterdir()):
                    if not path.is_file():
                        continue
                    try:
                        content = path.read_text(encoding="utf-8", errors="replace")
                    except OSError:
                        content = ""
                    files.append(
                        {
                            "id": counter,
                            "name": path.name,
                            "content": content,
                            "folder": folder,
                        }
                    )
                    counter += 1
        return files

    def write_workspace_file(self, folder: str, name: str, content: str = "") -> None:
        path = self._resolve(folder, name)
        with self._lock:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8")

    def remove_workspace_file(self, folder: str, name: str) -> None:
        path = self._resolve(folder, name)
        with self._lock:
            if path.is_file():
                path.unlink()

    def move_workspace_file(self, from_folder: str, to_folder: str, name: str) -> None:
        src = self._resolve(from_folder, name)
        dest = self._resolve(to_folder, name)
        with self._lock:
            if not src.is_file():
                raise FileNotFoundError(src)
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(src), str(dest))

    def reveal_folder(self, folder_name: str = "scripts") -> str:
        path = self._resolve(folder_name)
        path.mkdir(parents=True, exist_ok=True)
        os.startfile(path)
        return str(path)

    # --- settings -------------------------------------------------------

    def settings_path(self) -> Path:
        return self.root / SETTINGS_FILE

    def read_settings(self) -> dict[str, object]:
        path = self.settings_path()
        try:
            raw = path.read_text(encoding="utf-8")
        except FileNotFoundError:
            return {}
        except OSError:
            return {}

        try:
            data = json.loads(raw)
        except ValueError:
            return {}
        return data if isinstance(data, dict) else {}

    def write_settings(self, data: object) -> str:
        if not isinstance(data, dict):
            raise ValueError("settings must be an object")

        path = self.settings_path()
        with self._lock:
            # the ui only knows about its own sections, so merge on top of what
            # is already on disk instead of dropping keys it does not manage
            merged = self.read_settings()
            merged.update(data)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(
                json.dumps(merged, indent=2, ensure_ascii=False), encoding="utf-8"
            )
        return str(path)

    def set_rpc(self, enabled: bool) -> bool:
        self.rpc.setEnabled(bool(enabled))
        # the ui keeps this under general, older files had it at the top level
        settings = self.read_settings()
        general = settings.get("general")
        if not isinstance(general, dict):
            general = {}
            settings["general"] = general
        general["rpcEnabled"] = bool(enabled)
        settings.pop("rpcEnabled", None)
        self.write_settings(settings)
        return self.rpc.isEnabled()

    def discord_present(self) -> bool:
        return self.rpc.discordPresent()

    # --- executor -------------------------------------------------------

    def status(self) -> dict[str, object]:
        return self.executor.status()

    def inject(self) -> dict[str, object]:
        return self.executor.inject()

    def execute(self, source: str) -> dict[str, object]:
        return self.executor.execute(source)

    def clients(self) -> list[dict]:
        return self.executor.clients()

    def console_take(self) -> list[dict]:
        return [{"text": text, "color": color} for text, color in bridge.consoleTake()]

    def console_clear(self) -> int:
        bridge.consoleClearBuffer()
        return 0

    def luau_api(self) -> dict:
        return comp()

    # --- misc native bits ----------------------------------------------

    def open_url(self, url: str) -> None:
        os.startfile(url)

    def http_get(self, url: str) -> str:
        request = urllib.request.Request(url, headers={"User-Agent": BROWSER_UA})
        with urllib.request.urlopen(request, timeout=5) as response:
            return response.read().decode("utf-8", errors="replace")

    def exclude_from_defender(self) -> None:
        if os.name != "nt":
            raise RuntimeError("windows only")
        script = (
            "Start-Process powershell -Verb RunAs -WindowStyle Hidden -Wait "
            f"-ArgumentList '-NoProfile','-Command',\"Add-MpPreference "
            f"-ExclusionPath '{self.root}'\""
        )
        result = subprocess.run(
            ["powershell", "-NoProfile", "-Command", script],
            creationflags=CREATE_NO_WINDOW,
        )
        if result.returncode != 0:
            raise RuntimeError("cancelled")

    # --- window controls -----------------------------------------------

    def minimize(self) -> None:
        if not self.window:
            return
        hwnd = hwnd_of(self.window)
        if hwnd:
            user32.SendMessageW(hwnd, WM_SYSCOMMAND, SC_MINIMIZE, 0)
        else:
            self.window.minimize()

    def restore(self) -> None:
        if not self.window:
            return
        hwnd = hwnd_of(self.window)
        if hwnd:
            user32.SendMessageW(hwnd, WM_SYSCOMMAND, SC_RESTORE, 0)
        else:
            self.window.restore()

    def maximize(self) -> None:
        if self.window:
            self.window.maximize()

    def close(self) -> None:
        if self.window:
            self.window.destroy()

    def enable_animations(self) -> bool:
        return enable_window_animations(self.window)

    # --- single entry point used by the frontend ------------------------

    def invoke(self, cmd: str, args: dict[str, object] | None = None) -> object:
        payload = args or {}
        handlers = {
            "read_workspace_files": lambda: self.read_workspace_files(),
            "write_workspace_file": lambda: self.write_workspace_file(
                str(payload.get("folder", "scripts")),
                str(payload["name"]),
                str(payload.get("content", "")),
            ),
            "remove_workspace_file": lambda: self.remove_workspace_file(
                str(payload["folder"]), str(payload["name"])
            ),
            "move_workspace_file": lambda: self.move_workspace_file(
                str(payload["fromFolder"]),
                str(payload["toFolder"]),
                str(payload["name"]),
            ),
            "reveal_folder": lambda: self.reveal_folder(
                str(payload.get("folderName", "scripts"))
            ),
            "read_settings": lambda: self.read_settings(),
            "write_settings": lambda: self.write_settings(payload.get("data", {})),
            "open_url": lambda: self.open_url(str(payload["url"])),
            "http_get": lambda: self.http_get(str(payload["url"])),
            "exclude_from_defender": lambda: self.exclude_from_defender(),
            "get_status": lambda: self.status(),
            "inject": lambda: self.inject(),
            "execute": lambda: self.execute(str(payload.get("source", ""))),
            "get_clients": lambda: self.clients(),
            "get_console": lambda: self.console_take(),
            "clear_console": lambda: self.console_clear(),
            "get_luau_api": lambda: self.luau_api(),
            "set_rpc": lambda: self.set_rpc(bool(payload.get("enabled", False))),
            "discord_present": lambda: self.discord_present(),
        }
        handler = handlers.get(cmd)
        if handler is None:
            raise ValueError(f"unknown command: {cmd}")
        return handler()


def parse_size(value: str) -> tuple[int, int]:
    try:
        width, height = (int(part) for part in value.lower().split("x", 1))
        return width, height
    except ValueError:
        raise argparse.ArgumentTypeError("size must look like 1080x680") from None


def main() -> None:
    parser = argparse.ArgumentParser(description="funny executor webview shell")
    parser.add_argument("--dev", action="store_true", help="use the vite dev server")
    parser.add_argument("--debug", action="store_true", help="open devtools")
    parser.add_argument("--size", type=parse_size, default=DEFAULT_SIZE)
    args = parser.parse_args()

    httpd = None
    if args.dev:
        url = DEV_URL
        log("using dev server:", url)
    else:
        httpd, url = start_server(resolve_frontend())

    webview.settings["DRAG_REGION_SELECTOR"] = ".drag-region"

    window = webview.create_window(
        "Funny Executor",
        url,
        width=args.size[0],
        height=args.size[1],
        frameless=True,
        easy_drag=False,
        background_color="#1a1a1a",
    )
    shell = Shell(window)
    window.expose(
        shell.invoke,
        shell.minimize,
        shell.restore,
        shell.maximize,
        shell.close,
        shell.enable_animations,
    )

    def on_shown() -> None:
        # the hwnd only exists once the form is shown
        shell.enable_animations()

    def on_closed() -> None:
        log("window closed")
        shell.executor.stop()
        shell.rpc.stop()
        if httpd is not None:
            threading.Thread(target=httpd.shutdown, daemon=True).start()

    window.events.shown += on_shown
    window.events.closed += on_closed

    log("starting webview2 at", url)
    webview.start(debug=args.debug, private_mode=False)


if __name__ == "__main__":
    main()