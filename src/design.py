from PySide6.QtCore import QCoreApplication, QMetaObject, QRect, QSize, QByteArray, Qt, Signal
from PySide6.QtGui import QAction, QColor, QFont, QIcon, QPixmap, QPainter
from PySide6.QtSvg import QSvgRenderer
from PySide6.QtWidgets import (QFrame, QHBoxLayout, QLabel, QLineEdit, QMainWindow,
    QMenu, QPushButton, QSizePolicy, QStackedWidget, QTabBar, QTreeWidget, QVBoxLayout,
    QWidget)

railBg = "#161616"
panelBg = "#161616"
divider = "#2a2a2a"
textDim = "#9b9b9b"
textActive = "#ececec"

class Icons:
    execute = """<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="white" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M5 5a2 2 0 0 1 3.008-1.728l11.997 6.998a2 2 0 0 1 .003 3.458l-12 7A2 2 0 0 1 5 19z"/></svg>"""

    newTab = """<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="white" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M5 12h14"/><path d="M12 5v14"/></svg>"""

    file = """<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="white" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M4 12.15V4a2 2 0 0 1 2-2h8a2.4 2.4 0 0 1 1.706.706l3.588 3.588A2.4 2.4 0 0 1 20 8v12a2 2 0 0 1-2 2h-3.35"/><path d="M14 2v5a1 1 0 0 0 1 1h5"/><path d="m5 16-3 3 3 3"/><path d="m9 22 3-3-3-3"/></svg>"""

    folder = """<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="white" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M20 20a2 2 0 0 0 2-2V8a2 2 0 0 0-2-2h-7.9a2 2 0 0 1-1.69-.9L9.6 3.9A2 2 0 0 0 7.93 3H4a2 2 0 0 0-2 2v13a2 2 0 0 0 2 2Z"/></svg>"""

    inject = """<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="white" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="m16 6-8.414 8.586a2 2 0 0 0 2.829 2.829l8.414-8.586a4 4 0 1 0-5.657-5.657l-8.379 8.551a6 6 0 1 0 8.485 8.485l8.379-8.551"/></svg>"""

    editorTab = """<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="white" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect width="18" height="18" x="3" y="3" rx="2"/><path d="m7 9 2 2-2 2"/><path d="M13 15h4"/></svg>"""

    settingsTab = """<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="white" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="lucide lucide-settings preview-icon"><path d="M9.671 4.136a2.34 2.34 0 0 1 4.659 0 2.34 2.34 0 0 0 3.319 1.915 2.34 2.34 0 0 1 2.33 4.033 2.34 2.34 0 0 0 0 3.831 2.34 2.34 0 0 1-2.33 4.033 2.34 2.34 0 0 0-3.319 1.915 2.34 2.34 0 0 1-4.659 0 2.34 2.34 0 0 0-3.32-1.915 2.34 2.34 0 0 1-2.33-4.033 2.34 2.34 0 0 0 0-3.831A2.34 2.34 0 0 1 6.35 6.051a2.34 2.34 0 0 0 3.319-1.915"/><circle cx="12" cy="12" r="3"/></svg>"""

    exitIcon = """<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="white" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="lucide lucide-x preview-icon"><path d="M18 6 6 18"/><path d="m6 6 12 12"/></svg>"""

    minimizeIcon = """<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="white" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="lucide lucide-minus preview-icon"><path d="M5 12h14"/></svg>"""

    resizeIcon = """<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="white" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="lucide lucide-square preview-icon"><rect width="18" height="18" x="3" y="3" rx="2"/></svg>"""

    chevronLeft = """<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="white" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="m15 18-6-6 6-6"/></svg>"""

    chevronRight = """<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="white" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="m9 18 6-6-6-6"/></svg>"""

    spark = """<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="white" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M9.937 15.5A2 2 0 0 0 8.5 14.063l-6.135-1.582a.5.5 0 0 1 0-.962L8.5 9.936A2 2 0 0 0 9.937 8.5l1.582-6.135a.5.5 0 0 1 .963 0L14.063 8.5A2 2 0 0 0 15.5 9.937l6.135 1.581a.5.5 0 0 1 0 .964L15.5 14.063a2 2 0 0 0-1.437 1.437l-1.582 6.135a.5.5 0 0 1-.963 0z"/></svg>"""

