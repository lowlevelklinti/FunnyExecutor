"""Native Win32 file dialogs (replaces QFileDialog). ctypes-based, no Qt."""

import ctypes
import ctypes.wintypes as wt

OFN_NOCHANGEDIR = 0x00000008
OFN_OVERWRITEPROMPT = 0x00000002


class OPENFILENAMEW(ctypes.Structure):
    _fields_ = [
        ('lStructSize', wt.DWORD),
        ('hwndOwner', wt.HWND),
        ('hInstance', wt.HINSTANCE),
        ('lpstrFilter', wt.LPCWSTR),
        ('lpstrCustomFilter', wt.LPWSTR),
        ('nMaxCustFilter', wt.DWORD),
        ('nFilterIndex', wt.DWORD),
        ('lpstrFile', wt.LPWSTR),
        ('nMaxFile', wt.DWORD),
        ('lpstrFileTitle', wt.LPWSTR),
        ('nMaxFileTitle', wt.DWORD),
        ('lpstrInitialDir', wt.LPCWSTR),
        ('lpstrTitle', wt.LPCWSTR),
        ('Flags', wt.DWORD),
        ('nFileOffset', wt.WORD),
        ('nFileExtension', wt.WORD),
        ('lpstrDefExt', wt.LPCWSTR),
        ('lCustData', wt.LPARAM),
        ('lpfnHook', wt.LPVOID),
        ('lpTemplateName', wt.LPVOID),
        ('pvReserved', wt.LPVOID),
        ('dwReserved', wt.DWORD),
        ('FlagsEx', wt.DWORD),
    ]


def _build_filter(extensions):
    exts = [e.lstrip('*.') for e in (extensions or ['*'])]
    pattern = ';'.join('*.' + e for e in exts)
    return 'Scripts (%s)|%s|All files (*.*)|*.*|' % (pattern, pattern)


def open_file(extensions, title='Open File'):
    """Returns (path, text) or None on cancel."""
    file_buf = ctypes.create_unicode_buffer(32768)
    filter_buf = ctypes.create_unicode_buffer(
        _build_filter(extensions).replace('|', '\0') + '\0')

    ofn = OPENFILENAMEW()
    ofn.lStructSize = ctypes.sizeof(OPENFILENAMEW)
    ofn.hwndOwner = ctypes.windll.user32.GetForegroundWindow()
    ofn.lpstrFilter = ctypes.cast(filter_buf, wt.LPCWSTR)
    ofn.lpstrFile = ctypes.cast(file_buf, wt.LPWSTR)
    ofn.nMaxFile = 32768
    ofn.lpstrTitle = title
    ofn.Flags = OFN_NOCHANGEDIR

    if not ctypes.windll.comdlg32.GetOpenFileNameW(ctypes.byref(ofn)):
        return None

    path = file_buf.value
    if not path:
        return None
    try:
        with open(path, 'r', encoding='utf-8', errors='replace') as f:
            return path, f.read()
    except OSError:
        return path, ''


def save_file(default_name, content, extensions, title='Save File'):
    """Returns saved path or None on cancel."""
    file_buf = ctypes.create_unicode_buffer(default_name or 'script.luau')
    filter_buf = ctypes.create_unicode_buffer(
        _build_filter(extensions).replace('|', '\0') + '\0')

    ofn = OPENFILENAMEW()
    ofn.lStructSize = ctypes.sizeof(OPENFILENAMEW)
    ofn.hwndOwner = ctypes.windll.user32.GetForegroundWindow()
    ofn.lpstrFilter = ctypes.cast(filter_buf, wt.LPCWSTR)
    ofn.lpstrFile = ctypes.cast(file_buf, wt.LPWSTR)
    ofn.nMaxFile = 32768
    ofn.lpstrTitle = title
    ofn.lpstrDefExt = 'luau'
    ofn.Flags = OFN_NOCHANGEDIR | OFN_OVERWRITEPROMPT

    if not ctypes.windll.comdlg32.GetSaveFileNameW(ctypes.byref(ofn)):
        return None

    path = file_buf.value
    if not path:
        return None
    try:
        with open(path, 'w', encoding='utf-8') as f:
            f.write(content)
    except OSError:
        pass
    return path
