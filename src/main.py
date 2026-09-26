import json
import os.path
import shutil
import sys
import time
import psutil

from design import Ui_MainWindow, Icons, svgIcon, navIcon

from PySide6.QtCore import QTimer, Qt, QThread, QObject, Signal, Slot, QEvent
from PySide6.QtWidgets import QApplication, QMainWindow, QFileDialog, QSizeGrip, QTreeWidgetItem
from extras import CodeEditor, MessageBox, RpcManager

import FAPI

navDim = "#8a8a8a"
navActive = "#e6e6e6"

CLIENT_ID = "1553410003417960469"

class RobloxWorker(QObject):
    statusChanged = Signal(str)
    showMessage = Signal(str, str, str)

    def __init__(self):
        super().__init__()
        self.executor = None
        self.sdk = None
        self.injected = False
        self.queued = False
        self._injecting = False
        self._lastInjectTry = 0.0
        self._timer = None

    @Slot()
    def start(self):
        self._timer = QTimer()
        self._timer.timeout.connect(self.poll)
        self._timer.start(250)

    @Slot()
    def stop(self):
        if self._timer is not None:
            self._timer.stop()

    def ensureExecutor(self):
        if self.executor is not None and self.sdk is not None:
            try:
                if psutil.pid_exists(self.sdk.mem.process_id):
                    return True
            except:
                pass
            self.executor = None
            self.sdk = None

        try:
            if not FAPI.robloxOpen():
                self.executor = None
                self.sdk = None
                return False
        except:
            self.executor = None
            self.sdk = None
            return False

        try:
            self.executor = FAPI.Executor()
            self.sdk = self.executor.sdk
            return True
        except:
            self.executor = None
            self.sdk = None
            return False

    @Slot()
    def poll(self):
        if self._injecting:
            return

        if not self.ensureExecutor():
            self.queued = False
            self.injected = False
            self.statusChanged.emit('idle')
            return

        try:
            self.injected = self.executor.injected
        except:
            self.injected = False

        if self.injected:
            self.statusChanged.emit('injected')
        elif self.queued:
            self.statusChanged.emit('queued')
            self.tryInject()
        else:
            self.statusChanged.emit('idle')

    def tryInject(self):
        if self._injecting or self.injected:
            return

        try:
            if self.executor.injected:
                return
            dm = self.sdk.datamodel
            if not dm or dm.name != 'Ugc' or not dm.address:
                return
            if dm.address in self.executor._handledDms:
                return
            players = dm.findFirstChild('Players')
            if not players or not players.getChildren():
                return
        except:
            return

        if time.time() - self._lastInjectTry < 1.0:
            return

        self._lastInjectTry = time.time()
        self._injecting = True
        try:
            self.executor.inject()
        except Exception as e:
            print(e)
        finally:
            self._injecting = False

    @Slot()
    def requestInject(self):
        if not self.ensureExecutor():
            self.showMessage.emit('warning', 'Injection failed', 'You must have Roblox open to inject')
            return

        try:
            if self.executor.injected:
                self.showMessage.emit('information', 'Injection failed', 'Already injected')
                return
        except:
            pass

        self.queued = True
        self.tryInject()

    @Slot(str)
    def requestExecute(self, script):
        ready = False
        if self.executor is not None:
            try:
                ready = self.executor.injected
            except:
                ready = False

        if not ready:
            self.showMessage.emit('warning', 'Execution failed', 'You must inject before executing')
            return

        try:
            self.executor.execute(script)
        except Exception as e:
            print(e)