def _svgPixmap(svg, color, size):
    data = svg.replace('stroke="white"', 'stroke="%s"' % color).replace('fill="white"', 'fill="%s"' % color)
    renderer = QSvgRenderer(QByteArray(data.encode("utf-8")))
    scale = 2
    pm = QPixmap(size * scale, size * scale)
    pm.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pm)
    renderer.render(painter)
    painter.end()
    pm.setDevicePixelRatio(scale)
    return pm


def svgIcon(svg, color, size=18):
    return QIcon(_svgPixmap(svg, color, size))


def navIcon(svg, size=20, dim=textDim, active=textActive):
    icon = QIcon()
    icon.addPixmap(_svgPixmap(svg, dim, size), QIcon.Mode.Normal)
    icon.addPixmap(_svgPixmap(svg, active, size), QIcon.Mode.Active)
    icon.addPixmap(_svgPixmap(svg, active, size), QIcon.Mode.Selected)
    return icon


class ResizeGrip(QWidget):

    resizeStarted = Signal()
    resized = Signal(int)
    resizeFinished = Signal()

    barWidth = 3
    barHeight = 40

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName(u"resizeGrip")
        self.setFixedWidth(18)
        self.setCursor(Qt.CursorShape.SplitHCursor)
        self.setAttribute(Qt.WidgetAttribute.WA_Hover, True)
        self._pressX = 0

    def _barRect(self):
        x = (self.width() - self.barWidth)
        y = (self.height() - self.barHeight)
        return QRect(x, y, self.barWidth, self.barHeight)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor("#6a6a6a") if self.underMouse() else QColor("#3a3a3a"))
        painter.drawRoundedRect(self._barRect(), 2, 2)
        painter.end()

    def mousePressEvent(self, event):
        if event.button() != Qt.MouseButton.LeftButton:
            super().mousePressEvent(event)
            return
        self._pressX = event.position().x()
        self.resizeStarted.emit()

    def mouseMoveEvent(self, event):
        if not event.buttons() & Qt.MouseButton.LeftButton:
            super().mouseMoveEvent(event)
            return
        x = event.position().x()
        delta = int(x - self._pressX)
        self._pressX = x
        if delta != 0:
            self.resized.emit(delta)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.resizeFinished.emit()
        super().mouseReleaseEvent(event)


