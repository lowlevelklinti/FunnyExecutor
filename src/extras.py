import re

from PySide6.QtCore import QRegularExpression, QRect, QSize, Qt, QTimer
from PySide6.QtGui import QSyntaxHighlighter, QTextCharFormat, QColor, QFont, QPainter
from PySide6.QtWidgets import QPlainTextEdit, QMessageBox, QWidget

bold_font = 700

_luauRules = None

class LuauHighlighter(QSyntaxHighlighter):
    # debugger
    _re_block_comment = re.compile(r"--\[\[.*?\]\]", re.DOTALL)
    _re_line_comment = re.compile(r"--[^\n]*")
    _re_dstring = re.compile(r'"[^"\\]*(?:\\.[^"\\]*)*"')
    _re_sstring = re.compile(r"'[^'\\]*(?:\\.[^'\\]*)*'")

    _re_local_func = re.compile(r"\blocal\s+function\s+([A-Za-z_]\w*)")
    _re_local_vars = re.compile(r"\blocal\s+(?!function\b)((?:[A-Za-z_]\w*\s*,\s*)*[A-Za-z_]\w*)")
    _re_func_params = re.compile(r"\bfunction\b[^()]*\(([^)]*)\)")
    _re_for_in = re.compile(r"\bfor\s+((?:[A-Za-z_]\w*\s*,\s*)*[A-Za-z_]\w*)\s+in\b")
    _re_for_num = re.compile(r"\bfor\s+([A-Za-z_]\w*)\s*=")
    _re_assign_target = re.compile(r"\b([A-Za-z_]\w*)\s*=(?!=)")
    _re_identifier = re.compile(r"\b[A-Za-z_]\w*\b")
    _re_table_key = re.compile(r"\b([A-Za-z_]\w*)\s*=(?!=)")
    _re_func_call = re.compile(r"\b([A-Za-z_]\w*)\s*(?=[\({\"'])")
    _re_global_func = re.compile(r"(?<!\blocal\s)(?<!\blocal\s{2})(?<!\blocal\s{3})\bfunction\s+([A-Za-z_]\w*)")

    def __init__(self, document):
        super().__init__(document)

        global _luauRules

        self.progressiveLimit = None
        self._last_revision = None
        self.undefined_ranges = []
        self.unused_ranges = []

        if _luauRules is not None:
            self.rules = _luauRules['rules']
            self.comment_format = _luauRules['commentFormat']
            self.block_comment_start = _luauRules['blockCommentStart']
            self.block_comment_end = _luauRules['blockCommentEnd']
            self._known_builtins = _luauRules['knownBuiltins']
            return

        self.rules = []

        # keywords
        keyword_format = QTextCharFormat()
        keyword_format.setForeground(QColor("#8e9ae6"))
        keyword_format.setFontWeight(bold_font)
        self.keywords = [
            "and", "break", "do", "else", "elseif", "end",
            "for", "function", "if", "in", "local", "nil", "not",
            "or", "repeat", "return", "then", "until", "while",
            "continue", "export", "const"
        ]
        for word in self.keywords:
            pattern = QRegularExpression(f"\\b{word}\\b")
            self.rules.append((pattern, keyword_format))

        # booleans
        bool_format = QTextCharFormat()
        bool_format.setForeground(QColor("#d6cc61"))
        bool_format.setFontWeight(bold_font)
        self.booleans = ['true', 'false']
        for word in self.booleans:
            pattern = QRegularExpression(f"\\b{word}\\b")
            self.rules.append((pattern, bool_format))

        # globals
        globals_format = QTextCharFormat()
        globals_format.setForeground(QColor("#d6cc61"))
        self.globals_keywords = [
            "print", 'math', 'string', 'table',
            'type', 'tonumber', 'tostring', 'error', 'pcall',
            '_G', 'shared', 'game', 'workspace', 'warn', 'pairs', 'ipairs', 'next',
            'select', 'assert', 'require',
            'Instance', 'Enum', 'Vector2', 'Vector3', 'CFrame', 'UDim', 'UDim2',
            'Color3', 'BrickColor', 'Ray', 'Rect', 'Region3', 'Region3int16',
            'NumberSequence', 'NumberSequenceKeypoint', 'NumberRange',
            'ColorSequence', 'ColorSequenceKeypoint', 'PhysicalProperties',
            'TweenInfo', 'DateTime', 'Random', 'Vector3int16', 'Font',
            'task', 'coroutine', 'os', 'debug', 'utf8', 'bit32', 'buffer',
            'tick', 'wait', 'spawn', 'delay', 'elapsedTime',
            'setmetatable', 'getmetatable', 'rawget', 'rawset', 'rawequal', 'rawlen',
            'unpack', 'xpcall', 'collectgarbage', 'self',
        ]
        for word in self.globals_keywords:
            pattern = QRegularExpression(f"\\b{word}\\b")
            self.rules.append((pattern, globals_format))

        # unc
        unc_format = QTextCharFormat()
        unc_format.setForeground(QColor("#8e9ae6"))
        self.unc_keywords = [
            'getgenv', 'base64encode', 'base64decode', 'crypt',
            'lz4compress', 'lz4decompress', 'loadstring',
            'writefile', 'appendfile', 'readfile', 'isfile',
            'isfolder', 'delfile', 'delfolder', 'makefolder',
            'listfiles', 'setclipboard', 'getclipboard', 'messagebox',
            'identifyexecutor', 'isnetworkowner', 'loadfile', 'setfpscap',
            'getfpscap', 'getexecutorname', 'getexecutorversion', 'cloneref',
            'compareinstances', 'islclosure', 'iscclosure', 'newcclosure',
            'clonefunction', 'isexecutorclosure', 'checkclosure', 'gethui',
            'getnilinstances', 'getloadedmodules', 'getscripts',
            'getrunningscripts', 'isreadonly', 'queue_on_teleport',
            'getnamecallmethod', 'http_request', 'crypt', 'hash', 'messagebox',
            'mouse1click', 'mouse2click', 'mouse1press', 'mouse1release',
            'mouse2press', 'mouse2release', 'movemouse', 'mousemoveabs',
            'mouserel', 'mousemoverel', 'getmousepos', 'getmouselocation',
            'keyclick', 'keypress', 'keyrelease', 'iswindowactive', 'isrbxactive',
            'getscriptbytecode', 'dumpstring', 'getscripthash', 'Drawing',
            'WebSocket', 'decompile', 'saveinstance', 'savegame',
            'isrenderavailable', 'getrenderproperty', 'setrenderproperty',
            'request', 'syn', 'http', 'Signal',
            'openfiledialog', 'savefiledialog', 'openfolderdialog', 'openfilesdialog',
            'firetouchinterest', 'fireproximityprompt', 'fireclickdetector',
            'getconnections', 'hookfunction', 'hookmetamethod',
            'getrawmetatable', 'setrawmetatable', 'checkcaller',
            'getcallingscript', 'getinstances', 'gethiddenproperty', 'sethiddenproperty',
            'setsimulationradius', 'isscriptable', 'setscriptable', 'getcustomasset'
        ]
        for word in self.unc_keywords:
            pattern = QRegularExpression(f"\\b{word}\\b")
            self.rules.append((pattern, unc_format))

        # numbers
        number_format = QTextCharFormat()
        number_format.setForeground(QColor("#d6cc61"))
        self.rules.append((QRegularExpression(r"\b\d+(\.\d+)?\b"), number_format))

        # member
        member_format = QTextCharFormat()
        member_format.setForeground(QColor("#7b99ec"))

        member_pattern = QRegularExpression(r"(?<=\.)[a-zA-Z_][a-zA-Z0-9_]*\b")
        self.rules.append((member_pattern, member_format))

        # functions
        function_format = QTextCharFormat()
        function_format.setForeground(QColor("#7b99ec"))

        # func calls
        pat = '|'.join(self.unc_keywords + self.globals_keywords)
        call_pattern = QRegularExpression(r"\b(?!(?:"+pat+r")\b)[a-zA-Z_][a-zA-Z0-9_]*(?=\s*\()")
        self.rules.append((call_pattern, function_format))

        # func defs
        def_pattern = QRegularExpression(r"\bfunction\s+\K[a-zA-Z_][a-zA-Z0-9_]*\b")
        self.rules.append((def_pattern, function_format))

        # strings
        string_format = QTextCharFormat()
        string_format.setForeground(QColor("#abd4b4"))
        self.rules.append((QRegularExpression('"[^"\\\\]*(\\\\.[^"\\\\]*)*"'), string_format))
        self.rules.append((QRegularExpression("'[^'\\\\]*(\\\\.[^'\\\\]*)*'"), string_format))

        # comment
        self.comment_format = QTextCharFormat()
        self.comment_format.setForeground(QColor("#646464"))
        self.comment_format.setFontItalic(True)
        self.rules.append((QRegularExpression("--[^\n]*"), self.comment_format))

        self.block_comment_start = QRegularExpression(r"--\[\[")
        self.block_comment_end = QRegularExpression(r"\]\]")

        self.undefined_format = QTextCharFormat()
        self.undefined_format.setUnderlineStyle(QTextCharFormat.UnderlineStyle.SpellCheckUnderline)
        self.undefined_format.setUnderlineColor(QColor("#ff5561"))

        self._known_builtins = set(self.keywords) | set(self.booleans) | \
            set(self.globals_keywords) | set(self.unc_keywords)

        _luauRules = {
            'rules': self.rules,
            'commentFormat': self.comment_format,
            'blockCommentStart': self.block_comment_start,
            'blockCommentEnd': self.block_comment_end,
            'knownBuiltins': self._known_builtins,
        }

    def _find_table_key_positions(self, text):
        key_positions = set()
        brace_depth = 0
        brace_starts = []
        for i, ch in enumerate(text):
            if ch == '{':
                brace_depth += 1
                brace_starts.append(i)
            elif ch == '}':
                if brace_depth > 0:
                    brace_depth -= 1
                    brace_starts.pop()

        brace_ranges = []
        stack = []
        for i, ch in enumerate(text):
            if ch == '{':
                stack.append(i)
            elif ch == '}' and stack:
                start = stack.pop()
                brace_ranges.append((start, i))

        re_tkey = re.compile(r'\b([A-Za-z_]\w*)\s*=(?!=)')
        for bstart, bend in brace_ranges:
            region = text[bstart:bend + 1]
            for m in re_tkey.finditer(region):
                abs_start = bstart + m.start(1)
                abs_end = bstart + m.end(1)
                key_positions.add((abs_start, abs_end))

        return key_positions

    def analyze(self):
        doc = self.document()
        if self._last_revision == doc.revision():
            return
        self._last_revision = doc.revision()
        self.analyzeText(doc.toPlainText())

    def analyzeText(self, text):
        stripped = list(text)
        for rx in (self._re_block_comment, self._re_line_comment, self._re_dstring, self._re_sstring):
            for m in rx.finditer(text):
                for i in range(m.start(), m.end()):
                    if stripped[i] != '\n':
                        stripped[i] = ' '
        stripped_text = ''.join(stripped)

        table_key_positions = self._find_table_key_positions(stripped_text)

        func_call_positions = set()
        for m in self._re_func_call.finditer(stripped_text):
            func_call_positions.add((m.start(1), m.end(1)))

        declared = set()
        declared_positions = {}

        def add_names(group_text, base_offset):
            offset = 0
            for name in group_text.split(','):
                raw_name = name
                name = name.strip()
                if name and name != '...' and re.match(r'^[A-Za-z_]\w*$', name):
                    declared.add(name)
                    name_pos = group_text.find(name, offset)
                    if name_pos >= 0:
                        abs_pos = base_offset + name_pos
                        if name not in declared_positions:
                            declared_positions[name] = []
                        declared_positions[name].append(abs_pos)
                offset += len(raw_name) + 1  # +1 for comma

        for m in self._re_local_func.finditer(stripped_text):
            name = m.group(1)
            declared.add(name)
            if name not in declared_positions:
                declared_positions[name] = []
            declared_positions[name].append(m.start(1))

        for m in self._re_local_vars.finditer(stripped_text):
            add_names(m.group(1), m.start(1))

        for m in self._re_func_params.finditer(stripped_text):
            add_names(m.group(1), m.start(1))

        for m in self._re_for_in.finditer(stripped_text):
            add_names(m.group(1), m.start(1))

        for m in self._re_for_num.finditer(stripped_text):
            name = m.group(1)
            declared.add(name)
            if name not in declared_positions:
                declared_positions[name] = []
            declared_positions[name].append(m.start(1))

        for m in self._re_assign_target.finditer(stripped_text):
            declared.add(m.group(1))

        for m in self._re_global_func.finditer(stripped_text):
            declared.add(m.group(1))

        known = self._known_builtins | declared

        undefined_ranges = []
        used_names = set()

        for m in self._re_identifier.finditer(stripped_text):
            name = m.group()
            start = m.start()
            end = m.end()

            prev_char = stripped_text[start - 1] if start > 0 else ''
            if prev_char in ('.', ':'):
                continue

            if (start, end) in table_key_positions:
                continue

            if name in known:
                if name in declared_positions:
                    if start not in declared_positions[name]:
                        used_names.add(name)
                continue

            if (start, end) in func_call_positions:
                continue

            undefined_ranges.append((start, len(name)))

        self.undefined_ranges = undefined_ranges

        unused_ranges = []
        for name, positions in declared_positions.items():
            if name in used_names:
                continue
            if name.startswith('_'):
                continue
            if name in self._known_builtins:
                continue
            for pos in positions:
                unused_ranges.append((pos, len(name)))

        self.unused_ranges = unused_ranges

    def highlightBlock(self, text):
        limit = self.progressiveLimit
        if limit is not None:
            if limit == 0:
                return
            if self.currentBlock().blockNumber() >= limit:
                return

        for pattern, fmt in self.rules:
            match_iterator = pattern.globalMatch(text)
            while match_iterator.hasNext():
                match = match_iterator.next()
                self.setFormat(match.capturedStart(), match.capturedLength(), fmt)

        # block comments
        self.setCurrentBlockState(0)

        if self.previousBlockState() != 1:
            match = self.block_comment_start.match(text)
            start_index = match.capturedStart() if match.hasMatch() else -1
        else:
            start_index = 0

        while start_index >= 0:
            end_match = self.block_comment_end.match(text, start_index)
            if end_match.hasMatch():
                end_index = end_match.capturedStart()
                comment_length = end_index - start_index + end_match.capturedLength()
                self.setFormat(start_index, comment_length, self.comment_format)
                next_match = self.block_comment_start.match(text, start_index + comment_length)
                start_index = next_match.capturedStart() if next_match.hasMatch() else -1
            else:
                self.setCurrentBlockState(1)
                comment_length = len(text) - start_index
                self.setFormat(start_index, comment_length, self.comment_format)
                break

        block_start = self.currentBlock().position()
        block_end = block_start + len(text)

        for start, length in self.undefined_ranges:
            if start >= block_end or start + length <= block_start:
                continue
            rel_start = max(start, block_start) - block_start
            rel_end = min(start + length, block_end) - block_start
            if rel_end > rel_start:
                fmt = self.format(rel_start)
                fmt.setUnderlineStyle(QTextCharFormat.UnderlineStyle.SpellCheckUnderline)
                fmt.setUnderlineColor(QColor("#ff5561"))
                self.setFormat(rel_start, rel_end - rel_start, fmt)

        for start, length in self.unused_ranges:
            if start >= block_end or start + length <= block_start:
                continue
            rel_start = max(start, block_start) - block_start
            rel_end = min(start + length, block_end) - block_start
            if rel_end > rel_start:
                fmt = self.format(rel_start)
                fmt.setUnderlineStyle(QTextCharFormat.UnderlineStyle.SpellCheckUnderline)
                fmt.setUnderlineColor(QColor("#d6cc61"))
                self.setFormat(rel_start, rel_end - rel_start, fmt)

