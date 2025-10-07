from project.qt_bindings import QWidget, QVBoxLayout, QLabel
from project.dialogs.conflict_resolution import ConflictResolutionDialog
from project.helpers import resolve_resource_path

class DatabaseView(QWidget):
    def __init__(self, model=None, parent=None):
        super().__init__(parent)
        self.model = model
        lay = QVBoxLayout(self)
        lay.addWidget(QLabel("Database View (placeholder)"))

__all__ = ["DatabaseView"]