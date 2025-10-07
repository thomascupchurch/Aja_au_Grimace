import os, tempfile, csv, pytest
from PyQt6.QtWidgets import QApplication
from main import ProjectDataModel, CostEstimatesView


@pytest.fixture(scope="module")
def qapp():
    return QApplication.instance() or QApplication([])


def test_selected_only_csv_export(qapp):
    model = ProjectDataModel()
    model.rows = [
        {"Project Part":"Alpha","Parent":"","Production Cost":100,"Installation Cost":50,"Production Price":200,"Installation Price":80},
        {"Project Part":"Beta","Parent":"","Production Cost":150,"Installation Cost":70,"Production Price":260,"Installation Price":100},
    ]
    view = CostEstimatesView(model)
    view.refresh()
    view.table.selectRow(0)
    view.chk_selected_only.setChecked(True)
    from PyQt6.QtWidgets import QFileDialog
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix='.csv'); tmp.close()
    orig = QFileDialog.getSaveFileName
    try:
        QFileDialog.getSaveFileName = staticmethod(lambda *a, **k: (tmp.name, 'CSV Files (*.csv)'))
        view._export_csv()
    finally:
        QFileDialog.getSaveFileName = orig
    with open(tmp.name, newline='', encoding='utf-8') as f:
        rows = list(csv.reader(f))
    os.unlink(tmp.name)
    assert len(rows) == 2  # header + 1 data row
    assert rows[1][0] == 'Alpha'
