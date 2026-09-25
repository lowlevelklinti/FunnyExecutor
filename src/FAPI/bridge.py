import atexit
import base64
import ctypes
import ctypes.wintypes
import hashlib
import hmac as hmacMod
import json
import queue as queueMod
import shutil
import subprocess
from http.server import BaseHTTPRequestHandler
import socketserver
from threading import Thread, Event, Lock

from websocket import create_connection, WebSocketConnectionClosedException

initReceivedEvent = Event()
import os
from pathlib import Path, PureWindowsPath
from shutil import rmtree

import pydirectinput
import psutil
import pyperclip
import requests
from .compiler import Luau, BytecodeError

appData = Path(os.environ['APPDATA'])
parent = appData / 'FunnyExecutor'
oldParent = Path(__file__).resolve().parent

if os.path.exists(oldParent / 'workspace'):
    shutil.copytree(oldParent / 'workspace', appData / 'workspace')
    shutil.rmtree(oldParent / 'workspace')

blockedExtensions = {
    ".exe", ".scr", ".bat", ".com", ".csh", ".msi", ".vb", ".vbs",
    ".vbe", ".ws", ".wsf", ".wsh", ".ps1", ".py", ".apk", ".pif", ".cpl", ".msc",
    ".jar", ".cmd", ".hta", ".gadget", ".inf", ".ins", ".isp", ".psd1", ".psm1",
    ".reg", ".scf", ".shb", ".sys", ".js", ".jse", ".lnk", ".msp",
    ".zip", ".rar", ".7z", ".tar", ".gz", ".cab", ".iso", ".img",
    ".dll", ".ocx", ".drv", ".vxd", ".xml", ".ini", ".cpp", ".c", ".url", ".uri",
    ".deb", ".rpm", ".sh", ".bash", ".zsh", ".fish", ".npm"
}

def isBlocked(path: Path) -> bool:
    return path.name.rstrip(' .').lower().endswith(tuple(blockedExtensions))

workspaceRoot = parent / 'workspace'

def resolvePath(raw: bytes):
    try:
        rel = raw.decode('utf-8')
    except Exception:
        return None

    p = PureWindowsPath(rel)
    if p.is_absolute() or p.drive or p.root:
        return None
    if any(part == '..' for part in p.parts):
        return None

    try:
        root = workspaceRoot.resolve()
        target = (root / rel).resolve()
        target.relative_to(root)
    except (OSError, ValueError):
        return None
    return target


def robloxContentDir():
    content = None
    try:
        for p in psutil.process_iter(['name', 'exe']):
            try:
                if p.info.get('name') == 'RobloxPlayerBeta.exe' and p.info.get('exe'):
                    candidate = Path(p.info['exe']).parent / 'content'
                    if candidate.is_dir():
                        content = candidate
                        break
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
    except Exception:
        pass

    if content is None:
        bases = []
        for env in ('LOCALAPPDATA', 'ProgramFiles(x86)', 'ProgramFiles'):
            root = Path(os.environ.get(env, ''))
            for name in ('Roblox', 'Fishstrap'):
                base = root / name / 'Versions'
                if base.is_dir():
                    bases.append(base)

        preferred = getattr(_sdk, 'version', None) if _sdk is not None else None

        def versionDirs():
            for base in bases:
                try:
                    dirs = [e for e in base.iterdir() if e.is_dir()]
                except OSError:
                    continue
                dirs.sort(key=lambda e: e.stat().st_mtime, reverse=True)
                for d in dirs:
                    yield d

        for d in versionDirs():
            if preferred and d.name == preferred and (d / 'content').is_dir():
                content = d / 'content'
                break

        if content is None:
            for d in versionDirs():
                c = d / 'content'
                if c.is_dir() and ((d / 'RobloxPlayerBeta.exe').is_file() or (d / 'RobloxPlayer.exe').is_file()):
                    content = c
                    break

        if content is None:
            for d in versionDirs():
                c = d / 'content'
                if c.is_dir():
                    content = c
                    break

    return content


