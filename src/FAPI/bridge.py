import atexit
import base64
import ctypes
import ctypes.wintypes
import hashlib
import hmac as hmac_mod
import json
import queue as queue_mod
import shutil
import subprocess
from http.server import BaseHTTPRequestHandler
import socketserver
from threading import Thread, Event, Lock

from websocket import create_connection, WebSocketConnectionClosedException

init_received_event = Event()
import os
from pathlib import Path, PureWindowsPath
from shutil import rmtree

import pydirectinput
import psutil
import pyperclip
import requests
from .compiler import Luau, BytecodeError

appdata = Path(os.environ['APPDATA'])
parent = appdata / 'FunnyExecutor'
old_parent = Path(__file__).resolve().parent

if os.path.exists(old_parent / 'workspace'):
    shutil.copytree(old_parent / 'workspace', appdata / 'workspace')
    shutil.rmtree(old_parent / 'workspace')

blocked_extensions = {
    ".exe", ".scr", ".bat", ".com", ".csh", ".msi", ".vb", ".vbs",
    ".vbe", ".ws", ".wsf", ".wsh", ".ps1", ".py", ".apk", ".pif", ".cpl", ".msc",
    ".jar", ".cmd", ".hta", ".gadget", ".inf", ".ins", ".isp", ".psd1", ".psm1",
    ".reg", ".scf", ".shb", ".sys", ".js", ".jse", ".lnk", ".msp",
    ".zip", ".rar", ".7z", ".tar", ".gz", ".cab", ".iso", ".img",
    ".dll", ".ocx", ".drv", ".vxd", ".xml", ".ini", ".cpp", ".c", ".url", ".uri",
    ".deb", ".rpm", ".sh", ".bash", ".zsh", ".fish", ".npm"
}

def is_blocked(path: Path) -> bool:
    return path.name.rstrip(' .').lower().endswith(tuple(blocked_extensions))

workspace_root = parent / 'workspace'

def resolve_path(raw: bytes):
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
        root = workspace_root.resolve()
        target = (root / rel).resolve()
        target.relative_to(root)
    except (OSError, ValueError):
        return None
    return target


def roblox_content_dir():
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

        def version_dirs():
            for base in bases:
                try:
                    dirs = [e for e in base.iterdir() if e.is_dir()]
                except OSError:
                    continue
                dirs.sort(key=lambda e: e.stat().st_mtime, reverse=True)
                for d in dirs:
                    yield d

        for d in version_dirs():
            if preferred and d.name == preferred and (d / 'content').is_dir():
                content = d / 'content'
                break

        if content is None:
            for d in version_dirs():
                c = d / 'content'
                if c.is_dir() and ((d / 'RobloxPlayerBeta.exe').is_file() or (d / 'RobloxPlayer.exe').is_file()):
                    content = c
                    break

        if content is None:
            for d in version_dirs():
                c = d / 'content'
                if c.is_dir():
                    content = c
                    break

    return content


_asset_manifest = parent / 'custom_assets.json'

def asset_manifest_read():
    try:
        with open(_asset_manifest, 'r', encoding='utf-8') as f:
            data = json.load(f)
            if isinstance(data, list):
                return [str(p) for p in data if isinstance(p, str)]
    except (OSError, ValueError):
        pass
    return []

def asset_manifest_write(paths):
    try:
        with open(_asset_manifest, 'w', encoding='utf-8') as f:
            json.dump(paths, f)
    except OSError:
        pass

def cleanup_customassets():
    for p in asset_manifest_read():
        try:
            os.remove(p)
        except OSError:
            pass
    asset_manifest_write([])


_console_state = {'allocated': False}

def console_ensure():
    if not _console_state['allocated']:
        ctypes.windll.kernel32.AllocConsole()
        _console_state['allocated'] = True
    return ctypes.windll.kernel32.GetStdHandle(-11)  # STD_OUTPUT_HANDLE

def console_write(text: str, color: int = 7):
    handle = console_ensure()
    kernel32 = ctypes.windll.kernel32
    kernel32.SetConsoleTextAttribute(handle, color)
    written = ctypes.wintypes.DWORD()
    payload = text.replace('\n', '\r\n')
    kernel32.WriteConsoleW(handle, ctypes.c_wchar_p(payload), len(payload), ctypes.byref(written), None)

def console_clear():
    kernel32 = ctypes.windll.kernel32
    handle = console_ensure()

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

def console_input() -> str:
    kernel32 = ctypes.windll.kernel32
    console_ensure()
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

