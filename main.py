import sys
from PyQt5.QtWidgets import QApplication, QMainWindow, QStackedWidget, QListWidget, QWidget, QHBoxLayout, QVBoxLayout, QLabel

from PyQt5.QtWidgets import QTreeWidget, QTreeWidgetItem, QPushButton, QInputDialog, QMessageBox, QMenu


# Central data model for project parts
class ProjectDataModel:
    COLUMNS = [
        "Project Part", "Start Date", "Duration (days)", "Internal/External", "Dependencies", "Type", "Calculated End Date", "Deadline", "Resources", "Notes", "Responsible", "Images"
    ]
    def __init__(self):
        self.rows = []  # Each row is a dict with keys as COLUMNS, plus 'parent' (index or None)

    def add_row(self, data, parent=None):
        row = {col: val for col, val in zip(self.COLUMNS, data)}
        row['parent'] = parent
        self.rows.append(row)
        return len(self.rows) - 1

    def update_row(self, idx, data):
        for i, col in enumerate(self.COLUMNS):
            self.rows[idx][col] = data[i]

    def delete_row(self, idx):
        # Remove children recursively
        children = [i for i, r in enumerate(self.rows) if r['parent'] == idx]
        for c in sorted(children, reverse=True):
            self.delete_row(c)
        del self.rows[idx]
        # Update parent indices
        for r in self.rows:
            if r['parent'] is not None and r['parent'] > idx:
                r['parent'] -= 1

    def get_tree(self):
        # Returns a list of (row, children) tuples for tree rendering
        def collect(parent_idx):
            nodes = []
            for i, r in enumerate(self.rows):
                if r['parent'] == parent_idx:
                    nodes.append((i, collect(i)))
            return nodes
        return collect(None)

    def get_flat(self):
        return self.rows

class ProjectTreeView(QWidget):
    def __init__(self, model):
        print("ProjectTreeView: __init__ called")
        super().__init__()
        self.model = model
        layout = QVBoxLayout()
        layout.addWidget(QLabel("Project Tree (Read-Only)"))
        self.tree = QTreeWidget()
        self.tree.setHeaderLabels(ProjectDataModel.COLUMNS)
        layout.addWidget(self.tree)
        self.setLayout(layout)
        self.refresh()

    def refresh(self):
        self.tree.clear()
        def add_items(parent_widget, parent_idx):
            for idx, children in [(i, c) for i, c in enumerate(self.model.get_tree()) if self.model.rows[i]['parent'] == parent_idx]:
                row = self.model.rows[idx]
                item = QTreeWidgetItem([row[col] for col in ProjectDataModel.COLUMNS])
                if parent_widget is None:
                    self.tree.addTopLevelItem(item)
                else:
                    parent_widget.addChild(item)
                add_items(item, idx)
        add_items(None, None)

class GanttChartView(QWidget):
    def __init__(self):
        print("GanttChartView: __init__ called")
        super().__init__()
        layout = QVBoxLayout()
        layout.addWidget(QLabel("Gantt Chart (Read-Only)"))
        # TODO: Add Gantt chart rendering
        self.setLayout(layout)

class CalendarView(QWidget):
    def __init__(self):
        print("CalendarView: __init__ called")
        super().__init__()
        layout = QVBoxLayout()
        layout.addWidget(QLabel("Calendar (Read-Only)"))
        # TODO: Add calendar rendering
        self.setLayout(layout)

class TimelineView(QWidget):
    def __init__(self):
        print("TimelineView: __init__ called")
        super().__init__()
        layout = QVBoxLayout()
        layout.addWidget(QLabel("Project Timeline (Read-Only)"))
        # TODO: Add timeline rendering
        self.setLayout(layout)


# New DatabaseView class
from PyQt5.QtWidgets import QTableWidget, QTableWidgetItem

from PyQt5.QtWidgets import QDateEdit
from PyQt5.QtCore import QDate

