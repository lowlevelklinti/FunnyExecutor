import os
import re
import struct
import subprocess
import tempfile
import time
from collections import OrderedDict
from pathlib import Path

import zstandard

parent = Path(__file__).resolve().parent

class BytecodeError(Exception): pass

createNoWindow = 0x08000000
compileCacheLimit = 128
compileCache = OrderedDict()
compilerPath = str(parent / 'luau' / 'compile.exe')

def _cacheKey(source: str | bytes, chunkName: str):
    if type(source) == str:
        source = source.encode('utf-8')
    return (source, chunkName)

def _cacheGet(key):
    try:
        value = compileCache.pop(key)
    except KeyError:
        return None
    compileCache[key] = value
    return value

def _cachePut(key, value):
    compileCache[key] = value
    while len(compileCache) > compileCacheLimit:
        compileCache.popitem(last=False)

windowsReserved = {
    'CON', 'PRN', 'AUX', 'NUL',
    *(f'COM{i}' for i in range(1, 10)),
    *(f'LPT{i}' for i in range(1, 10)),
}

def safeChunkname(chunkName: str) -> str:
    name = (chunkName or '').strip()
    name = re.sub(r'[\\/:*?"<>|]', '_', name)
    name = name.strip(' .') or 'chunk'
    if name.upper() in windowsReserved:
        name = '_' + name
    return name[:120]

class Luau:
    @staticmethod
    def compile(source: str | bytes, chunkName: str = ''):
        key = _cacheKey(source, chunkName)
        cached = _cacheGet(key)
        if cached is not None:
            return cached

        if chunkName:
            with tempfile.TemporaryDirectory(prefix='FunnyExecutor-Chunk-') as tmpdir:
                name = safeChunkname(chunkName)
                path = os.path.join(tmpdir, name)
                Luau._writeSource(path, source)
                result = subprocess.run(
                    [compilerPath, name, '--binary'],
                    capture_output=True,
                    cwd=tmpdir,
                    creationflags=createNoWindow
                )
                if result.returncode != 0:
                    raise BytecodeError(
                        'Luau compile error:\n'
                        + result.stderr.decode('utf-8', 'replace').strip()
                    )
            _cachePut(key, result.stdout)
            return result.stdout

        path = tempfile.gettempdir() + f'\\FunnyExecutor-Temp-Source-{os.getpid()}-{time.time_ns()}.luau'

        try:
            Luau._writeSource(path, source)
            result = subprocess.run(
                [compilerPath, path, '--binary'],
                capture_output=True,
                creationflags=createNoWindow
            )
            if result.returncode != 0:
                raise BytecodeError(
                    'Luau compile error:\n'
                    + result.stderr.decode('utf-8', 'replace').strip()
                )
        finally:
            try:
                os.remove(path)
            except OSError:
                pass

        _cachePut(key, result.stdout)
        return result.stdout

    @staticmethod
    def decryptBytecode(encrypted: bytes) -> bytes:
        if len(encrypted) < 8:
            raise BytecodeError('bytecode too short')

        sign = b'RSB1'
        hashMultiplier = 41

        buffer = bytearray(encrypted)
        key = [0] * 4

        for i in range(4):
            key[i] = ((buffer[i] ^ sign[i]) - i * hashMultiplier) & 0xFF

        for i in range(len(buffer)):
            buffer[i] ^= (key[i % 4] + i * hashMultiplier) & 0xFF

        if not buffer.startswith(sign):
            raise BytecodeError('decryption failed')

        decompressedSize = struct.unpack_from('<I', buffer, 4)[0]

        if decompressedSize == 0 or decompressedSize > 50 * 1024 * 1024:
            raise BytecodeError('decompression failed')

        return zstandard.ZstdDecompressor().decompress(bytes(buffer[8:]), decompressedSize)

    @staticmethod
    def _writeSource(path: str, source: str | bytes):
        if type(source) == str:
            with open(path, 'w', encoding='utf-8') as f:
                f.write(source)
        else:
            with open(path, 'wb') as f:
                f.write(source)
