import re

from PySide6.QtCore import QRegularExpression, QRect, QSize, Qt, QTimer
from PySide6.QtGui import QSyntaxHighlighter, QTextCharFormat, QColor, QFont, QPainter
from PySide6.QtWidgets import QPlainTextEdit, QMessageBox, QWidget

boldFont = 700

_luauRules = None

class LuauHighlighter(QSyntaxHighlighter):
    # debugger
    _reBlockComment = re.compile(r"--\[\[.*?\]\]", re.DOTALL)
    _reLineComment = re.compile(r"--[^\n]*")
    _reDstring = re.compile(r'"[^"\\]*(?:\\.[^"\\]*)*"')
    _reSstring = re.compile(r"'[^'\\]*(?:\\.[^'\\]*)*'")

    _reLocalFunc = re.compile(r"\blocal\s+function\s+([A-Za-z_]\w*)")
    _reLocalVars = re.compile(r"\blocal\s+(?!function\b)((?:[A-Za-z_]\w*\s*,\s*)*[A-Za-z_]\w*)")
    _reFuncParams = re.compile(r"\bfunction\b[^()]*\(([^)]*)\)")
    _reForIn = re.compile(r"\bfor\s+((?:[A-Za-z_]\w*\s*,\s*)*[A-Za-z_]\w*)\s+in\b")
    _reForNum = re.compile(r"\bfor\s+([A-Za-z_]\w*)\s*=")
    _reAssignTarget = re.compile(r"\b([A-Za-z_]\w*)\s*=(?!=)")
    _reIdentifier = re.compile(r"\b[A-Za-z_]\w*\b")
    _reTableKey = re.compile(r"\b([A-Za-z_]\w*)\s*=(?!=)")
    _reFuncCall = re.compile(r"\b([A-Za-z_]\w*)\s*(?=[\({\"'])")
    _reGlobalFunc = re.compile(r"(?<!\blocal\s)(?<!\blocal\s{2})(?<!\blocal\s{3})\bfunction\s+([A-Za-z_]\w*)")

    def __init__(self, document):
        super().__init__(document)

        global _luauRules

        self.progressiveLimit = None
        self._lastRevision = None
        self.undefinedRanges = []
        self.unusedRanges = []

        if _luauRules is not None:
            self.rules = _luauRules['rules']
            self.commentFormat = _luauRules['commentFormat']
            self.blockCommentStart = _luauRules['blockCommentStart']
            self.blockCommentEnd = _luauRules['blockCommentEnd']
            self._knownBuiltins = _luauRules['knownBuiltins']
            return

        self.rules = []

        # keywords
        keywordFormat = QTextCharFormat()
        keywordFormat.setForeground(QColor("#8e9ae6"))
        keywordFormat.setFontWeight(boldFont)
        self.keywords = [
            "and", "break", "do", "else", "elseif", "end",
            "for", "function", "if", "in", "local", "nil", "not",
            "or", "repeat", "return", "then", "until", "while",
            "continue", "export", "const"
        ]
        for word in self.keywords:
            pattern = QRegularExpression(f"\\b{word}\\b")
            self.rules.append((pattern, keywordFormat))

        # booleans
        boolFormat = QTextCharFormat()
        boolFormat.setForeground(QColor("#d6cc61"))
        boolFormat.setFontWeight(boldFont)
        self.booleans = ['true', 'false']
        for word in self.booleans:
            pattern = QRegularExpression(f"\\b{word}\\b")
            self.rules.append((pattern, boolFormat))

        # globals
        globalsFormat = QTextCharFormat()
        globalsFormat.setForeground(QColor("#d6cc61"))
        self.globalsKeywords = [
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
        for word in self.globalsKeywords:
            pattern = QRegularExpression(f"\\b{word}\\b")
            self.rules.append((pattern, globalsFormat))

        # unc
        uncFormat = QTextCharFormat()
        uncFormat.setForeground(QColor("#8e9ae6"))
        self.uncKeywords = [
            'getgenv', 'base64encode', 'base64decode', 'crypt',
            'lz4compress', 'lz4decompress', 'loadstring', 'writefile',
            'appendfile', 'readfile', 'isfile', 'isfolder',
            'delfile', 'delfolder', 'makefolder', 'listfiles',
            'setclipboard', 'getclipboard', 'messagebox', 'identifyexecutor',
            'loadfile', 'setfpscap', 'getfpscap', 'getexecutorname',
            'getexecutorversion', 'cloneref', 'compareinstances', 'islclosure',
            'iscclosure', 'newcclosure', 'gethui', 'getnilinstances', 'getloadedmodules',
            'getscripts', 'getrunningscripts', 'isreadonly', 'queue_on_teleport',
            'getnamecallmethod', 'http_request', 'crypt', 'hash',
            'messagebox', 'mouse1click', 'mouse2click', 'mouse1press',
            'mouse1release', 'mouse2press', 'mouse2release', 'movemouse',
            'mousemoveabs', 'mouserel', 'mousemoverel', 'getmousepos',
            'getmouselocation', 'keyclick', 'keypress', 'keyrelease',
            'iswindowactive', 'isrbxactive', 'getscriptbytecode', 'dumpstring',
            'getscripthash', 'Drawing', 'WebSocket', 'websocket', 'decompile',
            'saveinstance', 'savegame', 'isrenderavailable', 'getrenderproperty',
            'setrenderproperty', 'request', 'syn', 'http',
            'Signal', 'openfiledialog', 'savefiledialog', 'openfolderdialog',
            'openfilesdialog', 'getinstances', 'getcustomasset',
            'getrenv', 'getreg', 'getgc', 'filtergc', 'getsenv',
            'getconstant', 'getconstants', 'getupvalue', 'getupvalues',
            'setupvalue', 'setconstant', 'getproto', 'getprotos',
            'getstack', 'setstack'
        ]
        for word in self.uncKeywords:
            pattern = QRegularExpression(f"\\b{word}\\b")
            self.rules.append((pattern, uncFormat))

        # numbers
        numberFormat = QTextCharFormat()
        numberFormat.setForeground(QColor("#d6cc61"))
        self.rules.append((QRegularExpression(r"\b\d+(\.\d+)?\b"), numberFormat))

        # member
        memberFormat = QTextCharFormat()
        memberFormat.setForeground(QColor("#7b99ec"))

        memberPattern = QRegularExpression(r"(?<=\.)[a-zA-Z_][a-zA-Z0-9_]*\b")
        self.rules.append((memberPattern, memberFormat))

        # functions
        functionFormat = QTextCharFormat()
        functionFormat.setForeground(QColor("#7b99ec"))

        # func calls
        pat = '|'.join(self.uncKeywords + self.globalsKeywords)
        callPattern = QRegularExpression(r"\b(?!(?:"+pat+r")\b)[a-zA-Z_][a-zA-Z0-9_]*(?=\s*\()")
        self.rules.append((callPattern, functionFormat))

        # func defs
        defPattern = QRegularExpression(r"\bfunction\s+\K[a-zA-Z_][a-zA-Z0-9_]*\b")
        self.rules.append((defPattern, functionFormat))

        # strings
        stringFormat = QTextCharFormat()
        stringFormat.setForeground(QColor("#abd4b4"))
        self.rules.append((QRegularExpression('"[^"\\\\]*(\\\\.[^"\\\\]*)*"'), stringFormat))
        self.rules.append((QRegularExpression("'[^'\\\\]*(\\\\.[^'\\\\]*)*'"), stringFormat))

        # comment
        self.commentFormat = QTextCharFormat()
        self.commentFormat.setForeground(QColor("#646464"))
        self.commentFormat.setFontItalic(True)
        self.rules.append((QRegularExpression("--[^\n]*"), self.commentFormat))

        self.blockCommentStart = QRegularExpression(r"--\[\[")
        self.blockCommentEnd = QRegularExpression(r"\]\]")

        self.undefinedFormat = QTextCharFormat()
        self.undefinedFormat.setUnderlineStyle(QTextCharFormat.UnderlineStyle.SpellCheckUnderline)
        self.undefinedFormat.setUnderlineColor(QColor("#ff5561"))

        self._knownBuiltins = set(self.keywords) | set(self.booleans) | \
            set(self.globalsKeywords) | set(self.uncKeywords)

        _luauRules = {
            'rules': self.rules,
            'commentFormat': self.commentFormat,
            'blockCommentStart': self.blockCommentStart,
            'blockCommentEnd': self.blockCommentEnd,
            'knownBuiltins': self._knownBuiltins,
        }

    def _findTableKeyPositions(self, text):
        keyPositions = set()
        braceDepth = 0
        braceStarts = []
        for i, ch in enumerate(text):
            if ch == '{':
                braceDepth += 1
                braceStarts.append(i)
            elif ch == '}':
                if braceDepth > 0:
                    braceDepth -= 1
                    braceStarts.pop()

        braceRanges = []
        stack = []
        for i, ch in enumerate(text):
            if ch == '{':
                stack.append(i)
            elif ch == '}' and stack:
                start = stack.pop()
                braceRanges.append((start, i))

        reTkey = re.compile(r'\b([A-Za-z_]\w*)\s*=(?!=)')
        for bstart, bend in braceRanges:
            region = text[bstart:bend + 1]
            for m in reTkey.finditer(region):
                absStart = bstart + m.start(1)
                absEnd = bstart + m.end(1)
                keyPositions.add((absStart, absEnd))

        return keyPositions

    def analyze(self):
        doc = self.document()
        if self._lastRevision == doc.revision():
            return
        self._lastRevision = doc.revision()
        self.analyzeText(doc.toPlainText())

    def analyzeText(self, text):
        stripped = list(text)
        for rx in (self._reBlockComment, self._reLineComment, self._reDstring, self._reSstring):
            for m in rx.finditer(text):
                for i in range(m.start(), m.end()):
                    if stripped[i] != '\n':
                        stripped[i] = ' '
        strippedText = ''.join(stripped)

        tableKeyPositions = self._findTableKeyPositions(strippedText)

        funcCallPositions = set()
        for m in self._reFuncCall.finditer(strippedText):
            funcCallPositions.add((m.start(1), m.end(1)))

        declared = set()
        declaredPositions = {}

        def addNames(groupText, baseOffset):
            offset = 0
            for name in groupText.split(','):
                rawName = name
                name = name.strip()
                if name and name != '...' and re.match(r'^[A-Za-z_]\w*$', name):
                    declared.add(name)
                    namePos = groupText.find(name, offset)
                    if namePos >= 0:
                        absPos = baseOffset + namePos
                        if name not in declaredPositions:
                            declaredPositions[name] = []
                        declaredPositions[name].append(absPos)
                offset += len(rawName) + 1  # +1 for comma

        for m in self._reLocalFunc.finditer(strippedText):
            name = m.group(1)
            declared.add(name)
            if name not in declaredPositions:
                declaredPositions[name] = []
            declaredPositions[name].append(m.start(1))

        for m in self._reLocalVars.finditer(strippedText):
            addNames(m.group(1), m.start(1))

        for m in self._reFuncParams.finditer(strippedText):
            addNames(m.group(1), m.start(1))

        for m in self._reForIn.finditer(strippedText):
            addNames(m.group(1), m.start(1))

        for m in self._reForNum.finditer(strippedText):
            name = m.group(1)
            declared.add(name)
            if name not in declaredPositions:
                declaredPositions[name] = []
            declaredPositions[name].append(m.start(1))

        for m in self._reAssignTarget.finditer(strippedText):
            declared.add(m.group(1))

        for m in self._reGlobalFunc.finditer(strippedText):
            declared.add(m.group(1))

        known = self._knownBuiltins | declared

        undefinedRanges = []
        usedNames = set()

        for m in self._reIdentifier.finditer(strippedText):
            name = m.group()
            start = m.start()
            end = m.end()

            prevChar = strippedText[start - 1] if start > 0 else ''
            if prevChar in ('.', ':'):
                continue

            if (start, end) in tableKeyPositions:
                continue

            if name in known:
                if name in declaredPositions:
                    if start not in declaredPositions[name]:
                        usedNames.add(name)
                continue

            if (start, end) in funcCallPositions:
                continue

            undefinedRanges.append((start, len(name)))

        self.undefinedRanges = undefinedRanges

        unusedRanges = []
        for name, positions in declaredPositions.items():
            if name in usedNames:
                continue
            if name.startswith('_'):
                continue
            if name in self._knownBuiltins:
                continue
            for pos in positions:
                unusedRanges.append((pos, len(name)))

        self.unusedRanges = unusedRanges

    def highlightBlock(self, text):
        limit = self.progressiveLimit
        if limit is not None:
            if limit == 0:
                return
            if self.currentBlock().blockNumber() >= limit:
                return

        for pattern, fmt in self.rules:
            matchIterator = pattern.globalMatch(text)
            while matchIterator.hasNext():
                match = matchIterator.next()
                self.setFormat(match.capturedStart(), match.capturedLength(), fmt)

        # block comments
        self.setCurrentBlockState(0)

        if self.previousBlockState() != 1:
            match = self.blockCommentStart.match(text)
            startIndex = match.capturedStart() if match.hasMatch() else -1
        else:
            startIndex = 0

        while startIndex >= 0:
            endMatch = self.blockCommentEnd.match(text, startIndex)
            if endMatch.hasMatch():
                endIndex = endMatch.capturedStart()
                commentLength = endIndex - startIndex + endMatch.capturedLength()
                self.setFormat(startIndex, commentLength, self.commentFormat)
                nextMatch = self.blockCommentStart.match(text, startIndex + commentLength)
                startIndex = nextMatch.capturedStart() if nextMatch.hasMatch() else -1
            else:
                self.setCurrentBlockState(1)
                commentLength = len(text) - startIndex
                self.setFormat(startIndex, commentLength, self.commentFormat)
                break

        blockStart = self.currentBlock().position()
        blockEnd = blockStart + len(text)

        for start, length in self.undefinedRanges:
            if start >= blockEnd or start + length <= blockStart:
                continue
            relStart = max(start, blockStart) - blockStart
            relEnd = min(start + length, blockEnd) - blockStart
            if relEnd > relStart:
                fmt = self.format(relStart)
                fmt.setUnderlineStyle(QTextCharFormat.UnderlineStyle.SpellCheckUnderline)
                fmt.setUnderlineColor(QColor("#ff5561"))
                self.setFormat(relStart, relEnd - relStart, fmt)

        for start, length in self.unusedRanges:
            if start >= blockEnd or start + length <= blockStart:
                continue
            relStart = max(start, blockStart) - blockStart
            relEnd = min(start + length, blockEnd) - blockStart
            if relEnd > relStart:
                fmt = self.format(relStart)
                fmt.setUnderlineStyle(QTextCharFormat.UnderlineStyle.SpellCheckUnderline)
                fmt.setUnderlineColor(QColor("#d6cc61"))
                self.setFormat(relStart, relEnd - relStart, fmt)

class LineNumberArea(QWidget):
    def __init__(self, editor):
        super().__init__(editor)
        self.editor = editor

    def sizeHint(self):
        return QSize(self.editor.lineNumberAreaWidth(), 0)

    def paintEvent(self, event):
        self.editor.lineNumberAreaPaintEvent(event)

class CodeEditor(QPlainTextEdit):
    syncBlockLimit = 200
    syncCharLimit = 10000
    progressiveChunk = 40

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
        return doc.blockCount() > self.syncBlockLimit or doc.characterCount() > self.syncCharLimit

    def attachHighlighter(self):
        if self.highlighter is not None:
            return
        self.highlighter = LuauHighlighter(self.document())

        if not self._isLarge():
            self.highlighter.analyze()
            self.highlighter.rehighlight()
            return

        self.highlighter.progressiveLimit = 0
        self.highlighter.undefinedRanges = []
        self.highlighter.unusedRanges = []
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

        end = min(start + self.progressiveChunk, total)
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
