import sys, types
from PyQt5 import QtCore as _QtCore, QtGui as _QtGui, QtWidgets as _QtWidgets, QtPrintSupport as _QtPrintSupport, QtSvg as _QtSvg

# Inject submodules so standard "from PyQt6.X import ..." works
sys.modules.setdefault("PyQt6.QtCore", _QtCore)
sys.modules.setdefault("PyQt6.QtGui", _QtGui)
sys.modules.setdefault("PyQt6.QtWidgets", _QtWidgets)
sys.modules.setdefault("PyQt6.QtPrintSupport", _QtPrintSupport)
sys.modules.setdefault("PyQt6.QtSvg", _QtSvg)

# Optional: expose top-level names (minimal)
QtCore = _QtCore
QtGui = _QtGui
QtWidgets = _QtWidgets
QtPrintSupport = _QtPrintSupport
QtSvg = _QtSvg

__all__ = ["QtCore","QtGui","QtWidgets","QtPrintSupport","QtSvg"]