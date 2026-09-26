import re
import shutil
from os import environ
from pathlib import Path

import requests
from pydantic import BaseModel
from pytauri import Commands, Manager
from pytauri.webview import WebviewWindow
from pytauri_wheel.lib import builder_factory, context_factory

from backend.worker import RobloxWorker

commands = Commands()

ROOT_DIR = Path(environ["APPDATA"]) / "FunnyExecutor"
STORE_DIR = ROOT_DIR
LUA_FILTER = ["lua", "luau", "txt"]
SCRIPT_EXTS = (".lua", ".luau", ".txt")
BASE_FOLDERS = ("scripts", "autoexec", "workspace")
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0 Safari/537.36")

_worker: RobloxWorker | None = None


def _getWorker() -> RobloxWorker:
    global _worker
    if _worker is None:
        _worker = RobloxWorker()
        _worker.start()
    return _worker


class Empty(BaseModel):
    pass


class ScriptBody(BaseModel):
    script: str


class WindowBody(BaseModel):
    action: str


class DialogBody(BaseModel):
    default_name: str | None = None
    content: str | None = None
    title: str | None = None


class TextBody(BaseModel):
    text: str


class StoreBody(BaseModel):
    name: str
    content: str | None = None


class PathBody(BaseModel):
    path: str


class WriteBody(BaseModel):
    path: str
    content: str = ""


class NewBody(BaseModel):
    name: str
    group: str | None = None
    folder: str | None = None


class MoveBody(BaseModel):
    path: str
    folder: str


class UrlBody(BaseModel):
    url: str


@commands.command()
async def inject(body: Empty, webview_window: WebviewWindow) -> dict:
    ok, message = _getWorker().requestInject()
    return {"ok": ok, "message": message}


@commands.command()
async def executeScript(body: ScriptBody, webview_window: WebviewWindow) -> dict:
    ok, message = _getWorker().requestExecute(body.script)
    return {"ok": ok, "message": message}


@commands.command()
async def windowControl(body: WindowBody, webview_window: WebviewWindow) -> None:
    action = body.action
    if action == "minimize":
        webview_window.minimize()
    elif action == "toggleMaximize":
        if webview_window.is_maximized():
            webview_window.unmaximize()
        else:
            webview_window.maximize()
    elif action == "close":
        webview_window.close()


@commands.command()
async def openFileDialog(body: Empty, webview_window: WebviewWindow) -> dict:
    from backend.native_dialogs import openFile

    result = openFile(LUA_FILTER)
    if not result:
        return {"canceled": True}
    path, text = result
    return {"canceled": False, "name": Path(path).name, "path": path, "content": text}


@commands.command()
async def saveFileDialog(body: DialogBody, webview_window: WebviewWindow) -> dict:
    from backend.native_dialogs import saveFile

    result = saveFile(
        default_name=body.default_name or "script.luau",
        content=body.content or "",
        extensions=LUA_FILTER,
        title=body.title or "Save File",
    )
    if not result:
        return {"canceled": True}
    return {"canceled": False, "name": Path(result).name, "path": result}


def _storePath(name: str) -> Path:
    safe = Path(name).name
    STORE_DIR.mkdir(parents=True, exist_ok=True)
    return STORE_DIR / safe


@commands.command()
async def readStore(body: TextBody, webview_window: WebviewWindow) -> str | None:
    p = _storePath(body.text)
    if not p.is_file():
        return None
    try:
        return p.read_text(encoding="utf-8")
    except OSError:
        return None


@commands.command()
async def writeStore(body: StoreBody, webview_window: WebviewWindow) -> None:
    p = _storePath(body.name)
    try:
        p.write_text(body.content or "", encoding="utf-8")
    except OSError:
        pass


@commands.command()
async def removeStore(body: TextBody, webview_window: WebviewWindow) -> None:
    try:
        _storePath(body.text).unlink(missing_ok=True)
    except OSError:
        pass


def _insideRoot(target: Path) -> bool:
    try:
        root = ROOT_DIR.resolve()
        target = target.resolve()
    except (OSError, RuntimeError):
        return False
    return root != target and root in target.parents


