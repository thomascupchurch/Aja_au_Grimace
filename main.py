# Minimal ImageCellWidget for image upload/preview in DatabaseView
from PyQt5.QtWidgets import QWidget, QHBoxLayout, QLabel, QPushButton, QFileDialog
from PyQt5.QtGui import QPixmap
import shutil

class ImageCellWidget(QWidget):
    def __init__(self, parent, row, col, model, on_data_changed=None):
        super().__init__(parent)
        self.row = row
        self.col = col
        self.model = model
        self.on_data_changed = on_data_changed
        layout = QHBoxLayout()
        self.img_label = QLabel()
        self.img_label.setFixedSize(48, 48)
        layout.addWidget(self.img_label)
        self.btn = QPushButton("Upload")
        self.btn.clicked.connect(self.upload_image)
        layout.addWidget(self.btn)
        self.setLayout(layout)
        self.refresh()

    def upload_image(self):
        fname, _ = QFileDialog.getOpenFileName(self, "Select Image", "", "Image Files (*.png *.jpg *.jpeg *.bmp *.gif)")
        if fname:
            images_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "images")
            if not os.path.exists(images_dir):
                os.makedirs(images_dir)
            base = os.path.basename(fname)
            dest = os.path.join(images_dir, base)
            count = 1
            orig_base, ext = os.path.splitext(base)
            while os.path.exists(dest):
                dest = os.path.join(images_dir, f"{orig_base}_{count}{ext}")
                count += 1
            shutil.copy2(fname, dest)
            rel_path = os.path.relpath(dest, os.path.dirname(os.path.abspath(__file__)))
            self.model.rows[self.row][self.model.COLUMNS[self.col]] = rel_path
            self.model.save_to_db()
            self.refresh()
            if self.on_data_changed:
                self.on_data_changed()

    def refresh(self):
        img_val = self.model.rows[self.row].get(self.model.COLUMNS[self.col], "")
        if img_val:
            img_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), img_val)
            pixmap = QPixmap(img_path)
            if not pixmap.isNull():
                self.img_label.setPixmap(pixmap.scaled(48, 48))
            else:
                self.img_label.clear()
        else:
            self.img_label.clear()
# DEBUG: Script started
print('DEBUG: main.py script started')
import os
# Add missing import for sqlite3
import sqlite3
# PyQt5 imports (all at top for clarity and to avoid NameError)
from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFileDialog, QTableWidget, QTableWidgetItem, QDateEdit,
    QTreeWidget, QTreeWidgetItem, QInputDialog, QMessageBox, QMenu, QStackedWidget, QListWidget,
    QGraphicsView, QGraphicsScene, QGraphicsEllipseItem, QGraphicsTextItem, QGraphicsLineItem
)
from PyQt5.QtGui import QPixmap
from PyQt5.QtCore import QPointF, Qt, QDate

import sys
from PyQt5.QtWidgets import QApplication, QMainWindow, QStackedWidget, QListWidget, QWidget, QHBoxLayout, QVBoxLayout, QLabel

from PyQt5.QtWidgets import QTreeWidget, QTreeWidgetItem, QPushButton, QInputDialog, QMessageBox, QMenu