_assetManifest = parent / 'custom_assets.json'

def assetManifestRead():
    try:
        with open(_assetManifest, 'r', encoding='utf-8') as f:
            data = json.load(f)
            if isinstance(data, list):
                return [str(p) for p in data if isinstance(p, str)]
    except (OSError, ValueError):
        pass
    return []

def assetManifestWrite(paths):
    try:
        with open(_assetManifest, 'w', encoding='utf-8') as f:
            json.dump(paths, f)
    except OSError:
        pass

def cleanupCustomAssets():
    for p in assetManifestRead():
        try:
            os.remove(p)
        except OSError:
            pass
    assetManifestWrite([])


_consoleState = {'allocated': False}

def consoleEnsure():
    if not _consoleState['allocated']:
        ctypes.windll.kernel32.AllocConsole()
        _consoleState['allocated'] = True
    return ctypes.windll.kernel32.GetStdHandle(-11)  # STD_OUTPUT_HANDLE

def consoleWrite(text: str, color: int = 7):
    handle = consoleEnsure()
    kernel32 = ctypes.windll.kernel32
    kernel32.SetConsoleTextAttribute(handle, color)
    written = ctypes.wintypes.DWORD()
    payload = text.replace('\n', '\r\n')
    kernel32.WriteConsoleW(handle, ctypes.c_wchar_p(payload), len(payload), ctypes.byref(written), None)

def consoleClear():
    kernel32 = ctypes.windll.kernel32
    handle = consoleEnsure()

    class COORD(ctypes.Structure):
        _fields_ = [('X', ctypes.c_short), ('Y', ctypes.c_short)]

    class CONSOLE_SCREEN_BUFFER_INFO(ctypes.Structure):
        _fields_ = [
            ('dwSize', COORD),
            ('dwCursorPosition', COORD),
            ('wAttributes', ctypes.c_ushort),
            ('srWindow', ctypes.c_short * 4),
            ('dwMaximumWindowSize', COORD),
        ]

    info = CONSOLE_SCREEN_BUFFER_INFO()
    if kernel32.GetConsoleScreenBufferInfo(handle, ctypes.byref(info)):
        count = info.dwSize.X * info.dwSize.Y
        origin = COORD(0, 0)
        written = ctypes.wintypes.DWORD()
        kernel32.FillConsoleOutputCharacterW(handle, ctypes.c_wchar(' '), count, origin, ctypes.byref(written))
        kernel32.SetConsoleCursorPosition(handle, origin)

def consoleInput() -> str:
    kernel32 = ctypes.windll.kernel32
    consoleEnsure()
    stdin = kernel32.GetStdHandle(-10)  # STD_INPUT_HANDLE
    buf = ctypes.create_unicode_buffer(4096)
    read = ctypes.wintypes.DWORD()
    kernel32.ReadConsoleW(stdin, buf, 4095, ctypes.byref(read), None)
    return buf.value.rstrip('\r\n')


