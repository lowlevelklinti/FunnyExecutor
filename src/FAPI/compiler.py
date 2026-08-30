import subprocess, tempfile
from pathlib import Path

parent = Path(__file__).resolve().parent

# created a separate py file for this only so i can use it in the bridge

class Luau:
    @staticmethod
    def compile(source: str | bytes):
        path = tempfile.gettempdir()+'\\FunnyExecutor-Temp-Source.luau'

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

        return result.stdout