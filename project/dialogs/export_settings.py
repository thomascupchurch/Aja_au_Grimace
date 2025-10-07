"""Export Settings Dialog extracted from main.py"""
from project.qt_bindings import QDialog, QFormLayout, QComboBox, QDialogButtonBox, QDoubleSpinBox, QCheckBox, QSettings

class ExportSettingsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Export Settings")
        self.resize(380, 220)
        form = QFormLayout(self)
        self.format_combo = QComboBox(); self.format_combo.addItems(["PNG","PDF"])
        self.size_combo = QComboBox(); self.size_combo.addItems(["A4","Letter","Legal","Tabloid"])
        self.orientation_combo = QComboBox(); self.orientation_combo.addItems(["Portrait","Landscape"])
        def mkspin():
            sb = QDoubleSpinBox(); sb.setRange(0.0,50.0); sb.setDecimals(1); sb.setSingleStep(0.5); sb.setSuffix(" mm"); return sb
        self.margin_left = mkspin(); self.margin_top = mkspin(); self.margin_right = mkspin(); self.margin_bottom = mkspin()
        self.include_header_cb = QCheckBox("Include Header Graphic")
        form.addRow("Format", self.format_combo)
        form.addRow("Page Size (PDF)", self.size_combo)
        form.addRow("Orientation (PDF)", self.orientation_combo)
        form.addRow("Left Margin", self.margin_left)
        form.addRow("Top Margin", self.margin_top)
        form.addRow("Right Margin", self.margin_right)
        form.addRow("Bottom Margin", self.margin_bottom)
        form.addRow("Header", self.include_header_cb)
        self.buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        self.buttons.accepted.connect(self.accept)
        self.buttons.rejected.connect(self.reject)
        form.addRow(self.buttons)
        s = QSettings("LSI","ProjectPlanner")
        self.format_combo.setCurrentText(s.value("Export/format","PNG"))
        self.size_combo.setCurrentText(s.value("Export/page_size","A4"))
        self.orientation_combo.setCurrentText(s.value("Export/orientation","Portrait"))
        self.margin_left.setValue(float(s.value("Export/margin_left_mm",8.0)))
        self.margin_top.setValue(float(s.value("Export/margin_top_mm",8.0)))
        self.margin_right.setValue(float(s.value("Export/margin_right_mm",8.0)))
        self.margin_bottom.setValue(float(s.value("Export/margin_bottom_mm",8.0)))
        inc_header = s.value("Export/include_header", True)
        if isinstance(inc_header,str):
            inc_header = inc_header.lower() in ("1","true","yes")
        self.include_header_cb.setChecked(bool(inc_header))
        self.format_combo.currentTextChanged.connect(lambda _: self._update_pdf_only())
        self._update_pdf_only()
    def _update_pdf_only(self):
        is_pdf = (self.format_combo.currentText() == "PDF")
        self.size_combo.setEnabled(is_pdf)
        self.orientation_combo.setEnabled(is_pdf)
    def accept(self):
        s = QSettings("LSI","ProjectPlanner")
        s.setValue("Export/format", self.format_combo.currentText())
        s.setValue("Export/page_size", self.size_combo.currentText())
        s.setValue("Export/orientation", self.orientation_combo.currentText())
        s.setValue("Export/margin_left_mm", float(self.margin_left.value()))
        s.setValue("Export/margin_top_mm", float(self.margin_top.value()))
        s.setValue("Export/margin_right_mm", float(self.margin_right.value()))
        s.setValue("Export/margin_bottom_mm", float(self.margin_bottom.value()))
        s.setValue("Export/include_header", bool(self.include_header_cb.isChecked()))
        return super().accept()
__all__ = ["ExportSettingsDialog"]