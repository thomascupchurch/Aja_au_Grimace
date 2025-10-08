from project.qt_bindings import (QMainWindow, QWidget, QHBoxLayout, QListWidget,
                                 QStackedWidget, QStatusBar)
from project.model import ProjectDataModel
from project.logging_utils import log_event
from project.helpers import resolve_resource_path, load_holiday_dates, save_holiday_dates
from project.views.tree_view import ProjectTreeView
from project.views.gantt_view import GanttChartView
from project.views.timeline_view import TimelineView
from project.views.calendar_view import CalendarView
from project.views.database_view import DatabaseView
from project.views.progress_dashboard import ProgressDashboard
from project.views.cost_estimates_view import CostEstimatesView
from project.dialogs.export_settings import ExportSettingsDialog, PricingSettingsDialog
from project.dialogs.first_run import FirstRunDialog
from project.dialogs.conflict_resolution import ConflictResolutionDialog

class MainWindow(QMainWindow):
    def __init__(self, model):
        super().__init__()
        self.model = model
        self.setWindowTitle("Project Planner")
        self.resize(1400, 900)

        root = QWidget()
        lay = QHBoxLayout(root)
        self.setCentralWidget(root)

        self.sidebar = QListWidget()
        self.sidebar.addItems([
            "Project Tree","Gantt","Timeline","Calendar","Database","Dashboard","Costs"
        ])
        lay.addWidget(self.sidebar)

        self.stack = QStackedWidget()
        lay.addWidget(self.stack, 1)

        self.project_tree_view   = ProjectTreeView(model)
        self.gantt_chart_view    = GanttChartView(model)
        self.timeline_view       = TimelineView(model)
        self.calendar_view       = CalendarView(model)
        self.database_view       = DatabaseView(model)
        self.progress_dashboard  = ProgressDashboard(model)
        self.cost_estimates_view = CostEstimatesView(model) if CostEstimatesView else QWidget()

        for w in (self.project_tree_view, self.gantt_chart_view, self.timeline_view,
                  self.calendar_view, self.database_view, self.progress_dashboard,
                  self.cost_estimates_view):
            self.stack.addWidget(w)

        self.sidebar.currentRowChanged.connect(self.stack.setCurrentIndex)
        self.sidebar.setCurrentRow(0)

        sb = QStatusBar()
        self.setStatusBar(sb)
        sb.showMessage("Ready")

        # Load holiday dates
        self.holiday_dates = load_holiday_dates()

    def new_project(self):
        # TODO: Implement new project creation
        pass

    def open_project(self):
        # TODO: Implement project opening
        pass

    def save_project(self):
        # TODO: Implement project saving
        pass

    def undo(self):
        # TODO: Implement undo action
        pass

    def redo(self):
        # TODO: Implement redo action
        pass

    def open_preferences(self):
        # TODO: Implement preferences dialog
        pass

    def zoom_in(self):
        # TODO: Implement zoom in functionality
        pass

    def zoom_out(self):
        # TODO: Implement zoom out functionality
        pass

    def reset_view(self):
        # TODO: Implement reset view functionality
        pass

    def show_about_dialog(self):
        # TODO: Implement about dialog
        pass

    def closeEvent(self, event):
        # Override the close event to prompt for confirmation
        reply = QMessageBox.question(self, "Confirm Exit", "Are you sure you want to exit?",
                                     QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if reply == QMessageBox.Yes:
            event.accept()
        else:
            event.ignore()