# Central data model for project parts
class ProjectDataModel:
    def update_calculated_end_dates(self):
        import datetime
        for row in self.rows:
            start = row.get("Start Date", "")
            duration = row.get("Duration (days)", "")
            try:
                if start and duration:
                    start_date = datetime.datetime.strptime(start, "%Y-%m-%d")
                    days = int(duration)
                    end_date = start_date + datetime.timedelta(days=days)
                    row["Calculated End Date"] = end_date.strftime("%Y-%m-%d")
                else:
                    row["Calculated End Date"] = ""
            except Exception:
                row["Calculated End Date"] = ""
    DB_FILE = "project_data.db"

    def create_table(self):
        with sqlite3.connect(self.DB_FILE) as conn:
            c = conn.cursor()
            fields = ", ".join([f'"{col}" TEXT' for col in self.COLUMNS])
            c.execute(f"""
                CREATE TABLE IF NOT EXISTS project_parts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    {fields}
                )
            """)
            conn.commit()

    def load_from_db(self):
        self.rows.clear()
        if not os.path.exists(self.DB_FILE):
            self.create_table()
            return
        with sqlite3.connect(self.DB_FILE) as conn:
            c = conn.cursor()
            c.execute(f"SELECT {', '.join([f'\"{col}\"' for col in self.COLUMNS])} FROM project_parts")
            for row in c.fetchall():
                row_dict = {col: val for col, val in zip(self.COLUMNS, row)}
                print(f"Loaded from DB: {row_dict}")
                self.rows.append(row_dict)
        self.update_calculated_end_dates()

    def save_to_db(self):
        self.update_calculated_end_dates()
        self.create_table()
        with sqlite3.connect(self.DB_FILE) as conn:
            c = conn.cursor()
            c.execute("DELETE FROM project_parts")
            for row in self.rows:
                values = [row.get(col, "") for col in self.COLUMNS]
                placeholders = ", ".join(["?" for _ in self.COLUMNS])
                c.execute(f"INSERT INTO project_parts ({', '.join([f'\"{col}\"' for col in self.COLUMNS])}) VALUES ({placeholders})", values)
            conn.commit()
    COLUMNS = [
        "Project Part", "Parent", "Children", "Start Date", "Duration (days)", "Internal/External", "Dependencies", "Type", "Calculated End Date", "Deadline", "Resources", "Notes", "Responsible", "Images"
    ]
    def __init__(self):
        self.rows = []  # Each row is a dict with keys as COLUMNS
        self.load_from_db()

    def add_row(self, data, parent=None):
        row = {col: val for col, val in zip(self.COLUMNS, data)}
        row['Parent'] = parent
        self.rows.append(row)
        return len(self.rows) - 1

    def update_row(self, idx, data):
        for i, col in enumerate(self.COLUMNS):
            self.rows[idx][col] = data[i]

    def delete_row(self, idx):
        # Remove children recursively
        children = [i for i, r in enumerate(self.rows) if r.get('Parent') == idx]
        for c in sorted(children, reverse=True):
            self.delete_row(c)
        del self.rows[idx]
        # Update parent indices
        for r in self.rows:
            if r.get('Parent') is not None and isinstance(r.get('Parent'), int) and r.get('Parent') > idx:
                r['Parent'] -= 1

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
        # Build a mapping from part name to row index
        name_to_index = {r["Project Part"]: i for i, r in enumerate(self.model.rows)}
        # Build a mapping from parent name to list of child indices
        parent_to_children = {}
        for i, r in enumerate(self.model.rows):
            parent = r.get("Parent", "")
            parent_to_children.setdefault(parent, []).append(i)

        def add_items(parent_widget, parent_name, visited=None):
            if visited is None:
                visited = set()
            for idx in parent_to_children.get(parent_name or "", []):
                row = self.model.rows[idx]
                part_name = row["Project Part"]
                if part_name in visited:
                    continue  # Prevent cycles
                visited.add(part_name)
                item = QTreeWidgetItem([row[col] for col in ProjectDataModel.COLUMNS])
                if parent_widget is None:
                    self.tree.addTopLevelItem(item)
                else:
                    parent_widget.addChild(item)
                add_items(item, part_name, visited.copy())
        add_items(None, "")

class GanttChartView(QWidget):
    def __init__(self):
        print("GanttChartView: __init__ called")
        super().__init__()
        layout = QVBoxLayout()
        layout.addWidget(QLabel("Gantt Chart (Read-Only)"))
        self.view = ZoomableGraphicsView()
        self.scene = QGraphicsScene()
        self.view.setScene(self.scene)
        layout.addWidget(self.view)
        self.setLayout(layout)

