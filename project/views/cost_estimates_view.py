from project.qt_bindings import QWidget, QVBoxLayout, QLabel
from project.helpers import resolve_resource_path

class CostEstimatesView(QWidget):
    def __init__(self, model=None, parent=None):
        super().__init__(parent)
        self.model = model
        lay = QVBoxLayout(self)
        lay.addWidget(QLabel("Cost Estimates View (placeholder)"))

__all__ = ["CostEstimatesView"]