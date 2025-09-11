import sys
from PyQt5.QtWidgets import QApplication, QMainWindow, QStackedWidget, QListWidget, QWidget, QHBoxLayout, QVBoxLayout, QLabel

from PyQt5.QtWidgets import QTreeWidget, QTreeWidgetItem, QPushButton, QInputDialog, QMessageBox, QMenu

class ProjectTreeView(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout()
        layout.addWidget(QLabel("Project Tree (Editable)"))

        self.tree = QTreeWidget()
        self.tree.setHeaderLabels(["Project Part", "Data"])
        self.tree.setContextMenuPolicy(3)  # Qt.CustomContextMenu
        self.tree.customContextMenuRequested.connect(self.open_menu)
        layout.addWidget(self.tree)

        btn_layout = QHBoxLayout()
        add_btn = QPushButton("Add Root Part")
        add_btn.clicked.connect(self.add_root_part)
        btn_layout.addWidget(add_btn)
        layout.addLayout(btn_layout)

        self.setLayout(layout)

    def add_root_part(self):
        name, ok = QInputDialog.getText(self, "Add Project Part", "Enter part name:")
        if ok and name:
            data, ok2 = QInputDialog.getText(self, "Add Data", "Enter associated data:")
            if ok2:
                item = QTreeWidgetItem([name, data])
                item.setFlags(item.flags() | 2)  # Qt.ItemIsEditable
                self.tree.addTopLevelItem(item)

    def open_menu(self, pos):
        item = self.tree.itemAt(pos)
        menu = QMenu()
        if item:
            menu.addAction("Add Child", lambda: self.add_child(item))
            menu.addAction("Edit", lambda: self.edit_item(item))
            menu.addAction("Delete", lambda: self.delete_item(item))
        else:
            menu.addAction("Add Root Part", self.add_root_part)
        menu.exec_(self.tree.viewport().mapToGlobal(pos))

    def add_child(self, parent_item):
        name, ok = QInputDialog.getText(self, "Add Child Part", "Enter child part name:")
        if ok and name:
            data, ok2 = QInputDialog.getText(self, "Add Data", "Enter associated data:")
            if ok2:
                child = QTreeWidgetItem([name, data])
                child.setFlags(child.flags() | 2)  # Qt.ItemIsEditable
                parent_item.addChild(child)
                parent_item.setExpanded(True)

    def edit_item(self, item):
        name, ok = QInputDialog.getText(self, "Edit Part Name", "Edit part name:", text=item.text(0))
        if ok and name:
            data, ok2 = QInputDialog.getText(self, "Edit Data", "Edit associated data:", text=item.text(1))
            if ok2:
                item.setText(0, name)
                item.setText(1, data)

    def delete_item(self, item):
        reply = QMessageBox.question(self, "Delete", f"Delete '{item.text(0)}'?", QMessageBox.Yes | QMessageBox.No)
        if reply == QMessageBox.Yes:
            root = self.tree.invisibleRootItem()
            (item.parent() or root).removeChild(item)

class GanttChartView(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout()
        layout.addWidget(QLabel("Gantt Chart (Read-Only)"))
        # TODO: Add Gantt chart rendering
        self.setLayout(layout)

class CalendarView(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout()
        layout.addWidget(QLabel("Calendar (Read-Only)"))
        # TODO: Add calendar rendering
        self.setLayout(layout)

class TimelineView(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout()
        layout.addWidget(QLabel("Project Timeline (Read-Only)"))
        # TODO: Add timeline rendering
        self.setLayout(layout)


# New DatabaseView class
from PyQt5.QtWidgets import QTableWidget, QTableWidgetItem

class DatabaseView(QWidget):
    def __init__(self, project_tree_widget=None):
        super().__init__()
        self.project_tree_widget = project_tree_widget
        layout = QVBoxLayout()
        self.table = QTableWidget()
        self.table.setColumnCount(2)
        self.table.setHorizontalHeaderLabels(["Project Part", "Data"])
        layout.addWidget(QLabel("Database View (All Project Parts and Data)"))
        layout.addWidget(self.table)
        self.setLayout(layout)
        self.refresh_table()

    def refresh_table(self):
        if not self.project_tree_widget:
            self.table.setRowCount(0)
            return
        items = []
        def collect_items(parent):
            for i in range(parent.childCount()):
                item = parent.child(i)
                items.append((item.text(0), item.text(1)))
                collect_items(item)
        root = self.project_tree_widget.invisibleRootItem()
        for i in range(self.project_tree_widget.topLevelItemCount()):
            item = self.project_tree_widget.topLevelItem(i)
            items.append((item.text(0), item.text(1)))
            collect_items(item)
        self.table.setRowCount(len(items))
        for row, (name, data) in enumerate(items):
            self.table.setItem(row, 0, QTableWidgetItem(name))
            self.table.setItem(row, 1, QTableWidgetItem(data))

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Project Management App")
        self.resize(900, 600)

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
        self.project_tree_view = ProjectTreeView()
        self.gantt_chart_view = GanttChartView()
        self.calendar_view = CalendarView()
        self.timeline_view = TimelineView()
        self.database_view = DatabaseView(self.project_tree_view.tree)

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

        self.sidebar.setCurrentRow(0)

    def display_view(self, index):
        self.views.setCurrentIndex(index)
        # Refresh database view when selected
        if index == 4:
            self.database_view.refresh_table()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())
