import os, sys, time, tempfile
from PyQt5.QtWidgets import QApplication

# Avoid launching a second QApplication if running inside a test harness
app = QApplication.instance() or QApplication(sys.argv)

import main

# Create model and window (do not show)
m = main.ProjectDataModel()
w = main.MainWindow(m)

# Point model to a temporary DB and ensure schema
cwd = os.getcwd()
tmp_dir = tempfile.mkdtemp(prefix="sync_test_", dir=cwd)
tmp_db = os.path.join(tmp_dir, "project_data_test.db")
# Create a physical file for mtime checks
open(tmp_db, 'ab').close()
w.model.DB_FILE = tmp_db

# Initialize status displays
w._update_db_status()

# Test 1: read-only badge visibility toggles off/on (use isHidden to avoid offscreen false)
w.model.read_only = True
w._update_read_only_indicator()
ro_hidden_on = bool(w.db_ro_label.isHidden())

w.model.read_only = False
w._update_read_only_indicator()
ro_hidden_off = bool(w.db_ro_label.isHidden())

# Test 2: Last Update label changes when file mtime changes
# Ensure label starts with default text
initial_text = w.db_sync_label.text() if hasattr(w, 'db_sync_label') else ""
# Establish baseline mtime
w._db_last_mtime = w._get_db_mtime()
# Touch DB file to advance mtime
now = time.time()
try:
    os.utime(tmp_db, (now + 2, now + 2))
except Exception:
    time.sleep(1.1)
    os.utime(tmp_db, None)

# Force check
w.model.read_only = True  # avoid prompt path
w._check_db_changed()

last_update_text = w.db_sync_label.text() if hasattr(w, 'db_sync_label') else ""

ok = True
err = []
if ro_hidden_on:
    ok = False
    err.append("Expected READ-ONLY badge to be visible when read_only=True")
if not ro_hidden_off:
    ok = False
    err.append("Expected READ-ONLY badge to be hidden when read_only=False")
if initial_text.strip() == last_update_text.strip() or '—' in last_update_text:
    ok = False
    err.append("Expected Last Update label to change after file modification")

if not ok:
    print("TEST FAILED:\n" + "\n".join(err))
    sys.exit(1)
else:
    print("TEST PASSED")
    sys.exit(0)
