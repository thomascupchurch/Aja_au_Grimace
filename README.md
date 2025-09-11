# Project Management App

This is a Python-based project management application using PyQt5. It allows you to manage projects with the following features:

- **Project Tree**: Add, edit, and delete project parts and associated data (the only editable view).
- **Gantt Chart**: Visualize project parts on a Gantt chart (read-only, generated on demand).
- **Calendar**: View project parts on a calendar (read-only, generated on demand).
- **Project Timeline**: See a linear timeline of project parts (read-only, generated on demand).

## How to Run

1. Ensure you have Python 3.7+ and the required packages installed:
   - PyQt5
   - matplotlib

2. Run the app:

   ```powershell
   .venv\Scripts\python.exe main.py
   ```

## Editing Data
- All project data can only be edited in the Project Tree view. All other views are for visualization only.

---

This is an initial scaffold. Further customization and features can be added as needed.