def dialog_pick_file(save: bool, multi: bool, options: dict):
    comdlg32 = ctypes.windll.comdlg32
    filter_str = 'All files (*.*)|*.*|'
    if options.get('extensionFilter'):
        exts = options['extensionFilter']
        if isinstance(exts, str):
            exts = [exts]
        pattern = ';'.join('*.' + e.lstrip('*.') for e in exts)
        filter_str = f'Files ({pattern})|{pattern}|All files (*.*)|*.*|'
    filter_buf = ctypes.create_unicode_buffer(filter_str.replace('|', '\0') + '\0')
    file_buf = ctypes.create_unicode_buffer(32768)
    if options.get('defaultPath'):
        file_buf.value = options['defaultPath']

    ofn = OPENFILENAMEW()
    ofn.lStructSize = ctypes.sizeof(OPENFILENAMEW)
    ofn.hwndOwner = ctypes.windll.user32.GetForegroundWindow()
    ofn.lpstrFilter = ctypes.cast(filter_buf, ctypes.wintypes.LPCWSTR)
    ofn.lpstrFile = ctypes.cast(file_buf, ctypes.wintypes.LPWSTR)
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

    raw = file_buf.raw.decode('utf-16-le').split('\x00')
    parts = [p for p in raw[:raw.index('') if '' in raw else None] if p]
    if not parts:
        return None
    if len(parts) > 1:
        folder = parts[0].rstrip('\\')
        return [os.path.join(folder, name) for name in parts[1:]]
    return parts[0]

def dialog_pick_folder(title: str):
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

    path_buf = ctypes.create_unicode_buffer(ctypes.wintypes.MAX_PATH)
    ok = shell32.SHGetPathFromIDListW(pidl, path_buf)
    ole32.CoTaskMemFree(pidl)
    ole32.CoUninitialize()
    return path_buf.value if ok else None

