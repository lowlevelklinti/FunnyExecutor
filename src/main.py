import json
import os.path
import shutil
import sys
import webbrowser

from design import Ui_MainWindow

from PySide6.QtCore import QTimer, Qt  # test
from PySide6.QtWidgets import QApplication, QMainWindow, QFileDialog
from extras import CodeEditor, MessageBox

import FAPI
import requests
import ctypes

executor: FAPI.Executor | None = None
sdk: FAPI.sdk.Roblox | None = None

def load_exec():
    global executor
    global sdk

    if FAPI.roblox_open():
        executor = FAPI.Executor()
        sdk = executor.sdk

def unload_exec():
    global executor
    global sdk

    executor, sdk = None, None

class Window(QMainWindow, Ui_MainWindow):
    def __init__(self):
        super().__init__()
        self.setupUi(self)

        self._injecting = False
        self._warned = False

        def inject():
            try:
                load_exec()
            except:
                unload_exec()

            if not executor:
                MessageBox.warning("Injection failed", "You must have Roblox open to inject")
                return

            if sdk.datamodel.name != 'Ugc':
                print(sdk.datamodel.name)
                MessageBox.warning("Injection failed", "You must be in-game to inject")
                return
            if executor.injected:
                MessageBox.information("Injection failed", "Already injected")
                return
            if self._injecting:
                return

            self._injecting = True
            executor.inject()
            self._injecting = False

        def execute():
            if not executor or not executor.injected:
                MessageBox.warning("Execution failed", "You must inject before executing")
                return

            script = self._get_current_editor().toPlainText()
            executor.execute(script)

        def update_status():
            if executor:
                if executor.injected:
                    self.statusLabel.setStyleSheet("color: rgb(50,200,50);")
                else:
                    self.statusLabel.setStyleSheet("color: rgb(200,50,50);")
            else:
                self.statusLabel.setStyleSheet("color: rgb(200,50,50);")

            self.statusLabel.update()

        def import_luau():
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

        def export_luau():
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

        self._tab_number = 0

        def new_tab(name=None, content=None):
            return self._add_tab(name, content)

        def close_tab(index):
            widget = self.tabWidget.widget(index)
            widget.deleteLater()
            self.tabWidget.removeTab(index)
            if self.tabWidget.count() == 0:
                self._tab_number = 1
                self._add_tab("Script #1")

        def load_script(fn):
            with open('scripts\\'+fn+'.lua', 'r', encoding='utf-8') as f:
                self.tabWidget.setCurrentIndex(new_tab(content=f.read()))

        def ontop():
            self.setWindowFlag(Qt.WindowType.WindowStaysOnTopHint, self.actionTop_Most.isChecked())
            self.show()  # cuz it hides the window for some reason

        self.injectButton.clicked.connect(inject)
        self.executeButton.clicked.connect(execute)

        self.importButton.clicked.connect(import_luau)
        self.exportButton.clicked.connect(export_luau)
        self.newTabButton.clicked.connect(lambda: self.tabWidget.setCurrentIndex(new_tab()))

        self.actionExit_Alt_F4.triggered.connect(QApplication.quit)
        self.actionExport.triggered.connect(export_luau)
        self.actionImport.triggered.connect(import_luau)
        self.actionInject.triggered.connect(inject)
        self.actionExecute.triggered.connect(execute)

        self.actionNew_Tab.triggered.connect(lambda: new_tab())
        self.actionSave_Tabs.triggered.connect(lambda: self._save_tabs())
        self.actionClear_Tabs.triggered.connect(self._clear_tabs)

        self.actionTop_Most.triggered.connect(ontop)

        self.tabWidget.tabCloseRequested.connect(close_tab)

        self._load_tabs()

        try:
            load_exec()
        except:
            unload_exec()

        update_status()
        ontop()

        timer_update = QTimer(self)
        timer_update.timeout.connect(update_status)
        timer_update.start(1000)

        timer_autosave = QTimer(self)
        timer_autosave.timeout.connect(self._save_tabs)
        timer_autosave.start(10000)

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
        editor = CodeEditor()

        if content is not None:
            editor.setPlainText(content)

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
    window.show()
    sys.exit(app.exec())