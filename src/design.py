from PySide6.QtCore import QCoreApplication, QMetaObject, QSize, QByteArray, Qt
from PySide6.QtGui import QAction, QFont, QIcon, QPixmap, QPainter
from PySide6.QtSvg import QSvgRenderer
from PySide6.QtWidgets import (QFrame, QHBoxLayout, QLabel, QLineEdit, QMainWindow,
    QMenu, QPushButton, QStackedWidget, QTabBar, QTreeWidget, QVBoxLayout, QWidget)

railBg = "#0f0f0f"
panelBg = "#131313"
divider = "#1e1e1e"
textDim = "#8a8a8a"
textActive = "#e6e6e6"

class Icons:
    execute = """<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="white" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M5 5a2 2 0 0 1 3.008-1.728l11.997 6.998a2 2 0 0 1 .003 3.458l-12 7A2 2 0 0 1 5 19z"/></svg>"""

    newTab = """<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="white" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M5 12h14"/><path d="M12 5v14"/></svg>"""

    file = """<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="white" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M4 12.15V4a2 2 0 0 1 2-2h8a2.4 2.4 0 0 1 1.706.706l3.588 3.588A2.4 2.4 0 0 1 20 8v12a2 2 0 0 1-2 2h-3.35"/><path d="M14 2v5a1 1 0 0 0 1 1h5"/><path d="m5 16-3 3 3 3"/><path d="m9 22 3-3-3-3"/></svg>"""

    folder = """<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="white" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M20 20a2 2 0 0 0 2-2V8a2 2 0 0 0-2-2h-7.9a2 2 0 0 1-1.69-.9L9.6 3.9A2 2 0 0 0 7.93 3H4a2 2 0 0 0-2 2v13a2 2 0 0 0 2 2Z"/></svg>"""

    inject = """<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="white" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="m16 6-8.414 8.586a2 2 0 0 0 2.829 2.829l8.414-8.586a4 4 0 1 0-5.657-5.657l-8.379 8.551a6 6 0 1 0 8.485 8.485l8.379-8.551"/></svg>"""

    editorTab = """<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="white" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect width="18" height="18" x="3" y="3" rx="2"/><path d="M7 8h8"/><path d="M7 12h10"/><path d="M7 16h6"/></svg>"""

    settingsTab = """<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="white" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="lucide lucide-settings preview-icon"><path d="M9.671 4.136a2.34 2.34 0 0 1 4.659 0 2.34 2.34 0 0 0 3.319 1.915 2.34 2.34 0 0 1 2.33 4.033 2.34 2.34 0 0 0 0 3.831 2.34 2.34 0 0 1-2.33 4.033 2.34 2.34 0 0 0-3.319 1.915 2.34 2.34 0 0 1-4.659 0 2.34 2.34 0 0 0-3.32-1.915 2.34 2.34 0 0 1-2.33-4.033 2.34 2.34 0 0 0 0-3.831A2.34 2.34 0 0 1 6.35 6.051a2.34 2.34 0 0 0 3.319-1.915"/><circle cx="12" cy="12" r="3"/></svg>"""

    exitIcon = """<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="white" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="lucide lucide-x preview-icon"><path d="M18 6 6 18"/><path d="m6 6 12 12"/></svg>"""

    minimizeIcon = """<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="white" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="lucide lucide-minus preview-icon"><path d="M5 12h14"/></svg>"""

    resizeIcon = """<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="white" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="lucide lucide-square preview-icon"><rect width="18" height="18" x="3" y="3" rx="2"/></svg>"""

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


