from PySide6.QtCore import QRegularExpression, QRect, Qt
from PySide6.QtGui import QSyntaxHighlighter, QTextCharFormat, QColor, QFont
from PySide6.QtWidgets import QPlainTextEdit, QMessageBox

bold_font = 700

class LuauHighlighter(QSyntaxHighlighter):
    def __init__(self, document):
        super().__init__(document)
        self.rules = []

        # keywords
        keyword_format = QTextCharFormat()
        keyword_format.setForeground(QColor("#eb7973"))
        keyword_format.setFontWeight(bold_font)
        keywords = [
            "and", "break", "do", "else", "elseif", "end",
            "for", "function", "if", "in", "local", "nil", "not",
            "or", "repeat", "return", "then" "until", "while",
            "continue", "export", "const"
        ]
        for word in keywords:
            pattern = QRegularExpression(f"\\b{word}\\b")
            self.rules.append((pattern, keyword_format))

        # booleans
        bool_format = QTextCharFormat()
        bool_format.setForeground(QColor("#f2ba2a"))
        bool_format.setFontWeight(bold_font)
        for word in ['true', 'false']:
            pattern = QRegularExpression(f"\\b{word}\\b")
            self.rules.append((pattern, bool_format))

        # globals
        globals_format = QTextCharFormat()
        globals_format.setForeground(QColor("#8fb4ff"))
        globals_keywords = [
            "print", 'math', 'string', 'table',
            'type', 'tonumber', 'tostring', 'error', 'pcall',
            '_G', 'shared', 'game', 'workspace', 'warn', 'pairs', 'ipairs', 'next',
            'select', 'assert', 'require'
        ]
        for word in globals_keywords:
            pattern = QRegularExpression(f"\\b{word}\\b")
            self.rules.append((pattern, globals_format))

        # unc
        unc_format = QTextCharFormat()
        unc_format.setForeground(QColor("#9f6dd1"))
        unc_keywords = [
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
            'getscriptbytecode', 'dumpstring', 'getscripthash'
        ]
        for word in unc_keywords:
            pattern = QRegularExpression(f"\\b{word}\\b")
            self.rules.append((pattern, unc_format))

        # numbers
        number_format = QTextCharFormat()
        number_format.setForeground(QColor("#f2ba2a"))
        self.rules.append((QRegularExpression(r"\b\d+(\.\d+)?\b"), number_format))

        # member
        member_format = QTextCharFormat()
        member_format.setForeground(QColor("#70a0ff"))

        member_pattern = QRegularExpression(r"(?<=\.)[a-zA-Z_][a-zA-Z0-9_]*\b")
        self.rules.append((member_pattern, member_format))

        # functions
        function_format = QTextCharFormat()
        function_format.setForeground(QColor("#fae4aa"))

        # func calls
        pat = '|'.join(unc_keywords + globals_keywords)
        call_pattern = QRegularExpression(r"\b(?!(?:"+pat+r")\b)[a-zA-Z_][a-zA-Z0-9_]*(?=\s*\()")
        self.rules.append((call_pattern, function_format))

        # func defs
        def_pattern = QRegularExpression(r"(?<=\bfunction\s+)[a-zA-Z_][a-zA-Z0-9_]*\b")
        self.rules.append((def_pattern, function_format))

        # strings
        string_format = QTextCharFormat()
        string_format.setForeground(QColor("#8ee9b6"))
        self.rules.append((QRegularExpression('"[^"\\\\]*(\\\\.[^"\\\\]*)*"'), string_format))
        self.rules.append((QRegularExpression("'[^'\\\\]*(\\\\.[^'\\\\]*)*'"), string_format))

        # comment
        comment_format = QTextCharFormat()
        comment_format.setForeground(QColor("#6a6f81"))
        comment_format.setFontItalic(True)
        self.rules.append((QRegularExpression("--[^\n]*"), comment_format))

    def highlightBlock(self, text):
        for pattern, fmt in self.rules:
            match_iterator = pattern.globalMatch(text)
            while match_iterator.hasNext():
                match = match_iterator.next()
                self.setFormat(match.capturedStart(), match.capturedLength(), fmt)

class CodeEditor(QPlainTextEdit):
    def __init__(self):
        super().__init__()

        self.setObjectName(u"codeEditor")
        self.setGeometry(QRect(10, 120, 821, 371))
        self.setLineWrapMode(QPlainTextEdit.NoWrap)

        font1 = QFont()
        font1.setFamilies([u"Cascadia Code"])
        font1.setPointSize(12)
        self.setFont(font1)

        LuauHighlighter(self.document())
        self.setPlainText('-- funnyexecutor by funnyfreak228\nprint("Welcome to Funnyexecutor!")')

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