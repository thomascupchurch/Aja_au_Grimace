"""Pricing Settings Dialog extracted."""
from project.qt_bindings import QDialog, QFormLayout, QDialogButtonBox, QDoubleSpinBox, QSettings

class PricingSettingsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Pricing Settings")
        self.resize(360, 180)
        form = QFormLayout(self)
        def mkspin(minv, maxv, step, dec=1, suffix=""):
            sb = QDoubleSpinBox(); sb.setRange(minv,maxv); sb.setDecimals(dec); sb.setSingleStep(step)
            if suffix: sb.setSuffix(" "+suffix)
            return sb
        self.target_margin = mkspin(0,95,1,1,"%")
        self.labor_rate = mkspin(0,1000,5,2,"$ /h")
        self.install_labor_rate = mkspin(0,1000,5,2,"$ /h")
        form.addRow("Target Margin %", self.target_margin)
        form.addRow("Fabrication Labor Rate", self.labor_rate)
        form.addRow("Install Labor Rate", self.install_labor_rate)
        s = QSettings("LSI","ProjectPlanner")
        try:
            self.target_margin.setValue(float(s.value("Pricing/target_margin",35)))
            self.labor_rate.setValue(float(s.value("Pricing/labor_rate",55)))
            self.install_labor_rate.setValue(float(s.value("Pricing/install_labor_rate",65)))
        except Exception:
            pass
        try:
            std = QDialogButtonBox.StandardButton
            buttons = QDialogButtonBox(std.Ok | std.Cancel)
        except Exception:
            buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        form.addWidget(buttons)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
    def accept(self):
        s = QSettings("LSI","ProjectPlanner")
        s.setValue("Pricing/target_margin", float(self.target_margin.value()))
        s.setValue("Pricing/labor_rate", float(self.labor_rate.value()))
        s.setValue("Pricing/install_labor_rate", float(self.install_labor_rate.value()))
        return super().accept()
__all__ = ["PricingSettingsDialog"]
