import json
import os.path
import shutil
import sys
import time
import psutil

from design import Ui_MainWindow

from PySide6.QtCore import QTimer, Qt, QThread, QObject, Signal, Slot
from PySide6.QtWidgets import QApplication, QMainWindow, QFileDialog
from extras import CodeEditor, MessageBox

import FAPI

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
            if not FAPI.roblox_open():
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
            if dm.address in self.executor._handled_dms:
                return
            players = dm.find_first_child('Players')
            if not players or not players.get_children():
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

        self._tab_number = 0

        self.statusLabel.setStyleSheet("color: rgb(200,50,50);")

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
        self.importButton.clicked.connect(self.importLuau)
        self.exportButton.clicked.connect(self.exportLuau)
        self.newTabButton.clicked.connect(self.onNewTab)

        self.actionExit_Alt_F4.triggered.connect(QApplication.quit)
        self.actionExport.triggered.connect(self.exportLuau)
        self.actionImport.triggered.connect(self.importLuau)
        self.actionInject.triggered.connect(self.onInject)
        self.actionExecute.triggered.connect(self.onExecute)

        self.actionNew_Tab.triggered.connect(lambda: self._add_tab())
        self.actionSave_Tabs.triggered.connect(lambda: self._save_tabs())
        self.actionClear_Tabs.triggered.connect(self._clear_tabs)

        self.actionTop_Most.triggered.connect(self.onTop)

        self.tabWidget.tabCloseRequested.connect(self.closeTab)
        self.tabWidget.currentChanged.connect(self.onTabChanged)

        self._load_tabs()
        self.attachCurrentEditor()

        self.onTop()

        self._thread.start()

        self._autosaveTimer = QTimer(self)
        self._autosaveTimer.timeout.connect(self._save_tabs)
        self._autosaveTimer.start(10000)

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
        editor = self._get_current_editor()
        if editor is None:
            return
        self.executeRequested.emit(editor.toPlainText())

    def onNewTab(self):
        self.tabWidget.setCurrentIndex(self._add_tab())

    def onTabChanged(self, index):
        if index < 0:
            return
        editor = self.tabWidget.widget(index)
        if editor is not None:
            editor.attachHighlighter()

    def attachCurrentEditor(self):
        editor = self.tabWidget.currentWidget()
        if editor is not None:
            editor.attachHighlighter()

    def onTop(self):
        self.setWindowFlag(Qt.WindowType.WindowStaysOnTopHint, self.actionTop_Most.isChecked())
        self.show()

    def importLuau(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Open File",
            "",
            "Luau Script (*.luau; *.lua);;All Files (*)"
        )
        editor = self._get_current_editor()

        if file_path and editor:
            with open(file_path, 'r', encoding='utf-8') as f:
                editor.setPlainText(f.read())

    def exportLuau(self):
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Save File",
            "",
            "Luau source files (*.lua; *.luau);;All Files (*)"
        )
        editor = self._get_current_editor()

        if file_path and editor:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(editor.toPlainText())

    def closeTab(self, index):
        widget = self.tabWidget.widget(index)
        widget.deleteLater()
        self.tabWidget.removeTab(index)
        if self.tabWidget.count() == 0:
            self._tab_number = 1
            self._add_tab("Script #1")

    def _shutdownWorker(self):
        self._worker.stop()
        self._thread.quit()
        self._thread.wait(3000)

    def _save_tabs(self):
        data = [self._tab_number]
        for i in range(self.tabWidget.count()):
            data.append([
                self.tabWidget.tabText(i),
                self.tabWidget.widget(i).toPlainText()
            ])

        with open(appdata+'\\tabs.json', 'w', encoding='utf-8') as f:
            f.write(json.dumps(data))

    def _clear_tabs(self):
        if MessageBox.question(
                'FunnyExecutor',
                'Are you sure you want to clear all of your tabs? This action is irreversible',
                MessageBox.StandardButton.Yes | MessageBox.StandardButton.No
        ) == MessageBox.StandardButton.Yes:
            self.tabWidget.clear()
            self._tab_number = 1
            self._add_tab("Script #1")

    def _add_tab(self, name=None, content=None):
        editor = CodeEditor(content)

        if name is None:
            self._tab_number += 1
            name = f'Script #{self._tab_number}'

        return self.tabWidget.addTab(editor, name)

    def _load_tabs(self):
        if os.path.exists(appdata+'\\tabs.json'):
            with open(appdata+'\\tabs.json', 'r', encoding='utf-8') as f:
                data = json.loads(f.read())
                self._tab_number = data.pop(0)
                for i in data:
                    self._add_tab(i[0], i[1])
        else:
            self._add_tab()

    def closeEvent(self, event):
        answer = MessageBox.question(
            "Quit",
            "Are you sure you want to quit?",
            MessageBox.StandardButton.Yes | MessageBox.StandardButton.No
        )
        if answer == MessageBox.StandardButton.Yes:
            self._save_tabs()
            self._shutdownWorker()
            event.accept()
        else:
            event.ignore()

    def _get_current_editor(self):
        return self.tabWidget.currentWidget()

appdata = os.environ['APPDATA']+'\\FunnyExecutor'

if __name__ == '__main__':

    if not os.path.exists(appdata):
        os.mkdir(appdata)

    if os.path.exists('tabs.json'):
        shutil.copy('tabs.json', appdata + '\\tabs.json')
        os.remove('tabs.json')

    sys.argv += ['-platform', 'windows:darkmode=2']
    app = QApplication(sys.argv)
    app.styleHints().setColorScheme(Qt.ColorScheme.Dark)

    window = Window()
    app.aboutToQuit.connect(window._shutdownWorker)
    window.show()
    sys.exit(app.exec())