class LineNumberArea(QWidget):
    def __init__(self, editor):
        super().__init__(editor)
        self.editor = editor

    def sizeHint(self):
        return QSize(self.editor.lineNumberAreaWidth(), 0)

    def paintEvent(self, event):
        self.editor.lineNumberAreaPaintEvent(event)

class CodeEditor(QPlainTextEdit):
    SYNC_BLOCK_LIMIT = 200
    SYNC_CHAR_LIMIT = 10000
    PROGRESSIVE_CHUNK = 40

    def __init__(self, content=None):
        super().__init__()

        self.setObjectName(u"codeEditor")
        self.setLineWrapMode(QPlainTextEdit.NoWrap)
        self.setStyleSheet("QPlainTextEdit{background-color:#131313;color:#d0d0d0;border:none;padding:6px 6px 6px 4px;selection-background-color:#264f78;}")

        font1 = QFont()
        font1.setFamilies([u"Consolas"])
        font1.setPointSize(11)
        self.setFont(font1)

        self.lineNumberArea = LineNumberArea(self)
        self.blockCountChanged.connect(self.updateLineNumberAreaWidth)
        self.updateRequest.connect(self.updateLineNumberArea)
        self.updateLineNumberAreaWidth()

        self.highlighter = None
        self._rehighlighting = False
        self._progressiveBlock = 0

        self._highlightTimer = QTimer(self)
        self._highlightTimer.setSingleShot(True)
        self._highlightTimer.setInterval(200)
        self._highlightTimer.timeout.connect(self._runHighlight)

        self._progressiveTimer = QTimer(self)
        self._progressiveTimer.setInterval(0)
        self._progressiveTimer.timeout.connect(self._progressiveStep)

        if content is None:
            content = 'print("Hello, World!")'
        self.setPlainText(content)

        self.document().contentsChanged.connect(self._onContentsChanged)

    def _isLarge(self):
        doc = self.document()
        return doc.blockCount() > self.SYNC_BLOCK_LIMIT or doc.characterCount() > self.SYNC_CHAR_LIMIT

    def attachHighlighter(self):
        if self.highlighter is not None:
            return
        self.highlighter = LuauHighlighter(self.document())

        if not self._isLarge():
            self.highlighter.analyze()
            self.highlighter.rehighlight()
            return

        self.highlighter.progressiveLimit = 0
        self.highlighter.undefined_ranges = []
        self.highlighter.unused_ranges = []
        self._startProgressive()

    def _startProgressive(self):
        if self.highlighter is None:
            return
        self._progressiveBlock = 0
        if not self._progressiveTimer.isActive():
            self._progressiveTimer.start()

    def _progressiveStep(self):
        hl = self.highlighter
        if hl is None:
            self._progressiveTimer.stop()
            return

        doc = self.document()
        total = doc.blockCount()
        start = self._progressiveBlock

        if start >= total:
            hl.progressiveLimit = None
            self._progressiveTimer.stop()
            return

        end = min(start + self.PROGRESSIVE_CHUNK, total)
        hl.progressiveLimit = end

        block = doc.findBlockByNumber(start)
        if block.isValid():
            hl.rehighlightBlock(block)

        self._progressiveBlock = end

        if end >= total:
            hl.progressiveLimit = None
            self._progressiveTimer.stop()

    def _onContentsChanged(self):
        if self.highlighter is None or self._progressiveTimer.isActive():
            return
        self._highlightTimer.start()

    def _runHighlight(self):
        if self.highlighter is None or self._rehighlighting:
            return
        if self._isLarge():
            return
        self._rehighlighting = True
        try:
            self.highlighter.analyze()
            self.highlighter.rehighlight()
        finally:
            self._rehighlighting = False

    def lineNumberAreaWidth(self):
        digits = max(1, len(str(self.blockCount())))
        return 16 + self.fontMetrics().horizontalAdvance("9") * digits

    def updateLineNumberAreaWidth(self, _=0):
        self.setViewportMargins(self.lineNumberAreaWidth(), 0, 0, 0)

    def updateLineNumberArea(self, rect, dy):
        if dy:
            self.lineNumberArea.scroll(0, dy)
        else:
            self.lineNumberArea.update(0, rect.y(), self.lineNumberArea.width(), rect.height())
        if rect.contains(self.viewport().rect()):
            self.updateLineNumberAreaWidth()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        cr = self.contentsRect()
        self.lineNumberArea.setGeometry(QRect(cr.left(), cr.top(), self.lineNumberAreaWidth(), cr.height()))

    def lineNumberAreaPaintEvent(self, event):
        painter = QPainter(self.lineNumberArea)
        painter.fillRect(event.rect(), QColor("#131313"))
        block = self.firstVisibleBlock()
        blockNumber = block.blockNumber()
        top = self.blockBoundingGeometry(block).translated(self.contentOffset()).top()
        bottom = top + self.blockBoundingRect(block).height()
        painter.setPen(QColor("#4a4a4a"))
        height = self.fontMetrics().height()
        while block.isValid() and top <= event.rect().bottom():
            if block.isVisible() and bottom >= event.rect().top():
                painter.drawText(0, int(top), self.lineNumberArea.width() - 8, height,
                                 Qt.AlignmentFlag.AlignRight, str(blockNumber + 1))
            block = block.next()
            top = bottom
            bottom = top + self.blockBoundingRect(block).height()
            blockNumber += 1

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