# Add a custom QGraphicsView subclass for zooming
from PyQt5.QtWidgets import QGraphicsView
from PyQt5.QtCore import Qt

class ZoomableGraphicsView(QGraphicsView):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._zoom = 0
        self.setDragMode(QGraphicsView.ScrollHandDrag)

    def wheelEvent(self, event):
        if event.modifiers() & Qt.ControlModifier:
            if event.angleDelta().y() > 0:
                self.zoomIn()
            else:
                self.zoomOut()
        else:
            super().wheelEvent(event)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Plus or event.key() == Qt.Key_Equal:
            self.zoomIn()
        elif event.key() == Qt.Key_Minus:
            self.zoomOut()
        else:
            super().keyPressEvent(event)

    def zoomIn(self):
        self._zoom += 1
        self.scale(1.2, 1.2)

    def zoomOut(self):
        self._zoom -= 1
        self.scale(1/1.2, 1/1.2)

    def render_gantt(self, model):
        self.scene.clear()
        # Get all rows with valid start date and duration
        rows = [r for r in model.rows if r.get("Start Date") and r.get("Duration (days)")]
        if not rows:
            return
        # Parse dates and durations
        import datetime
        bar_height = 24
        bar_gap = 10
        min_date = None
        max_date = None
        bars = []
        name_to_bar = {}
        for i, row in enumerate(rows):
            try:
                start = datetime.datetime.strptime(row["Start Date"], "%Y-%m-%d")
                duration = int(row["Duration (days)"])
                end = start + datetime.timedelta(days=duration)
                if min_date is None or start < min_date:
                    min_date = start
                if max_date is None or end > max_date:
                    max_date = end
                bars.append((row["Project Part"], start, duration, i, row))
            except Exception:
                continue
        if not bars:
            return
        # Draw bars and record their positions
        from PyQt5.QtGui import QColor
        gantt_color = QColor("#FF8200")
        for name, start, duration, idx, row in bars:
            x = (start - min_date).days * 10 + 100  # 10px per day, offset for labels
            y = idx * (bar_height + bar_gap) + 40
            width = max(duration * 10, 10)
            rect = self.scene.addRect(x, y, width, bar_height)
            rect.setBrush(gantt_color)
            label = self.scene.addText(name)
            label.setPos(10, y)
            date_label = self.scene.addText(start.strftime("%Y-%m-%d"))
            date_label.setPos(x, y + bar_height)
            name_to_bar[name] = (x, y, width, bar_height)

        # Draw x-axis with date marks
        if min_date and max_date:
            axis_y = 30
            axis_x0 = 100
            axis_x1 = (max_date - min_date).days * 10 + 100 + 40
            self.scene.addLine(axis_x0, axis_y, axis_x1, axis_y)
            # Draw tick marks and date labels every 7 days
            tick_interval = 7
            total_days = (max_date - min_date).days
            for d in range(0, total_days + 1, tick_interval):
                tick_x = axis_x0 + d * 10
                self.scene.addLine(tick_x, axis_y - 5, tick_x, axis_y + 5)
                tick_date = min_date + datetime.timedelta(days=d)
                tick_label = self.scene.addText(tick_date.strftime("%Y-%m-%d"))
                tick_label.setPos(tick_x - 30, axis_y - 25)

        # Draw dependency lines (red, thick, robust to whitespace/case)
        from PyQt5.QtGui import QPen, QColor
        dep_pen_red = QPen(QColor(220, 0, 0))
        dep_pen_red.setWidth(3)
        dep_pen_black = QPen(QColor(0, 0, 0))
        dep_pen_black.setWidth(3)
        import datetime
        # Build a mapping from name to (start, end) dates
        name_to_dates = {}
        for name, start, duration, idx, row in bars:
            end = start + datetime.timedelta(days=duration)
            name_to_dates[name] = (start, end)
        for name, start, duration, idx, row in bars:
            deps = row.get("Dependencies", "")
            if not deps:
                continue
            for dep_name in [d.strip() for d in deps.split(",") if d.strip()]:
                # Case-insensitive match
                dep_key = next((k for k in name_to_bar if k.strip().lower() == dep_name.lower()), None)
                this_key = next((k for k in name_to_bar if k.strip().lower() == name.lower()), None)
                if dep_key and this_key:
                    dep_x, dep_y, dep_width, dep_height = name_to_bar[dep_key]
                    this_x, this_y, _, _ = name_to_bar[this_key]
                    # Determine arrow color
                    dep_end = name_to_dates.get(dep_key, (None, None))[1]
                    this_start = name_to_dates.get(this_key, (None, None))[0]
                    if dep_end and this_start and this_start > dep_end:
                        pen = dep_pen_black
                    else:
                        pen = dep_pen_red
                    # Draw a line from end of dependency bar to start of this bar
                    self.scene.addLine(dep_x + dep_width, dep_y + bar_height // 2, this_x, this_y + bar_height // 2, pen)
                    # Draw a small arrowhead
                    arrow_size = 8
                    arrow_x = this_x
                    arrow_y = this_y + bar_height // 2
                    self.scene.addLine(arrow_x, arrow_y, arrow_x - arrow_size, arrow_y - arrow_size, pen)
                    self.scene.addLine(arrow_x, arrow_y, arrow_x - arrow_size, arrow_y + arrow_size, pen)
        self.view.setSceneRect(0, 0, 800, max(300, len(bars)*(bar_height+bar_gap)+60))

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
    "Type": ["Milestone", "Phase", "Feature", "Item"]
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
        for row, rowdata in enumerate(self.model.rows):
            for col, colname in enumerate(ProjectDataModel.COLUMNS):
                # Only use QDateEdit for editable date fields, not Calculated End Date
                if colname in self.DATE_FIELDS and colname != "Calculated End Date":
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
                elif colname == "Calculated End Date":
                    # Show as read-only text
                    val = rowdata.get(colname, "")
                    self.table.setItem(row, col, QTableWidgetItem(val))
                elif colname in self.DROPDOWN_FIELDS or colname == "Parent":
                    from PyQt5.QtWidgets import QComboBox
                    combo = QComboBox()
                    if colname == "Parent":
                        # List all other project part names except this row
                        part_names = [self.model.rows[i]["Project Part"] for i in range(len(self.model.rows)) if i != row]
                        combo.addItem("")  # Allow no parent
                        combo.addItems(part_names)
                        current_val = rowdata.get("Parent", "")
                        if current_val in part_names:
                            combo.setCurrentText(current_val)
                        combo.currentTextChanged.connect(lambda val, r=row, c=col: self.dropdown_changed(r, c, val))
                        self.table.setCellWidget(row, col, combo)
                        self.table.setItem(row, col, QTableWidgetItem(combo.currentText()))
                    else:
                        combo.addItems(self.DROPDOWN_FIELDS[colname])
                        current_val = rowdata.get(colname, "")
                        if current_val in self.DROPDOWN_FIELDS[colname]:
                            combo.setCurrentText(current_val)
                        combo.currentTextChanged.connect(lambda val, r=row, c=col: self.dropdown_changed(r, c, val))
                        self.table.setCellWidget(row, col, combo)
                        self.table.setItem(row, col, QTableWidgetItem(combo.currentText()))
                elif colname == "Images":
                    img_widget = ImageCellWidget(self, row, col, self.model, self.on_data_changed)
                    self.table.setCellWidget(row, col, img_widget)
                    img_widget.refresh()  # Ensure preview is updated after loading
                    img_val = rowdata.get(colname, "")
                    if img_val:
                        self.table.setItem(row, col, QTableWidgetItem(img_val.split("/")[-1] or img_val.split("\\")[-1]))
                    else:
                        self.table.setItem(row, col, QTableWidgetItem(""))
                elif colname == "Children":
                    # Read-only: list all project parts whose parent is this part
                    this_part = rowdata.get("Project Part", "")
                    children = [r["Project Part"] for r in self.model.rows if r.get("Parent", "") == this_part]
                    self.table.setItem(row, col, QTableWidgetItem(", ".join(children)))
                else:
                    self.table.setItem(row, col, QTableWidgetItem(rowdata.get(colname, "")))
        self.table.blockSignals(False)
        # Ensure all image widgets are refreshed after table is populated
        for row in range(self.table.rowCount()):
            for col in range(self.table.columnCount()):
                colname = ProjectDataModel.COLUMNS[col]
                if colname == "Images":
                    widget = self.table.cellWidget(row, col)
                    if widget and hasattr(widget, "refresh"):
                        widget.refresh()

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
        self.model.save_to_db()
        
        self.refresh_table()
        if self.on_data_changed:
            self.on_data_changed()

    def delete_row(self):
        row = self.table.currentRow()
        if row >= 0:
            self.model.delete_row(row)
            self.model.save_to_db()
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
        elif colname in self.DROPDOWN_FIELDS or colname == "Parent":
            widget = self.table.cellWidget(row, col)
            if widget:
                self.model.rows[row][colname] = widget.currentText()
        else:
            val = self.table.item(row, col).text()
            self.model.rows[row][colname] = val
        self.model.update_calculated_end_dates()
        self.model.save_to_db()
        self.refresh_table()
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
    def on_data_changed(self):
        # Handle data changes if needed (refresh views, etc.)
        pass
    def display_view(self, index):
        self.views.setCurrentIndex(index)
        if index == 0:
            self.project_tree_view.refresh()
        elif index == 1:
            self.gantt_chart_view.render_gantt(self.model)
        elif index == 4:
            self.database_view.refresh_table()
    def __init__(self, model):
        print("MainWindow: __init__ called")
        super().__init__()
        self.setWindowTitle("Project Management App")
        self.resize(1200, 700)
        # Set global stylesheet for background and foreground colors
        self.setStyleSheet("""
            QWidget {
                background-color: #4B4B4B;
                color: #FF8200;
            }
            QLineEdit, QTableWidget, QTreeWidget, QComboBox, QDateEdit, QHeaderView::section {
                background-color: #333333;
                color: #FF8200;
                border: 1px solid #FF8200;
            }
            QPushButton {
                background-color: #333333;
                color: #FF8200;
                border: 1px solid #FF8200;
            }
            QTableWidget QTableCornerButton::section {
                background-color: #333333;
            }
        """)

        self.model = model

        # Header with centered logo
        header_layout = QHBoxLayout()
        header_layout.addStretch(1)
        logo_label = QLabel()
        logo_pixmap = QPixmap(os.path.join(os.path.dirname(os.path.abspath(__file__)), "LSI_Power_T_Combo_Logo.png"))
        logo_label.setPixmap(logo_pixmap.scaledToHeight(64, Qt.SmoothTransformation))
        header_layout.addWidget(logo_label, alignment=Qt.AlignCenter)
        header_layout.addStretch(1)

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
        main_layout = QVBoxLayout()
        main_layout.addLayout(header_layout)
        content_layout = QHBoxLayout()
        content_layout.addWidget(self.sidebar)
        content_layout.addWidget(self.views, 1)
        main_layout.addLayout(content_layout)

        container = QWidget()
        container.setLayout(main_layout)
        self.setCentralWidget(container)

        self.sidebar.setCurrentRow(4)  # Start on Database view for editing

 # --- Ensure the app starts ---
if __name__ == "__main__":
    print('DEBUG: Entered __main__ block')
    import sys
    app = QApplication(sys.argv)
    print('DEBUG: QApplication created')
    model = ProjectDataModel()
    print('DEBUG: ProjectDataModel created')
    window = MainWindow(model)
    print('DEBUG: MainWindow created')
    window.show()
    print('DEBUG: window.show() called')
    sys.exit(app.exec_())