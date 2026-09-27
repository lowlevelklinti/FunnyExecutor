import json
import time
import threading

from PySide6.QtCore import Qt, Property, QPropertyAnimation, QEasingCurve, Signal
from PySide6.QtGui import QColor, QPainter
from PySide6.QtWidgets import QMessageBox, QWidget

try:
    from qtmonaco import Monaco
    import qtmonaco.monaco as _monaco_module
except Exception as e:
    raise ImportError(
        'FunnyExecutor needs qtmonaco and the Qt WebEngine bindings.\n'
        'Install them with:  pip install "qtmonaco[all,pyside6]"'
    ) from e


_monaco_module.get_pylsp_host = lambda: ""


defaultScript = 'print("Hello, World!")'

luauKeywords = [
    "and", "break", "continue", "do", "else", "elseif", "end", "export",
    "false", "for", "function", "if", "in", "local", "nil", "not", "or",
    "repeat", "return", "then", "true", "type", "typeof", "until", "while",
]

robloxGlobals = [
    "game", "workspace", "script", "plugin", "Instance", "Enum", "Vector2",
    "Vector3", "CFrame", "UDim", "UDim2", "Color3", "BrickColor", "Ray",
    "Rect", "Region3", "Region3int16", "NumberSequence",
    "NumberSequenceKeypoint", "NumberRange", "ColorSequence",
    "ColorSequenceKeypoint", "PhysicalProperties", "TweenInfo", "DateTime",
    "Random", "Vector3int16", "Font", "Axes", "Faces", "print", "warn",
    "error", "math", "string", "table", "os", "coroutine", "task", "debug",
    "utf8", "bit32", "buffer", "tonumber", "tostring",
    "pcall", "xpcall", "select", "assert", "require", "pairs", "ipairs",
    "next", "unpack", "rawget", "rawset", "rawequal", "rawlen",
    "setmetatable", "getmetatable", "collectgarbage", "tick", "wait",
    "spawn", "delay", "elapsedTime", "_G", "shared", "self",
]

