import os
import json
import tempfile
import shutil
import time
import contextlib

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')

from PyQt6.QtWidgets import QApplication

app = QApplication.instance() or QApplication([])

import importlib.util
import sys

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
    try:
        yield db_path
    finally:
        shutil.rmtree(d, ignore_errors=True)

def test_lock_acquire_release_updates_label():
    with temp_db_copy() as db_path:
        os.environ['PROJECT_DB_PATH'] = db_path
        model = main.ProjectDataModel()
        model.read_only = False
        win = main.MainWindow(model)
        try:
            lock_path = os.path.abspath(db_path) + '.lock.json'
            if os.path.exists(lock_path):
                os.remove(lock_path)
            win._update_lock_status()
            assert '—' in win.lock_label.text()
            ok = win._acquire_edit_lock()
            assert ok
            txt = win.lock_label.text()
            assert 'Lock:' in txt and '@' in txt
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
            from PyQt6.QtCore import QSettings
            s = QSettings('LSI','ProjectApp'); s.setValue('Lock/prompt_takeover', True); s.setValue('Lock/stale_minutes', 1)
            lock_path = os.path.abspath(db_path) + '.lock.json'
            info = {"owner":"other@host","when":"2000-01-01 00:00:00","pid":0}
            with open(lock_path, 'w', encoding='utf-8') as f:
                json.dump(info, f)
            from PyQt6.QtWidgets import QMessageBox
            orig_exec = getattr(QMessageBox, "exec", None)
            def fake_exec(self):
                return QMessageBox.StandardButton.Yes
            QMessageBox.exec = fake_exec
            try:
                ok = win._acquire_edit_lock()
                assert ok
                assert win.lock_label.text().startswith('Lock:') and '(stale)' not in win.lock_label.text()
            finally:
                if orig_exec is not None:
                    QMessageBox.exec = orig_exec
        finally:
            win.close()

from project import ProjectDataModel

def test_basic_model_instantiation():
    m = ProjectDataModel()
    assert isinstance(m.rows, list)