def _safeScript(path: str) -> Path | None:
    try:
        target = Path(path).expanduser().resolve()
    except (OSError, RuntimeError):
        return None
    if not _insideRoot(target) or target.suffix.lower() not in SCRIPT_EXTS:
        return None
    return target


def _safeFolder(path: str | None, default: Path | None = None) -> Path | None:
    if not path:
        return default
    try:
        target = Path(path).expanduser().resolve()
    except (OSError, RuntimeError):
        return None
    return target if _insideRoot(target) else None


def _cleanName(name: str) -> str:
    cleaned = re.sub(r'[<>:"/\\|?*\x00-\x1f]', '', (name or '').strip())
    return cleaned.strip('. ')[:64]


def _freePath(directory: Path, name: str) -> Path:
    stem, suffix = Path(name).stem, Path(name).suffix
    target = directory / name
    i = 2
    while target.exists():
        target = directory / f"{stem} {i}{suffix}"
        i += 1
    return target


def _fileEntry(p: Path) -> dict:
    try:
        stat = p.stat()
        size, modified = stat.st_size, int(stat.st_mtime)
    except OSError:
        size, modified = 0, 0
    return {"name": p.name, "path": str(p), "size": size, "modified": modified}


def _folderEntry(p: Path) -> dict:
    folders, files = [], []
    try:
        entries = sorted(p.iterdir(), key=lambda e: (not e.is_dir(), e.name.lower()))
    except OSError:
        entries = []
    for entry in entries:
        try:
            if entry.is_dir():
                folders.append(_folderEntry(entry))
            elif entry.is_file() and entry.suffix.lower() in SCRIPT_EXTS:
                files.append(_fileEntry(entry))
        except OSError:
            continue
    return {"name": p.name, "path": str(p), "folders": folders, "files": files}


@commands.command()
async def listScripts(body: Empty, webview_window: WebviewWindow) -> dict:
    ROOT_DIR.mkdir(parents=True, exist_ok=True)
    folders = []
    for key in BASE_FOLDERS:
        directory = ROOT_DIR / key
        try:
            directory.mkdir(parents=True, exist_ok=True)
            folders.append(_folderEntry(directory))
        except OSError:
            continue
    return {"folders": folders}


@commands.command()
async def readScript(body: PathBody, webview_window: WebviewWindow) -> dict:
    p = _safeScript(body.path)
    if p is None or not p.is_file():
        return {"ok": False, "message": "File not found"}
    try:
        content = p.read_text(encoding="utf-8", errors="replace")
    except OSError as e:
        return {"ok": False, "message": str(e)}
    return {"ok": True, "name": p.name, "path": str(p), "content": content}


@commands.command()
async def writeScript(body: WriteBody, webview_window: WebviewWindow) -> dict:
    p = _safeScript(body.path)
    if p is None:
        return {"ok": False, "message": "Path is outside the scripts folder"}
    try:
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(body.content or "", encoding="utf-8")
    except OSError as e:
        return {"ok": False, "message": str(e)}
    return {"ok": True, "path": str(p)}


@commands.command()
async def newScript(body: NewBody, webview_window: WebviewWindow) -> dict:
    name = _cleanName(body.name)
    if not name:
        return {"ok": False, "message": "No name given"}
    if Path(name).suffix.lower() not in SCRIPT_EXTS:
        name += ".luau"

    directory = _safeFolder(body.folder) or (ROOT_DIR / BASE_FOLDERS[0])
    try:
        directory.mkdir(parents=True, exist_ok=True)
        target = _freePath(directory, name)
        target.write_text("", encoding="utf-8")
    except OSError as e:
        return {"ok": False, "message": str(e)}
    return {"ok": True, "name": target.name, "path": str(target), "content": ""}


@commands.command()
async def createFolder(body: NewBody, webview_window: WebviewWindow) -> dict:
    name = _cleanName(body.name)
    if not name:
        return {"ok": False, "message": "No name given"}
    parent = _safeFolder(body.folder) or (ROOT_DIR / BASE_FOLDERS[0])
    try:
        parent.mkdir(parents=True, exist_ok=True)
        target = parent / name
        if target.exists():
            return {"ok": False, "message": "That folder already exists"}
        target.mkdir()
    except OSError as e:
        return {"ok": False, "message": str(e)}
    return {"ok": True, "name": target.name, "path": str(target)}


