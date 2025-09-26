import os, tempfile
from PyQt5.QtWidgets import QApplication
from main import ProjectDataModel, CostEstimatesView

try:
    import openpyxl  # noqa: F401
    HAVE_OPENPYXL = True
except Exception:
    HAVE_OPENPYXL = False

def run_test():
    app = QApplication.instance() or QApplication([])
    model = ProjectDataModel()
    model.rows = [
        {"Project Part":"Alpha","Parent":"","Production Cost":100,"Installation Cost":50,"Production Price":200,"Installation Price":80},
        {"Project Part":"Beta","Parent":"","Production Cost":150,"Installation Cost":70,"Production Price":260,"Installation Price":100},
        {"Project Part":"Gamma","Parent":"","Production Cost":120,"Installation Cost":60,"Production Price":210,"Installation Price":90},
    ]
    view = CostEstimatesView(model)
    view.refresh()
    # Select two rows
    view.table.selectRow(0)
    view.table.selectRow(2)
    view.chk_selected_only.setChecked(True)
    if not HAVE_OPENPYXL:
        print({'skipped': True, 'reason': 'openpyxl not installed'})
        return
    from PyQt5.QtWidgets import QFileDialog
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix='.xlsx'); tmp.close()
    orig = QFileDialog.getSaveFileName
    try:
        QFileDialog.getSaveFileName = staticmethod(lambda *a, **k: (tmp.name, 'Excel Workbook (*.xlsx)'))
        view._export_xlsx()
    finally:
        QFileDialog.getSaveFileName = orig
    # Inspect workbook
    import openpyxl
    wb = openpyxl.load_workbook(tmp.name, data_only=True)
    costs = wb['Costs']
    meta = wb['_Meta']
    # Header row + two selected rows expected
    rows_written = costs.max_row - 1
    subset_val = None
    for row in meta.iter_rows(values_only=True):
        if row[0] == 'Subset':
            subset_val = row[1]
            break
    result = {
        'rows_written': rows_written,
        'expected_rows': 2,
        'subset_meta': subset_val,
        'pass': rows_written == 2 and subset_val == 'Selected'
    }
    print(result)
    wb.close(); os.unlink(tmp.name)
    return result

if __name__ == '__main__':
    run_test()
