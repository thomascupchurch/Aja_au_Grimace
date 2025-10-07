from project.qt_bindings import QWidget, QVBoxLayout, QLabel

class ProgressDashboard(QWidget):
    def __init__(self, model=None, parent=None):
        super().__init__(parent)
        self.model = model
        lay = QVBoxLayout(self)
        lay.addWidget(QLabel("Progress Dashboard (placeholder)"))

__all__ = ["ProgressDashboard"]