style = """
#centralwidget { background-color: #131313; }
#iconRail { background-color: #0f0f0f; border-right: 1px solid #1e1e1e; }
#sidebar { background-color: #131313; border-right: 1px solid #1e1e1e; }
#tabStrip { background-color: #0f0f0f; border-bottom: 1px solid #1e1e1e; }
#breadcrumb { background-color: #131313; border-bottom: 1px solid #1e1e1e; }
#editorStack { background-color: #131313; }
#editorPage, #settingsPage, #mainStack { background-color: #131313; }

#soonLabel { color: #383838; }

#pathLabel { color: #6f6f6f; font-size: 12px; }

QToolTip { background-color: #1b1b1b; color: #d0d0d0; border: 1px solid #2a2a2a; }

#iconRail QPushButton, #newTabButton, #breadcrumb QPushButton {
    background: transparent; border: none; border-radius: 6px;
}
#iconRail QPushButton:hover, #newTabButton:hover, #breadcrumb QPushButton:hover {
    background-color: #1e1e1e;
}
#iconRail QPushButton:checked { background-color: #1e1e1e; }
#iconRail QPushButton[active="true"] { background-color: #1e1e1e; }
#iconRail QPushButton[active="true"]:hover { background-color: #1e1e1e; }
#yellowBtn, #greenBtn, #redBtn {
    background: transparent; border: none; border-radius: 4px;
}
#yellowBtn:hover, #greenBtn:hover, #redBtn:hover { background-color: #1e1e1e; }
#yellowBtn:pressed, #greenBtn:pressed, #redBtn:pressed { background-color: #2a2a2a; }
#yellowBtn:checked, #greenBtn:checked, #redBtn:checked { background-color: transparent; }

QLineEdit#searchEdit {
    background-color: #1a1a1a; border: 1px solid #1e1e1e; border-radius: 6px;
    color: #cfcfcf; padding-left: 8px; selection-background-color: #2a2a2a;
}

QTreeWidget#scriptTree {
    background-color: #131313; border: none; outline: 0;
    color: #9a9a9a; font-size: 12px;
}
QTreeWidget#scriptTree::item { height: 30px; border: none; }
QTreeWidget#scriptTree::item:hover {
    color: #ffffff; background-color: #1e1e1e; border: none; border-radius: 4px;
}
QTreeWidget#scriptTree::item:selected {
    color: #ffffff; background-color: #1e1e1e; border: none; border-radius: 4px;
}
QTreeWidget#scriptTree::item:selected:hover {
    color: #ffffff; background-color: #1e1e1e; border: none; border-radius: 4px;
}

QTabBar#tabBar { qproperty-drawBase: 0; }
QTabBar#tabBar::tab {
    background-color: #0f0f0f; color: #8a8a8a;
    padding: 9px 16px; border: none; border-right: 1px solid #1e1e1e;
}
QTabBar#tabBar::tab:selected { background-color: #131313; color: #e6e6e6; }
QTabBar#tabBar::tab:hover { color: #cfcfcf; }

QMenu { background-color: #1b1b1b; color: #d0d0d0; border: 1px solid #2a2a2a; padding: 4px; }
QMenu::item { padding: 6px 22px; border-radius: 4px; }
QMenu::item:selected { background-color: #2a2a2a; }
QMenu::separator { height: 1px; background-color: #2a2a2a; margin: 4px 6px; }

QScrollBar:vertical { background: transparent; width: 10px; margin: 0; }
QScrollBar::handle:vertical { background-color: #2a2a2a; border-radius: 5px; min-height: 24px; }
QScrollBar::handle:vertical:hover { background-color: #3a3a3a; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical { background: transparent; }
QScrollBar:horizontal { background: transparent; height: 10px; margin: 0; }
QScrollBar::handle:horizontal { background-color: #2a2a2a; border-radius: 5px; min-width: 24px; }
QScrollBar::handle:horizontal:hover { background-color: #3a3a3a; }
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal { width: 0; }
QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal { background: transparent; }
"""


