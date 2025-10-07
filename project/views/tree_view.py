from project.qt_bindings import *
from project.helpers import resolve_resource_path, load_holiday_dates

# Move ProjectTreeView + Image preview logic (ProjectTreeView class only)
# Remove unrelated classes.

class ProjectTreeView:
    def __init__(self, parent=None):
        super(ProjectTreeView, self).__init__(parent)
        # Initialize your tree view here

    def load_project(self, project_path):
        # Logic to load project into the tree view
        pass

    def refresh_view(self):
        # Logic to refresh the tree view
        pass

    def context_menu_event(self, event):
        # Logic for context menu in the tree view
        pass

    # Add more methods as required for the ProjectTreeView functionality

def preview_image(image_path):
    # Logic to preview image
    pass

def on_holiday_dates_loaded(dates):
    # Logic to execute when holiday dates are loaded
    pass

# Connect signals and slots as required