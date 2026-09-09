import os
import re
import struct
import subprocess
import tempfile
import time
from pathlib import Path

import zstandard

parent = Path(__file__).resolve().parent

class BytecodeError(Exception): pass

WINDOWS_RESERVED = {
    'CON', 'PRN', 'AUX', 'NUL',
    *(f'COM{i}' for i in range(1, 10)),
    *(f'LPT{i}' for i in range(1, 10)),
}

def safe_chunkname(chunkname: str) -> str:
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
    def decrypt_bytecode(encrypted: bytes) -> bytes:
        if len(encrypted) < 8:
            raise BytecodeError('bytecode too short')

        sign = b'RSB1'
        hash_mul = 41

        buffer = bytearray(encrypted)
        key = [0] * 4

        for i in range(4):
            key[i] = ((buffer[i] ^ sign[i]) - i * hash_mul) & 0xFF

        for i in range(len(buffer)):
            buffer[i] ^= (key[i % 4] + i * hash_mul) & 0xFF

        if not buffer.startswith(sign):
            raise BytecodeError('decryption failed')

        decomp_size = struct.unpack_from('<I', buffer, 4)[0]

        if decomp_size == 0 or decomp_size > 50 * 1024 * 1024:
            raise BytecodeError('decompression failed')

        return zstandard.ZstdDecompressor().decompress(bytes(buffer[8:]), decomp_size)

    @staticmethod
    def _write_source(path: str, source: str | bytes):
        if type(source) == str:
            with open(path, 'w', encoding='utf-8') as f:
                f.write(source)
        else:
            with open(path, 'wb') as f:
                f.write(source)