class OPENFILENAMEW(ctypes.Structure):
    _fields_ = [
        ('lStructSize', ctypes.wintypes.DWORD),
        ('hwndOwner', ctypes.wintypes.HWND),
        ('hInstance', ctypes.wintypes.HINSTANCE),
        ('lpstrFilter', ctypes.wintypes.LPCWSTR),
        ('lpstrCustomFilter', ctypes.wintypes.LPWSTR),
        ('nMaxCustFilter', ctypes.wintypes.DWORD),
        ('nFilterIndex', ctypes.wintypes.DWORD),
        ('lpstrFile', ctypes.wintypes.LPWSTR),
        ('nMaxFile', ctypes.wintypes.DWORD),
        ('lpstrFileTitle', ctypes.wintypes.LPWSTR),
        ('nMaxFileTitle', ctypes.wintypes.DWORD),
        ('lpstrInitialDir', ctypes.wintypes.LPCWSTR),
        ('lpstrTitle', ctypes.wintypes.LPCWSTR),
        ('Flags', ctypes.wintypes.DWORD),
        ('nFileOffset', ctypes.wintypes.WORD),
        ('nFileExtension', ctypes.wintypes.WORD),
        ('lpstrDefExt', ctypes.wintypes.LPCWSTR),
        ('lCustData', ctypes.wintypes.LPARAM),
        ('lpfnHook', ctypes.wintypes.LPVOID),
        ('lpTemplateName', ctypes.wintypes.LPCWSTR),
        ('pvReserved', ctypes.wintypes.LPVOID),
        ('dwReserved', ctypes.wintypes.DWORD),
        ('FlagsEx', ctypes.wintypes.DWORD),
    ]

OFN_NOCHANGEDIR = 0x00000008
OFN_ALLOWMULTISELECT = 0x00000200
OFN_EXPLORER = 0x00080000
OFN_OVERWRITEPROMPT = 0x00000002

def dialogPickFile(save: bool, multi: bool, options: dict):
    comdlg32 = ctypes.windll.comdlg32
    filterStr = 'All files (*.*)|*.*|'
    if options.get('extensionFilter'):
        exts = options['extensionFilter']
        if isinstance(exts, str):
            exts = [exts]
        pattern = ';'.join('*.' + e.lstrip('*.') for e in exts)
        filterStr = f'Files ({pattern})|{pattern}|All files (*.*)|*.*|'
    filterBuf = ctypes.create_unicode_buffer(filterStr.replace('|', '\0') + '\0')
    fileBuf = ctypes.create_unicode_buffer(32768)
    if options.get('defaultPath'):
        fileBuf.value = options['defaultPath']

    ofn = OPENFILENAMEW()
    ofn.lStructSize = ctypes.sizeof(OPENFILENAMEW)
    ofn.hwndOwner = ctypes.windll.user32.GetForegroundWindow()
    ofn.lpstrFilter = ctypes.cast(filterBuf, ctypes.wintypes.LPCWSTR)
    ofn.lpstrFile = ctypes.cast(fileBuf, ctypes.wintypes.LPWSTR)
    ofn.nMaxFile = 32768
    ofn.lpstrTitle = options.get('title') or None
    ofn.Flags = OFN_NOCHANGEDIR
    if multi:
        ofn.Flags |= OFN_ALLOWMULTISELECT | OFN_EXPLORER
    if save:
        ofn.Flags |= OFN_OVERWRITEPROMPT

    success = comdlg32.GetSaveFileNameW(ctypes.byref(ofn)) if save else comdlg32.GetOpenFileNameW(ctypes.byref(ofn))
    if not success:
        return None

    raw = fileBuf.raw.decode('utf-16-le').split('\x00')
    parts = [p for p in raw[:raw.index('') if '' in raw else None] if p]
    if not parts:
        return None
    if len(parts) > 1:
        folder = parts[0].rstrip('\\')
        return [os.path.join(folder, name) for name in parts[1:]]
    return parts[0]