class DatabaseView(QWidget):
    DATE_FIELDS = {"Start Date", "Calculated End Date", "Deadline"}
    DROPDOWN_FIELDS = {
        "Internal/External": ["Internal", "External"],
        "Type": ["Milestone", "Phase", "Feature", "Type"]
    }

    def __init__(self, model, on_data_changed=None):
        print("DatabaseView: __init__ called")
        super().__init__()
        self.model = model
        self.on_data_changed = on_data_changed
        layout = QVBoxLayout()
        layout.addWidget(QLabel("Database View (Editable)"))
        self.table = QTableWidget()
        self.table.setColumnCount(len(ProjectDataModel.COLUMNS))
        self.table.setHorizontalHeaderLabels(ProjectDataModel.COLUMNS)
        # Set tooltip for Duration column
        duration_col = ProjectDataModel.COLUMNS.index("Duration (days)")
        self.table.horizontalHeaderItem(duration_col).setToolTip("Duration is in days")
        layout.addWidget(self.table)

        btn_layout = QHBoxLayout()
        add_btn = QPushButton("Add Row")
        add_btn.clicked.connect(self.add_row)
        btn_layout.addWidget(add_btn)
        del_btn = QPushButton("Delete Row")
        del_btn.clicked.connect(self.delete_row)
        btn_layout.addWidget(del_btn)
        layout.addLayout(btn_layout)

        self.setLayout(layout)
        self.refresh_table()
        self.table.cellChanged.connect(self.cell_edited)

    def refresh_table(self):
        self.table.blockSignals(True)
        self.table.setRowCount(len(self.model.rows))
    from PyQt5.QtWidgets import QPushButton, QFileDialog, QWidget, QHBoxLayout, QLabel
    from PyQt5.QtGui import QPixmap
        for row, rowdata in enumerate(self.model.rows):
            for col, colname in enumerate(ProjectDataModel.COLUMNS):
                if colname in self.DATE_FIELDS:
                    date_val = rowdata.get(colname, "")
                    date_edit = QDateEdit()
                    date_edit.setCalendarPopup(True)
                    if date_val:
                        try:
                            date = QDate.fromString(date_val, "yyyy-MM-dd")
                            if date.isValid():
                                date_edit.setDate(date)
                            else:
                                date_edit.setDate(QDate.currentDate())
                        except Exception:
                            date_edit.setDate(QDate.currentDate())
                    else:
                        date_edit.setDate(QDate.currentDate())
                    date_edit.dateChanged.connect(lambda d, r=row, c=col: self.date_changed(r, c, d))
                    self.table.setCellWidget(row, col, date_edit)
                    self.table.setItem(row, col, QTableWidgetItem(date_edit.date().toString("yyyy-MM-dd")))
                elif colname in self.DROPDOWN_FIELDS:
                    from PyQt5.QtWidgets import QComboBox
                    combo = QComboBox()
                    combo.addItems(self.DROPDOWN_FIELDS[colname])
                    current_val = rowdata.get(colname, "")
                    if current_val in self.DROPDOWN_FIELDS[colname]:
                        combo.setCurrentText(current_val)
                    combo.currentTextChanged.connect(lambda val, r=row, c=col: self.dropdown_changed(r, c, val))
                    self.table.setCellWidget(row, col, combo)
                    self.table.setItem(row, col, QTableWidgetItem(combo.currentText()))
                elif colname == "Images":
                    # Add a button to upload/select image file and show preview
                    widget = QWidget()
                    hbox = QHBoxLayout()
                    hbox.setContentsMargins(0, 0, 0, 0)
                    btn = QPushButton("Upload Image")
                    img_label = QLabel()
                    img_label.setFixedSize(48, 48)
                    img_label.setScaledContents(True)
                    def open_file_dialog(row=row, col=col):
                        fname, _ = QFileDialog.getOpenFileName(self, "Select Image", "", "Image Files (*.png *.jpg *.jpeg *.bmp *.gif)")
                        if fname:
                            self.model.rows[row][colname] = fname
                            pixmap = QPixmap(fname)
                            if not pixmap.isNull():
                                img_label.setPixmap(pixmap.scaled(48, 48))
                            self.table.setItem(row, col, QTableWidgetItem(fname.split("/")[-1] or fname.split("\\")[-1]))
                            if self.on_data_changed:
                                self.on_data_changed()
                    btn.clicked.connect(open_file_dialog)
                    hbox.addWidget(btn)
                    hbox.addWidget(img_label)
                    widget.setLayout(hbox)
                    self.table.setCellWidget(row, col, widget)
                    # Show preview if present
                    img_val = rowdata.get(colname, "")
                    if img_val:
                        pixmap = QPixmap(img_val)
                        if not pixmap.isNull():
                            img_label.setPixmap(pixmap.scaled(48, 48))
                        self.table.setItem(row, col, QTableWidgetItem(img_val.split("/")[-1] or img_val.split("\\")[-1]))
                    else:
                        img_label.clear()
                        self.table.setItem(row, col, QTableWidgetItem(""))
                else:
                    self.table.setItem(row, col, QTableWidgetItem(rowdata.get(colname, "")))
        self.table.blockSignals(False)

    def add_row(self):
        data = []
        for col in ProjectDataModel.COLUMNS:
            if col == "Duration (days)":
                data.append("1")
            elif col == "Internal/External":
                data.append("Internal")
            else:
                data.append("")
        idx = self.model.add_row(data)
        self.refresh_table()
        if self.on_data_changed:
            self.on_data_changed()

    def delete_row(self):
        row = self.table.currentRow()
        if row >= 0:
            self.model.delete_row(row)
            self.refresh_table()
            if self.on_data_changed:
                self.on_data_changed()


    def cell_edited(self, row, col):
        colname = ProjectDataModel.COLUMNS[col]
        if colname in self.DATE_FIELDS:
            widget = self.table.cellWidget(row, col)
            if widget:
                date_val = widget.date().toString("yyyy-MM-dd")
                self.model.rows[row][colname] = date_val
        elif colname in self.DROPDOWN_FIELDS:
            widget = self.table.cellWidget(row, col)
            if widget:
                self.model.rows[row][colname] = widget.currentText()
        else:
            val = self.table.item(row, col).text()
            self.model.rows[row][colname] = val
        if self.on_data_changed:
            self.on_data_changed()

    def dropdown_changed(self, row, col, value):
        colname = ProjectDataModel.COLUMNS[col]
        self.model.rows[row][colname] = value
        self.table.blockSignals(True)
        self.table.setItem(row, col, QTableWidgetItem(value))
        self.table.blockSignals(False)
        if self.on_data_changed:
            self.on_data_changed()

    def date_changed(self, row, col, qdate):
        colname = ProjectDataModel.COLUMNS[col]
        date_val = qdate.toString("yyyy-MM-dd")
        self.model.rows[row][colname] = date_val
        self.table.blockSignals(True)
        self.table.setItem(row, col, QTableWidgetItem(date_val))
        self.table.blockSignals(False)
        if self.on_data_changed:
            self.on_data_changed()


