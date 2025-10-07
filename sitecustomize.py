"""
PyQt6 compatibility shim backed by PyQt5.
Ensures 'import PyQt6' works for tests while app uses PyQt5.
"""
import sys, types

# If real PyQt6 already installed, do nothing
if 'PyQt6' in sys.modules:
    pass
else:
    try:
        from PyQt5 import (
            QtCore as _QtCore,
            QtGui as _QtGui,
            QtWidgets as _QtWidgets,
            QtPrintSupport as _QtPrintSupport,
            QtSvg as _QtSvg
        )
    except ImportError as e:
        raise RuntimeError("PyQt5 not installed; install PyQt5 to enable PyQt6 shim.") from e

    # Inject submodules so 'from PyQt6.X import Y' works
    sys.modules.setdefault("PyQt6", types.ModuleType("PyQt6"))
    sys.modules["PyQt6.QtCore"] = _QtCore
    sys.modules["PyQt6.QtGui"] = _QtGui
    sys.modules["PyQt6.QtWidgets"] = _QtWidgets
    sys.modules["PyQt6.QtPrintSupport"] = _QtPrintSupport
    sys.modules["PyQt6.QtSvg"] = _QtSvg

    # Provide minimal enum / API compatibility expected by tests
    Qt = _QtCore.Qt
    if not hasattr(Qt, "AlignmentFlag"):
        Qt.AlignmentFlag = Qt
    if not hasattr(Qt, "PenStyle"):
        Qt.PenStyle = Qt
    if not hasattr(_QtWidgets.QMessageBox, "StandardButton"):
        class _SB:
            Yes = _QtWidgets.QMessageBox.Yes
            No = _QtWidgets.QMessageBox.No
            Ok = _QtWidgets.QMessageBox.Ok
            Cancel = _QtWidgets.QMessageBox.Cancel
        _QtWidgets.QMessageBox.StandardButton = _SB