def dialogPickFolder(title: str):
    shell32 = ctypes.windll.shell32
    ole32 = ctypes.windll.ole32
    ole32.CoInitialize(None)

    class BROWSEINFOW(ctypes.Structure):
        _fields_ = [
            ('hwndOwner', ctypes.wintypes.HWND),
            ('pidlRoot', ctypes.wintypes.LPVOID),
            ('pszDisplayName', ctypes.wintypes.LPWSTR),
            ('lpszTitle', ctypes.wintypes.LPCWSTR),
            ('ulFlags', ctypes.wintypes.UINT),
            ('lpfn', ctypes.wintypes.LPVOID),
            ('lParam', ctypes.wintypes.LPARAM),
            ('iImage', ctypes.wintypes.INT),
        ]

    display = ctypes.create_unicode_buffer(ctypes.wintypes.MAX_PATH)
    bi = BROWSEINFOW()
    bi.hwndOwner = ctypes.windll.user32.GetForegroundWindow()
    bi.pszDisplayName = ctypes.cast(display, ctypes.wintypes.LPWSTR)
    bi.lpszTitle = title
    bi.ulFlags = 0x0001  # BIF_RETURNONLYFSDIRS

    pidl = shell32.SHBrowseForFolderW(ctypes.byref(bi))
    if not pidl:
        ole32.CoUninitialize()
        return None

    pathBuf = ctypes.create_unicode_buffer(ctypes.wintypes.MAX_PATH)
    ok = shell32.SHGetPathFromIDListW(pidl, pathBuf)
    ole32.CoTaskMemFree(pidl)
    ole32.CoUninitialize()
    return pathBuf.value if ok else None

inputHandlers = {
    'mouse1click': lambda a: pydirectinput.click(button='left'),
    'mouse2click': lambda a: pydirectinput.click(button='right'),
    'middleclick': lambda a: pydirectinput.click(button='middle'),
    'mouse1down': lambda a: pydirectinput.mouseDown(button='left'),
    'mouse1up': lambda a: pydirectinput.mouseUp(button='left'),
    'mouse2down': lambda a: pydirectinput.mouseDown(button='right'),
    'mouse2up': lambda a: pydirectinput.mouseUp(button='right'),
    'middledown': lambda a: pydirectinput.mouseDown(button='middle'),
    'middleup': lambda a: pydirectinput.mouseUp(button='middle'),
    'movemouse': lambda a: pydirectinput.moveTo(int(a[0]), int(a[1])),
    'mousemoveabs': lambda a: pydirectinput.moveTo(int(a[0]), int(a[1])),
    'movemouserel': lambda a: pydirectinput.moveRel(int(a[0]), int(a[1])),
    'mousemoverel': lambda a: pydirectinput.moveRel(int(a[0]), int(a[1])),
    'keyclick': lambda a: pydirectinput.press(a[0].decode('utf-8')),
    'keydown': lambda a: pydirectinput.keyDown(a[0].decode('utf-8')),
    'keyup': lambda a: pydirectinput.keyUp(a[0].decode('utf-8')),
    'keypress': lambda a: pydirectinput.keyDown(a[0].decode('utf-8')),
    'keyrelease': lambda a: pydirectinput.keyUp(a[0].decode('utf-8')),
    'mousescroll': lambda a: pydirectinput.scroll(int(a[0])),
}

def decodeBytecode(bytecode: bytes) -> bytes:
    try:
        return Luau.decryptBytecode(bytecode)
    except BytecodeError:
        return bytecode