uncApi = {
    "getgenv": ("()", "Returns the global environment shared by every script."),
    "getrenv": ("()", "Returns the Roblox (sanitised) global environment."),
    "getreg": ("()", "Returns the Lua registry table."),
    "getgc": ("(includeTables)", "Returns a list of all garbage-collected values."),
    "filtergc": ("(type, options)", "Returns gc values filtered by type or a predicate."),
    "getsenv": ("(script)", "Returns the environment of the given script."),
    "getinstances": ("()", "Returns every Instance currently in the game."),
    "getnilinstances": ("()", "Returns instances parented to nil."),
    "getloadedmodules": ("()", "Returns all loaded ModuleScripts."),
    "getscripts": ("()", "Returns every script object in the game."),
    "getscriptbytecode": ("(script)", "Returns the compiled bytecode of a script."),
    "getscripthash": ("(script)", "Returns the hash of a script's bytecode."),
    "getupvalue": ("(func, index)", "Returns the value of an upvalue."),
    "getupvalues": ("(func)", "Returns a list of the function's upvalues."),
    "setupvalue": ("(func, index, value)", "Sets the value of an upvalue."),
    "getconstant": ("(func, index)", "Returns a constant from a function."),
    "getconstants": ("(func)", "Returns all constants of a function."),
    "setconstant": ("(func, index, value)", "Overwrites a constant in a function."),
    "getproto": ("(func, index)", "Returns a nested prototype of a function."),
    "getprotos": ("(func)", "Returns all nested prototypes of a function."),
    "getstack": ("(level)", "Returns the stack of a running thread."),
    "setstack": ("(level, index, value)", "Overwrites a value on the stack."),
    "isreadonly": ("(table)", "Returns true when the table is read-only."),
    "islclosure": ("(func)", "Returns true for Lua closures."),
    "iscclosure": ("(func)", "Returns true for C closures."),
    "newcclosure": ("(func)", "Wraps a Lua function so it reports as a C closure."),
    "loadstring": ("(code)", "Compiles a string and returns a function."),
    "gethui": ("()", "Returns a hidden UI container that is not replicated."),
    "identifyexecutor": ("()", "Returns the executor name and version."),
    "getexecutorname": ("()", "Returns the name of the current executor."),
    "getexecutorversion": ("()", "Returns the version of the current executor."),
    "setfpscap": ("(fps)", "Raises or removes the frame rate cap."),
    "getfpscap": ("()", "Returns the current frame rate cap."),
    "base64encode": ("(data)", "Encodes a string to base64."),
    "base64decode": ("(data)", "Decodes a base64 string."),
    "crypt": ("(data, key)", "Encrypts or decrypts data with a key."),
    "hash": ("(data)", "Hashes a string."),
    "lz4compress": ("(data)", "Compresses data with LZ4."),
    "lz4decompress": ("(data)", "Decompresses LZ4 data."),
    "dumpstring": ("(func)", "Dumps a string from a function's constants."),
    "decompile": ("(script)", "Attempts to decompile a script back to source."),
    "saveinstance": ("(options)", "Saves the current game to disk."),
    "savegame": ("()", "Saves the current place."),
    "writefile": ("(path, data)", "Writes data to a file in the workspace folder."),
    "appendfile": ("(path, data)", "Appends data to a file."),
    "readfile": ("(path)", "Reads a file and returns its contents."),
    "isfile": ("(path)", "Returns true when the path is a file."),
    "isfolder": ("(path)", "Returns true when the path is a folder."),
    "delfile": ("(path)", "Deletes a file."),
    "delfolder": ("(path)", "Deletes a folder."),
    "makefolder": ("(path)", "Creates a folder."),
    "listfiles": ("(path)", "Lists the contents of a folder."),
    "loadfile": ("(path)", "Loads a file from disk and returns a function."),
    "setclipboard": ("(text)", "Copies text to the system clipboard."),
    "getclipboard": ("()", "Returns the current clipboard contents."),
    "messagebox": ("(text, caption, type)", "Shows a native message box."),
    "request": ("(options)", "Performs an HTTP request. Returns StatusCode, Body, Headers."),
    "http_request": ("(options)", "Alias of request()."),
    "queue_on_teleport": ("(code)", "Queues code to run after a teleport."),
    "getnamecallmethod": ("()", "Returns the method name of the current namecall."),
    "setnamecallmethod": ("(name)", "Spoofs the namecall method name."),
    "getrawmetatable": ("(object)", "Returns the real metatable of an object."),
    "setrawmetatable": ("(object, metatable)", "Sets the real metatable of an object."),
    "getcustomasset": ("(path)", "Returns a content string usable by ImageLabel and Sound."),
    "mouse1click": ("()", "Clicks the left mouse button."),
    "mouse2click": ("()", "Clicks the right mouse button."),
    "mouse1press": ("()", "Presses the left mouse button."),
    "mouse1release": ("()", "Releases the left mouse button."),
    "mouse2press": ("()", "Presses the right mouse button."),
    "mouse2release": ("()", "Releases the right mouse button."),
    "mousemoveabs": ("(x, y)", "Moves the cursor to absolute screen coordinates."),
    "mousemoverel": ("(x, y)", "Moves the cursor relative to its position."),
    "getmousepos": ("()", "Returns the cursor position."),
    "keyclick": ("(key)", "Presses and releases a key."),
    "keypress": ("(key)", "Presses a key."),
    "keyrelease": ("(key)", "Releases a key."),
    "isrbxactive": ("()", "Returns true when the Roblox window is focused."),
    "iswindowactive": ("()", "Returns true when the Roblox window is focused."),
    "Drawing": ("()", "Creates a new Drawing object."),
    "WebSocket": ("(url)", "Opens a websocket connection."),
    "firesignal": ("(signal, args)", "Fires a RobloxScriptSignal."),
    "getconnections": ("(signal)", "Returns the connections of a signal."),
    "fireproximityprompt": ("(prompt)", "Triggers a ProximityPrompt."),
    "openfiledialog": ("(options)", "Opens a native file picker dialog."),
    "savefiledialog": ("(options)", "Opens a native save dialog."),
    "getrenderproperty": ("(instance, property)", "Reads a render property."),
    "setrenderproperty": ("(instance, property, value)", "Writes a render property."),
}

def buildSnippet(name, params):
    inner = params.strip()[1:-1].strip() if params.startswith("(") else ""
    if not inner:
        return name + "()"
    parts = [p.strip() for p in inner.split(",") if p.strip()]
    args = ", ".join("${%d:%s}" % (i + 1, p) for i, p in enumerate(parts))
    return "%s(%s)" % (name, args)