class Window(QMainWindow, Ui_MainWindow):
    injectRequested = Signal()
    executeRequested = Signal(str)

    def __init__(self):
        super().__init__()
        self.setupUi(self)

        self._tabNumber = 0
        self.sidebarVisible = True

        self.statusLabel.setStyleSheet("color: rgb(200,50,50);")

        self.sizeGrip = QSizeGrip(self)
        self.sizeGrip.resize(16, 16)

        self.iconRail.installEventFilter(self)
        self.breadcrumb.installEventFilter(self)
        self.tabStrip.installEventFilter(self)
        self.topBar.installEventFilter(self)

        self._thread = QThread(self)
        self._worker = RobloxWorker()
        self._worker.moveToThread(self._thread)
        self._worker.statusChanged.connect(self.onStatusChanged)
        self._worker.showMessage.connect(self.onShowMessage)
        self.injectRequested.connect(self._worker.requestInject)
        self.executeRequested.connect(self._worker.requestExecute)
        self._thread.started.connect(self._worker.start)

        self.injectButton.clicked.connect(self.onInject)
        self.executeButton.clicked.connect(self.onExecute)
        self.newTabButton.clicked.connect(self.onNewTab)

        self.redBtn.clicked.connect(self.close)
        self.yellowBtn.clicked.connect(self.showMinimized)
        self.greenBtn.clicked.connect(self._toggleMax)

        self.editorNavBtn.clicked.connect(self.onShowEditor)
        self.filesNavBtn.clicked.connect(self.onToggleSidebar)
        self.settingsNavBtn.clicked.connect(self.onShowSettings)
        self.settingsNavBtn.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.settingsNavBtn.customContextMenuRequested.connect(self.onSettingsMenu)

        self.scriptTree.itemDoubleClicked.connect(self._onTreeItemDoubleClicked)
        self.searchEdit.textChanged.connect(self._onSearch)

        self.actionExitAltF4.triggered.connect(QApplication.quit)
        self.actionExport.triggered.connect(self.exportLuau)
        self.actionImport.triggered.connect(self.importLuau)
        self.actionInject.triggered.connect(self.onInject)
        self.actionExecute.triggered.connect(self.onExecute)

        self.actionNewTab.triggered.connect(lambda: self.onNewTab())
        self.actionSaveTabs.triggered.connect(lambda: self._saveTabs())
        self.actionClearTabs.triggered.connect(self._clearTabs)

        self.actionTopMost.triggered.connect(self.onTop)

        self.actionExecute.setShortcut("Ctrl+Return")
        self.actionInject.setShortcut("Ctrl+I")
        self.actionNewTab.setShortcut("Ctrl+N")
        self.actionSaveTabs.setShortcut("Ctrl+S")
        self.actionImport.setShortcut("Ctrl+O")
        self.actionExport.setShortcut("Ctrl+Shift+S")
        for act in (self.actionExecute, self.actionInject, self.actionNewTab,
                    self.actionSaveTabs, self.actionImport, self.actionExport,
                    self.actionClearTabs, self.actionExitAltF4):
            self.addAction(act)

        self.tabBar.tabCloseRequested.connect(self.closeTab)
        self.tabBar.currentChanged.connect(self.onTabChanged)
        self.tabBar.tabMoved.connect(self._onTabMoved)

        self._refreshTree()

        self.applyNavState()

        self._loadTabs()
        self.attachCurrentEditor()

        self.onTop()

        self._thread.start()

        self._rpcManager = RpcManager(CLIENT_ID, pollInterval=5.0)
        self._rpcManager.setExecutor(self._worker)

        discord_ok = self._rpcManager.discordPresent()
        settings = self._loadSettings()
        rpc_enabled = bool(settings.get('rpcEnabled', False)) and discord_ok
        self.rpcSwitch.setEnabled(discord_ok)
        self.rpcSwitch.toggled.connect(self._onRpcToggled)
        self.rpcSwitch.setChecked(rpc_enabled)
        if discord_ok:
            self.rpcSwitch.setToolTip("Show what you're doing on Discord")
        else:
            self.rpcSwitch.setToolTip("Discord not detected — start Discord to enable Rich Presence")
        self._rpcManager.setEnabled(rpc_enabled)
        self._rpcManager.start()

        self._autosaveTimer = QTimer(self)
        self._autosaveTimer.timeout.connect(self._saveTabs)
        self._autosaveTimer.start(10000)

    def eventFilter(self, obj, event):
        if obj in (self.iconRail, self.breadcrumb, self.tabStrip, self.topBar) and event.type() == QEvent.Type.MouseButtonPress:
            if event.button() == Qt.MouseButton.LeftButton:
                handle = self.windowHandle()
                if handle is not None:
                    handle.startSystemMove()
        return super().eventFilter(obj, event)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.sizeGrip.move(self.width() - self.sizeGrip.width(), self.height() - self.sizeGrip.height())
        self.sizeGrip.raise_()

    def _toggleMax(self):
        if self.isMaximized():
            self.showNormal()
        else:
            self.showMaximized()

    def onShowEditor(self):
        self.mainStack.setCurrentWidget(self.editorPage)
        self.applyNavState()

    def onShowSettings(self):
        self.mainStack.setCurrentWidget(self.settingsPage)
        self.applyNavState()

    def onToggleSidebar(self):
        self.sidebarVisible = not self.sidebarVisible
        self.sidebar.setVisible(self.sidebarVisible)
        self.applyNavState()

    def setNavIcon(self, button, svg, active):
        base = navActive if active else navDim
        button.setIcon(navIcon(svg, 20, dim=base, active=navActive))
        button.setChecked(active)
        button.setProperty('active', 'true' if active else 'false')
        button.style().unpolish(button)
        button.style().polish(button)

    def applyNavState(self):
        showingSettings = self.mainStack.currentWidget() is self.settingsPage
        self.setNavIcon(self.editorNavBtn, Icons.editorTab, not showingSettings)
        self.setNavIcon(self.filesNavBtn, Icons.folder, self.sidebarVisible)
        self.setNavIcon(self.settingsNavBtn, Icons.settingsTab, showingSettings)

    def onSettingsMenu(self, pos):
        self.settingsMenu.exec(self.settingsNavBtn.mapToGlobal(pos))

    def _refreshTree(self):
        self.scriptTree.clear()
        folderIcon = svgIcon(Icons.folder, "#9a9a9a", 16)
        fileIcon = svgIcon(Icons.file, "#9a9a9a", 16)
        for label, folder in (("Scripts", scriptsDir), ("Auto-Execute", autoexecDir), ("Workspace", workspaceDir)):
            node = QTreeWidgetItem(self.scriptTree, [label])
            node.setIcon(0, folderIcon)
            node.setData(0, Qt.ItemDataRole.UserRole, None)
            try:
                os.makedirs(folder, exist_ok=True)
                for name in sorted(os.listdir(folder)):
                    full = os.path.join(folder, name)
                    if os.path.isfile(full):
                        child = QTreeWidgetItem(node, [name])
                        child.setIcon(0, fileIcon)
                        child.setData(0, Qt.ItemDataRole.UserRole, full)
            except:
                pass
        self.scriptTree.expandAll()

    def _onTreeItemDoubleClicked(self, item, column):
        path = item.data(0, Qt.ItemDataRole.UserRole)
        if not path:
            return
        try:
            with open(path, 'r', encoding='utf-8') as f:
                content = f.read()
        except:
            return
        index = self._addTab(os.path.basename(path), content)
        self.tabBar.setCurrentIndex(index)

    def _onSearch(self, text):
        query = text.lower().strip()
        for i in range(self.scriptTree.topLevelItemCount()):
            node = self.scriptTree.topLevelItem(i)
            visibleChildren = 0
            for j in range(node.childCount()):
                child = node.child(j)
                match = query in child.text(0).lower()
                child.setHidden(bool(query) and not match)
                if not child.isHidden():
                    visibleChildren += 1
            node.setHidden(bool(query) and visibleChildren == 0)

    @Slot(str)
    def onStatusChanged(self, state):
        if state == 'injected':
            self.statusLabel.setStyleSheet("color: rgb(50,200,50);")
        elif state == 'queued':
            self.statusLabel.setStyleSheet("color: rgb(255,165,0);")
        else:
            self.statusLabel.setStyleSheet("color: rgb(200,50,50);")

    @Slot(str, str, str)
    def onShowMessage(self, kind, title, text):
        if kind == 'information':
            MessageBox.information(title, text)
        else:
            MessageBox.warning(title, text)

    def onInject(self):
        self.injectRequested.emit()

    def onExecute(self):
        editor = self._getCurrentEditor()
        if editor is None:
            return
        self.executeRequested.emit(editor.toPlainText())

    def onNewTab(self):
        index = self._addTab()
        self.tabBar.setCurrentIndex(index)

    def onTabChanged(self, index):
        if index < 0:
            return
        self.editorStack.setCurrentIndex(index)
        editor = self.editorStack.widget(index)
        if editor is not None:
            editor.attachHighlighter()
        self._updateBreadcrumb()

    def _onTabMoved(self, frm, to):
        widget = self.editorStack.widget(frm)
        if widget is None:
            return
        self.editorStack.removeWidget(widget)
        self.editorStack.insertWidget(to, widget)
        self.editorStack.setCurrentIndex(self.tabBar.currentIndex())

    def _updateBreadcrumb(self):
        index = self.tabBar.currentIndex()
        name = self.tabBar.tabText(index) if index >= 0 else ""
        if name:
            self.pathLabel.setText(u"Funny Executor  \u203a  " + name)
        else:
            self.pathLabel.setText(u"Funny Executor")

    def attachCurrentEditor(self):
        editor = self.editorStack.currentWidget()
        if editor is not None:
            editor.attachHighlighter()

    def onTop(self):
        flags = Qt.WindowType.Window | Qt.WindowType.FramelessWindowHint
        if self.actionTopMost.isChecked():
            flags |= Qt.WindowType.WindowStaysOnTopHint
        self.setWindowFlags(flags)
        self.show()

    def importLuau(self):
        filePath, _ = QFileDialog.getOpenFileName(
            self,
            "Open File",
            "",
            "Luau Script (*.luau; *.lua);;All Files (*)"
        )
        editor = self._getCurrentEditor()

        if filePath and editor:
            with open(filePath, 'r', encoding='utf-8') as f:
                editor.setPlainText(f.read())

    def exportLuau(self):
        filePath, _ = QFileDialog.getSaveFileName(
            self,
            "Save File",
            "",
            "Luau source files (*.lua; *.luau);;All Files (*)"
        )
        editor = self._getCurrentEditor()

        if filePath and editor:
            with open(filePath, 'w', encoding='utf-8') as f:
                f.write(editor.toPlainText())
            self._refreshTree()

    def closeTab(self, index):
        widget = self.editorStack.widget(index)
        if widget is not None:
            self.editorStack.removeWidget(widget)
            widget.deleteLater()
        self.tabBar.removeTab(index)
        if self.tabBar.count() == 0:
            self._tabNumber = 1
            newIndex = self._addTab("Script #1")
            self.tabBar.setCurrentIndex(newIndex)

    def _shutdownWorker(self):
        if hasattr(self, '_rpcManager'):
            self._rpcManager.stop()
        self._worker.stop()
        self._thread.quit()
        self._thread.wait(3000)

    def _onRpcToggled(self, checked):
        if hasattr(self, '_rpcManager'):
            self._rpcManager.setEnabled(self.rpcSwitch.isChecked())
            self._saveSetting('rpcEnabled', self.rpcSwitch.isChecked())

    def _loadSettings(self):
        try:
            with open(appData + '\\settings.json', 'r', encoding='utf-8') as f:
                return json.loads(f.read())
        except Exception:
            return {}

    def _saveSetting(self, key, value):
        data = self._loadSettings()
        data[key] = value
        try:
            with open(appData + '\\settings.json', 'w', encoding='utf-8') as f:
                f.write(json.dumps(data))
        except Exception:
            pass

    def _saveTabs(self):
        data = [self._tabNumber]
        for i in range(self.tabBar.count()):
            editor = self.editorStack.widget(i)
            data.append([
                self.tabBar.tabText(i),
                editor.toPlainText() if editor is not None else ""
            ])

        with open(appData+'\\tabs.json', 'w', encoding='utf-8') as f:
            f.write(json.dumps(data))

    def _clearTabs(self):
        if MessageBox.question(
                'FunnyExecutor',
                'Are you sure you want to clear all of your tabs? This action cannot be undone.',
                MessageBox.StandardButton.Yes | MessageBox.StandardButton.No
        ) == MessageBox.StandardButton.Yes:
            for i in reversed(range(self.editorStack.count())):
                widget = self.editorStack.widget(i)
                self.editorStack.removeWidget(widget)
                widget.deleteLater()
            while self.tabBar.count() > 0:
                self.tabBar.removeTab(0)
            self._tabNumber = 1
            newIndex = self._addTab("Script #1")
            self.tabBar.setCurrentIndex(newIndex)

    def _addTab(self, name=None, content=None):
        editor = CodeEditor(content)

        if name is None:
            self._tabNumber += 1
            name = f'Script #{self._tabNumber}'

        self.editorStack.addWidget(editor)
        return self.tabBar.addTab(name)

    def _loadTabs(self):
        if os.path.exists(appData+'\\tabs.json'):
            with open(appData+'\\tabs.json', 'r', encoding='utf-8') as f:
                data = json.loads(f.read())
                self._tabNumber = data.pop(0)
                for i in data:
                    self._addTab(i[0], i[1])
        else:
            self._addTab()

        if self.tabBar.count() > 0:
            self.tabBar.setCurrentIndex(0)
            self.onTabChanged(0)

    def closeEvent(self, event):
        answer = MessageBox.question(
            "Quit",
            "Are you sure you want to quit?",
            MessageBox.StandardButton.Yes | MessageBox.StandardButton.No
        )
        if answer == MessageBox.StandardButton.Yes:
            self._saveTabs()
            self._shutdownWorker()
            event.accept()
        else:
            event.ignore()

    def _getCurrentEditor(self):
        return self.editorStack.currentWidget()

appData = os.environ['APPDATA']+'\\FunnyExecutor'
scriptsDir = appData+'\\scripts'
autoexecDir = appData+'\\autoexec'
workspaceDir = appData+'\\workspace'

if __name__ == '__main__':

    if not os.path.exists(appData):
        os.mkdir(appData)

    for sub in (scriptsDir, autoexecDir, workspaceDir):
        os.makedirs(sub, exist_ok=True)

    if os.path.exists('tabs.json'):
        shutil.copy('tabs.json', appData + '\\tabs.json')
        os.remove('tabs.json')

    sys.argv += ['-platform', 'windows:darkmode=2']
    app = QApplication(sys.argv)
    app.styleHints().setColorScheme(Qt.ColorScheme.Dark)

    window = Window()
    app.aboutToQuit.connect(window._shutdownWorker)
    window.show()
    sys.exit(app.exec())
