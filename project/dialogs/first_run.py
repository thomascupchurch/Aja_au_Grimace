"""First run onboarding dialog."""
from project.qt_bindings import QDialog, QVBoxLayout, QLabel, QPushButton, QHBoxLayout, QCheckBox

class FirstRunDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Welcome – Getting Started")
        v = QVBoxLayout(self)
        v.addWidget(QLabel("This appears to be a new or empty project database.\nYou can start adding parts or import data."))
        self.skip_cb = QCheckBox("Don't show again")
        v.addWidget(self.skip_cb)
        h = QHBoxLayout()
        add_btn = QPushButton("Add First Part")
        close_btn = QPushButton("Close")
        h.addWidget(add_btn); h.addWidget(close_btn)
        v.addLayout(h)
        add_btn.clicked.connect(lambda: self.done(2))  # custom code for 'add'
        close_btn.clicked.connect(self.accept)
    def suppress_future(self) -> bool:
        return self.skip_cb.isChecked()
__all__ = ["FirstRunDialog"]
from project.qt_bindings import *
class FirstRunDialog(QDialog):
    # ...existing code moved from main (FirstRunDialog)...
    pass