style = """
#appFrame { background-color: #161616; border: 1px solid #2a2a2a; }
#iconRail { background-color: #161616; border-right: 1px solid #2a2a2a; }
#titlebar { background-color: #161616; }
#rightArea { background-color: #161616; }
#windowTitle { color: #dcdcdc; font-size: 18px; font-weight: 500; }

#logoBubble { background-color: #1f1f1f; border-radius: 16px; }

#navBtn {
    background-color: #1f1f1f; border: 1px solid transparent; border-radius: 15px;
}
#navBtn:hover { background-color: #2a2a2a; }
#navBtn:checked, #navBtn[active="true"] {
    background-color: #303030; border-color: #3b3b3b;
}
#navBtn:checked:hover, #navBtn[active="true"]:hover { background-color: #303030; }

#winBtn {
    background: transparent; border: none; border-radius: 8px;
}
#winBtn:hover { background-color: #262626; }
#winBtn#closeBtn:hover { background-color: #c42b1c; }

#tabStrip { background-color: #161616; }
QTabBar#tabBar { qproperty-drawBase: 0; }
QTabBar#tabBar::tab {
    background-color: #161616; color: #9b9b9b;
    border: none; border-top-left-radius: 8px; border-top-right-radius: 8px;
    padding: 8px 14px; margin-right: 2px; min-width: 54px;
}
QTabBar#tabBar::tab:hover { background-color: #1f1f1f; color: #d0d0d0; }
QTabBar#tabBar::tab:selected { background-color: #0c0c0c; color: #ececec; }
QTabBar#tabBar::close-button {
    subcontrol-position: right; width: 13px; height: 13px; margin-left: 6px;
    border-radius: 7px; background: transparent;
}
QTabBar#tabBar::close-button:hover { background-color: #2a2a2a; }

#newTabButton {
    background: transparent; border: none; border-radius: 8px;
}
#newTabButton:hover { background-color: #1f1f1f; }

#editorStack { background-color: #000000; }

#actionBar { background-color: #161616; }
#pathLabel { color: #6f6f6f; font-size: 12px; }

#injectButton {
    background-color: #1a1a1a; border: 1px solid #2c2c2c; border-radius: 10px;
    color: #eeeeee; font-size: 13px; font-weight: 600; padding: 7px 16px;
}
#injectButton:hover { background-color: #242424; }
#injectButton:pressed { background-color: #2a2a2a; }
#executeButton {
    background-color: #f1f1f1; border: 1px solid #f1f1f1; border-radius: 10px;
    color: #0a0a0a; font-size: 13px; font-weight: 600; padding: 7px 16px;
}
#executeButton:hover { background-color: #ffffff; }
#executeButton:pressed { background-color: #e2e2e2; }

#explorerPanel { background-color: #161616; border-left: 1px solid #2a2a2a; }
#explorerPill {
    background-color: #1f1f1f; border: 1px solid #2a2a2a; border-radius: 12px;
}
#explorerPill:hover { background-color: #2a2a2a; }
#explorerPill:pressed { background-color: #303030; }
#panelTitle {
    color: #9b9b9b; font-size: 12px; font-weight: 600; letter-spacing: 0.6px;
}

#searchEdit {
    background-color: #1a1a1a; border: 1px solid #2a2a2a; border-radius: 10px;
    color: #ffffff; padding: 4px 12px; font-size: 13px;
    selection-background-color: #2a2a2a;
}
#searchEdit:focus { border-color: #6a6a6a; }
QLineEdit#searchEdit::placeholder { color: #5e5e5e; }

QTreeWidget#scriptTree {
    background-color: #161616; border: none; outline: 0;
    color: #9b9b9b; font-size: 13px;
}
QTreeWidget#scriptTree::item { height: 30px; border: none; border-radius: 6px; }
QTreeWidget#scriptTree::item:hover {
    color: #ffffff; background-color: #1f1f1f; border: none; border-radius: 6px;
}
QTreeWidget#scriptTree::item:selected {
    color: #ffffff; background-color: #2a2a2a; border: none; border-radius: 6px;
}
QTreeWidget#scriptTree::item:selected:hover {
    color: #ffffff; background-color: #2a2a2a; border: none; border-radius: 6px;
}
QTreeWidget#scriptTree::branch { background: transparent; }

#settingsPage { background-color: #161616; }
#pageTitle { color: #ffffff; font-size: 26px; font-weight: 600; }
#settingCard { background-color: #0c0c0c; border-radius: 14px; }
#cardTitle { color: #f0f0f0; font-size: 15px; font-weight: 600; }
#cardDesc { color: #9b9b9b; font-size: 13px; }
#cardBadge {
    background-color: #1a1a1a; border: 1px solid #2a2a2a; border-radius: 4px;
    color: #cfcfcf; font-size: 12px; font-weight: 600; padding: 3px 9px;
}

QToolTip { background-color: #1b1b1b; color: #d0d0d0; border: 1px solid #2a2a2a; }

QMenu { background-color: #1b1b1b; color: #d0d0d0; border: 1px solid #2a2a2a; padding: 4px; }
QMenu::item { padding: 6px 22px; border-radius: 4px; }
QMenu::item:selected { background-color: #2a2a2a; }
QMenu::separator { height: 1px; background-color: #2a2a2a; margin: 4px 6px; }

QScrollBar:vertical { background: transparent; width: 10px; margin: 0; }
QScrollBar::handle:vertical { background-color: #2c2c2c; border-radius: 5px; min-height: 24px; }
QScrollBar::handle:vertical:hover { background-color: #3a3a3a; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical { background: transparent; }
QScrollBar:horizontal { background: transparent; height: 10px; margin: 0; }
QScrollBar::handle:horizontal { background-color: #2c2c2c; border-radius: 5px; min-width: 24px; }
QScrollBar::handle:horizontal:hover { background-color: #3a3a3a; }
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal { width: 0; }
QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal { background: transparent; }
"""