def comp():
    items = []
    for word in luauKeywords:
        items.append({"label": word, "kind": "Keyword", "detail": "keyword"})
    for word in robloxGlobals:
        items.append({"label": word, "kind": "Variable", "detail": "Roblox global"})
    for name, (params, doc) in sorted(uncApi.items()):
        items.append({
            "label": name,
            "kind": "Function",
            "detail": name + params,
            "doc": doc,
            "insert": buildSnippet(name, params),
            "snippet": True,
        })

    hover = {}
    signatures = {}
    for word in robloxGlobals:
        hover[word] = {"sig": word, "doc": "Roblox global"}
    for name, (params, doc) in uncApi.items():
        hover[name] = {"sig": name + params, "doc": doc}
        inner = params.strip()[1:-1].strip()
        signatures[name] = {
            "label": name + params,
            "doc": doc,
            "params": [p.strip() for p in inner.split(",") if p.strip()],
        }
    return {"items": items, "hover": hover, "signatures": signatures}

def _monacoSetupScript():
    data = json.dumps(comp())
    return """
(function () {
    var qt = window.qtmonaco;
    if (!qt || !qt.monaco) { return 'no-monaco'; }
    var monaco = qt.monaco;
    var ed = qt.editor;
    var DATA = %(data)s;

    document.body.style.background = '#131313';

    monaco.editor.defineTheme('funny-dark', {
        base: 'vs-dark',
        inherit: true,
        rules: [
            { token: '', foreground: 'd0d0d0' },
            { token: 'keyword', foreground: '8e9ae6', fontStyle: 'bold' },
            { token: 'keyword.control', foreground: '8e9ae6', fontStyle: 'bold' },
            { token: 'support.function', foreground: 'd6cc61' },
            { token: 'identifier', foreground: 'd0d0d0' },
            { token: 'number', foreground: 'd6cc61' },
            { token: 'number.hex', foreground: 'd6cc61' },
            { token: 'number.float', foreground: 'd6cc61' },
            { token: 'string', foreground: 'abd4b4' },
            { token: 'string.escape', foreground: 'd6cc61' },
            { token: 'string.invalid', foreground: 'ff5561' },
            { token: 'comment', foreground: '646464', fontStyle: 'italic' },
            { token: 'operator', foreground: '8a8a8a' },
            { token: 'delimiter', foreground: '8a8a8a' }
        ],
        colors: {
            'editor.background': '#131313',
            'editor.foreground': '#d0d0d0',
            'editorGutter.background': '#131313',
            'editorLineNumber.foreground': '#4a4a4a',
            'editorLineNumber.activeForeground': '#9a9a9a',
            'editor.lineHighlightBackground': '#171717',
            'editor.lineHighlightBorder': '#00000000',
            'editor.selectionBackground': '#264f78',
            'editor.inactiveSelectionBackground': '#1f3b57',
            'editorCursor.foreground': '#e6e6e6',
            'editorIndentGuide.background': '#1e1e1e',
            'editorIndentGuide.activeBackground': '#2a2a2a',
            'editorWidget.background': '#1b1b1b',
            'editorWidget.border': '#2a2a2a',
            'editorSuggestWidget.background': '#1b1b1b',
            'editorSuggestWidget.border': '#2a2a2a',
            'editorSuggestWidget.selectedBackground': '#2a2a2a',
            'editorHoverWidget.background': '#1b1b1b',
            'editorHoverWidget.border': '#2a2a2a',
            'editorOverviewRuler.border': '#00000000',
            'scrollbarSlider.background': '#2a2a2a99',
            'scrollbarSlider.hoverBackground': '#3a3a3acc',
            'scrollbarSlider.activeBackground': '#3a3a3a'
        }
    });
    monaco.editor.setTheme('funny-dark');

    var KIND = monaco.languages.CompletionItemKind;
    var SNIPPET = monaco.languages.CompletionItemInsertTextRule;

    monaco.languages.registerCompletionItemProvider('lua', {
        triggerCharacters: ['.', ':'],
        provideCompletionItems: function (model, position) {
            var word = model.getWordUntilPosition(position);
            var range = {
                startLineNumber: position.lineNumber,
                endLineNumber: position.lineNumber,
                startColumn: word.startColumn,
                endColumn: word.endColumn
            };
            var suggestions = DATA.items.map(function (it) {
                var item = {
                    label: it.label,
                    kind: KIND[it.kind] || KIND.Text,
                    detail: it.detail,
                    insertText: it.insert || it.label,
                    range: range
                };
                if (it.doc) { item.documentation = { value: it.doc }; }
                if (it.snippet) { item.insertTextRules = SNIPPET.InsertAsSnippet; }
                return item;
            });
            return { suggestions: suggestions };
        }
    });

    monaco.languages.registerHoverProvider('lua', {
        provideHover: function (model, position) {
            var word = model.getWordAtPosition(position);
            if (!word) { return null; }
            var info = DATA.hover[word.word];
            if (!info) { return null; }
            return {
                contents: [
                    { value: '```lua\\n' + info.sig + '\\n```' },
                    { value: info.doc }
                ]
            };
        }
    });

    monaco.languages.registerSignatureHelpProvider('lua', {
        signatureHelpTriggerCharacters: ['(', ','],
        signatureHelpRetriggerCharacters: [','],
        provideSignatureHelp: function (model, position) {
            var line = model.getValueInRange({
                startLineNumber: position.lineNumber, startColumn: 1,
                endLineNumber: position.lineNumber, endColumn: position.column
            });
            var match = line.match(/([A-Za-z_][\\w.:]*)\\s*\\(([^()]*)$/);
            if (!match) { return null; }
            var name = match[1].split('.').pop().split(':').pop();
            var sig = DATA.signatures[name];
            if (!sig) { return null; }
            var active = match[2].split(',').length - 1;
            return {
                value: {
                    signatures: [{
                        label: sig.label,
                        documentation: { value: sig.doc },
                        parameters: sig.params.map(function (p) { return { label: p }; })
                    }],
                    activeSignature: 0,
                    activeParameter: Math.min(active, Math.max(sig.params.length - 1, 0))
                },
                dispose: function () {}
            };
        }
    });

    if (ed) {
        ed.updateOptions({
            fontFamily: 'Consolas',
            fontSize: 14,
            fontLigatures: false,
            minimap: { enabled: false },
            scrollBeyondLastLine: false,
            renderLineHighlight: 'line',
            tabSize: 4,
            insertSpaces: true,
            automaticLayout: true,
            padding: { top: 6, bottom: 6 },
            scrollbar: { verticalScrollbarSize: 10, horizontalScrollbarSize: 10 },
            smoothScrolling: true,
            cursorBlinking: 'smooth',
            quickSuggestions: true,
            suggestOnTriggerCharacters: true,
            wordBasedSuggestions: 'currentDocument'
        });
    }
    return 'ok';
})()
""" % {"data": data}