@commands.command()
async def moveScript(body: MoveBody, webview_window: WebviewWindow) -> dict:
    source = _safeScript(body.path)
    if source is None or not source.is_file():
        return {"ok": False, "message": "File not found"}
    dest = _safeFolder(body.folder)
    if dest is None or not dest.is_dir():
        return {"ok": False, "message": "Drop it on a folder"}
    if dest == source.parent:
        return {"ok": True, "path": str(source), "name": source.name}
    try:
        dest.mkdir(parents=True, exist_ok=True)
        target = _freePath(dest, source.name)
        shutil.move(str(source), str(target))
    except OSError as e:
        return {"ok": False, "message": str(e)}
    return {"ok": True, "path": str(target), "name": target.name}


@commands.command()
async def moveFolder(body: MoveBody, webview_window: WebviewWindow) -> dict:
    source = _safeFolder(body.path)
    if source is None or not source.is_dir():
        return {"ok": False, "message": "Folder not found"}
    if source.parent == ROOT_DIR and source.name in BASE_FOLDERS:
        return {"ok": False, "message": "The main folders cannot be moved"}
    dest = _safeFolder(body.folder)
    if dest is None or not dest.is_dir():
        return {"ok": False, "message": "Drop it on a folder"}
    if dest == source or source in dest.parents:
        return {"ok": False, "message": "A folder cannot go inside itself"}
    if dest == source.parent:
        return {"ok": True, "path": str(source), "name": source.name}
    try:
        dest.mkdir(parents=True, exist_ok=True)
        target = _freePath(dest, source.name)
        shutil.move(str(source), str(target))
    except OSError as e:
        return {"ok": False, "message": str(e)}
    return {"ok": True, "path": str(target), "name": target.name}


@commands.command()
async def deleteScript(body: PathBody, webview_window: WebviewWindow) -> dict:
    p = _safeScript(body.path)
    if p is None or not p.is_file():
        return {"ok": False, "message": "File not found"}
    try:
        p.unlink()
    except OSError as e:
        return {"ok": False, "message": str(e)}
    return {"ok": True, "path": str(p)}


@commands.command()
async def deleteFolder(body: PathBody, webview_window: WebviewWindow) -> dict:
    p = _safeFolder(body.path)
    if p is None or not p.is_dir():
        return {"ok": False, "message": "Folder not found"}
    try:
        shutil.rmtree(p)
        if p.parent == ROOT_DIR and p.name in BASE_FOLDERS:
            p.mkdir(parents=True, exist_ok=True)
    except OSError as e:
        return {"ok": False, "message": str(e)}
    return {"ok": True, "path": str(p)}


@commands.command()
async def hubFetch(body: UrlBody, webview_window: WebviewWindow) -> dict:
    url = (body.url or "").strip()
    if not url.lower().startswith(("http://", "https://")):
        return {"ok": False, "message": "Bad url"}
    try:
        response = requests.get(
            url,
            headers={"User-Agent": UA, "Accept": "application/json, text/plain, */*"},
            timeout=25,
        )
    except Exception as e:
        return {"ok": False, "message": str(e) or "Request failed"}
    if response.status_code >= 400:
        return {"ok": False, "message": f"HTTP {response.status_code}"}
    return {"ok": True, "text": response.text}


LOG_FILE = ROOT_DIR / "ui.log"


@commands.command()
async def logMessage(body: TextBody) -> dict:
    try:
        with LOG_FILE.open("a", encoding="utf-8") as fh:
            fh.write(str(body.text) + "\n")
    except OSError:
        pass
    return {"ok": True}


def main() -> int:
    from anyio.from_thread import start_blocking_portal

    _getWorker()

    src_tauri_dir = Path(__file__).parent.parent.absolute()

    with start_blocking_portal("asyncio") as portal:
        app = builder_factory().build(
            context=context_factory(src_tauri_dir),
            invoke_handler=commands.generate_handler(portal),
        )
        exit_code = app.run_return()
    return exit_code
