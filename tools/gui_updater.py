import sys
import os
import zipfile
import shutil
from PyQt6.QtWidgets import (
    QApplication, QWidget, QLabel, QPushButton, QVBoxLayout, QHBoxLayout,
    QFileDialog, QMessageBox, QProgressBar
)
from PyQt6.QtCore import Qt

def get_version_from_file(path):
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return f.read().strip()
    except Exception:
        return None

def get_version_from_zip(zip_path):
    try:
        with zipfile.ZipFile(zip_path, 'r') as z:
            with z.open('VERSION') as vf:
                return vf.read().decode('utf-8').strip()
    except Exception:
        return None

class UpdaterWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle('App Updater')
        self.setFixedSize(400, 260)
        self.layout = QVBoxLayout(self)

        self.current_version_label = QLabel('Current version: —')
        self.new_version_label = QLabel('Update version: —')
        self.zip_path_label = QLabel('No update zip selected.')
        self.progress = QProgressBar()
        self.progress.setVisible(False)
        self.progress.setMinimum(0)
        self.progress.setMaximum(100)

        self.select_zip_btn = QPushButton('Select Update Zip')
        self.update_btn = QPushButton('Update App')
        self.update_btn.setEnabled(False)

        self.layout.addWidget(self.current_version_label)
        self.layout.addWidget(self.new_version_label)
        self.layout.addWidget(self.zip_path_label)
        self.layout.addWidget(self.select_zip_btn)
        self.layout.addWidget(self.update_btn)
        self.layout.addWidget(self.progress)

        self.select_zip_btn.clicked.connect(self.select_zip)
        self.update_btn.clicked.connect(self.run_update)

        self.zip_path = None
        self.current_version = None
        self.new_version = None
        self.detect_current_version()

    def detect_current_version(self):
        exe_dir = os.path.dirname(os.path.abspath(sys.argv[0]))
        version_path = os.path.join(exe_dir, 'VERSION')
        self.current_version = get_version_from_file(version_path)
        self.current_version_label.setText(f'Current version: {self.current_version or "—"}')

    def select_zip(self):
        zip_path, _ = QFileDialog.getOpenFileName(self, 'Select Update Zip', '', 'Zip Files (*.zip)')
        if zip_path:
            self.zip_path = zip_path
            self.zip_path_label.setText(f'Selected: {os.path.basename(zip_path)}')
            self.new_version = get_version_from_zip(zip_path)
            self.new_version_label.setText(f'Update version: {self.new_version or "—"}')
            self.update_btn.setEnabled(bool(self.new_version))

    def run_update(self):
        if not self.zip_path or not self.new_version:
            QMessageBox.warning(self, 'Error', 'No update zip or version detected.')
            return
        exe_dir = os.path.dirname(os.path.abspath(sys.argv[0]))
        backup_dir = os.path.join(exe_dir, 'backup_' + (self.current_version or 'old'))
        try:
            self.progress.setVisible(True)
            self.progress.setValue(10)
            # Backup old files
            if not os.path.exists(backup_dir):
                os.makedirs(backup_dir)
            for fname in os.listdir(exe_dir):
                if fname.endswith('.exe') or fname == 'VERSION':
                    shutil.copy2(os.path.join(exe_dir, fname), os.path.join(backup_dir, fname))
            self.progress.setValue(40)
            # Extract new files
            with zipfile.ZipFile(self.zip_path, 'r') as z:
                for member in z.namelist():
                    if member.endswith('.exe') or member == 'VERSION':
                        z.extract(member, exe_dir)
            self.progress.setValue(90)
            self.detect_current_version()
            self.progress.setValue(100)
            QMessageBox.information(self, 'Update Complete', f'App updated to version {self.new_version}. Backup saved to {backup_dir}.')
        except Exception as e:
            QMessageBox.critical(self, 'Update Failed', f'Error: {e}')
        finally:
            self.progress.setVisible(False)

def main():
    app = QApplication(sys.argv)
    win = UpdaterWindow()
    win.show()
    sys.exit(app.exec())

if __name__ == '__main__':
    main()