class CodeEditor(Monaco):

    def __init__(self, content=None):
        super().__init__()
        self.setObjectName(u"codeEditor")
        self._ready = False
        self.initialized.connect(self._onInitialized)

        self.page().setBackgroundColor(QColor("#131313"))
        self.setStyleSheet("QWebEngineView { background-color: #131313; }")

        self.set_minimap_enabled(False)
        self.set_scroll_beyond_last_line_enabled(False)
        self.set_language("lua")
        self.set_theme("vs-dark")
        self.set_text(defaultScript if content is None else content)

    def _onInitialized(self):
        if self._ready:
            return
        self._ready = True
        self.page().runJavaScript(_monacoSetupScript())

    def toPlainText(self):
        return self.get_text()

    def setPlainText(self, text):
        self.set_text(text)

    def setText(self, text):
        self.set_text(text)

    def refresh(self):
        self.page().runJavaScript(
            "window.qtmonaco && window.qtmonaco.editor && window.qtmonaco.editor.layout()"
        )

    def setFocus(self):
        super().setFocus()
        self.page().runJavaScript(
            "window.qtmonaco && window.qtmonaco.editor && window.qtmonaco.editor.focus()"
        )


def msgb(icon, title, text, buttons):
    msg = QMessageBox()

    msg.setStandardButtons(buttons)
    msg.setWindowTitle(title)
    msg.setText(text)
    msg.setIcon(icon)
    msg.setWindowFlags(msg.windowFlags() | Qt.WindowType.WindowStaysOnTopHint)

    return msg.exec()

class MessageBox:
    StandardButton = QMessageBox.StandardButton
    @staticmethod
    def warning(title, text, options=QMessageBox.StandardButton.Ok):
        return msgb(QMessageBox.Icon.Warning, title, text, options)

    @staticmethod
    def question(title, text, options=QMessageBox.StandardButton.Ok):
        return msgb(QMessageBox.Icon.Question, title, text, options)

    @staticmethod
    def information(title, text, options=QMessageBox.StandardButton.Ok):
        return msgb(QMessageBox.Icon.Information, title, text, options)


