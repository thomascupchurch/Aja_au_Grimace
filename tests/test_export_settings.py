import os
import pytest

from project.dialogs.export_settings import ExportSettingsDialog
from project.qt_bindings import QSettings, QApplication


@pytest.fixture(scope="module")
def qapp():
    # Create a single QApplication for dialog tests if not already present
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    yield app


def test_export_settings_persistence(tmp_path, qapp, monkeypatch):
    # Use a temporary organization/app name to avoid clobbering real user settings
    monkeypatch.setenv('QT_HASH_SEED', '0')  # Just to keep deterministic ordering if relevant
    # Redirect QSettings to INI format in temp dir
    ini_path = tmp_path / 'settings.ini'
    QSettings.setPath(QSettings.IniFormat, QSettings.UserScope, str(tmp_path))
    s = QSettings(QSettings.IniFormat, QSettings.UserScope, 'LSI_Test','ProjectPlannerTest')
    s.clear()

    # Instantiate dialog (should load defaults)
    dlg = ExportSettingsDialog()
    # Adjust some values
    dlg.format_combo.setCurrentText('PDF')
    dlg.size_combo.setCurrentText('Letter')
    dlg.orientation_combo.setCurrentText('Landscape')
    dlg.margin_left.setValue(12.5)
    dlg.margin_top.setValue(6.0)
    dlg.margin_right.setValue(9.5)
    dlg.margin_bottom.setValue(11.0)
    dlg.include_header_cb.setChecked(False)

    # Accept to persist
    dlg.accept()

    # Read back via new QSettings instance (using real production keys the dialog expects)
    s2 = QSettings('LSI','ProjectPlanner')
    # Fall back to test scope if prod scope empty (depending on environment)
    fmt = s2.value('Export/format') or s.value('Export/format')
    assert fmt == 'PDF'
    assert (s2.value('Export/page_size') or s.value('Export/page_size')) == 'Letter'
    assert (s2.value('Export/orientation') or s.value('Export/orientation')) == 'Landscape'
    assert float(s2.value('Export/margin_left_mm') or s.value('Export/margin_left_mm')) == pytest.approx(12.5)
    assert float(s2.value('Export/margin_top_mm') or s.value('Export/margin_top_mm')) == pytest.approx(6.0)
    assert float(s2.value('Export/margin_right_mm') or s.value('Export/margin_right_mm')) == pytest.approx(9.5)
    assert float(s2.value('Export/margin_bottom_mm') or s.value('Export/margin_bottom_mm')) == pytest.approx(11.0)
    inc_header = s2.value('Export/include_header')
    if isinstance(inc_header,str):
        inc_header = inc_header.lower() in ('1','true','yes')
    elif inc_header is None:
        inc_header = s.value('Export/include_header')
    assert not bool(inc_header)

    # Open second dialog to confirm UI restores values
    dlg2 = ExportSettingsDialog()
    assert dlg2.format_combo.currentText() == 'PDF'
    assert dlg2.size_combo.currentText() == 'Letter'
    assert dlg2.orientation_combo.currentText() == 'Landscape'
    assert dlg2.margin_left.value() == pytest.approx(12.5)
    assert dlg2.margin_top.value() == pytest.approx(6.0)
    assert dlg2.margin_right.value() == pytest.approx(9.5)
    assert dlg2.margin_bottom.value() == pytest.approx(11.0)
    assert dlg2.include_header_cb.isChecked() is False


def test_export_settings_pdf_toggle(qapp):
    dlg = ExportSettingsDialog()
    dlg.format_combo.setCurrentText('PNG')
    assert dlg.size_combo.isEnabled() is False
    assert dlg.orientation_combo.isEnabled() is False
    dlg.format_combo.setCurrentText('PDF')
    assert dlg.size_combo.isEnabled() is True
    assert dlg.orientation_combo.isEnabled() is True