def recvMethod(method, args):
    createWorkspace()

    if method == 'listfiles' and (not args or not args[0]):
        path = workspaceRoot.resolve()
    else:
        path = resolvePath(args[0]) if args else None

    # non-file functions

    if method in inputHandlers:
        try:
            inputHandlers[method](args)
            return b'ok'
        except Exception:
            return b'fail'

    if method == 'setclipboard':
        try:
            pyperclip.copy(base64.b64decode(args[0]).decode('utf-8', 'replace'))
        except Exception:
            return b'bad content'
        return b'ok'

    elif method == 'getclipboard':
        return pyperclip.paste().encode('utf-8')

    elif method == 'compile':
        try:
            source = base64.b64decode(args[0])
            chunkName = ''
            if len(args) > 1 and args[1]:
                chunkName = base64.b64decode(args[1]).decode('utf-8', 'replace')
        except Exception:
            return b'fail'
        try:
            return base64.b64encode(Luau.compile(source, chunkName))
        except subprocess.CalledProcessError as e:
            return b'fail\n' + (e.stderr or b'compile error').strip()

    elif method == 'setfpscap':
        try:
            fps = int(args[0])
        except (ValueError, IndexError):
            return b'fail'
        if fps < 0 or fps > 9999:
            return b'fail'
        return b'ok' if setFpsCap(9999 if fps == 0 else fps) else b'fail'

    elif method == 'getfpscap':
        value = getFpsCap()
        if value is None:
            return b'fail'
        return str(value).encode('ascii')

    elif method == 'hash':
        try:
            data = base64.b64decode(args[1])
        except Exception:
            return b'fail'
        algo = args[0].decode('ascii', 'replace').lower()
        for candidate in (algo, algo.replace('-', ''), algo.replace('-', '_'), algo.replace('_', '')):
            try:
                return hashlib.new(candidate, data).hexdigest().encode('ascii')
            except Exception:
                continue
        return b'fail'

    elif method == 'hmac':
        try:
            key = base64.b64decode(args[1])
            data = base64.b64decode(args[2])
        except Exception:
            return b'fail'
        algo = args[0].decode('ascii', 'replace').lower()
        for candidate in (algo, algo.replace('-', ''), algo.replace('-', '_'), algo.replace('_', '')):
            try:
                digest = hmacMod.new(key, data, candidate).digest()
                return base64.b64encode(digest)
            except Exception:
                continue
        return b'fail'

    elif method == 'messagebox':
        try:
            text = base64.b64decode(args[0]).decode('utf-8', 'replace')
            title = base64.b64decode(args[1]).decode('utf-8', 'replace') if len(args) > 1 and args[1] else 'FunnyExecutor'
            flags = int(args[2]) if len(args) > 2 and args[2].isdigit() else 0
        except Exception:
            return b'fail'
        result = ctypes.windll.user32.MessageBoxW(None, text, title, flags)
        return str(result).encode('ascii')

    elif method in ('rconsoleprint', 'rconsoleinfo', 'rconsolewarn', 'rconsoleerr'):
        try:
            text = base64.b64decode(args[0]).decode('utf-8', 'replace')
        except Exception:
            return b'fail'
        colors = {'rconsoleprint': 7, 'rconsoleinfo': 10, 'rconsolewarn': 14, 'rconsoleerr': 12}
        consoleWrite(text + '\n', colors[method])
        return b'ok'

    elif method == 'rconsoleinput':
        return base64.b64encode(consoleInput().encode('utf-8'))

    elif method == 'rconsoleclear':
        consoleClear()
        return b'ok'

    elif method == 'rconsolename':
        try:
            title = base64.b64decode(args[0]).decode('utf-8', 'replace')
        except Exception:
            return b'fail'
        consoleEnsure()
        ctypes.windll.kernel32.SetConsoleTitleW(title)
        return b'ok'

    elif method in ('rconsoleshow', 'rconsolehide'):
        consoleEnsure()
        hwnd = ctypes.windll.kernel32.GetConsoleWindow()
        if hwnd:
            ctypes.windll.user32.ShowWindow(hwnd, 5 if method == 'rconsoleshow' else 0)
        return b'ok'

    elif method in ('openfiledialog', 'openfilesdialog', 'savefiledialog', 'openfolderdialog'):
        options = {}
        if args and args[0]:
            try:
                options = json.loads(base64.b64decode(args[0]).decode('utf-8'))
            except Exception:
                options = {}
        if method == 'openfolderdialog':
            result = dialogPickFolder(options.get('title') or 'Select Folder')
        else:
            result = dialogPickFile(
                save=method == 'savefiledialog',
                multi=method == 'openfilesdialog',
                options=options,
            )
        if not result:
            return b''
        if isinstance(result, list):
            return base64.b64encode('\n'.join(result).encode('utf-8'))
        return base64.b64encode(str(result).encode('utf-8'))

    elif method == 'getmousepos':
        try:
            x, y = pydirectinput.position()
            return f'{x},{y}'.encode('ascii')
        except Exception:
            return b'fail'

    elif method == 'iswindowactive':
        try:
            hwnd = ctypes.windll.user32.GetForegroundWindow()
            pid = ctypes.wintypes.DWORD()
            ctypes.windll.user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
            name = psutil.Process(pid.value).name().lower()
            return b'true' if name == 'robloxplayerbeta.exe' else b'false'
        except Exception:
            return b'fail'

    elif method == 'getscriptbytecode':
        if _sdk is None:
            return b'fail'
        try:
            root = _sdk.datamodel.find('CoreGui', '_funnyexecutor')
            holder = root.findFirstChild(args[0].decode('utf-8'))
            script = holder.value
            bytecode = script.getAuthenticBytecode()
            if not bytecode:
                return b'nil'
            return base64.b64encode(decodeBytecode(bytecode))
        except Exception:
            return b'fail'

    elif method == 'getscripthash':
        if _sdk is None:
            return b'fail'
        try:
            root = _sdk.datamodel.find('CoreGui', '_funnyexecutor')
            holder = root.findFirstChild(args[0].decode('utf-8'))
            script = holder.value
            bytecode = script.getAuthenticBytecode()
            if not bytecode:
                return b'nil'
            return hashlib.sha256(decodeBytecode(bytecode)).hexdigest().encode('ascii')
        except Exception:
            return b'fail'

    elif method == 'decompile':
        try:
            r = requests.post(
                'https://api.lua.expert/decompile',
                json={'script': args[0].decode('ascii')},
                timeout=30
            )
        except requests.RequestException:
            return b'fail'
        if r.status_code != 200:
            return b'fail'
        return r.content

    elif method == 'getinit':
        initReceivedEvent.set()
        print('giving init')
        with open(oldParent / 'luau' / 'init.luau', 'rb') as f:
            source = f.read()
        return base64.b64encode(Luau.compile(source))

    elif method == 'getinitraw':
        initReceivedEvent.set()
        with open(oldParent / 'luau' / 'init.luau', 'rb') as f:
            source = f.read()
        return Luau.compile(source)

    elif method == 'client_init':
        pid = None
        if _sdk is not None:
            try:
                pid = _sdk.mem.process_id
                dm = _sdk.datamodel
                if dm and dm.address:
                    _confirmedDms.add(dm.address)
            except:
                pass

        if pid is not None:
            global _notifiedPids
            _notifiedPids = {p for p in _notifiedPids if psutil.pid_exists(p)}
            if pid not in _notifiedPids:
                _notifiedPids.add(pid)
                return b'notify'
            else:
                return b'silent'
        return b'notify'

    elif method == 'websocket_connect':
        try:
            url = base64.b64decode(args[0]).decode('utf-8')
        except Exception:
            return b'fail'
        if not url.startswith(('ws://', 'wss://')):
            return b'fail'
        wsId = _wsNextId()
        _wsPool[wsId] = {
            'status': 'connecting',
            'url': url,
            'socket': None,
            'events': queueMod.Queue(),
            'pending': [],
        }
        Thread(target=_wsWorker, args=(wsId, url), daemon=True).start()
        return str(wsId).encode('ascii')

    elif method == 'websocket_send':
        try:
            wsId = int(args[0])
            data = base64.b64decode(args[1]).decode('utf-8', 'replace')
        except Exception:
            return b'fail'
        entry = _wsPool.get(wsId)
        if not entry:
            return b'fail'
        if entry['status'] == 'connecting':
            entry['pending'].append(data)
            return b'ok'
        if entry['status'] != 'open' or not entry['socket']:
            return b'fail'
        try:
            entry['socket'].send(data)
        except Exception:
            return b'fail'
        return b'ok'

    elif method == 'websocket_poll':
        try:
            wsId = int(args[0])
        except Exception:
            return b'[]'
        entry = _wsPool.get(wsId)
        if not entry:
            return b'[]'
        events = []
        while True:
            try:
                kind, data = entry['events'].get_nowait()
            except queueMod.Empty:
                break
            if kind == 'open':
                events.append({'t': 'open'})
            elif kind == 'message':
                events.append({
                    't': 'message',
                    'd': base64.b64encode(data.encode('utf-8', 'replace')).decode('ascii'),
                })
            elif kind == 'close':
                events.append({'t': 'close', 'c': data[0], 'r': data[1]})
        return json.dumps(events).encode('utf-8')

    elif method == 'websocket_close':
        try:
            wsId = int(args[0])
        except Exception:
            return b'fail'
        entry = _wsPool.get(wsId)
        if not entry:
            return b'fail'
        entry['status'] = 'closed'
        socket = entry.get('socket')
        if socket:
            try:
                socket.close()
            except Exception:
                pass
        return b'ok'

    # file api

    if not path:
        return b'bad request'
    elif method == 'writefile':
        if isBlocked(path):
            return b'blocked'
        try:
            content = base64.b64decode(args[1])
        except Exception:
            return b'bad content'
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            with open(path, 'wb') as f:
                f.write(content)
        except OSError:
            return b'fail'
        return b'ok'

    elif method == 'appendfile':
        if isBlocked(path):
            return b'blocked'
        try:
            content = base64.b64decode(args[1])
        except Exception:
            return b'bad content'
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            with open(path, 'ab') as f:
                f.write(content)
        except OSError:
            return b'fail'
        return b'ok'

    elif method == 'getcustomasset':
        if not path.is_file():
            return b'fail'
        try:
            data = path.read_bytes()
        except OSError:
            return b'fail'
        contentDir = robloxContentDir()
        if contentDir is None:
            return b'fail'
        try:
            contentDir.mkdir(parents=True, exist_ok=True)
            name = hashlib.sha1(data).hexdigest() + (path.suffix or '')
            target = contentDir / name
            if not (target.exists() and target.read_bytes() == data):
                tmp = contentDir / (name + '.tmp')
                tmp.write_bytes(data)
                os.replace(tmp, target)
            paths = assetManifestRead()
            if str(target) not in paths:
                paths.append(str(target))
                assetManifestWrite(paths)
        except OSError:
            return b'fail'
        return ('rbxasset://' + name).encode('ascii')

    elif method == 'readfile':
        try:
            with open(path, 'rb') as f:
                return base64.b64encode(f.read())
        except OSError:
            return b'fail'

    elif method == 'isfile':
        return b'true' if path.is_file() else b'false'

    elif method == 'isfolder':
        return b'true' if path.is_dir() else b'false'

    elif method == 'delfile':
        if path.is_file():
            try:
                os.remove(path)
            except OSError:
                return b'fail'
            return b'ok'
        else:
            return b'fail'

    elif method == 'delfolder':
        if path.is_dir():
            try:
                rmtree(path)
            except OSError:
                return b'fail'
            return b'ok'
        else:
            return b'fail'

    elif method == 'makefolder':
        try:
            path.mkdir(parents=True, exist_ok=True)
        except OSError:
            return b'fail'
        return b'ok'

    elif method == 'listfiles':
        if not path.is_dir():
            return b'fail'
        root = workspaceRoot
        l = []
        for i in path.iterdir():
            try:
                rel = str(i.relative_to(root))
            except ValueError:
                rel = i.name
            l.append(rel.encode('utf-8'))
        return b'\n'.join(l)

    return b'bad request'