class Ui_MainWindow(object):
    def setupUi(self, MainWindow):
        if not MainWindow.objectName():
            MainWindow.setObjectName(u"MainWindow")
        MainWindow.resize(1070, 615)
        MainWindow.setMinimumSize(QSize(1200, 600))

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
        self.centralwidget.setObjectName(u"centralwidget")
        rootLayout = QHBoxLayout(self.centralwidget)
        rootLayout.setContentsMargins(0, 0, 0, 0)
        rootLayout.setSpacing(0)

        self.iconRail = QFrame(self.centralwidget)
        self.iconRail.setObjectName(u"iconRail")
        self.iconRail.setFixedWidth(64)
        railLayout = QVBoxLayout(self.iconRail)
        railLayout.setContentsMargins(14, 14, 14, 14)
        railLayout.setSpacing(12)

        self.editorNavBtn = QPushButton(self.iconRail)
        self.editorNavBtn.setObjectName(u"editorNavBtn")
        self.editorNavBtn.setFixedSize(36, 36)
        self.editorNavBtn.setCheckable(True)
        self.editorNavBtn.setChecked(True)
        self.editorNavBtn.setToolTip(u"Editor")
        self.editorNavBtn.setIcon(navIcon(Icons.editorTab))
        self.editorNavBtn.setIconSize(QSize(20, 20))

        self.filesNavBtn = QPushButton(self.iconRail)
        self.filesNavBtn.setObjectName(u"filesNavBtn")
        self.filesNavBtn.setFixedSize(36, 36)
        self.filesNavBtn.setCheckable(True)
        self.filesNavBtn.setToolTip(u"File Explorer")
        self.filesNavBtn.setIcon(navIcon(Icons.folder))
        self.filesNavBtn.setIconSize(QSize(20, 20))

        self.settingsNavBtn = QPushButton(self.iconRail)
        self.settingsNavBtn.setObjectName(u"settingsNavBtn")
        self.settingsNavBtn.setFixedSize(36, 36)
        self.settingsNavBtn.setCheckable(True)
        self.settingsNavBtn.setToolTip(u"Settings")
        self.settingsNavBtn.setIcon(navIcon(Icons.settingsTab))
        self.settingsNavBtn.setIconSize(QSize(20, 20))

        railLayout.addWidget(self.editorNavBtn, 0, Qt.AlignmentFlag.AlignHCenter)
        railLayout.addWidget(self.filesNavBtn, 0, Qt.AlignmentFlag.AlignHCenter)
        railLayout.addStretch()
        railLayout.addWidget(self.settingsNavBtn, 0, Qt.AlignmentFlag.AlignHCenter)

        self.sidebar = QFrame(self.centralwidget)
        self.sidebar.setObjectName(u"sidebar")
        self.sidebar.setFixedWidth(246)
        sideLayout = QVBoxLayout(self.sidebar)
        sideLayout.setContentsMargins(10, 12, 10, 10)
        sideLayout.setSpacing(8)
        self.searchEdit = QLineEdit(self.sidebar)
        self.searchEdit.setObjectName(u"searchEdit")
        self.searchEdit.setFixedHeight(30)
        self.scriptTree = QTreeWidget(self.sidebar)
        self.scriptTree.setObjectName(u"scriptTree")
        self.scriptTree.setHeaderHidden(True)
        self.scriptTree.setIndentation(14)
        sideLayout.addWidget(self.searchEdit)
        sideLayout.addWidget(self.scriptTree)

        self.rightPanel = QWidget(self.centralwidget)
        self.rightPanel.setObjectName(u"rightPanel")
        rightLayout = QVBoxLayout(self.rightPanel)
        rightLayout.setContentsMargins(0, 0, 0, 0)
        rightLayout.setSpacing(0)

        self.mainStack = QStackedWidget(self.rightPanel)
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
        stripLayout.setContentsMargins(0, 0, 10, 0)
        stripLayout.setSpacing(6)
        self.tabBar = QTabBar(self.tabStrip)
        self.tabBar.setObjectName(u"tabBar")
        self.tabBar.setTabsClosable(True)
        self.tabBar.setMovable(True)
        self.tabBar.setExpanding(False)
        self.tabBar.setDrawBase(False)
        self.newTabButton = QPushButton(self.tabStrip)
        self.newTabButton.setObjectName(u"newTabButton")
        self.newTabButton.setFixedSize(30, 30)
        self.newTabButton.setToolTip(u"New Tab")
        self.newTabButton.setIcon(navIcon(Icons.newTab, 16))
        self.newTabButton.setIconSize(QSize(16, 16))
        stripLayout.addWidget(self.tabBar)
        stripLayout.addWidget(self.newTabButton)
        stripLayout.addStretch()

        self.yellowBtn = QPushButton(self.tabStrip)
        self.yellowBtn.setObjectName(u"yellowBtn")
        self.yellowBtn.setFixedSize(28, 28)
        self.yellowBtn.setCheckable(False)
        self.yellowBtn.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.yellowBtn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.yellowBtn.setToolTip(u"Minimize")
        self.yellowBtn.setIcon(navIcon(Icons.minimizeIcon, 16))
        self.yellowBtn.setIconSize(QSize(16, 16))

        self.greenBtn = QPushButton(self.tabStrip)
        self.greenBtn.setObjectName(u"greenBtn")
        self.greenBtn.setFixedSize(28, 28)
        self.greenBtn.setCheckable(False)
        self.greenBtn.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.greenBtn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.greenBtn.setToolTip(u"Maximize")
        self.greenBtn.setIcon(navIcon(Icons.resizeIcon, 16))
        self.greenBtn.setIconSize(QSize(16, 16))

        self.redBtn = QPushButton(self.tabStrip)
        self.redBtn.setObjectName(u"redBtn")
        self.redBtn.setFixedSize(28, 28)
        self.redBtn.setCheckable(False)
        self.redBtn.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.redBtn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.redBtn.setToolTip(u"Close")
        self.redBtn.setIcon(navIcon(Icons.exitIcon, 16))
        self.redBtn.setIconSize(QSize(16, 16))

        stripLayout.addWidget(self.yellowBtn)
        stripLayout.addWidget(self.greenBtn)
        stripLayout.addWidget(self.redBtn)

        self.breadcrumb = QFrame(self.editorPage)
        self.breadcrumb.setObjectName(u"breadcrumb")
        self.breadcrumb.setFixedHeight(46)
        crumbLayout = QHBoxLayout(self.breadcrumb)
        crumbLayout.setContentsMargins(16, 0, 12, 0)
        crumbLayout.setSpacing(10)
        self.pathLabel = QLabel(self.breadcrumb)
        self.pathLabel.setObjectName(u"pathLabel")
        self.statusLabel = QLabel(self.breadcrumb)
        self.statusLabel.setObjectName(u"statusLabel")
        statusFont = QFont()
        statusFont.setPointSize(13)
        statusFont.setBold(True)
        self.statusLabel.setFont(statusFont)
        self.statusLabel.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.statusLabel.setFixedWidth(22)
        self.injectButton = QPushButton(self.breadcrumb)
        self.injectButton.setObjectName(u"injectButton")
        self.injectButton.setFixedSize(34, 30)
        self.injectButton.setToolTip(u"Inject")
        self.injectButton.setIcon(navIcon(Icons.inject, 18))
        self.injectButton.setIconSize(QSize(18, 18))
        self.executeButton = QPushButton(self.breadcrumb)
        self.executeButton.setObjectName(u"executeButton")
        self.executeButton.setFixedSize(34, 30)
        self.executeButton.setToolTip(u"Execute")
        self.executeButton.setIcon(navIcon(Icons.execute, 18, dim="#9fd6ab", active="#c8f0d1"))
        self.executeButton.setIconSize(QSize(18, 18))
        crumbLayout.addWidget(self.pathLabel)
        crumbLayout.addStretch()
        crumbLayout.addWidget(self.statusLabel)
        crumbLayout.addWidget(self.injectButton)
        crumbLayout.addWidget(self.executeButton)

        self.editorStack = QStackedWidget(self.editorPage)
        self.editorStack.setObjectName(u"editorStack")

        editorPageLayout.addWidget(self.tabStrip)
        editorPageLayout.addWidget(self.breadcrumb)
        editorPageLayout.addWidget(self.editorStack, 1)

        self.settingsPage = QWidget(self.mainStack)
        self.settingsPage.setObjectName(u"settingsPage")
        settingsPageLayout = QVBoxLayout(self.settingsPage)
        settingsPageLayout.setContentsMargins(0, 0, 0, 0)
        soonFont = QFont()
        soonFont.setPointSize(34)
        soonFont.setBold(True)
        soonFont.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, 3)
        self.soonLabel = QLabel(self.settingsPage)
        self.soonLabel.setObjectName(u"soonLabel")
        self.soonLabel.setFont(soonFont)
        self.soonLabel.setAlignment(Qt.AlignmentFlag.AlignCenter)
        settingsPageLayout.addWidget(self.soonLabel)

        self.mainStack.addWidget(self.editorPage)
        self.mainStack.addWidget(self.settingsPage)
        rightLayout.addWidget(self.mainStack)

        rootLayout.addWidget(self.iconRail)
        rootLayout.addWidget(self.sidebar)
        rootLayout.addWidget(self.rightPanel, 1)

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
        self.searchEdit.setPlaceholderText(QCoreApplication.translate("MainWindow", u"Search", None))
        self.pathLabel.setText(QCoreApplication.translate("MainWindow", u"Funny Executor", None))
        self.statusLabel.setText(QCoreApplication.translate("MainWindow", u"\u2b24", None))
        self.soonLabel.setText(QCoreApplication.translate("MainWindow", u"SOON!", None))
