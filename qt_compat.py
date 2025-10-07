# Compatibility layer for PyQt6 migration.
from PyQt6 import QtCore, QtGui, QtWidgets

Qt = QtCore.Qt

# Provide legacy-style attribute shortcuts if missing.
def _alias(obj, legacy, real):
    if not hasattr(obj, legacy) and hasattr(obj, real):
        setattr(obj, legacy, getattr(obj, real))

# Alignment
_alias(Qt, "AlignLeft", "AlignmentFlag.AlignLeft")
_alias(Qt, "AlignRight", "AlignmentFlag.AlignRight")
_alias(Qt, "AlignHCenter", "AlignmentFlag.AlignHCenter")
_alias(Qt, "AlignVCenter", "AlignmentFlag.AlignVCenter")
_alias(Qt, "AlignCenter", "AlignmentFlag.AlignCenter")
_alias(Qt, "AlignTop", "AlignmentFlag.AlignTop")
_alias(Qt, "AlignBottom", "AlignmentFlag.AlignBottom")

# Item flags
_alias(Qt, "ItemIsEnabled", "ItemFlag.ItemIsEnabled")
_alias(Qt, "ItemIsSelectable", "ItemFlag.ItemIsSelectable")
_alias(Qt, "ItemIsEditable", "ItemFlag.ItemIsEditable")
_alias(Qt, "ItemIsUserCheckable", "ItemFlag.ItemIsUserCheckable")

# Orientation
_alias(Qt, "Horizontal", "Orientation.Horizontal")
_alias(Qt, "Vertical", "Orientation.Vertical")

# Check state
_alias(Qt, "Checked", "CheckState.Checked")
_alias(Qt, "Unchecked", "CheckState.Unchecked")
_alias(Qt, "PartiallyChecked", "CheckState.PartiallyChecked")

# Cursor shape example (add as needed):
_alias(Qt, "PointingHandCursor", "CursorShape.PointingHandCursor")

# Dialog codes shortcut
from PyQt6.QtWidgets import QDialog
if not hasattr(QDialog, "Accepted"):
    QDialog.DialogCode.Accepted = QDialog.DialogCode.Accepted
    QDialog.DialogCode.Rejected = QDialog.DialogCode.Rejected

# Exec alias (if older code calls .exec())
def exec_dialog(dlg):
    return dlg.exec()

__all__ = [
    "QtCore", "QtGui", "QtWidgets", "Qt", "QDialog", "exec_dialog"
]