_wsPool = {}
_wsCounter = 0
_wsLock = Lock()

def _wsNextId():
    global _wsCounter
    with _wsLock:
        _wsCounter += 1
        return _wsCounter

def _wsParseClose(payload):
    code = 1006
    reason = ''
    if payload and len(payload) >= 2:
        code = int.from_bytes(payload[:2], 'big')
        if len(payload) > 2:
            reason = payload[2:].decode('utf-8', 'replace')
    return code, reason

def _wsCloseInfo(socket, payload=None):
    if payload:
        return _wsParseClose(payload)
    status = getattr(socket, 'close_status', None)
    reason = getattr(socket, 'close_reason', '') or ''
    return (status or 1006), reason

def _wsWorker(wsId, url):
    entry = _wsPool.get(wsId)
    if entry is None:
        return

    try:
        socket = create_connection(url, timeout=30, enable_multithread=True)
    except Exception as e:
        entry['status'] = 'closed'
        entry['events'].put(('close', (1006, str(e))))
        return

    entry['socket'] = socket
    entry['status'] = 'open'
    for msg in entry['pending']:
        try:
            socket.send(msg)
        except Exception:
            pass
    entry['pending'].clear()
    entry['events'].put(('open', None))

    while True:
        if entry['status'] == 'closed':
            break
        try:
            opcode, frame = socket.recv_data(control_frame=True)
        except WebSocketConnectionClosedException:
            entry['status'] = 'closed'
            code, reason = _wsCloseInfo(socket)
            entry['events'].put(('close', (code, reason)))
            break
        except Exception as e:
            entry['status'] = 'closed'
            entry['events'].put(('close', (1006, str(e))))
            break

        if opcode == 0x1:  # text
            try:
                text = frame.decode('utf-8', 'replace') if isinstance(frame, bytes) else str(frame)
            except Exception:
                text = ''
            entry['events'].put(('message', text))
        elif opcode == 0x2:  # binary
            try:
                text = frame.decode('utf-8', 'replace') if isinstance(frame, bytes) else str(frame)
            except Exception:
                text = ''
            entry['events'].put(('message', text))
        elif opcode == 0x8:  # close
            entry['status'] = 'closed'
            code, reason = _wsCloseInfo(socket, frame)
            entry['events'].put(('close', (code, reason)))
            break