class Ui_MainWindow(object):
    def setupUi(self, MainWindow):
        if not MainWindow.objectName():
            MainWindow.setObjectName(u"MainWindow")
        MainWindow.resize(1180, 690)
        MainWindow.setMinimumSize(QSize(1040, 600))

        self.actionExitAltF4 = QAction(MainWindow)
        self.actionExitAltF4.setObjectName(u"actionExit_Alt_F4")
        self.actionInject = QAction(MainWindow)
        self.actionInject.setObjectName(u"actionInject")
        self.actionExecute = QAction(MainWindow)
        self.actionExecute.setObjectName(u"actionExecute")
        self.actionExport = QAction(MainWindow)
        self.actionExport.setObjectName(u"actionExport")
        self.actionImport = QAction(MainWindow)
        self.actionImport.setObjectName(u"actionImport")
        self.actionInfo = QAction(MainWindow)
        self.actionInfo.setObjectName(u"actionInfo")
        self.actionSaveTabs = QAction(MainWindow)
        self.actionSaveTabs.setObjectName(u"actionSave_Tabs")
        self.actionNewTab = QAction(MainWindow)
        self.actionNewTab.setObjectName(u"actionNew_Tab")
        self.actionClearTabs = QAction(MainWindow)
        self.actionClearTabs.setObjectName(u"actionClear_Tabs")
        self.actionBtools = QAction(MainWindow)
        self.actionBtools.setObjectName(u"actionBtools")
        self.actionTopMost = QAction(MainWindow)
        self.actionTopMost.setObjectName(u"actionTop_Most")
        self.actionTopMost.setCheckable(True)
        self.actionTopMost.setChecked(True)

        self.centralwidget = QWidget(MainWindow)
        self.centralwidget.setObjectName(u"appFrame")
        rootLayout = QHBoxLayout(self.centralwidget)
        rootLayout.setContentsMargins(1, 1, 1, 1)
        rootLayout.setSpacing(0)

        self.iconRail = QFrame(self.centralwidget)
        self.iconRail.setObjectName(u"iconRail")
        self.iconRail.setFixedWidth(50)
        railLayout = QVBoxLayout(self.iconRail)
        railLayout.setContentsMargins(0, 9, 0, 10)
        railLayout.setSpacing(0)

        self.logo = QLabel(self.iconRail)
        self.logo.setObjectName(u"logoBubble")
        self.logo.setFixedSize(32, 32)
        self.logo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.logo.setPixmap(_svgPixmap(Icons.spark, "#cfcfcf", 16))
        railLayout.addWidget(self.logo, 0, Qt.AlignmentFlag.AlignHCenter)
        railLayout.addSpacing(18)

        self.editorNavBtn = QPushButton(self.iconRail)
        self.editorNavBtn.setObjectName(u"navBtn")
        self.editorNavBtn.setFixedSize(30, 30)
        self.editorNavBtn.setCheckable(True)
        self.editorNavBtn.setChecked(True)
        self.editorNavBtn.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.editorNavBtn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.editorNavBtn.setToolTip(u"Editor")
        self.editorNavBtn.setIcon(navIcon(Icons.editorTab, 16, dim="#cfcfcf", active="#ffffff"))
        self.editorNavBtn.setIconSize(QSize(16, 16))

        self.filesNavBtn = QPushButton(self.iconRail)
        self.filesNavBtn.setObjectName(u"navBtn")
        self.filesNavBtn.setFixedSize(30, 30)
        self.filesNavBtn.setCheckable(True)
        self.filesNavBtn.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.filesNavBtn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.filesNavBtn.setToolTip(u"File Explorer")
        self.filesNavBtn.setIcon(navIcon(Icons.folder, 16, dim="#cfcfcf", active="#ffffff"))
        self.filesNavBtn.setIconSize(QSize(16, 16))

        self.settingsNavBtn = QPushButton(self.iconRail)
        self.settingsNavBtn.setObjectName(u"navBtn")
        self.settingsNavBtn.setFixedSize(30, 30)
        self.settingsNavBtn.setCheckable(True)
        self.settingsNavBtn.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.settingsNavBtn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.settingsNavBtn.setToolTip(u"Settings")
        self.settingsNavBtn.setIcon(navIcon(Icons.settingsTab, 16, dim="#cfcfcf", active="#ffffff"))
        self.settingsNavBtn.setIconSize(QSize(16, 16))

        railLayout.addWidget(self.editorNavBtn, 0, Qt.AlignmentFlag.AlignHCenter)
        railLayout.addSpacing(18)
        railLayout.addWidget(self.filesNavBtn, 0, Qt.AlignmentFlag.AlignHCenter)
        railLayout.addStretch()
        railLayout.addWidget(self.settingsNavBtn, 0, Qt.AlignmentFlag.AlignHCenter)

        self.rightArea = QWidget(self.centralwidget)
        self.rightArea.setObjectName(u"rightArea")
        rightAreaLayout = QVBoxLayout(self.rightArea)
        rightAreaLayout.setContentsMargins(0, 0, 0, 0)
        rightAreaLayout.setSpacing(0)

        self.titlebar = QFrame(self.rightArea)
        self.titlebar.setObjectName(u"titlebar")
        self.titlebar.setFixedHeight(51)
        titleLayout = QHBoxLayout(self.titlebar)
        titleLayout.setContentsMargins(14, 0, 6, 0)
        titleLayout.setSpacing(0)
        self.windowTitle = QLabel(self.titlebar)
        self.windowTitle.setObjectName(u"windowTitle")
        titleLayout.addWidget(self.windowTitle)
        titleLayout.addStretch()

        self.minimizeBtn = QPushButton(self.titlebar)
        self.minimizeBtn.setObjectName(u"winBtn")
        self.minimizeBtn.setFixedSize(40, 34)
        self.minimizeBtn.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.minimizeBtn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.minimizeBtn.setToolTip(u"Minimize")
        self.minimizeBtn.setIcon(navIcon(Icons.minimizeIcon, 15, dim="#dedede", active="#ffffff"))
        self.minimizeBtn.setIconSize(QSize(15, 15))

        self.maximizeBtn = QPushButton(self.titlebar)
        self.maximizeBtn.setObjectName(u"winBtn")
        self.maximizeBtn.setFixedSize(40, 34)
        self.maximizeBtn.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.maximizeBtn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.maximizeBtn.setToolTip(u"Maximize")
        self.maximizeBtn.setIcon(navIcon(Icons.resizeIcon, 15, dim="#dedede", active="#ffffff"))
        self.maximizeBtn.setIconSize(QSize(15, 15))

        self.closeBtn = QPushButton(self.titlebar)
        self.closeBtn.setObjectName(u"closeBtn")
        self.closeBtn.setFixedSize(40, 34)
        self.closeBtn.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.closeBtn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.closeBtn.setToolTip(u"Close")
        self.closeBtn.setIcon(navIcon(Icons.exitIcon, 15, dim="#dedede", active="#ffffff"))
        self.closeBtn.setIconSize(QSize(15, 15))

        titleLayout.addWidget(self.minimizeBtn)
        titleLayout.addWidget(self.maximizeBtn)
        titleLayout.addWidget(self.closeBtn)

        self.mainStack = QStackedWidget(self.rightArea)
        self.mainStack.setObjectName(u"mainStack")

        self.editorPage = QWidget(self.mainStack)
        self.editorPage.setObjectName(u"editorPage")
        editorPageLayout = QVBoxLayout(self.editorPage)
        editorPageLayout.setContentsMargins(0, 0, 0, 0)
        editorPageLayout.setSpacing(0)

        self.tabStrip = QFrame(self.editorPage)
        self.tabStrip.setObjectName(u"tabStrip")
        self.tabStrip.setFixedHeight(40)
        stripLayout = QHBoxLayout(self.tabStrip)
        stripLayout.setContentsMargins(6, 8, 12, 0)
        stripLayout.setSpacing(4)
        self.tabBar = QTabBar(self.tabStrip)
        self.tabBar.setObjectName(u"tabBar")
        self.tabBar.setTabsClosable(True)
        self.tabBar.setMovable(True)
        self.tabBar.setExpanding(False)
        self.tabBar.setDrawBase(False)
        self.newTabButton = QPushButton(self.tabStrip)
        self.newTabButton.setObjectName(u"newTabButton")
        self.newTabButton.setFixedSize(30, 28)
        self.newTabButton.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.newTabButton.setCursor(Qt.CursorShape.PointingHandCursor)
        self.newTabButton.setToolTip(u"New Tab")
        self.newTabButton.setIcon(navIcon(Icons.newTab, 16, dim="#cfcfcf", active="#ffffff"))
        self.newTabButton.setIconSize(QSize(16, 16))
        stripLayout.addWidget(self.tabBar)
        stripLayout.addWidget(self.newTabButton, 0, Qt.AlignmentFlag.AlignBottom)
        stripLayout.addStretch()

        self.editorStack = QStackedWidget(self.editorPage)
        self.editorStack.setObjectName(u"editorStack")
        self.editorStack.layout().setContentsMargins(6, 0, 0, 0)

        self.explorerPill = QPushButton(self.editorPage)
        self.explorerPill.setObjectName(u"explorerPill")
        self.explorerPill.setFixedSize(24, 60)
        self.explorerPill.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.explorerPill.setCursor(Qt.CursorShape.PointingHandCursor)
        self.explorerPill.setIcon(navIcon(Icons.chevronRight, 16, dim="#cfcfcf", active="#ffffff"))
        self.explorerPill.setIconSize(QSize(16, 16))

        self.explorerPanel = QFrame(self.editorPage)
        self.explorerPanel.setObjectName(u"explorerPanel")
        panelLayout = QHBoxLayout(self.explorerPanel)
        panelLayout.setContentsMargins(0, 0, 0, 0)
        panelLayout.setSpacing(0)

        self.explorerGrip = ResizeGrip(self.explorerPanel)

        self.explorerContent = QWidget(self.explorerPanel)
        self.explorerContent.setObjectName(u"explorerContent")
        contentLayout = QVBoxLayout(self.explorerContent)
        contentLayout.setContentsMargins(4, 12, 12, 12)
        contentLayout.setSpacing(8)
        self.panelTitle = QLabel(self.explorerContent)
        self.panelTitle.setObjectName(u"panelTitle")
        self.searchEdit = QLineEdit(self.explorerContent)
        self.searchEdit.setObjectName(u"searchEdit")
        self.searchEdit.setFixedHeight(32)
        self.scriptTree = QTreeWidget(self.explorerContent)
        self.scriptTree.setObjectName(u"scriptTree")
        self.scriptTree.setHeaderHidden(True)
        self.scriptTree.setIndentation(14)
        contentLayout.addWidget(self.panelTitle)
        contentLayout.addWidget(self.searchEdit)
        contentLayout.addWidget(self.scriptTree, 1)

        panelLayout.addWidget(self.explorerGrip)
        panelLayout.addWidget(self.explorerContent, 1)

        self.editorRow = QWidget(self.editorPage)
        self.editorRow.setObjectName(u"editorRow")
        editorRowLayout = QHBoxLayout(self.editorRow)
        editorRowLayout.setContentsMargins(0, 0, 0, 8)
        editorRowLayout.setSpacing(0)
        editorRowLayout.addWidget(self.editorStack, 1)
        editorRowLayout.addSpacing(8)
        editorRowLayout.addWidget(self.explorerPill, 0, Qt.AlignmentFlag.AlignVCenter)
        editorRowLayout.addSpacing(8)
        editorRowLayout.addWidget(self.explorerPanel, 0)

        self.actionBar = QFrame(self.editorPage)
        self.actionBar.setObjectName(u"actionBar")
        self.actionBar.setFixedHeight(50)
        actionLayout = QHBoxLayout(self.actionBar)
        actionLayout.setContentsMargins(16, 0, 14, 0)
        actionLayout.setSpacing(10)
        self.pathLabel = QLabel(self.actionBar)
        self.pathLabel.setObjectName(u"pathLabel")
        self.statusLabel = QLabel(self.actionBar)
        self.statusLabel.setObjectName(u"statusLabel")
        statusFont = QFont()
        statusFont.setFamilies([u"Segoe UI Symbol", u"Segoe UI"])
        statusFont.setPixelSize(13)
        self.statusLabel.setFont(statusFont)
        self.statusLabel.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.statusLabel.setFixedWidth(18)
        self.injectButton = QPushButton(self.actionBar)
        self.injectButton.setObjectName(u"injectButton")
        self.injectButton.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.injectButton.setCursor(Qt.CursorShape.PointingHandCursor)
        self.injectButton.setToolTip(u"Inject")
        self.executeButton = QPushButton(self.actionBar)
        self.executeButton.setObjectName(u"executeButton")
        self.executeButton.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.executeButton.setCursor(Qt.CursorShape.PointingHandCursor)
        self.executeButton.setToolTip(u"Execute")
        actionLayout.addWidget(self.pathLabel)
        actionLayout.addStretch()
        actionLayout.addWidget(self.statusLabel)
        actionLayout.addWidget(self.injectButton)
        actionLayout.addWidget(self.executeButton)

        editorPageLayout.addWidget(self.tabStrip)
        editorPageLayout.addWidget(self.editorRow, 1)
        editorPageLayout.addWidget(self.actionBar)

        self.settingsPage = QWidget(self.mainStack)
        self.settingsPage.setObjectName(u"settingsPage")
        settingsPageLayout = QVBoxLayout(self.settingsPage)
        settingsPageLayout.setContentsMargins(32, 28, 32, 36)
        settingsPageLayout.setSpacing(0)
        self.pageTitle = QLabel(self.settingsPage)
        self.pageTitle.setObjectName(u"pageTitle")
        self.pageTitle.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        settingsPageLayout.addWidget(self.pageTitle, 0, Qt.AlignmentFlag.AlignLeft)
        settingsPageLayout.addSpacing(22)

        self.settingsList = QWidget(self.settingsPage)
        self.settingsList.setObjectName(u"settingsList")
        settingsListLayout = QVBoxLayout(self.settingsList)
        settingsListLayout.setContentsMargins(0, 0, 0, 0)
        settingsListLayout.setSpacing(10)
        settingsListLayout.setAlignment(Qt.AlignmentFlag.AlignTop)

        self.settingCard = QFrame(self.settingsList)
        self.settingCard.setObjectName(u"settingCard")
        cardLayout = QHBoxLayout(self.settingCard)
        cardLayout.setContentsMargins(18, 16, 18, 16)
        cardLayout.setSpacing(24)
        cardText = QWidget(self.settingCard)
        cardText.setObjectName(u"settingCardText")
        cardTextLayout = QVBoxLayout(cardText)
        cardTextLayout.setContentsMargins(0, 0, 0, 0)
        cardTextLayout.setSpacing(3)
        self.cardTitle = QLabel(cardText)
        self.cardTitle.setObjectName(u"cardTitle")
        self.cardDesc = QLabel(cardText)
        self.cardDesc.setObjectName(u"cardDesc")
        self.cardDesc.setWordWrap(True)
        cardTextLayout.addWidget(self.cardTitle)
        cardTextLayout.addWidget(self.cardDesc)
        cardLayout.addWidget(cardText, 1)
        self.cardBadge = QLabel(self.settingCard)
        self.cardBadge.setObjectName(u"cardBadge")
        self.cardBadge.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        self.cardBadge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        cardLayout.addWidget(self.cardBadge, 0, Qt.AlignmentFlag.AlignVCenter)
        settingsListLayout.addWidget(self.settingCard)
        self.settingsList.setFixedWidth(640)
        settingsPageLayout.addWidget(self.settingsList)
        settingsPageLayout.addStretch()

        self.mainStack.addWidget(self.editorPage)
        self.mainStack.addWidget(self.settingsPage)
        rightAreaLayout.addWidget(self.titlebar)
        rightAreaLayout.addWidget(self.mainStack, 1)

        rootLayout.addWidget(self.iconRail)
        rootLayout.addWidget(self.rightArea, 1)

        MainWindow.setCentralWidget(self.centralwidget)

        self.settingsMenu = QMenu(MainWindow)
        self.settingsMenu.addAction(self.actionNewTab)
        self.settingsMenu.addAction(self.actionSaveTabs)
        self.settingsMenu.addSeparator()
        self.settingsMenu.addAction(self.actionImport)
        self.settingsMenu.addAction(self.actionExport)
        self.settingsMenu.addSeparator()
        self.settingsMenu.addAction(self.actionClearTabs)
        self.settingsMenu.addSeparator()
        self.settingsMenu.addAction(self.actionTopMost)
        self.settingsMenu.addAction(self.actionExitAltF4)

        MainWindow.setStyleSheet(style)

        self.retranslateUi(MainWindow)

        QMetaObject.connectSlotsByName(MainWindow)

    def retranslateUi(self, MainWindow):
        MainWindow.setWindowTitle(QCoreApplication.translate("MainWindow", u"Funny Executor", None))
        self.actionExitAltF4.setText(QCoreApplication.translate("MainWindow", u"Exit", None))
        self.actionInject.setText(QCoreApplication.translate("MainWindow", u"Inject", None))
        self.actionExecute.setText(QCoreApplication.translate("MainWindow", u"Execute", None))
        self.actionExport.setText(QCoreApplication.translate("MainWindow", u"Export...", None))
        self.actionImport.setText(QCoreApplication.translate("MainWindow", u"Import...", None))
        self.actionInfo.setText(QCoreApplication.translate("MainWindow", u"Info", None))
        self.actionSaveTabs.setText(QCoreApplication.translate("MainWindow", u"Save Tabs", None))
        self.actionNewTab.setText(QCoreApplication.translate("MainWindow", u"New Tab", None))
        self.actionClearTabs.setText(QCoreApplication.translate("MainWindow", u"Clear Tabs", None))
        self.actionBtools.setText(QCoreApplication.translate("MainWindow", u"F3X", None))
        self.actionTopMost.setText(QCoreApplication.translate("MainWindow", u"On Top", None))
        self.windowTitle.setText(QCoreApplication.translate("MainWindow", u"Funny Executor", None))
        self.searchEdit.setPlaceholderText(QCoreApplication.translate("MainWindow", u"Search", None))
        self.panelTitle.setText(QCoreApplication.translate("MainWindow", u"FILES", None))
        self.pathLabel.setText(QCoreApplication.translate("MainWindow", u"Funny Executor", None))
        self.statusLabel.setText(QCoreApplication.translate("MainWindow", u"\u2b24", None))
        self.injectButton.setText(QCoreApplication.translate("MainWindow", u"Inject", None))
        self.executeButton.setText(QCoreApplication.translate("MainWindow", u"Execute", None))
        self.pageTitle.setText(QCoreApplication.translate("MainWindow", u"Settings", None))
        self.cardTitle.setText(QCoreApplication.translate("MainWindow", u"Coming soon", None))
        self.cardDesc.setText(QCoreApplication.translate("MainWindow", u"More settings are still being worked on. For now, right-click the settings button in the rail for quick actions.", None))
        self.cardBadge.setText(QCoreApplication.translate("MainWindow", u"SOON", None))
