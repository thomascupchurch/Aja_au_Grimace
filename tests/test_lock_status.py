import os
import json
import tempfile
import shutil
import time
import contextlib

# Skip GUI if no display; PyQt5 on Windows usually works headless enough for simple widget instantiation
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')

from PyQt5.QtWidgets import QApplication

app = QApplication.instance() or QApplication([])

import importlib.util
import sys

# Dynamically import main.py as a module
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
MAIN_PATH = os.path.join(ROOT, 'main.py')
spec = importlib.util.spec_from_file_location('app_main', MAIN_PATH)
main = importlib.util.module_from_spec(spec)
sys.modules['app_main'] = main
spec.loader.exec_module(main)

@contextlib.contextmanager
def temp_db_copy(src_db=None):
    d = tempfile.mkdtemp(prefix='locktest_')
    db_path = os.path.join(d, 'project_data.db')
    if src_db and os.path.exists(src_db):
        shutil.copy2(src_db, db_path)
        for ext in ('-wal','-shm'):
            side = src_db + ext
            if os.path.exists(side):
                shutil.copy2(side, db_path + ext)
    else:
        # create minimal empty DB by letting the model initialize
        pass
    try:
        yield db_path
    finally:
        shutil.rmtree(d, ignore_errors=True)


def test_lock_acquire_release_updates_label():
    with temp_db_copy() as db_path:
        # Force app to use this DB
        os.environ['PROJECT_DB_PATH'] = db_path
        model = main.ProjectDataModel()
        # Ensure read-write
        model.read_only = False
        win = main.MainWindow(model)
        try:
            # Ensure clean start
            lock_path = os.path.abspath(db_path) + '.lock.json'
            if os.path.exists(lock_path):
                os.remove(lock_path)
            win._update_lock_status()
            assert '—' in win.lock_label.text()
            # Acquire
            ok = win._acquire_edit_lock()
            assert ok
            txt = win.lock_label.text()
            assert 'Lock:' in txt and '@' in txt
            # Release
            ok2 = win._release_edit_lock()
            assert ok2
            assert '—' in win.lock_label.text()
        finally:
            win.close()


def test_stale_lock_marking():
    with temp_db_copy() as db_path:
        os.environ['PROJECT_DB_PATH'] = db_path
        model = main.ProjectDataModel()
        win = main.MainWindow(model)
        try:
            lock_path = os.path.abspath(db_path) + '.lock.json'
            # Write a stale lock (older than 1 minute)
            info = {"owner":"other@host","when":"2000-01-01 00:00:00","pid":0}
            with open(lock_path, 'w', encoding='utf-8') as f:
                json.dump(info, f)
            win._update_lock_status()
            assert '(stale)' in win.lock_label.text()
        finally:
            win.close()


def test_takeover_prompt_path_simulated():
    with temp_db_copy() as db_path:
        os.environ['PROJECT_DB_PATH'] = db_path
        model = main.ProjectDataModel()
        win = main.MainWindow(model)
        try:
            # Configure to prompt takeover
            from PyQt5.QtCore import QSettings
            s = QSettings('LSI','ProjectApp'); s.setValue('Lock/prompt_takeover', True); s.setValue('Lock/stale_minutes', 1)
            # Existing stale lock from other user
            lock_path = os.path.abspath(db_path) + '.lock.json'
            info = {"owner":"other@host","when":"2000-01-01 00:00:00","pid":0}
            with open(lock_path, 'w', encoding='utf-8') as f:
                json.dump(info, f)
            # Monkeypatch QMessageBox to auto-Yes
            from PyQt5.QtWidgets import QMessageBox
            orig = QMessageBox.exec_
            def fake_exec(self):
                return QMessageBox.Yes
            QMessageBox.exec_ = fake_exec
            try:
                ok = win._acquire_edit_lock()
                assert ok
                assert win.lock_label.text().startswith('Lock:') and '(stale)' not in win.lock_label.text()
            finally:
                QMessageBox.exec_ = orig
        finally:
            win.close()
