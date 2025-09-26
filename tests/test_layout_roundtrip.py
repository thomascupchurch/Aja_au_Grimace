import sys, os, json
from PyQt5.QtWidgets import QApplication

# Minimal runtime test for layout programmatic API
# Run: python -m tests.test_layout_roundtrip

def main():
    app = QApplication.instance() or QApplication(sys.argv)
    # Import main module
    import main as appmod
    model = appmod.ProjectDataModel()
    # Seed with a few rows to ensure table populates
    if not model.rows:
        model.rows.append({col: '' for col in model.COLUMNS})
        model.rows[0]['Project Part'] = 'SampleRoot'
    view = appmod.CostEstimatesView(model)
    # Hide a couple columns and reorder one
    if view.table.columnCount() >= 4:
        view.table.setColumnHidden(2, True)  # hide Prod Cost
        view.table.setColumnHidden(3, True)  # hide Inst Cost
    view.save_layout_programmatic('TEST_LAYOUT')
    # Mutate visibility
    if view.table.columnCount() >= 4:
        view.table.setColumnHidden(2, False)
        view.table.setColumnHidden(3, False)
    ok, msg = view.apply_layout_programmatic('TEST_LAYOUT')
    result = {
        'apply_ok': ok,
        'message': msg,
        'hidden_after': [i for i in range(view.table.columnCount()) if view.table.isColumnHidden(i)],
        'saved_layout_exists': False
    }
    try:
        from PyQt5.QtCore import QSettings
        s = QSettings('LSI','ProjectPlanner')
        raw = s.value('Columns/layouts', '{}')
        layouts = json.loads(raw) if raw else {}
        result['saved_layout_exists'] = 'TEST_LAYOUT' in layouts
    except Exception:
        pass
    print(json.dumps(result, indent=2))
    return 0 if ok else 1

if __name__ == '__main__':
    raise SystemExit(main())