class Handler(BaseHTTPRequestHandler):
    def log_message(self, format, *args) -> None:
        pass

    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-Type', 'text/plain')
        self.end_headers()

        self.wfile.write(_targetSource)

    def do_POST(self):
        contentLength = int(self.headers.get('Content-Length', 0))
        bodyData = self.rfile.read(contentLength)

        args = bodyData.split(b'\n')
        method = args.pop(0).decode('utf-8')

        response = recvMethod(method, args)
        print(response)

        self.send_response(200)
        self.send_header("Content-Type", "text/plain")  # application/json
        self.send_header("Content-Length", str(len(response)))
        self.end_headers()

        self.wfile.write(response)

_targetSource = b'1234'
port = 9475

def startBridge():
    httpd = socketserver.ThreadingTCPServer(("127.0.0.1", port), Handler)
    httpd.daemon_threads = True
    Thread(target=httpd.serve_forever, daemon=True).start()
    cleanupCustomAssets()
    atexit.register(cleanupCustomAssets)

def createWorkspace():
    if not (parent / 'workspace').is_dir():
        os.mkdir(parent / 'workspace')

def setSource(source: bytes):
    global _targetSource
    _targetSource = source

_sdk = None
_notifiedPids = set()
_confirmedDms = set()

def isDmConfirmed(dmAddr):
    return dmAddr in _confirmedDms

def setSdk(sdk):
    global _sdk
    _sdk = sdk

def setFpsCap(fps: int) -> bool:
    if _sdk is None:
        return False
    try:
        _sdk.setFpsCap(fps)
    except Exception:
        return False
    return True

def getFpsCap():
    if _sdk is None:
        return None
    try:
        return _sdk.getFpsCap()
    except Exception:
        return None

if __name__ == '__main__':
    startBridge()
    with open('..\\archive\\iy.lua', 'rb') as f:
        setSource(f.read())
    __import__('time').sleep(1e9)