input_handlers = {
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

def decode_bytecode(bytecode: bytes) -> bytes:
    try:
        return Luau.decrypt_bytecode(bytecode)
    except BytecodeError:
        return bytecode

def recv_method(method, args):
    create_workspace()

    if method == 'listfiles' and (not args or not args[0]):
        path = workspace_root.resolve()
    else:
        path = resolve_path(args[0]) if args else None

    # non-file functions

    if method in input_handlers:
        try:
            input_handlers[method](args)
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
            chunkname = ''
            if len(args) > 1 and args[1]:
                chunkname = base64.b64decode(args[1]).decode('utf-8', 'replace')
        except Exception:
            return b'fail'
        try:
            return base64.b64encode(Luau.compile(source, chunkname))
        except subprocess.CalledProcessError as e:
            return b'fail\n' + (e.stderr or b'compile error').strip()

    elif method == 'setfpscap':
        try:
            fps = int(args[0])
        except (ValueError, IndexError):
            return b'fail'
        if fps < 0 or fps > 9999:
            return b'fail'
        return b'ok' if set_fps_cap(9999 if fps == 0 else fps) else b'fail'

    elif method == 'getfpscap':
        value = get_fps_cap()
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
                digest = hmac_mod.new(key, data, candidate).digest()
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
        console_write(text + '\n', colors[method])
        return b'ok'

    elif method == 'rconsoleinput':
        return base64.b64encode(console_input().encode('utf-8'))

    elif method == 'rconsoleclear':
        console_clear()
        return b'ok'

    elif method == 'rconsolename':
        try:
            title = base64.b64decode(args[0]).decode('utf-8', 'replace')
        except Exception:
            return b'fail'
        console_ensure()
        ctypes.windll.kernel32.SetConsoleTitleW(title)
        return b'ok'

    elif method in ('rconsoleshow', 'rconsolehide'):
        console_ensure()
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
            result = dialog_pick_folder(options.get('title') or 'Select Folder')
        else:
            result = dialog_pick_file(
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
            holder = root.find_first_child(args[0].decode('utf-8'))
            script = holder.value
            bytecode = script.get_authentic_bytecode()
            if not bytecode:
                return b'nil'
            return base64.b64encode(decode_bytecode(bytecode))
        except Exception:
            return b'fail'

    elif method == 'getscripthash':
        if _sdk is None:
            return b'fail'
        try:
            root = _sdk.datamodel.find('CoreGui', '_funnyexecutor')
            holder = root.find_first_child(args[0].decode('utf-8'))
            script = holder.value
            bytecode = script.get_authentic_bytecode()
            if not bytecode:
                return b'nil'
            return hashlib.sha256(decode_bytecode(bytecode)).hexdigest().encode('ascii')
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
        init_received_event.set()
        print('giving init')
        with open(old_parent / 'luau' / 'init.luau', 'rb') as f:
            source = f.read()
        return base64.b64encode(Luau.compile(source))

    elif method == 'getinitraw':
        init_received_event.set()
        with open(old_parent / 'luau' / 'init.luau', 'rb') as f:
            source = f.read()
        return Luau.compile(source)

    elif method == 'client_init':
        pid = None
        if _sdk is not None:
            try:
                pid = _sdk.mem.process_id
                dm = _sdk.datamodel
                if dm and dm.address:
                    _confirmed_dms.add(dm.address)
            except:
                pass

        if pid is not None:
            global _notified_pids
            _notified_pids = {p for p in _notified_pids if psutil.pid_exists(p)}
            if pid not in _notified_pids:
                _notified_pids.add(pid)
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
        ws_id = _ws_next_id()
        _ws_pool[ws_id] = {
            'status': 'connecting',
            'url': url,
            'socket': None,
            'events': queue_mod.Queue(),
            'pending': [],
        }
        Thread(target=_ws_worker, args=(ws_id, url), daemon=True).start()
        return str(ws_id).encode('ascii')

    elif method == 'websocket_send':
        try:
            ws_id = int(args[0])
            data = base64.b64decode(args[1]).decode('utf-8', 'replace')
        except Exception:
            return b'fail'
        entry = _ws_pool.get(ws_id)
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
            ws_id = int(args[0])
        except Exception:
            return b'[]'
        entry = _ws_pool.get(ws_id)
        if not entry:
            return b'[]'
        events = []
        while True:
            try:
                kind, data = entry['events'].get_nowait()
            except queue_mod.Empty:
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
            ws_id = int(args[0])
        except Exception:
            return b'fail'
        entry = _ws_pool.get(ws_id)
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
        if is_blocked(path):
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
        if is_blocked(path):
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
        content_dir = roblox_content_dir()
        if content_dir is None:
            return b'fail'
        try:
            content_dir.mkdir(parents=True, exist_ok=True)
            name = hashlib.sha1(data).hexdigest() + (path.suffix or '')
            target = content_dir / name
            if not (target.exists() and target.read_bytes() == data):
                tmp = content_dir / (name + '.tmp')
                tmp.write_bytes(data)
                os.replace(tmp, target)
            paths = asset_manifest_read()
            if str(target) not in paths:
                paths.append(str(target))
                asset_manifest_write(paths)
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
        root = workspace_root
        l = []
        for i in path.iterdir():
            try:
                rel = str(i.relative_to(root))
            except ValueError:
                rel = i.name
            l.append(rel.encode('utf-8'))
        return b'\n'.join(l)

    return b'bad request'

_ws_pool = {}
_ws_counter = 0
_ws_lock = Lock()

def _ws_next_id():
    global _ws_counter
    with _ws_lock:
        _ws_counter += 1
        return _ws_counter

def _ws_parse_close(payload):
    code = 1006
    reason = ''
    if payload and len(payload) >= 2:
        code = int.from_bytes(payload[:2], 'big')
        if len(payload) > 2:
            reason = payload[2:].decode('utf-8', 'replace')
    return code, reason

def _ws_close_info(socket, payload=None):
    if payload:
        return _ws_parse_close(payload)
    status = getattr(socket, 'close_status', None)
    reason = getattr(socket, 'close_reason', '') or ''
    return (status or 1006), reason

def _ws_worker(ws_id, url):
    entry = _ws_pool.get(ws_id)
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
            code, reason = _ws_close_info(socket)
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
            code, reason = _ws_close_info(socket, frame)
            entry['events'].put(('close', (code, reason)))
            break

class Handler(BaseHTTPRequestHandler):
    def log_message(self, format, *args) -> None:
        pass

    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-Type', 'text/plain')
        self.end_headers()

        self.wfile.write(_target_source)

    def do_POST(self):
        content_length = int(self.headers.get('Content-Length', 0))
        body_data = self.rfile.read(content_length)

        args = body_data.split(b'\n')
        method = args.pop(0).decode('utf-8')

        response = recv_method(method, args)
        print(response)

        self.send_response(200)
        self.send_header("Content-Type", "text/plain")  # application/json
        self.send_header("Content-Length", str(len(response)))
        self.end_headers()

        self.wfile.write(response)

_target_source = b'1234'
PORT = 9475

def start_bridge():
    httpd = socketserver.ThreadingTCPServer(("127.0.0.1", PORT), Handler)
    httpd.daemon_threads = True
    Thread(target=httpd.serve_forever, daemon=True).start()
    cleanup_customassets()
    atexit.register(cleanup_customassets)

def create_workspace():
    if not (parent / 'workspace').is_dir():
        os.mkdir(parent / 'workspace')

def set_source(source: bytes):
    global _target_source
    _target_source = source

_sdk = None
_notified_pids = set()
_confirmed_dms = set()

def is_dm_confirmed(dm_addr):
    return dm_addr in _confirmed_dms

def set_sdk(sdk):
    global _sdk
    _sdk = sdk

def set_fps_cap(fps: int) -> bool:
    if _sdk is None:
        return False
    try:
        _sdk.set_fps_cap(fps)
    except Exception:
        return False
    return True

def get_fps_cap():
    if _sdk is None:
        return None
    try:
        return _sdk.get_fps_cap()
    except Exception:
        return None

if __name__ == '__main__':
    start_bridge()
    with open('..\\archive\\iy.lua', 'rb') as f:
        set_source(f.read())
    __import__('time').sleep(1e9)
