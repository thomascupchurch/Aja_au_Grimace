import os, tempfile, csv
from PyQt5.QtWidgets import QApplication
from main import ProjectDataModel, CostEstimatesView

# Simple runtime test (not a formal framework) to validate Selected Only CSV export subset.

def run_test():
    app = QApplication.instance() or QApplication([])
    model = ProjectDataModel()
    # Ensure two test rows
    model.rows = [
        {"Project Part":"Alpha","Parent":"","Production Cost":100,"Installation Cost":50,"Production Price":200,"Installation Price":80},
        {"Project Part":"Beta","Parent":"","Production Cost":150,"Installation Cost":70,"Production Price":260,"Installation Price":100},
    ]
    view = CostEstimatesView(model)
    view.refresh()
    # Select first row only
    view.table.selectRow(0)
    view.chk_selected_only.setChecked(True)
    # Monkeypatch file dialog to auto choose temp path
    from PyQt5.QtWidgets import QFileDialog
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix='.csv'); tmp.close()
    orig = QFileDialog.getSaveFileName
    try:
        QFileDialog.getSaveFileName = staticmethod(lambda *a, **k: (tmp.name, 'CSV Files (*.csv)'))
        view._export_csv()
    finally:
        QFileDialog.getSaveFileName = orig
    # Read back CSV
    with open(tmp.name, newline='', encoding='utf-8') as f:
        reader = list(csv.reader(f))
    os.unlink(tmp.name)
    header = reader[0]
    data_rows = reader[1:]
    result = {
        "rows_written": len(data_rows),
        "first_row_part": data_rows[0][0] if data_rows else None,
        "expected_rows": 1,
        "pass": len(data_rows) == 1 and (data_rows[0][0] == 'Alpha')
    }
    print(result)
    return result

if __name__ == '__main__':
    run_test()
