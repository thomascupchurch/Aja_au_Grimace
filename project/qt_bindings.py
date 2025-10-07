from PyQt5 import QtCore, QtGui, QtWidgets, QtSvg, QtPrintSupport

# Core
Qt        = QtCore.Qt
QDate      = QtCore.QDate
QEvent     = QtCore.QEvent
QTimer     = QtCore.QTimer
QSettings  = QtCore.QSettings

# Widgets
QApplication    = QtWidgets.QApplication
QMainWindow     = QtWidgets.QMainWindow
QWidget         = QtWidgets.QWidget
QDialog         = QtWidgets.QDialog
QLabel          = QtWidgets.QLabel
QLineEdit       = QtWidgets.QLineEdit
QTextEdit       = QtWidgets.QTextEdit
QComboBox       = QtWidgets.QComboBox
QDateEdit       = QtWidgets.QDateEdit
QSpinBox        = QtWidgets.QSpinBox
QDoubleSpinBox  = QtWidgets.QDoubleSpinBox
QPushButton     = QtWidgets.QPushButton
QHBoxLayout     = QtWidgets.QHBoxLayout
QVBoxLayout     = QtWidgets.QVBoxLayout
QFormLayout     = QtWidgets.QFormLayout
QListWidget     = QtWidgets.QListWidget
QTreeWidget     = QtWidgets.QTreeWidget
QTreeWidgetItem = QtWidgets.QTreeWidgetItem
QTableWidget    = QtWidgets.QTableWidget
QTableWidgetItem= QtWidgets.QTableWidgetItem
QStackedWidget  = QtWidgets.QStackedWidget
QGraphicsView   = QtWidgets.QGraphicsView
QGraphicsScene  = QtWidgets.QGraphicsScene
QGraphicsItem   = QtWidgets.QGraphicsItem
QMessageBox     = QtWidgets.QMessageBox
QStatusBar      = QtWidgets.QStatusBar
QFileDialog     = QtWidgets.QFileDialog
QMenu           = QtWidgets.QMenu
QToolButton     = QtWidgets.QToolButton
QScrollArea     = QtWidgets.QScrollArea
QCalendarWidget = QtWidgets.QCalendarWidget

# GUI
QPixmap    = QtGui.QPixmap
QPainter   = QtGui.QPainter
QPen       = QtGui.QPen
QBrush     = QtGui.QBrush
QColor     = QtGui.QColor
QFont      = QtGui.QFont
QKeySequence = QtGui.QKeySequence

# SVG
QSvgRenderer = QtSvg.QSvgRenderer

# Print / Export
QPrinter        = QtPrintSupport.QPrinter
QPrintDialog    = QtPrintSupport.QPrintDialog
QPageSetupDialog= QtPrintSupport.QPageSetupDialog

# QMessageBox StandardButton shim (for test code using PyQt6 style)
if not hasattr(QMessageBox, "StandardButton"):
    class _SB:
        Yes = QMessageBox.Yes
        No = QMessageBox.No
        Cancel = QMessageBox.Cancel
    QMessageBox.StandardButton = _SB

__all__ = [n for n in globals() if not n.startswith('_')]