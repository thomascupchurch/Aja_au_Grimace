# Paste FULL ProjectDataModel definition (second/full one from main.py) here.
# Remove any UI imports (QWidgets). Keep only sqlite, datetime, json, etc.
# Ensure resolve_resource_path / holidays helpers if model uses them OR import from helpers.

import sqlite3
from datetime import datetime
import json

# If the model uses resolve_resource_path or holidays helpers, ensure they are imported
# from helpers import resolve_resource_path, holidays

class ProjectDataModel:
    def __init__(self, db_path):
        self.db_path = db_path
        self.connection = None

    def connect(self):
        """Establish a database connection."""
        self.connection = sqlite3.connect(self.db_path)
        self.connection.row_factory = sqlite3.Row

    def close(self):
        """Close the database connection."""
        if self.connection:
            self.connection.close()

    def fetch_projects(self):
        """Fetch all projects from the database."""
        with self.connection:
            return [dict(row) for row in self.connection.execute("SELECT * FROM projects")]

    def add_project(self, project_data):
        """Add a new project to the database."""
        with self.connection:
            self.connection.execute(
                "INSERT INTO projects (name, start_date, end_date) VALUES (?, ?, ?)",
                (project_data['name'], project_data['start_date'], project_data['end_date'])
            )

    def update_project(self, project_id, project_data):
        """Update an existing project in the database."""
        with self.connection:
            self.connection.execute(
                "UPDATE projects SET name = ?, start_date = ?, end_date = ? WHERE id = ?",
                (project_data['name'], project_data['start_date'], project_data['end_date'], project_id)
            )

    def delete_project(self, project_id):
        """Delete a project from the database."""
        with self.connection:
            self.connection.execute("DELETE FROM projects WHERE id = ?", (project_id,))

    # Additional methods for handling project data can be added here