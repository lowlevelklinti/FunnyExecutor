import os
import re
import subprocess
import tempfile
import time
from pathlib import Path

parent = Path(__file__).resolve().parent

WINDOWS_RESERVED = {
    'CON', 'PRN', 'AUX', 'NUL',
    *(f'COM{i}' for i in range(1, 10)),
    *(f'LPT{i}' for i in range(1, 10)),
}

def safe_chunkname(chunkname: str) -> str:
    """Turn a chunkname into a legal single-component Windows file name.
    compile.exe embeds the input file name as the chunk name, so compiling a
    file literally named after the chunkname gives the chunk that source."""
    name = (chunkname or '').strip()
    name = re.sub(r'[\\/:*?"<>|]', '_', name)
    name = name.strip(' .') or 'chunk'
    if name.upper() in WINDOWS_RESERVED:
        name = '_' + name
    return name[:120]

class Luau:
    @staticmethod
    def compile(source: str | bytes, chunkname: str = ''):
        if chunkname:
            with tempfile.TemporaryDirectory(prefix='FunnyExecutor-Chunk-') as tmpdir:
                name = safe_chunkname(chunkname)
                path = os.path.join(tmpdir, name)
                Luau._write_source(path, source)
                result = subprocess.run(
                    [parent/'luau'/'compile.exe', name, '--binary'],
                    capture_output=True,
                    check=True,
                    cwd=tmpdir
                )
            return result.stdout

        path = tempfile.gettempdir() + f'\\FunnyExecutor-Temp-Source-{os.getpid()}-{time.time_ns()}.luau'

        try:
            Luau._write_source(path, source)
            result = subprocess.run(
                [parent/'luau'/'compile.exe', path, '--binary'],
                capture_output=True,
                check=True
            )
        finally:
            try:
                os.remove(path)
            except OSError:
                pass

        return result.stdout

    @staticmethod
    def _write_source(path: str, source: str | bytes):
        if type(source) == str:
            with open(path, 'w', encoding='utf-8') as f:
                f.write(source)
        else:
            with open(path, 'wb') as f:
                f.write(source)
