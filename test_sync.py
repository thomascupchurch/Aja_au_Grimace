"""Converted from script-style test to pytest tests.

Validations:
 - READ-ONLY badge visibility toggles with model.read_only flag.
 - Last Update label changes after touching DB file (mtime).
"""

import os, time, tempfile, shutil, pytest
from PyQt6.QtWidgets import QApplication
import main


@pytest.fixture(scope="module")
def qapp():
    return QApplication.instance() or QApplication([])


@pytest.fixture()
def window_tmpdb(qapp, tmp_path):
    model = main.ProjectDataModel()
    win = main.MainWindow(model)
    # Point to temp DB
    db_path = tmp_path / "project_data_test.db"
    db_path.touch()
    win.model.DB_FILE = str(db_path)
    win._update_db_status()
    yield win
    win.close()


def test_read_only_badge_toggles(window_tmpdb):
    w = window_tmpdb
    w.model.read_only = True
    w._update_read_only_indicator()
    assert not w.db_ro_label.isHidden(), "READ-ONLY badge should be visible when read_only=True"
    w.model.read_only = False
    w._update_read_only_indicator()
    assert w.db_ro_label.isHidden(), "READ-ONLY badge should be hidden when read_only=False"


def test_last_update_changes_after_touch(window_tmpdb):
    w = window_tmpdb
    initial_text = w.db_sync_label.text() if hasattr(w, 'db_sync_label') else ""
    w._db_last_mtime = w._get_db_mtime()
    # Touch file forward in time
    db_path = w.model.DB_FILE
    now = time.time()
    try:
        os.utime(db_path, (now + 3, now + 3))
    except Exception:
        time.sleep(1.1)
        os.utime(db_path, None)
    w.model.read_only = True
    w._check_db_changed()
    last_text = w.db_sync_label.text() if hasattr(w, 'db_sync_label') else ""
    assert initial_text.strip() != last_text.strip(), "Last Update label should change after DB mtime modification"
    # Allow em dash status suffixes (e.g. "— auto", "— reload"), just ensure we replaced placeholder only state
    assert last_text.strip() != "Last: —", "Last Update label still shows placeholder after update"
    # Require a YYYY-MM-DD date stamp presence
    import re
    assert re.search(r"Last:\s+\d{4}-\d{2}-\d{2}", last_text), f"Last Update label missing timestamp: {last_text}"