class Switch(QWidget):
    toggled = Signal(bool)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._checked = False
        self._position = 0.0
        self.setFixedSize(44, 24)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self._anim = QPropertyAnimation(self, b"position", self)
        self._anim.setDuration(180)
        self._anim.setEasingCurve(QEasingCurve.Type.OutCubic)

    def getPosition(self):
        return self._position

    def setPosition(self, value):
        self._position = value
        self.update()

    position = Property(float, getPosition, setPosition)

    def isChecked(self):
        return self._checked

    def setChecked(self, checked):
        if self._checked == checked:
            return
        self._checked = checked
        self._anim.stop()
        self._anim.setStartValue(self._position)
        self._anim.setEndValue(1.0 if checked else 0.0)
        self._anim.start()

    def toggle(self):
        self.setChecked(not self._checked)

    def setEnabled(self, enabled):
        super().setEnabled(enabled)
        self.update()

    def mousePressEvent(self, event):
        if not self.isEnabled():
            return
        self.toggle()
        self.toggled.emit(self._checked)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(Qt.PenStyle.NoPen)

        h = self.height()
        r = h / 2
        if not self.isEnabled():
            trackColor = QColor("#232323")
        elif self._checked:
            trackColor = QColor("#4f7cff")
        else:
            trackColor = QColor("#2a2a2a")
        painter.setBrush(trackColor)
        painter.drawRoundedRect(0, 0, self.width(), h, r, r)

        knobDiameter = h - 6
        maxX = self.width() - knobDiameter - 3
        x = int(self._position * maxX) + 3
        y = (h - knobDiameter) // 2
        painter.setBrush(QColor("#ffffff") if self.isEnabled() else QColor("#5a5a5a"))
        painter.drawEllipse(x, y, knobDiameter, knobDiameter)



discordInv = "https://discord.gg/e9Ru9nuSyv"


def dbg(msg):
        print(f"{msg}")


def discordPresent():
    try:
        import psutil
    except Exception:
        return False

    try:
        for proc in psutil.process_iter(['name']):
            try:
                name = (proc.name() or "").lower()
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
            if name.startswith("discord"):
                return True
    except Exception:
        return False
    return False


def updateRpc(rpc, gameInfo=None):
    if rpc is None:
        return
    try:
        rpc.update(
            state="Using Funny Executor",
            details="Skidding",
            large_image="logo",
            large_text="Funny Executor",
            buttons=[
                {"label": "Join Discord Server", "url": discordInv},
                {"label": "Download", "url": "https://github.com/lowlevelklinti/FunnyExecutor"},
            ],
        )
    except Exception as e:
        dbg(f"rpc update failed: {e}")


class RpcManager:
    def __init__(self, clientId, pollInterval=5.0):
        self.clientId = clientId
        self.pollInterval = pollInterval
        self._running = False
        self._enabled = False
        self._connected = False
        self._rpc = None
        self._thread = None
        self._lastGameId = None
        self._scriptExecuted = False
        self._lastGameSeen = None
        self._worker = None

    def setExecutor(self, worker):
        self._worker = worker

    def discordPresent(self):
        return discordPresent()

    def _ensureConnection(self):
        if self._connected and self._rpc is not None:
            return True
        try:
            from pypresence import Presence
            self._rpc = Presence(self.clientId)
            self._rpc.connect()
            self._connected = True
            dbg("connected to Discord RPC")
            return True
        except Exception as e:
            dbg(f"Discord RPC connect failed: {e}")
            self._rpc = None
            self._connected = False
            return False

    def _disconnect(self):
        if self._rpc is not None:
            try:
                self._rpc.clear()
            except Exception:
                pass
            try:
                self._rpc.close()
            except Exception:
                pass
        self._rpc = None
        self._connected = False

    def setEnabled(self, enabled):
        if enabled and not discordPresent():
            dbg("Discord not detected, leaving RPC disabled")
            self._enabled = False
            return

        self._enabled = enabled

        self._scriptExecuted = False
        self._lastGameId = None
        try:
            from FAPI import bridge
            bridge.game_state = {}
        except Exception:
            pass

    def isEnabled(self):
        return self._enabled

    def clear(self):
        if self._rpc is not None:
            try:
                self._rpc.clear()
            except Exception:
                pass

    def start(self):
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._pollLoop, daemon=True)
        self._thread.start()

    def stop(self):
        self._running = False
        if self._thread:
            self._thread.join(timeout=self.pollInterval + 1)
        self.clear()
        self._disconnect()

    def _pollLoop(self):
        while self._running:
            try:
                if not self._enabled:
                    if self._connected:
                        self.clear()
                        self._disconnect()
                    time.sleep(1)
                    continue

                if not self._connected:
                    if not self._ensureConnection():
                        time.sleep(2)
                        continue
                    updateRpc(self._rpc, None)
            except Exception as e:
                dbg(f"poll error: {e}")

            time.sleep(self.pollInterval)