class MainWindow(QMainWindow):
    def __init__(self, model):
        print("MainWindow: __init__ called")
        super().__init__()
        self.setWindowTitle("Project Management App")
        self.resize(1200, 700)

        self.model = model

        # Sidebar for view selection
        self.sidebar = QListWidget()
        self.sidebar.addItems([
            "Project Tree",
            "Gantt Chart",
            "Calendar",
            "Project Timeline",
            "Database"
        ])
        self.sidebar.currentRowChanged.connect(self.display_view)

        # Stacked widget for views
        self.project_tree_view = ProjectTreeView(self.model)
        self.gantt_chart_view = GanttChartView()
        self.calendar_view = CalendarView()
        self.timeline_view = TimelineView()
        self.database_view = DatabaseView(self.model, on_data_changed=self.on_data_changed)

        self.views = QStackedWidget()
        self.views.addWidget(self.project_tree_view)
        self.views.addWidget(self.gantt_chart_view)
        self.views.addWidget(self.calendar_view)
        self.views.addWidget(self.timeline_view)
        self.views.addWidget(self.database_view)

        # Layout
        main_layout = QHBoxLayout()
        main_layout.addWidget(self.sidebar)
        main_layout.addWidget(self.views, 1)

        container = QWidget()
        container.setLayout(main_layout)
        self.setCentralWidget(container)

        self.sidebar.setCurrentRow(4)  # Start on Database view for editing

    def display_view(self, index):
        self.views.setCurrentIndex(index)
        if index == 0:
            self.project_tree_view.refresh()
        elif index == 4:
            self.database_view.refresh_table()

    def on_data_changed(self):
        self.project_tree_view.refresh()

if __name__ == "__main__":
    print("__main__ block: Creating QApplication")
    app = QApplication(sys.argv)
    print("__main__ block: Creating ProjectDataModel")
    model = ProjectDataModel()
    print("__main__ block: Creating MainWindow")
    window = MainWindow(model)
    print("__main__ block: Showing MainWindow")
    window.show()
    sys.exit(app.exec_())
