# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'mainwindow.ui'
##
## Created by: Qt User Interface Compiler version 6.11.1
##
## WARNING! All changes made in this file will be lost when recompiling UI file!
################################################################################

from PySide6.QtCore import (QCoreApplication, QDate, QDateTime, QLocale,
    QMetaObject, QObject, QPoint, QRect,
    QSize, QTime, QUrl, Qt)
from PySide6.QtGui import (QAction, QBrush, QColor, QConicalGradient,
    QCursor, QFont, QFontDatabase, QGradient,
    QIcon, QImage, QKeySequence, QLinearGradient,
    QPainter, QPalette, QPixmap, QRadialGradient,
    QTransform)
from PySide6.QtWidgets import (QApplication, QLabel, QMainWindow, QMenu,
    QMenuBar, QPushButton, QSizePolicy, QTabWidget,
    QWidget)

class Ui_MainWindow(object):
    def setupUi(self, MainWindow):
        if not MainWindow.objectName():
            MainWindow.setObjectName(u"MainWindow")
        MainWindow.resize(841, 564)
        sizePolicy = QSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(MainWindow.sizePolicy().hasHeightForWidth())
        MainWindow.setSizePolicy(sizePolicy)
        MainWindow.setMinimumSize(QSize(841, 564))
        MainWindow.setMaximumSize(QSize(841, 564))
        self.actionExit_Alt_F4 = QAction(MainWindow)
        self.actionExit_Alt_F4.setObjectName(u"actionExit_Alt_F4")
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
        self.actionSave_Tabs = QAction(MainWindow)
        self.actionSave_Tabs.setObjectName(u"actionSave_Tabs")
        self.actionNew_Tab = QAction(MainWindow)
        self.actionNew_Tab.setObjectName(u"actionNew_Tab")
        self.actionClear_Tabs = QAction(MainWindow)
        self.actionClear_Tabs.setObjectName(u"actionClear_Tabs")
        self.actionInfYield = QAction(MainWindow)
        self.actionInfYield.setObjectName(u"actionInfYield")
        self.actionDex = QAction(MainWindow)
        self.actionDex.setObjectName(u"actionDex")
        self.actionBtools = QAction(MainWindow)
        self.actionBtools.setObjectName(u"actionBtools")
        self.actionTop_Most = QAction(MainWindow)
        self.actionTop_Most.setObjectName(u"actionTop_Most")
        self.actionTop_Most.setCheckable(True)
        self.actionTop_Most.setChecked(True)
        self.actionTop_Most.setEnabled(True)
        self.centralwidget = QWidget(MainWindow)
        self.centralwidget.setObjectName(u"centralwidget")
        self.executeButton = QPushButton(self.centralwidget)
        self.executeButton.setObjectName(u"executeButton")
        self.executeButton.setGeometry(QRect(100, 500, 81, 26))
        self.injectButton = QPushButton(self.centralwidget)
        self.injectButton.setObjectName(u"injectButton")
        self.injectButton.setGeometry(QRect(10, 500, 81, 26))
        self.exportButton = QPushButton(self.centralwidget)
        self.exportButton.setObjectName(u"exportButton")
        self.exportButton.setGeometry(QRect(660, 500, 81, 26))
        self.importButton = QPushButton(self.centralwidget)
        self.importButton.setObjectName(u"importButton")
        self.importButton.setGeometry(QRect(750, 500, 81, 26))
        self.statusLabel = QLabel(self.centralwidget)
        self.statusLabel.setObjectName(u"statusLabel")
        self.statusLabel.setGeometry(QRect(183, 497, 31, 31))
        font = QFont()
        font.setPointSize(18)
        font.setBold(True)
        self.statusLabel.setFont(font)
        self.statusLabel.setLayoutDirection(Qt.LayoutDirection.LeftToRight)
        self.statusLabel.setTextFormat(Qt.TextFormat.AutoText)
        self.statusLabel.setScaledContents(False)
        self.statusLabel.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.tabWidget = QTabWidget(self.centralwidget)
        self.tabWidget.setObjectName(u"tabWidget")
        self.tabWidget.setGeometry(QRect(10, 35, 821, 456))
        self.tabWidget.setTabsClosable(True)
        self.newTabButton = QPushButton(self.centralwidget)
        self.newTabButton.setObjectName(u"newTabButton")
        self.newTabButton.setGeometry(QRect(750, 30, 81, 26))
        MainWindow.setCentralWidget(self.centralwidget)
        self.tabWidget.raise_()
        self.executeButton.raise_()
        self.injectButton.raise_()
        self.exportButton.raise_()
        self.importButton.raise_()
        self.statusLabel.raise_()
        self.newTabButton.raise_()
        self.menubar = QMenuBar(MainWindow)
        self.menubar.setObjectName(u"menubar")
        self.menubar.setGeometry(QRect(0, 0, 841, 33))
        self.menuFile = QMenu(self.menubar)
        self.menuFile.setObjectName(u"menuFile")
        self.menuExecute = QMenu(self.menubar)
        self.menuExecute.setObjectName(u"menuExecute")
        self.menuWindow = QMenu(self.menubar)
        self.menuWindow.setObjectName(u"menuWindow")
        MainWindow.setMenuBar(self.menubar)

        self.menubar.addAction(self.menuFile.menuAction())
        self.menubar.addAction(self.menuExecute.menuAction())
        self.menubar.addAction(self.menuWindow.menuAction())
        self.menuFile.addSeparator()
        self.menuFile.addAction(self.actionExport)
        self.menuFile.addAction(self.actionImport)
        self.menuFile.addSeparator()
        self.menuFile.addAction(self.actionNew_Tab)
        self.menuFile.addAction(self.actionSave_Tabs)
        self.menuFile.addAction(self.actionClear_Tabs)
        self.menuExecute.addAction(self.actionInject)
        self.menuExecute.addAction(self.actionExecute)
        self.menuWindow.addAction(self.actionExit_Alt_F4)
        self.menuWindow.addAction(self.actionTop_Most)

        self.retranslateUi(MainWindow)

        self.tabWidget.setCurrentIndex(-1)


        QMetaObject.connectSlotsByName(MainWindow)
    # setupUi

    def retranslateUi(self, MainWindow):
        MainWindow.setWindowTitle(QCoreApplication.translate("MainWindow", u"Funny Executor", None))
        self.actionExit_Alt_F4.setText(QCoreApplication.translate("MainWindow", u"Exit (Alt+F4)", None))
        self.actionInject.setText(QCoreApplication.translate("MainWindow", u"Inject", None))
        self.actionExecute.setText(QCoreApplication.translate("MainWindow", u"Execute", None))
        self.actionExport.setText(QCoreApplication.translate("MainWindow", u"Export...", None))
        self.actionImport.setText(QCoreApplication.translate("MainWindow", u"Import...", None))
        self.actionInfo.setText(QCoreApplication.translate("MainWindow", u"Info", None))
        self.actionSave_Tabs.setText(QCoreApplication.translate("MainWindow", u"Save Tabs", None))
        self.actionNew_Tab.setText(QCoreApplication.translate("MainWindow", u"New Tab", None))
        self.actionClear_Tabs.setText(QCoreApplication.translate("MainWindow", u"Clear Tabs", None))
        self.actionInfYield.setText(QCoreApplication.translate("MainWindow", u"Infinite Yield", None))
        self.actionDex.setText(QCoreApplication.translate("MainWindow", u"Dex", None))
        self.actionBtools.setText(QCoreApplication.translate("MainWindow", u"F3X", None))
        self.actionTop_Most.setText(QCoreApplication.translate("MainWindow", u"On Top", None))
        self.executeButton.setText(QCoreApplication.translate("MainWindow", u"Execute", None))
        self.injectButton.setText(QCoreApplication.translate("MainWindow", u"Inject", None))
        self.exportButton.setText(QCoreApplication.translate("MainWindow", u"Export...", None))
        self.importButton.setText(QCoreApplication.translate("MainWindow", u"Import...", None))
        self.statusLabel.setText(QCoreApplication.translate("MainWindow", u"\u2b24", None))
        self.newTabButton.setText(QCoreApplication.translate("MainWindow", u"New Tab", None))
        self.menuFile.setTitle(QCoreApplication.translate("MainWindow", u"File", None))
        self.menuExecute.setTitle(QCoreApplication.translate("MainWindow", u"Execute", None))
        self.menuWindow.setTitle(QCoreApplication.translate("MainWindow", u"Window", None))
    # retranslateUi

