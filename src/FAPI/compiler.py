import os
import subprocess
import tempfile
import time
from pathlib import Path

parent = Path(__file__).resolve().parent

class Luau:
    @staticmethod
    def compile(source: str | bytes):
        path = tempfile.gettempdir() + f'\\FunnyExecutor-Temp-Source-{os.getpid()}-{time.time_ns()}.luau'

        try:
            if type(source) == str:
                with open(path, 'w', encoding='utf-8') as f:
                    f.write(source)
            else:
                with open(path, 'wb') as f:
                    f.write(source)

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