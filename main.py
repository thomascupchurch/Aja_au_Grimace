from PyQt5.QtWidgets import QDialog, QFormLayout, QLineEdit, QTextEdit, QComboBox, QDateEdit, QPushButton, QFileDialog, QLabel, QHBoxLayout
from PyQt5.QtWidgets import QMessageBox
from PyQt5.QtCore import QDate


# Minimal ImageCellWidget for image upload/preview in DatabaseView
from PyQt5.QtWidgets import QWidget, QHBoxLayout, QVBoxLayout, QLabel, QPushButton, QFileDialog, QMainWindow, QApplication, QListWidget, QTreeWidget, QGraphicsScene, QStackedWidget, QDialog
from PyQt5.QtWidgets import QTreeWidgetItem
import os
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

    def refresh(self):
        img_path = self.model.rows[self.row].get(self.model.COLUMNS[self.col], "")
        if img_path:
            import sys
            if getattr(sys, 'frozen', False):
                base_dir = os.path.dirname(sys.executable)
            else:
                base_dir = os.path.dirname(os.path.abspath(__file__))
            img_path_full = os.path.join(base_dir, img_path)

            pixmap = QPixmap(img_path_full)
            if not pixmap.isNull():
                self.img_label.setPixmap(pixmap.scaled(48, 48, Qt.KeepAspectRatio, Qt.SmoothTransformation))
                self.img_label.setCursor(Qt.PointingHandCursor)
                self.img_label.mousePressEvent = lambda event: self.show_full_image(img_path_full)
            else:
                self.img_label.setText("[Image not found]")
                self.img_label.setCursor(Qt.ArrowCursor)
                self.img_label.mousePressEvent = None
        else:
            self.img_label.setText("")
            self.img_label.setCursor(Qt.ArrowCursor)
            self.img_label.mousePressEvent = None

    def show_full_image(self, img_path_full):
        dlg = QDialog(self)
        dlg.setWindowTitle("Image Preview")
        vbox = QVBoxLayout(dlg)
        lbl = QLabel()
        pixmap = QPixmap(img_path_full)
        if not pixmap.isNull():
            lbl.setPixmap(pixmap.scaledToWidth(600, Qt.SmoothTransformation))
        else:
            lbl.setText("[Image not found]")
        vbox.addWidget(lbl)
        dlg.setLayout(vbox)
        dlg.exec_()

class ProjectDataModel:
    # NOTE: Append-only pattern; new progress-related columns added at end to avoid breaking older rows
    COLUMNS = [
        "Project Part", "Parent", "Children", "Start Date", "Duration (days)", "Internal/External", "Dependencies", "Type", "Calculated End Date", "Resources", "Notes", "Responsible", "Images", "Pace Link", "Attachments",
        # Progress tracking fields
        "% Complete",            # Integer 0-100 (leaf editable, parents rolled up)
        "Status",                 # Planned | In Progress | Blocked | Done | Deferred
        "Actual Start Date",      # Set when Status transitions to In Progress
        "Actual Finish Date",     # Set when Status transitions to Done
        "Baseline Start Date",    # Captured first time valid start/duration appear
        "Baseline End Date"       # Derived from baseline start + duration (working days not yet applied)
    ]
    DB_FILE = "project_data.db"

    def __init__(self):
        self.rows = []  # Each row is a dict with keys as COLUMNS
        self.ensure_schema()
        self.load_from_db()

    # --- Schema migration to add progress columns if missing ---
    def ensure_schema(self):
        import sqlite3, os
        if not os.path.exists(self.DB_FILE):
            # Table will be created later in create_table()
            return
        with sqlite3.connect(self.DB_FILE) as conn:
            c = conn.cursor()
            # Inspect existing columns
            try:
                c.execute("PRAGMA table_info(project_parts)")
                existing = [row[1] for row in c.fetchall()]  # name in 2nd column
            except Exception:
                existing = []
            to_add = [col for col in self.COLUMNS if col not in existing]
            for col in to_add:
                # Decide type based on semantic
                if col == "% Complete":
                    col_type = "INTEGER"
                elif col == "Attachments":
                    col_type = "TEXT"  # JSON list of relative paths
                else:
                    col_type = "TEXT"
                try:
                    c.execute(f'ALTER TABLE project_parts ADD COLUMN "{col}" {col_type}')
                except Exception:
                    pass
            conn.commit()

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
                if r.get('parent') == parent_idx:
                    nodes.append((i, collect(i)))
            return nodes
        return collect(None)

    def get_flat(self):
        return self.rows

    def load_from_db(self):
        import os
        import sqlite3
        self.rows.clear()
        if not os.path.exists(self.DB_FILE):
            self.create_table()
            return
        with sqlite3.connect(self.DB_FILE) as conn:
            c = conn.cursor()
            c.execute(f"SELECT {', '.join([f'\"{col}\"' for col in self.COLUMNS])} FROM project_parts")
            for row in c.fetchall():
                row_dict = {col: val for col, val in zip(self.COLUMNS, row)}
                # Default missing progress fields (older rows) if any are absent or None
                if row_dict.get("% Complete") in (None, ""):
                    row_dict["% Complete"] = 0
                if not row_dict.get("Status"):
                    row_dict["Status"] = "Planned"
                # Normalize attachments field to JSON list string
                import json as _json_att
                att_val = row_dict.get("Attachments")
                if att_val in (None, ""):
                    row_dict["Attachments"] = "[]"
                else:
                    try:
                        parsed = _json_att.loads(att_val)
                        if not isinstance(parsed, list):
                            row_dict["Attachments"] = _json_att.dumps([att_val])
                    except Exception:
                        row_dict["Attachments"] = _json_att.dumps([att_val])
                print(f"Loaded from DB: {row_dict}")
                self.rows.append(row_dict)
        self.update_calculated_end_dates()
        # After loading & computing end dates, establish baseline if missing
        self.capture_missing_baselines()

    def capture_missing_baselines(self):
        import datetime
        for r in self.rows:
            start = r.get("Start Date")
            dur = r.get("Duration (days)")
            if start and dur and (not r.get("Baseline Start Date") or not r.get("Baseline End Date")):
                try:
                    sd = datetime.datetime.strptime(start, "%m-%d-%Y")
                    d = int(dur)
                    end = sd + datetime.timedelta(days=d)
                    if not r.get("Baseline Start Date"):
                        r["Baseline Start Date"] = sd.strftime("%m-%d-%Y")
                    if not r.get("Baseline End Date"):
                        r["Baseline End Date"] = end.strftime("%m-%d-%Y")
                except Exception:
                    pass

    def save_to_db(self):
        import sqlite3
        self.update_calculated_end_dates()
        # Roll-ups before save to persist auto-calculated parent progress
        self.rollup_progress()
        self.create_table()
        with sqlite3.connect(self.DB_FILE) as conn:
            c = conn.cursor()
            c.execute("DELETE FROM project_parts")
            for row in self.rows:
                values = [row.get(col, "") for col in self.COLUMNS]
                placeholders = ", ".join(["?" for _ in self.COLUMNS])
                c.execute(f"INSERT INTO project_parts ({', '.join([f'\"{col}\"' for col in self.COLUMNS])}) VALUES ({placeholders})", values)
            conn.commit()

    def create_table(self):
        import sqlite3
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

    def update_calculated_end_dates(self):
        import datetime
        for row in self.rows:
            start = row.get("Start Date", "")
            duration = row.get("Duration (days)", "")
            try:
                if start and duration:
                    start_date = datetime.datetime.strptime(start, "%m-%d-%Y")
                    days = int(duration)
                    current_date = start_date
                    added_days = 0
                    while added_days < days:
                        current_date += datetime.timedelta(days=1)
                        # Skip Saturday (5) and Sunday (6)
                        if current_date.weekday() < 5:
                            added_days += 1
                    row["Calculated End Date"] = current_date.strftime("%m-%d-%Y")
                else:
                    row["Calculated End Date"] = ""
            except Exception:
                row["Calculated End Date"] = ""

    # --- Progress Roll-up Logic ---
    def rollup_progress(self):
        # Build children mapping by parent part name (string)
        name_to_row = {r.get("Project Part", ""): r for r in self.rows}
        children = {}
        for r in self.rows:
            p = r.get("Parent") or ""
            if p:
                children.setdefault(p, []).append(r)

        # Depth-first post-order to compute parent % Complete
        visited = set()
        def dfs(name):
            if name in visited:
                return
            visited.add(name)
            row = name_to_row.get(name)
            if not row:
                return
            # Leaf: ensure numeric % Complete & Status defaults
            if name not in children:
                try:
                    pc = int(row.get("% Complete") or 0)
                except Exception:
                    pc = 0
                row["% Complete"] = max(0, min(100, pc))
                if row.get("Status") == "Done" and row["% Complete"] < 100:
                    row["% Complete"] = 100
                return
            # Recurse children first
            total_weight = 0
            weighted = 0
            all_done = True
            any_in_progress = False
            any_blocked = False
            for child in children[name]:
                cname = child.get("Project Part", "")
                dfs(cname)
                try:
                    dur = int(child.get("Duration (days)") or 0)
                except Exception:
                    dur = 0
                try:
                    cpc = int(child.get("% Complete") or 0)
                except Exception:
                    cpc = 0
                weighted += cpc * dur
                total_weight += dur
                st = child.get("Status") or "Planned"
                if st != "Done":
                    all_done = False
                if st == "In Progress":
                    any_in_progress = True
                if st == "Blocked":
                    any_blocked = True
            if total_weight > 0:
                row["% Complete"] = int(round(weighted / total_weight))
            else:
                # No duration children: average raw
                vals = []
                for child in children[name]:
                    try:
                        vals.append(int(child.get("% Complete") or 0))
                    except Exception:
                        pass
                row["% Complete"] = int(round(sum(vals)/len(vals))) if vals else 0
            # Derive parent status
            if all_done and children[name]:
                row["Status"] = "Done"
                row["% Complete"] = 100
            else:
                # Preserve explicit Blocked if all children blocked
                if any_blocked and not any_in_progress:
                    row["Status"] = "Blocked"
                elif any_in_progress:
                    row["Status"] = "In Progress"
                else:
                    # Keep existing or default
                    row["Status"] = row.get("Status") or "Planned"

        # Start DFS from top-level rows (no Parent or blank)
        for r in self.rows:
            if not (r.get("Parent") or ""):
                dfs(r.get("Project Part", ""))

    # --- Aggregate metrics helper for dashboard ---
    def progress_metrics(self):
        import datetime
        total_tasks = 0
        sum_weighted = 0
        total_weight = 0
        critical_tasks = 0
        critical_weighted = 0
        critical_weight = 0
        done = 0
        today = datetime.datetime.today().date()
        overdue = 0
        at_risk = 0
        # Identify critical path quickly (reuse minimal logic)
        try:
            name_to_row = {r.get("Project Part", ""): r for r in self.rows}
            graph = {}
            duration_map = {}
            min_date = None
            for r in self.rows:
                n = r.get("Project Part", "")
                deps = [d.strip() for d in (r.get("Dependencies", "") or '').split(',') if d.strip()]
                graph[n] = deps
                try:
                    duration_map[n] = int(r.get("Duration (days)") or 0)
                except Exception:
                    duration_map[n] = 0
                try:
                    sd = r.get("Start Date", "")
                    if sd:
                        dt = datetime.datetime.strptime(sd, "%m-%d-%Y")
                        if min_date is None or dt < min_date:
                            min_date = dt
                except Exception:
                    pass
            visited = set(); order = []
            def dfs(n):
                if n in visited: return
                for d in graph.get(n, []): dfs(d)
                visited.add(n); order.append(n)
            for n in graph: dfs(n)
            earliest_finish = {}; earliest_start = {}
            base_min = min_date or datetime.datetime.today()
            for n in order:
                deps = graph.get(n, [])
                if not deps:
                    row = name_to_row.get(n, {})
                    try:
                        earliest_start[n] = datetime.datetime.strptime(row.get("Start Date", ""), "%m-%d-%Y")
                    except Exception:
                        earliest_start[n] = base_min
                else:
                    earliest_start[n] = max([earliest_finish.get(d, base_min) for d in deps])
                earliest_finish[n] = earliest_start[n] + datetime.timedelta(days=duration_map.get(n,0))
            project_finish = max(earliest_finish.values()) if earliest_finish else base_min
            latest_start = {}; latest_finish = {}
            for n in reversed(order):
                succs = [k for k,v in graph.items() if n in v]
                if not succs:
                    latest_finish[n] = project_finish
                else:
                    latest_finish[n] = min([latest_start[s] for s in succs]) if succs else project_finish
                latest_start[n] = latest_finish[n] - datetime.timedelta(days=duration_map.get(n,0))
            critical_set = {n for n in order if abs((earliest_start[n]-latest_start[n]).days) <= 0}
        except Exception:
            critical_set = set()
        for r in self.rows:
            # Skip parent aggregator tasks for EV style metrics: treat non-leaf if it has children with durations
            name = r.get("Project Part", "")
            has_child = any(ch.get("Parent", "") == name for ch in self.rows if ch is not r)
            try:
                dur = int(r.get("Duration (days)") or 0)
            except Exception:
                dur = 0
            try:
                pc = int(r.get("% Complete") or 0)
            except Exception:
                pc = 0
            status_val = (r.get("Status") or "").strip()
            if dur and not has_child:
                total_tasks += 1
                total_weight += dur
                sum_weighted += pc * dur
                if status_val == "Done":
                    done += 1
                # Overdue / at-risk logic (mirrors Gantt drawing)
                try:
                    end_calc = r.get("Calculated End Date", "")
                    if end_calc:
                        end_dt = datetime.datetime.strptime(end_calc, "%m-%d-%Y").date()
                    else:
                        start_dt = datetime.datetime.strptime(r.get("Start Date", ""), "%m-%d-%Y").date()
                        end_dt = start_dt + datetime.timedelta(days=dur)
                    if pc < 100 and today > end_dt:
                        overdue += 1
                    elif pc == 0 and today > start_dt and status_val in ("Planned", "Blocked"):
                        at_risk += 1
                except Exception:
                    pass
            if name in critical_set and dur and not has_child:
                critical_tasks += 1
                critical_weight += dur
                critical_weighted += pc * dur
        overall_pc = (sum_weighted/total_weight) if total_weight else 0
        critical_pc = (critical_weighted/critical_weight) if critical_weight else 0
        return {
            "overall_percent": round(overall_pc, 1),
            "critical_percent": round(critical_pc, 1),
            "leaf_count": total_tasks,
            "done_count": done,
            "overdue": overdue,
            "at_risk": at_risk,
            "critical_leaf_count": critical_tasks
        }

class ProgressDashboard(QWidget):
    def __init__(self, model):
        super().__init__()
        self.model = model
        self.vbox = QVBoxLayout()
        self.vbox.addWidget(QLabel("Progress Dashboard"))
        self.summary_label = QLabel()
        self.summary_label.setStyleSheet("QLabel { font-family: Consolas, monospace; }")
        self.vbox.addWidget(self.summary_label)
        refresh_btn = QPushButton("Refresh Metrics")
        refresh_btn.clicked.connect(self.refresh)
        self.vbox.addWidget(refresh_btn)
        self.setLayout(self.vbox)
        self.refresh()
    def refresh(self):
        m = self.model.progress_metrics()
        text = (
            f"Overall % Complete: {m['overall_percent']}%\n"
            f"Critical Path % Complete: {m['critical_percent']}%\n"
            f"Leaf Tasks: {m['leaf_count']} | Done: {m['done_count']}\n"
            f"Overdue: {m['overdue']} | At Risk: {m['at_risk']}\n"
            f"Critical Leaf Tasks: {m['critical_leaf_count']}"
        )
        self.summary_label.setText(text)

class ProjectTreeView(QWidget):
    def __init__(self, model, on_part_selected=None):
        super().__init__()
        self.model = model
        self.on_part_selected = on_part_selected
        layout = QVBoxLayout()
        layout.addWidget(QLabel("Project Tree (Drag-and-Drop Enabled)"))
        self.tree = QTreeWidget()
        self.display_columns = ["Project Part", "Type"]
        self.tree.setHeaderLabels(self.display_columns)
        # Enable drag and drop
        self.tree.setDragEnabled(True)
        self.tree.setAcceptDrops(True)
        self.tree.setDropIndicatorShown(True)
        self.tree.setDefaultDropAction(Qt.MoveAction)
        self.tree.setDragDropMode(QTreeWidget.InternalMove)
        layout.addWidget(self.tree)

        # Add image preview label
        self.preview_label = QLabel()
        self.preview_label.setFixedHeight(200)
        self.preview_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.preview_label)

        self.setLayout(layout)
        self.tree.itemSelectionChanged.connect(self.handle_selection)
        self.tree.dropEvent = self.dropEvent  # Override dropEvent
        self.tree.setMouseTracking(True)
        self.tree.viewport().setMouseTracking(True)
        self.tree.viewport().installEventFilter(self)
        self.refresh()

    def eventFilter(self, obj, event):
        from PyQt5.QtCore import QEvent
        if obj == self.tree.viewport():
            if event.type() == QEvent.MouseMove:
                pos = event.pos()
                item = self.tree.itemAt(pos)
                if item:
                    part_name = item.text(0)
                    row = next((r for r in self.model.rows if r["Project Part"] == part_name), None)
                    if row:
                        img_path = row.get("Images", "")
                        if img_path and str(img_path).strip():
                            import os
                            from PyQt5.QtGui import QPixmap
                            if not os.path.isabs(img_path):
                                base_dir = os.path.dirname(os.path.abspath(__file__))
                                img_path_full = os.path.join(base_dir, img_path)
                            else:
                                img_path_full = img_path
                            pixmap = QPixmap(img_path_full)
                            if not pixmap.isNull():
                                self.preview_label.setPixmap(pixmap.scaledToHeight(180, Qt.SmoothTransformation))
                            else:
                                self.preview_label.setText("[Image not found]")
                        else:
                            self.preview_label.clear()
                    else:
                        self.preview_label.clear()
                else:
                    self.preview_label.clear()
            elif event.type() == QEvent.Leave:
                self.preview_label.clear()
        return super().eventFilter(obj, event)

    def dropEvent(self, event):
        # Call the default dropEvent to move the item visually
        QTreeWidget.dropEvent(self.tree, event)
        # After the move, update the model
        self.update_model_after_drag()

    def update_model_after_drag(self):
        # Rebuild parent relationships in the model based on the new tree structure
        def recurse(item, parent_name):
            part_name = item.text(0)
            for row in self.model.rows:
                if row["Project Part"] == part_name:
                    row["Parent"] = parent_name if parent_name else None
            for i in range(item.childCount()):
                recurse(item.child(i), part_name)
        for i in range(self.tree.topLevelItemCount()):
            recurse(self.tree.topLevelItem(i), None)
        self.model.save_to_db()
        self.refresh()

    def handle_selection(self):
        selected = self.tree.selectedItems()
        if selected and self.on_part_selected:
            part_name = selected[0].text(0)
            self.on_part_selected(part_name)

    def refresh(self):
        self.tree.clear()
        # Build a mapping from part name to row index
        name_to_index = {r["Project Part"]: i for i, r in enumerate(self.model.rows)}
        # Build a mapping from parent part name to list of child indices
        parent_to_children = {}
        for i, r in enumerate(self.model.rows):
            parent = r.get("Parent", "") or ""
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
                item = QTreeWidgetItem([row.get(col, "") for col in self.display_columns])
                if parent_widget is None:
                    self.tree.addTopLevelItem(item)
                else:
                    parent_widget.addChild(item)
                add_items(item, part_name, visited.copy())
        add_items(None, "")


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


class GanttChartView(QWidget):
    # --- Filtering Support (extensible for future filter panel) ---
    def _init_filters(self):
        # Stored criteria; None / empty means no filtering
        self._filter_statuses = None          # set of status strings
        self._filter_internal_external = None # set like {"Internal","External"}
        self._filter_responsible_substr = None # lowercase substring
        self._filter_critical_only = False     # boolean
        self._filter_risk_only = False         # boolean (overdue OR at-risk)
        self._current_critical_set = set()     # populated during render

    def set_filters(self, statuses=None, internal_external=None, responsible_substr=None,
                    critical_only=None, risk_only=None):
        """Update filter criteria and refresh the Gantt chart.
        Parameters are optional; pass None to leave unchanged, pass empty iterable/string to clear.
        """
        if statuses is not None:
            self._filter_statuses = set(s.strip() for s in statuses if s.strip()) if statuses else None
        if internal_external is not None:
            self._filter_internal_external = set(s.strip() for s in internal_external if s.strip()) if internal_external else None
        if responsible_substr is not None:
            rs = responsible_substr.strip()
            self._filter_responsible_substr = rs.lower() if rs else None
        if critical_only is not None:
            self._filter_critical_only = bool(critical_only)
        if risk_only is not None:
            self._filter_risk_only = bool(risk_only)
        if hasattr(self, 'model') and self.model:
            self.render_gantt(self.model)

    def _passes_filters(self, row):
        try:
            if self._filter_statuses and (row.get("Status") or "").strip() not in self._filter_statuses:
                return False
            if self._filter_internal_external and (row.get("Internal/External") or "").strip() not in self._filter_internal_external:
                return False
            if self._filter_responsible_substr:
                resp = (row.get("Responsible") or "").lower()
                if self._filter_responsible_substr not in resp:
                    return False
            # Critical path filter
            if self._filter_critical_only:
                name = row.get("Project Part", "")
                if name not in self._current_critical_set:
                    return False
            # Risk filter (overdue OR at-risk)
            if self._filter_risk_only:
                import datetime as _dt_rf
                overdue = False; at_risk = False
                try:
                    # Derive start & end
                    start_str = row.get("Start Date", "")
                    dur = int(row.get("Duration (days)") or 0)
                    if start_str:
                        start_dt = _dt_rf.datetime.strptime(start_str, "%m-%d-%Y")
                    else:
                        start_dt = None
                    if row.get("Calculated End Date"):
                        scheduled_end = _dt_rf.datetime.strptime(row.get("Calculated End Date"), "%m-%d-%Y")
                    elif start_dt and dur:
                        scheduled_end = start_dt + _dt_rf.timedelta(days=dur)
                    else:
                        scheduled_end = None
                    today = _dt_rf.datetime.today()
                    pc_val = int(row.get("% Complete") or 0)
                    status_val = (row.get("Status") or "").strip()
                    if scheduled_end and pc_val < 100 and today.date() > scheduled_end.date():
                        overdue = True
                    elif start_dt and pc_val == 0 and status_val in ("Planned", "Blocked") and today.date() > start_dt.date():
                        at_risk = True
                except Exception:
                    pass
                if not (overdue or at_risk):
                    return False
            return True
        except Exception:
            return True

    # --- Public helper to highlight & scroll to a bar by name (used by search/jump) ---
    def highlight_bar(self, part_name):
        if not part_name:
            return
        # Clear previous bar highlight pen styling
        try:
            for item in getattr(self, '_name_to_rect', {}).values():
                if item and hasattr(item, 'setPen'):
                    from PyQt5.QtGui import QPen
                    item.setPen(item.data(99) or QPen(item.pen()))
        except Exception:
            pass
        rect_item = getattr(self, '_name_to_rect', {}).get(part_name)
        if rect_item:
            from PyQt5.QtGui import QPen, QColor
            # Store original pen once
            if rect_item.data(99) is None:
                rect_item.setData(99, rect_item.pen())
            pen = QPen(QColor('#00BFFF'))
            pen.setWidth(3)
            rect_item.setPen(pen)
            # Center the view on the rectangle
            if hasattr(self, 'view') and self.view:
                center_pt = rect_item.sceneBoundingRect().center()
                self.view.centerOn(center_pt)
            # Also use existing connector/label highlight logic
            self._highlight_connectors(part_name, True)
        else:
            print(f"highlight_bar: No bar found for '{part_name}' (may be filtered out)")
   
    def show_edit_dialog(self, row):
        dialog = QDialog(self)
        dialog.setWindowTitle(f"Edit Project Part: {row.get('Project Part', '')}")
        layout = QFormLayout(dialog)
        edits = {}
        for col in self.model.COLUMNS:
            val = row.get(col, "")
            if col in ("Start Date", "Calculated End Date"):
                date_edit = QDateEdit()
                date_edit.setCalendarPopup(True)
                min_blank = QDate(1753, 1, 1)
                date_edit.setMinimumDate(min_blank)
                date_edit.setSpecialValueText("")
                if val:
                    date = QDate.fromString(val, "MM-dd-yyyy")
                    if date.isValid() and date != QDate(1752, 9, 14) and date != min_blank:
                        date_edit.setDate(date)
                    else:
                        date_edit.setDate(min_blank)
                else:
                    date_edit.setDate(min_blank)
                edits[col] = date_edit
                layout.addRow(col, date_edit)
            elif col == "Type":
                combo = QComboBox()
                combo.addItems(["Milestone", "Phase", "Feature", "Item"])
                if val:
                    combo.setCurrentText(val)
                edits[col] = combo
                layout.addRow(col, combo)
            elif col == "Internal/External":
                combo = QComboBox()
                combo.addItems(["Internal", "External"])
                if val:
                    combo.setCurrentText(val)
                edits[col] = combo
                layout.addRow(col, combo)
            elif col == "% Complete":
                from PyQt5.QtWidgets import QSpinBox
                spin = QSpinBox()
                spin.setRange(0, 100)
                try:
                    spin.setValue(int(val or 0))
                except Exception:
                    spin.setValue(0)
                # Disable if this row is a parent (rolled up)
                name = row.get("Project Part", "")
                has_children = any(r.get("Parent", "") == name for r in self.model.rows if r is not row)
                if has_children:
                    spin.setEnabled(False)
                    spin.setToolTip("Parent progress rolls up from children.")
                edits[col] = spin
                layout.addRow(col, spin)
            elif col == "Status":
                combo = QComboBox()
                combo.addItems(["Planned", "In Progress", "Blocked", "Done", "Deferred"])
                if val:
                    combo.setCurrentText(str(val))
                name = row.get("Project Part", "")
                has_children = any(r.get("Parent", "") == name for r in self.model.rows if r is not row)
                if has_children:
                    combo.setEnabled(False)
                    combo.setToolTip("Parent status is derived from children.")
                edits[col] = combo
                layout.addRow(col, combo)
            elif col in ("Actual Start Date", "Actual Finish Date", "Baseline Start Date", "Baseline End Date"):
                # Show read-only line edits for audit trail
                from PyQt5.QtWidgets import QLineEdit as _QLineEdit
                le = _QLineEdit(str(val) if val else "")
                le.setReadOnly(True)
                le.setStyleSheet("QLineEdit { background-color: #222; color: #bbb; }")
                edits[col] = le
                layout.addRow(col, le)
            elif col == "Notes":
                text = QTextEdit()
                text.setPlainText(val)
                edits[col] = text
                layout.addRow(col, text)
            elif col == "Images":
                hbox = QHBoxLayout()
                img_label = QLabel()
                if val:
                    import os
                    from PyQt5.QtGui import QPixmap
                    if not os.path.isabs(val):
                        base_dir = os.path.dirname(os.path.abspath(__file__))
                        img_path_full = os.path.join(base_dir, val)
                    else:
                        img_path_full = val
                    pixmap = QPixmap(img_path_full)
                    if not pixmap.isNull():
                        img_label.setPixmap(pixmap.scaledToHeight(48, Qt.SmoothTransformation))
                btn = QPushButton("Change Image")
                def pick_image():
                    fname, _ = QFileDialog.getOpenFileName(dialog, "Select Image", "", "Image Files (*.png *.jpg *.jpeg *.bmp *.gif)")
                    if fname:
                        img_label.setPixmap(QPixmap(fname).scaledToHeight(48, Qt.SmoothTransformation))
                        edits[col].setText(fname)
                btn.clicked.connect(pick_image)
                img_path_edit = QLineEdit(val)
                edits[col] = img_path_edit
                hbox.addWidget(img_label)
                hbox.addWidget(img_path_edit)
                hbox.addWidget(btn)
                layout.addRow(col, hbox)
            elif col == "Pace Link":
                link_edit = QLineEdit(val)
                edits[col] = link_edit
                link_label = QLabel()
                if val and (val.startswith("http://") or val.startswith("https://")):
                    link_label.setText(f'<a href="{val}">{val}</a>')
                    link_label.setOpenExternalLinks(True)
                else:
                    link_label.setText("")
                layout.addRow(col, link_edit)
                layout.addRow("Link Preview", link_label)
                def update_link_label():
                    v = link_edit.text()
                    if v and (v.startswith("http://") or v.startswith("https://")):
                        link_label.setText(f'<a href="{v}">{v}</a>')
                        link_label.setOpenExternalLinks(True)
                    else:
                        link_label.setText("")
                link_edit.textChanged.connect(update_link_label)
            else:
                # Fallback generic text field; ensure string conversion
                line = QLineEdit(str(val) if val is not None else "")
                edits[col] = line
                layout.addRow(col, line)
        save_btn = QPushButton("Save")
        cancel_btn = QPushButton("Cancel")
        def save():
            try:
                for col in self.model.COLUMNS:
                    widget = edits[col]
                    if isinstance(widget, QLineEdit):
                        row[col] = widget.text()
                    elif isinstance(widget, QComboBox):
                        row[col] = widget.currentText()
                        if col == "Status" and row[col] == "Done" and str(row.get("% Complete")) != "100":
                            row["% Complete"] = 100
                            import datetime as _dt
                            if not row.get("Actual Start Date"):
                                row["Actual Start Date"] = _dt.datetime.today().strftime("%m-%d-%Y")
                            if not row.get("Actual Finish Date"):
                                row["Actual Finish Date"] = _dt.datetime.today().strftime("%m-%d-%Y")
                        if col == "Status" and row[col] == "In Progress" and not row.get("Actual Start Date"):
                            import datetime as _dt
                            row["Actual Start Date"] = _dt.datetime.today().strftime("%m-%d-%Y")
                    elif isinstance(widget, QDateEdit):
                        d = widget.date()
                        min_blank = QDate(1753, 1, 1)
                        if not d.isValid() or d == min_blank:
                            row[col] = ""
                        else:
                            row[col] = d.toString("MM-dd-yyyy")
                    elif hasattr(widget, 'value') and col == "% Complete":
                        try:
                            row[col] = int(widget.value())
                            if int(row[col]) >= 100:
                                row[col] = 100
                                if row.get("Status") != "Done":
                                    row["Status"] = "Done"
                                    import datetime as _dt
                                    if not row.get("Actual Start Date"):
                                        row["Actual Start Date"] = _dt.datetime.today().strftime("%m-%d-%Y")
                                    if not row.get("Actual Finish Date"):
                                        row["Actual Finish Date"] = _dt.datetime.today().strftime("%m-%d-%Y")
                        except Exception:
                            row[col] = 0
                    elif isinstance(widget, QTextEdit):
                        row[col] = widget.toPlainText()
                self.model.save_to_db()
                self.render_gantt(self.model)
                dialog.accept()
            except Exception as e:
                import traceback
                print(f"ERROR in GanttChartView.save(): {e}")
                traceback.print_exc()
                QMessageBox.critical(dialog, "Save Error", f"An error occurred while saving: {e}")
        save_btn.clicked.connect(save)
        cancel_btn.clicked.connect(dialog.reject)
        btn_hbox = QHBoxLayout()
        btn_hbox.addWidget(save_btn)
        btn_hbox.addWidget(cancel_btn)
        layout.addRow(btn_hbox)
        dialog.setLayout(layout)
        dialog.exec_()
    def highlight_group(self, part_name):
        # Find parent and children for the given part_name
        parent = None
        children = set()
        for row in self.model.rows:
            if row["Project Part"] == part_name:
                parent = row.get("Parent")
            if row.get("Parent") == part_name:
                children.add(row["Project Part"])
        group = {part_name}
        if parent:
            group.add(parent)
        group.update(children)
        # Highlight bars in group
        from PyQt5.QtGui import QPen, QColor
        highlight_color = QColor("#00BFFF")
        for item in self.scene.items():
            if hasattr(item, 'data') and callable(item.data):
                if item.data(0) in group:
                    item.setPen(QPen(highlight_color, 3))
                else:
                    item.setPen(QPen())
            elif hasattr(item, 'toGraphicsObject') and hasattr(item, 'setDefaultTextColor'):
                if hasattr(item, 'toPlainText') and item.toPlainText() in group:
                    item.setDefaultTextColor(highlight_color)
                else:
                    item.setDefaultTextColor(QColor("black"))

    def export_gantt_chart(self):
        self._export_scene_with_header(self.scene, title="Gantt Chart")

    def _export_scene_with_header(self, scene, title="Export"):
        from PyQt5.QtGui import QPainter
        # Ask for target format (PNG or PDF)
        path, _ = QFileDialog.getSaveFileName(self, f"Export {title}", f"{title.lower().replace(' ', '_')}.png", "PNG Files (*.png);;PDF Files (*.pdf)")
        if not path:
            return
        rect = scene.sceneRect().toRect()
        if rect.isEmpty():
            print("Scene is empty; nothing to export.")
            return
        is_pdf = path.lower().endswith('.pdf')
        header_path = os.path.join(os.path.dirname(__file__), "header.png")
        header_pixmap = QPixmap(header_path) if os.path.exists(header_path) else None
        if is_pdf:
            # Use QPrinter for PDF
            from PyQt5.QtPrintSupport import QPrinter
            printer = QPrinter(QPrinter.HighResolution)
            printer.setOutputFileName(path)
            printer.setOutputFormat(QPrinter.PdfFormat)
            # Landscape orientation assumed
            painter = QPainter(printer)
            y_offset = 0
            if header_pixmap:
                header_w = printer.pageRect().width()
                scaled_header = header_pixmap.scaledToWidth(header_w, Qt.SmoothTransformation)
                painter.drawPixmap( (header_w - scaled_header.width())//2 , 0, scaled_header)
                y_offset = scaled_header.height() + 10
            painter.translate(0, y_offset)
            scale_x = printer.pageRect().width() / rect.width()
            scale_y = (printer.pageRect().height() - y_offset) / rect.height()
            scale = min(scale_x, scale_y)
            painter.scale(scale, scale)
            scene.render(painter)
            painter.end()
            print(f"Exported PDF -> {path}")
            return
        # Raster export (PNG)
        content_pixmap = QPixmap(rect.size())
        content_pixmap.fill()
        painter = QPainter(content_pixmap)
        scene.render(painter)
        painter.end()
        if header_pixmap:
            combined_width = max(header_pixmap.width(), content_pixmap.width())
            combined_height = header_pixmap.height() + content_pixmap.height()
            combined = QPixmap(combined_width, combined_height)
            combined.fill()
            painter = QPainter(combined)
            header_x = (combined_width - header_pixmap.width()) // 2
            painter.drawPixmap(header_x, 0, header_pixmap)
            painter.drawPixmap(0, header_pixmap.height(), content_pixmap)
            painter.end()
            combined.save(path, 'PNG')
        else:
            content_pixmap.save(path, 'PNG')
        print(f"Exported PNG -> {path}")
    def __init__(self):
        print("GanttChartView: __init__ called")
        super().__init__()
        layout = QVBoxLayout()
        layout.addWidget(QLabel("Gantt Chart (Read-Only)"))
        self.view = ZoomableGraphicsView()
        self.scene = QGraphicsScene()
        self.view.setScene(self.scene)
        layout.addWidget(self.view)

        # Initialize filtering state
        self._init_filters()

        # Image preview area
        self.preview_label = QLabel()
        self.preview_label.setFixedHeight(200)
        self.preview_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.preview_label)

        # Export button
        export_btn = QPushButton("Export Gantt Chart")
        export_btn.clicked.connect(self.export_gantt_chart)
        layout.addWidget(export_btn)

        # Refresh button
        refresh_btn = QPushButton("Refresh Gantt Chart")
        refresh_btn.clicked.connect(self.refresh_gantt)
        layout.addWidget(refresh_btn)
        
        # Hierarchy connectors toggle (feature 1)
        from PyQt5.QtWidgets import QCheckBox
        self.hierarchy_checkbox = QCheckBox("Show Hierarchy Lines")
        self.hierarchy_checkbox.setChecked(True)
        self.hierarchy_checkbox.stateChanged.connect(lambda _s: self.refresh_gantt())
        layout.addWidget(self.hierarchy_checkbox)

        # Legend inclusion flag (feature 5)
        self.include_legend = True

        # Critical path toggle (new feature) default off
        self.critical_path_checkbox = QCheckBox("Show Critical Path")
        self.critical_path_checkbox.setChecked(False)
        self.critical_path_checkbox.stateChanged.connect(lambda _s: self.refresh_gantt())
        layout.addWidget(self.critical_path_checkbox)

        # Zoom controls
        zoom_layout = QHBoxLayout()
        zoom_in_btn = QPushButton("Zoom In")
        zoom_out_btn = QPushButton("Zoom Out")
        zoom_reset_btn = QPushButton("Reset Zoom")
        zoom_in_btn.clicked.connect(lambda: self.view.scale(1.2, 1.2))
        zoom_out_btn.clicked.connect(lambda: self.view.scale(1/1.2, 1/1.2))
        zoom_reset_btn.clicked.connect(self.reset_zoom)
        zoom_layout.addWidget(zoom_in_btn)
        zoom_layout.addWidget(zoom_out_btn)
        zoom_layout.addWidget(zoom_reset_btn)
        layout.addLayout(zoom_layout)

        self.setLayout(layout)

    def reset_zoom(self):
        self.view.resetTransform()

    def refresh_gantt(self):
        if hasattr(self, 'model') and self.model:
            self.render_gantt(self.model)

    # Unified connector + label highlighting
    # Restores original dynamic connector line highlighting AND integrates label font/background highlight.
    def _highlight_connectors(self, part_name, on):
        from PyQt5.QtGui import QPen, QColor, QFont, QBrush
        # 1. Connector lines
        if hasattr(self, '_connector_lines_map'):
            lines = self._connector_lines_map.get(part_name, [])
            if lines:
                if on:
                    pen = QPen(QColor("#00BFFF"))  # bright cyan accent
                    pen.setWidth(2)
                else:
                    pen = QPen(QColor("#888"))
                    pen.setWidth(1)
                for ln in lines:
                    try:
                        ln.setPen(pen)
                    except Exception:
                        pass
        # 2. Label font + background (preserve original orange bg when turning off)
        if hasattr(self, '_name_to_text_item'):
            ti = self._name_to_text_item.get(part_name)
            if ti:
                orig_font = ti.data(1)
                bg = ti.data(3)
                orig_brush = ti.data(4)  # stored original brush
                if on:
                    if isinstance(orig_font, QFont):
                        bold_font = QFont(orig_font)
                        bold_font.setBold(True)
                        ti.setFont(bold_font)
                    if bg:
                        base_col = QColor(255,130,0)
                        glow = QColor(base_col.red(), base_col.green(), base_col.blue(), 160)
                        bg.setBrush(QBrush(glow))
                else:
                    if isinstance(orig_font, QFont):
                        ti.setFont(orig_font)
                    if bg:
                        if orig_brush:
                            bg.setBrush(orig_brush)
                        else:
                            bg.setBrush(QBrush(QColor("#FF8200")))
    def render_gantt(self, model):
        self.model = model
        self.scene.clear()
        self.preview_label.clear()
        if not hasattr(model, 'rows'):
            return
        raw_rows = model.rows
        # Precompute critical path set for filtering/highlighting
        self._current_critical_set = set()
        try:
            import datetime as _dt
            name_to_row_cp = {r.get("Project Part", ""): r for r in raw_rows}
            graph = {}
            for r in raw_rows:
                nm = r.get("Project Part", "")
                preds_raw = (r.get("Predecessors") or "").strip()
                preds = [p.strip() for p in preds_raw.split(',') if p.strip()] if preds_raw else []
                graph[nm] = preds
            visited = set(); order = []
            def dfs(n):
                if n in visited: return
                visited.add(n)
                for p in graph.get(n, []):
                    if p in name_to_row_cp:
                        dfs(p)
                order.append(n)
            for n in graph:
                dfs(n)
            es = {}; ef = {}
            for n in order:
                r = name_to_row_cp.get(n) or {}
                s_str = r.get("Start Date", "")
                try:
                    s_dt = _dt.datetime.strptime(s_str, "%m-%d-%Y") if s_str else None
                    dur = int(r.get("Duration (days)") or 0)
                except Exception:
                    s_dt = None; dur = 0
                pred_finishes = [ef[p] for p in graph.get(n, []) if p in ef]
                base = max(pred_finishes) if pred_finishes else s_dt
                if base is None:
                    base = _dt.datetime.today()
                es[n] = base
                ef[n] = base + _dt.timedelta(days=dur)
            if order:
                proj_finish = max(ef.values())
                ls = {}; lf = {}
                for n in reversed(order):
                    succs = [s for s, preds in graph.items() if n in preds]
                    if not succs:
                        lf[n] = proj_finish
                    else:
                        lf[n] = min(ls[s] for s in succs)
                    dur = (ef[n] - es[n]).days
                    ls[n] = lf[n] - _dt.timedelta(days=dur)
                self._current_critical_set = {n for n in order if abs((es[n]-ls[n]).days) <= 0}
        except Exception:
            self._current_critical_set = set()

        matched = []
        name_to_row = {}
        for r in raw_rows:
            name_to_row[r.get("Project Part", "")] = r
            if self._passes_filters(r):
                matched.append(r)
        if any([self._filter_statuses, self._filter_internal_external, self._filter_responsible_substr,
                self._filter_critical_only, self._filter_risk_only]):
            parent_names_needed = set()
            for r in matched:
                parent_name = r.get("Parent") or ""
                while parent_name:
                    if parent_name in parent_names_needed:
                        break
                    parent_names_needed.add(parent_name)
                    parent_row = next((x for x in raw_rows if x.get("Project Part") == parent_name), None)
                    if parent_row:
                        parent_name = parent_row.get("Parent") or ""
                    else:
                        break
            rows = [r for r in raw_rows if r in matched or r.get("Project Part") in parent_names_needed]
        else:
            rows = raw_rows

        # ---------- Helpers ----------
        def topo_sort(all_rows):
            name_to_row = {r.get("Project Part", ""): r for r in all_rows}
            visited = set()
            result = []
            def visit(r):
                name = r.get("Project Part", "")
                if name in visited:
                    return
                parent = r.get("Parent", "")
                if parent and parent in name_to_row:
                    visit(name_to_row[parent])
                visited.add(name)
                result.append(r)
            for r in all_rows:
                visit(r)
            return result

        def compute_parent_spans(all_rows):
            import datetime as _dt
            children = {}
            for r in all_rows:
                p = r.get("Parent", "")
                if p:
                    children.setdefault(p, []).append(r)
            def update_span(r, visited=None):
                if visited is None:
                    visited = set()
                name = r.get("Project Part", "")
                if name in visited:
                    return None, None
                visited.add(name)
                if name not in children:
                    try:
                        s = _dt.datetime.strptime(r.get("Start Date", ""), "%m-%d-%Y")
                        d = int(r.get("Duration (days)", 0))
                        e = s + _dt.timedelta(days=d)
                        return s, e
                    except Exception:
                        return None, None
                child_spans = [update_span(c, visited.copy()) for c in children[name]]
                starts = [s for s, e in child_spans if s]
                ends = [e for s, e in child_spans if e]
                if starts and ends:
                    r["_auto_start"] = min(starts)
                    r["_auto_end"] = max(ends)
                    return r["_auto_start"], r["_auto_end"]
                return None, None
            for r in all_rows:
                update_span(r)

        compute_parent_spans(rows)
        rows = topo_sort(rows)
        if not rows:
            return

        # ---------- Build bar data ----------
        import datetime
        bar_height = 24
        bar_gap = 10
        min_date = None
        max_date = None
        bars = []  # (name, start, duration, index, row_dict)
        for idx, r in enumerate(rows):
            if "_auto_start" in r and "_auto_end" in r:
                start = r["_auto_start"]
                end = r["_auto_end"]
                duration = (end - start).days
            else:
                try:
                    start_str = r.get("Start Date", "")
                    dur_val = r.get("Duration (days)", 0)
                    if not start_str or not dur_val:
                        continue
                    start = datetime.datetime.strptime(start_str, "%m-%d-%Y")
                    duration = int(dur_val)
                    end = start + datetime.timedelta(days=duration)
                except Exception:
                    continue
            if not start:
                continue
            if min_date is None or start < min_date:
                min_date = start
            if max_date is None or end > max_date:
                max_date = end
            bars.append((r.get("Project Part", ""), start, duration, idx, r))

        if not bars:
            return

        chart_min_date = min_date  # earliest start

        # ---------- Draw bars ----------
        from PyQt5.QtGui import QColor
        from PyQt5.QtWidgets import QGraphicsRectItem, QGraphicsItem
        gantt_color = QColor("#FF8200")

        # Optional critical path calculation
        critical_set = set()
        if hasattr(self, 'critical_path_checkbox') and self.critical_path_checkbox.isChecked():
            try:
                # Build dependency graph and durations
                name_to_row = {r.get("Project Part", ""): r for r in rows}
                graph = {}
                duration_map = {}
                import datetime as _dt_cp
                for r in rows:
                    name = r.get("Project Part", "")
                    deps = [d.strip() for d in (r.get("Dependencies", "") or "").split(',') if d.strip()]
                    graph[name] = deps
                    try:
                        if "_auto_start" in r and "_auto_end" in r:
                            duration_map[name] = (r["_auto_end"] - r["_auto_start"]).days
                        else:
                            duration_map[name] = int(r.get("Duration (days)", 0) or 0)
                    except Exception:
                        duration_map[name] = 0
                # Topological order (simple DFS; assumes no complex cycles)
                visited = set(); order = []
                def dfs(n):
                    if n in visited: return
                    for d in graph.get(n, []): dfs(d)
                    visited.add(n); order.append(n)
                for n in graph: dfs(n)
                # Forward pass: earliest finish
                earliest_finish = {}
                earliest_start = {}
                for n in order:
                    deps = graph.get(n, [])
                    if not deps:
                        # Use explicit start date if available for alignment; else zero
                        row = name_to_row.get(n, {})
                        try:
                            if "_auto_start" in row:
                                est = row["_auto_start"]
                            else:
                                est = datetime.datetime.strptime(row.get("Start Date", ""), "%m-%d-%Y")
                        except Exception:
                            est = min_date
                        earliest_start[n] = est
                    else:
                        # earliest start is max earliest finish of deps
                        ef_candidates = []
                        for d in deps:
                            if d in earliest_finish:
                                ef_candidates.append(earliest_finish[d])
                        base = max(ef_candidates) if ef_candidates else min_date
                        earliest_start[n] = base
                    earliest_finish[n] = earliest_start[n] + datetime.timedelta(days=duration_map.get(n,0))
                project_finish = max(earliest_finish.values()) if earliest_finish else None
                # Backward pass: latest start
                latest_start = {}; latest_finish = {}
                for n in reversed(order):
                    # Successors: tasks that depend on n
                    succs = [k for k,v in graph.items() if n in v]
                    if not succs:
                        latest_finish[n] = project_finish
                    else:
                        latest_finish[n] = min([latest_start[s] for s in succs]) if succs else project_finish
                    latest_start[n] = latest_finish[n] - datetime.timedelta(days=duration_map.get(n,0))
                # Critical tasks: zero total float (allow <= 0 days tolerance)
                for n in order:
                    if abs((earliest_start[n] - latest_start[n]).days) <= 0:
                        critical_set.add(n)
            except Exception as e:
                print(f"WARNING: Critical path calculation failed: {e}")

        class ClickableBar(QGraphicsRectItem):
            def __init__(self, x, y, w, h, row_dict, preview_label, gantt_view):
                super().__init__(x, y, w, h)
                self.row = row_dict
                self.preview_label = preview_label
                self.gantt_view = gantt_view
                self.setAcceptHoverEvents(True)
                self.setFlag(QGraphicsItem.ItemIsSelectable, True)

            # --- Attachment utilities ---
            def _attachments_list(self):
                import json
                raw = self.row.get("Attachments") or "[]"
                try:
                    lst = json.loads(raw)
                    if isinstance(lst, list):
                        return [p for p in lst if isinstance(p, str)]
                except Exception:
                    pass
                return []
            def _save_attachments_list(self, lst):
                import json
                self.row["Attachments"] = json.dumps(lst)
                # Persist via model if parent widget exposes save_model()
                pw = self.preview_label.parentWidget()
                if pw and hasattr(pw, 'model'):
                    try:
                        pw.model.save_to_db()
                    except Exception as e:
                        print(f"Attachment save failed: {e}")
            def contextMenuEvent(self, event):
                from PyQt5.QtWidgets import QMenu
                menu = QMenu()
                open_action = menu.addAction("Open Attachments…")
                add_action = menu.addAction("Add Attachment…")
                open_folder_action = menu.addAction("Open Attachments Folder")
                chosen = menu.exec_(event.screenPos())
                if chosen == open_action:
                    self.show_attachments_dialog()
                elif chosen == add_action:
                    self.add_attachment_files()
                elif chosen == open_folder_action:
                    self.open_attachments_folder()
            def add_attachment_files(self):
                from PyQt5.QtWidgets import QFileDialog
                import os, shutil
                files, _ = QFileDialog.getOpenFileNames(None, "Select Attachment(s)")
                if not files:
                    return
                import sys
                if getattr(sys, 'frozen', False):
                    base_dir = os.path.dirname(sys.executable)
                else:
                    base_dir = os.path.dirname(os.path.abspath(__file__))
                attach_dir = os.path.join(base_dir, 'attachments')
                if not os.path.exists(attach_dir):
                    os.makedirs(attach_dir)
                current = self._attachments_list()
                for f in files:
                    name = os.path.basename(f)
                    dest = os.path.join(attach_dir, name)
                    root, ext = os.path.splitext(name)
                    counter = 1
                    while os.path.exists(dest):
                        dest = os.path.join(attach_dir, f"{root}_{counter}{ext}")
                        counter += 1
                    try:
                        shutil.copy2(f, dest)
                        rel = os.path.relpath(dest, base_dir)
                        current.append(rel)
                    except Exception as e:
                        print(f"Attachment copy failed: {e}")
                self._save_attachments_list(current)
            def open_attachments_folder(self):
                import os, sys, subprocess
                if getattr(sys, 'frozen', False):
                    base_dir = os.path.dirname(sys.executable)
                else:
                    base_dir = os.path.dirname(os.path.abspath(__file__))
                attach_dir = os.path.join(base_dir, 'attachments')
                if not os.path.exists(attach_dir):
                    os.makedirs(attach_dir)
                if sys.platform.startswith('win'):
                    os.startfile(attach_dir)
                elif sys.platform == 'darwin':
                    subprocess.Popen(['open', attach_dir])
                else:
                    subprocess.Popen(['xdg-open', attach_dir])
            def show_attachments_dialog(self):
                from PyQt5.QtWidgets import QDialog, QVBoxLayout, QListWidget, QPushButton, QHBoxLayout, QLabel
                import os, webbrowser
                dlg = QDialog()
                dlg.setWindowTitle(f"Attachments - {self.row.get('Project Part','')}")
                vbox = QVBoxLayout(dlg)
                info = QLabel("Double-click or Open to launch. Remove only deletes reference.")
                vbox.addWidget(info)
                lst = QListWidget(); vbox.addWidget(lst)
                thumb = QLabel(); thumb.setFixedHeight(110); vbox.addWidget(thumb)
                btn_row = QHBoxLayout()
                add_btn = QPushButton("Add…"); rem_btn = QPushButton("Remove"); open_btn = QPushButton("Open")
                btn_row.addWidget(add_btn); btn_row.addWidget(rem_btn); btn_row.addWidget(open_btn)
                vbox.addLayout(btn_row)
                for p in self._attachments_list():
                    lst.addItem(p)
                def refresh_thumb():
                    from PyQt5.QtGui import QPixmap
                    item = lst.currentItem()
                    if not item:
                        thumb.clear(); return
                    rel = item.text()
                    if getattr(sys, 'frozen', False):
                        base_dir = os.path.dirname(sys.executable)
                    else:
                        base_dir = os.path.dirname(os.path.abspath(__file__))
                    full = os.path.join(base_dir, rel)
                    if os.path.exists(full) and os.path.splitext(full)[1].lower() in ('.png','.jpg','.jpeg','.bmp','.gif'):
                        pm = QPixmap(full)
                        if not pm.isNull():
                            thumb.setPixmap(pm.scaledToHeight(100, Qt.SmoothTransformation)); return
                    thumb.setText(os.path.basename(full))
                def do_add():
                    self.add_attachment_files(); lst.clear(); [lst.addItem(p) for p in self._attachments_list()]; refresh_thumb()
                def do_remove():
                    item = lst.currentItem();
                    if not item: return
                    rel = item.text()
                    remain = [p for p in self._attachments_list() if p != rel]
                    self._save_attachments_list(remain)
                    lst.takeItem(lst.currentRow()); refresh_thumb()
                def do_open():
                    item = lst.currentItem();
                    if not item: return
                    rel = item.text()
                    if getattr(sys, 'frozen', False):
                        base_dir = os.path.dirname(sys.executable)
                    else:
                        base_dir = os.path.dirname(os.path.abspath(__file__))
                    full = os.path.join(base_dir, rel)
                    if os.path.exists(full):
                        webbrowser.open(full)
                lst.currentItemChanged.connect(lambda *_: refresh_thumb())
                lst.itemDoubleClicked.connect(lambda *_: do_open())
                add_btn.clicked.connect(do_add)
                rem_btn.clicked.connect(do_remove)
                open_btn.clicked.connect(do_open)
                refresh_thumb()
                dlg.exec_()
            def _set_preview(self):
                img_path = self.row.get("Images", "")
                if img_path and str(img_path).strip():
                    import os, sys
                    from PyQt5.QtGui import QPixmap
                    if not os.path.isabs(img_path):
                        if getattr(sys, 'frozen', False):
                            base_dir = os.path.dirname(sys.executable)
                        else:
                            base_dir = os.path.dirname(os.path.abspath(__file__))
                        img_path_full = os.path.join(base_dir, img_path)
                    else:
                        img_path_full = img_path
                    pm = QPixmap(img_path_full)
                    if not pm.isNull():
                        self.preview_label.setPixmap(pm.scaledToHeight(90, Qt.SmoothTransformation))
                        self.preview_label.setText("")
                        return
                # Ensure QPixmap is imported when clearing
                from PyQt5.QtGui import QPixmap
                self.preview_label.setText("")
                self.preview_label.setPixmap(QPixmap())
            def mousePressEvent(self, event):
                try:
                    self._set_preview()
                    parent_widget = self.preview_label.parentWidget()
                    if parent_widget and hasattr(parent_widget, 'show_edit_dialog'):
                        parent_widget.show_edit_dialog(self.row)
                except Exception as e:
                    print(f"ERROR in ClickableBar.mousePressEvent: {e}")
            def hoverEnterEvent(self, event):
                self._set_preview()
                part = self.row.get("Project Part", "")
                if part:
                    self.gantt_view._highlight_connectors(part, True)
                parent = self.row.get("Parent", "")
                if parent:
                    self.gantt_view._highlight_connectors(parent, True)
            def hoverLeaveEvent(self, event):
                self.preview_label.clear()
                part = self.row.get("Project Part", "")
                if part:
                    self.gantt_view._highlight_connectors(part, False)
                parent = self.row.get("Parent", "")
                if parent:
                    self.gantt_view._highlight_connectors(parent, False)
                # Fallback to first image attachment preview if no explicit image assigned
                if not self.row.get("Images"):
                    atts = self._attachments_list()
                    if atts:
                        import os
                        from PyQt5.QtGui import QPixmap
                        if getattr(sys, 'frozen', False):
                            base_dir = os.path.dirname(sys.executable)
                        else:
                            base_dir = os.path.dirname(os.path.abspath(__file__))
                        full = os.path.join(base_dir, atts[0])
                        if os.path.exists(full):
                            pm = QPixmap(full)
                            if not pm.isNull():
                                self.preview_label.setPixmap(pm.scaledToHeight(90, Qt.SmoothTransformation))
                                self.preview_label.setText("")

        name_to_bar = {}
        self._name_to_rect = {}
        bar_items = []
        # (Reverted) Previously labels were placed in a dedicated left column and bars were offset.
        # We now restore inline style with external labels to the right of bars.
        from PyQt5.QtGui import QFontMetrics, QFont
        font = self.font() if hasattr(self, 'font') else None
        fm = QFontMetrics(font) if font else None
        max_chars_fixed = 32  # keep truncation behavior
        left_margin = 60
        bar_offset_x = left_margin
        self._name_to_text_item = {}
        for name, start, duration, i, r in bars:
            x = (start - chart_min_date).days * 10 + bar_offset_x
            y = i * (bar_height + bar_gap) + 40
            width = max(duration * 10, 10)
            rect = ClickableBar(x, y, width, bar_height, r, self.preview_label, self)
            rect.setBrush(QColor("#333333"))
            from PyQt5.QtGui import QPen as _QPen4
            import datetime as _dt_ov
            overdue = False; at_risk = False
            try:
                if "_auto_end" in r:
                    scheduled_end = r["_auto_end"]
                else:
                    end_calc = r.get("Calculated End Date", "")
                    if end_calc:
                        scheduled_end = _dt_ov.datetime.strptime(end_calc, "%m-%d-%Y")
                    else:
                        scheduled_end = start + _dt_ov.timedelta(days=duration)
                today = _dt_ov.datetime.today()
                pc_val = int(r.get("% Complete") or 0)
                status_val = (r.get("Status") or "").strip()
                if pc_val < 100 and today.date() > scheduled_end.date():
                    overdue = True
                elif pc_val == 0 and status_val in ("Planned", "Blocked") and today.date() > start.date():
                    at_risk = True
            except Exception:
                pass
            outline_pen = _QPen4(Qt.NoPen)
            if overdue:
                outline_pen = _QPen4(QColor("red")); outline_pen.setWidth(2)
            elif at_risk:
                outline_pen = _QPen4(QColor("#FFA500")); outline_pen.setWidth(2)
            rect.setPen(outline_pen)
            self.scene.addItem(rect)
            self._name_to_rect[name] = rect
            try:
                pc = int(r.get("% Complete") or 0)
            except Exception:
                pc = 0
            if pc > 0:
                prog_w = max(2, int(width * pc / 100))
                prog_color = QColor("#DAA520") if name in critical_set else gantt_color
                from PyQt5.QtGui import QPen as _QPen3
                prog_rect = self.scene.addRect(x, y, prog_w, bar_height, _QPen3(Qt.NoPen), prog_color)
                prog_rect.setAcceptedMouseButtons(Qt.NoButton)
                prog_rect.setZValue(rect.zValue() + 1)
            full_name = name
            display_name = full_name
            # Paperclip if attachments present
            try:
                import json as _json_attlabel
                att_raw = r.get("Attachments") or "[]"
                att_list = _json_attlabel.loads(att_raw) if att_raw else []
                if isinstance(att_list, list) and len(att_list) > 0:
                    display_name = "\uD83D\uDCCE " + display_name  # paperclip emoji
            except Exception:
                pass
            if len(display_name) > max_chars_fixed:
                display_name = display_name[:max_chars_fixed-1] + "…"
            text_item = self.scene.addText(display_name)
            from PyQt5.QtGui import QColor as _QColor, QFont, QBrush, QPen
            text_item.setDefaultTextColor(_QColor("black"))
            orig_font = text_item.font()
            text_item.setData(1, orig_font)
            text_item.setData(2, full_name)  # store full for tooltip
            text_item.setToolTip(full_name)
            ty = y + (bar_height - text_item.boundingRect().height())/2
            # Place label just to the right of the bar with small gap
            gap = 6
            text_item.setPos(x + width + gap, ty)
            # Always-visible subtle contrasting background for readability
            br = text_item.boundingRect().translated(text_item.pos())
            from PyQt5.QtGui import QPen as _LblPen, QBrush as _LblBrush, QColor as _LblColor, QPainterPath as _LblPath
            bg_color = _LblColor("#FF8200")  # orange background
            padded = br.adjusted(-3,-1,3,1)
            path = _LblPath()
            radius = 6
            path.addRoundedRect(padded, radius, radius)
            bg_brush = _LblBrush(bg_color)
            bg_rect = self.scene.addPath(path, _LblPen(Qt.NoPen), bg_brush)
            bg_rect.setZValue(text_item.zValue()-1)
            text_item.setData(3, bg_rect)  # store bg rect
            text_item.setData(4, bg_brush)  # store original brush
            self._name_to_text_item[name] = text_item
            name_to_bar[name] = (x, y, width, bar_height)
            bar_items.append((rect, r))

        # ---------- Selection handling ----------
        self._bar_rect_to_row = {}
        for rect, r in bar_items:
            rect.setFlag(QGraphicsItem.ItemIsSelectable, True)
            self._bar_rect_to_row[rect] = r
        def on_selection_changed():
            selected = [it for it in self.scene.selectedItems() if it in self._bar_rect_to_row]
            if selected:
                bar = selected[0]
                try:
                    if bar.scene() is not None:
                        r = self._bar_rect_to_row[bar]
                        self.show_edit_dialog(r)
                        bar.setSelected(False)
                except RuntimeError:
                    pass
        try:
            self.scene.selectionChanged.disconnect()
        except TypeError:
            pass
        self.scene.selectionChanged.connect(on_selection_changed)

        # ---------- Axis ----------
        if min_date and max_date:
            axis_y = 30
            axis_x0 = bar_offset_x
            axis_x1 = (max_date - chart_min_date).days * 10 + bar_offset_x + 40
            self.scene.addLine(axis_x0, axis_y, axis_x1, axis_y)
            tick_interval = 7
            total_days = (max_date - chart_min_date).days
            import datetime as _dt2
            for d in range(0, total_days + 1, tick_interval):
                tick_x = axis_x0 + d * 10
                self.scene.addLine(tick_x, axis_y - 5, tick_x, axis_y + 5)
                tick_date = chart_min_date + _dt2.timedelta(days=d)
                tick_label = self.scene.addText(tick_date.strftime("%m-%d-%Y"))
                from PyQt5.QtGui import QColor as _QColor
                tick_label.setDefaultTextColor(_QColor("white"))
                tick_label.setPos(tick_x - 30, axis_y - 25)

        # ---------- Dependency arrows (simple) ----------
        from PyQt5.QtGui import QPen, QColor as _QColor2
        import datetime as _dt3
        name_to_dates = {}
        for name, start, duration, i, r in bars:
            end = start + _dt3.timedelta(days=duration)
            name_to_dates[name] = (start, end)
        for name, start, duration, i, r in bars:
            deps = r.get("Dependencies", "")
            if not deps:
                continue
            dep_list = [d.strip() for d in deps.split(',') if d.strip()]
            for dep_name in dep_list:
                if dep_name not in name_to_bar:
                    continue
                dep_x, dep_y, dep_w, dep_h = name_to_bar[dep_name]
                this_x, this_y, this_w, this_h = name_to_bar.get(name, (None, None, None, None))
                if this_x is None:
                    continue
                dep_end = name_to_dates.get(dep_name, (None, None))[1]
                this_start = name_to_dates.get(name, (None, None))[0]
                conflict = dep_end and this_start and dep_end >= this_start
                if conflict:
                    pen = QPen(_QColor2("red"), 2)
                else:
                    # Critical path dependency (both tasks critical and not conflict) use gold
                    if dep_name in critical_set and name in critical_set:
                        pen = QPen(_QColor2("#DAA520"), 2)
                    else:
                        pen = QPen(_QColor2("#FF8200"), 2)
                start_x = dep_x + dep_w
                start_y = dep_y + dep_h/2
                end_x = this_x
                end_y = this_y + this_h/2
                # L-shaped routing (feature 6)
                self.scene.addLine(start_x, start_y, end_x, start_y, pen)
                self.scene.addLine(end_x, start_y, end_x, end_y, pen)
        # ---------- Parent-child connectors (hierarchical fan-out, animated) ----------
        from PyQt5.QtGui import QPen as _QPen, QColor as _QColor3
        from PyQt5.QtWidgets import QGraphicsLineItem
        from PyQt5.QtCore import QPropertyAnimation, pyqtProperty
        draw_hierarchy = True
        if hasattr(self, 'hierarchy_checkbox'):
            try:
                draw_hierarchy = self.hierarchy_checkbox.isChecked()
            except Exception:
                draw_hierarchy = True
        class _AnimatedConnector(QGraphicsLineItem):
            def __init__(self, x1, y1, x2, y2, base_pen, highlight_pen, style):
                super().__init__(x1, y1, x2, y2)
                self._base_pen = _QPen(base_pen)
                self._highlight_pen = _QPen(highlight_pen)
                if style == 'trunk':
                    self._base_pen.setStyle(Qt.DashLine)
                    self._base_pen.setWidth(2)
                    self._highlight_pen.setWidth(3)
                else:
                    self._base_pen.setWidth(1)
                    self._highlight_pen.setWidth(2)
                self.setPen(self._base_pen)
                self._opacity = 0.55
                self._anim = None
                self._apply_opacity()
            def _apply_opacity(self):
                p = self.pen()
                c = p.color()
                c.setAlphaF(self._opacity)
                p.setColor(c)
                self.setPen(p)
            def getOpacity(self):
                return self._opacity
            def setOpacity(self, val):
                self._opacity = val
                self._apply_opacity()
            opacity = pyqtProperty(float, fget=getOpacity, fset=setOpacity)
            def fade(self, target, duration):
                if self._anim:
                    self._anim.stop()
                self._anim = QPropertyAnimation(self, b"opacity")
                self._anim.setDuration(duration)
                self._anim.setStartValue(self._opacity)
                self._anim.setEndValue(target)
                self._anim.start()
            def set_highlight(self, on):
                if on:
                    self.setPen(self._highlight_pen)
                    self.fade(1.0, 180)
                else:
                    self.setPen(self._base_pen)
                    self.fade(0.55, 260)
        self._connector_lines_map = {}
        if draw_hierarchy:
            base_color = _QColor3(180,180,180)
            trunk_color = _QColor3(160,160,160)
            highlight_color = _QColor3('#00BFFF')
            parent_children = {}
            for name, start, duration, i, r in bars:
                parent_name = r.get("Parent", "") or ""
                if parent_name and parent_name in name_to_bar and name in name_to_bar:
                    parent_children.setdefault(parent_name, []).append(name)
            def _register(part, item):
                self._connector_lines_map.setdefault(part, []).append(item)
            for parent, children in parent_children.items():
                if not children:
                    continue
                px, py, pw, ph = name_to_bar[parent]
                parent_mid_x = px + pw/2
                parent_bottom_y = py + ph
                child_positions = []
                for child in children:
                    cx, cy, cw, ch = name_to_bar[child]
                    child_positions.append((child, cx + cw/2, cy))
                child_positions.sort(key=lambda t: t[2])
                trunk_top = parent_bottom_y
                trunk_bottom = child_positions[-1][2]
                trunk = _AnimatedConnector(parent_mid_x, trunk_top, parent_mid_x, trunk_bottom,
                                            base_pen=_QPen(trunk_color), highlight_pen=_QPen(highlight_color), style='trunk')
                trunk.setZValue(-1)
                self.scene.addItem(trunk)
                _register(parent, trunk)
                for child, cmx, cty in child_positions:
                    h_line = _AnimatedConnector(min(parent_mid_x, cmx), cty, max(parent_mid_x, cmx), cty,
                                                base_pen=_QPen(base_color), highlight_pen=_QPen(highlight_color), style='child')
                    h_line.setZValue(-1)
                    self.scene.addItem(h_line)
                    v_line = _AnimatedConnector(cmx, cty, cmx, cty,
                                                base_pen=_QPen(base_color), highlight_pen=_QPen(highlight_color), style='child')
                    v_line.setZValue(-1)
                    self.scene.addItem(v_line)
                    _register(parent, h_line); _register(child, h_line)
                    _register(child, v_line); _register(parent, v_line)

        # ---------- Scene rect ----------
        self.view.setSceneRect(0, 0, 800, max(300, len(bars)*(bar_height+bar_gap)+60))
        # Adjust scene width to fit axis_x1 if larger
        current_rect = self.view.sceneRect()
        if current_rect.width() < axis_x1 + 100:
            self.view.setSceneRect(0, 0, axis_x1 + 100, current_rect.height())

    # Click-to-lock highlight support
    def mousePressEvent(self, event):
        super().mousePressEvent(event)
        # Determine if a bar was clicked -> lock its label highlight until another click
        pos = event.pos()
        if hasattr(self, 'view'):
            scene_pos = self.view.mapToScene(pos)
            items = self.scene.items(scene_pos)
            target_name = None
            for it in items:
                if hasattr(it, 'row') and isinstance(it.row, dict):
                    target_name = it.row.get("Project Part", "")
                    break
            if target_name:
                # Clear previous lock
                if hasattr(self, '_locked_label') and self._locked_label and self._locked_label != target_name:
                    self._highlight_connectors(self._locked_label, False)
                self._locked_label = target_name
                self._highlight_connectors(target_name, True)
        event.accept()

class CalendarView(QWidget):
    def __init__(self, model=None):
        super().__init__()
        self.model = model
        from PyQt5.QtWidgets import QCalendarWidget, QListWidget, QMessageBox, QPushButton, QHBoxLayout
        from PyQt5.QtGui import QTextCharFormat, QBrush, QColor
        layout = QVBoxLayout()
        layout.addWidget(QLabel("Calendar (Click a date to see tasks)"))
        self.calendar = QCalendarWidget()
        self.calendar.setGridVisible(True)
        layout.addWidget(self.calendar)
        self.task_list = QListWidget()
        layout.addWidget(self.task_list)
        # Add 'Today' and 'Export Calendar' buttons
        btn_layout = QHBoxLayout()
        today_btn = QPushButton("Today")
        today_btn.clicked.connect(self.go_to_today)
        btn_layout.addWidget(today_btn)
        export_btn = QPushButton("Export Calendar (.ics)")
        export_btn.clicked.connect(self.export_calendar_ics)
        btn_layout.addWidget(export_btn)
        layout.addLayout(btn_layout)
        self.setLayout(layout)
        self.calendar.selectionChanged.connect(self.update_task_list)
        self.calendar.clicked.connect(self.show_task_details)
        self.highlight_task_dates()
        self.update_task_list()

    def export_calendar_ics(self):
        """Export all tasks as iCalendar (.ics) file, including Pace Link, Responsible, and Type."""
        from PyQt5.QtWidgets import QFileDialog, QMessageBox
        import datetime
        if not self.model or not hasattr(self.model, 'rows'):
            QMessageBox.warning(self, "Export Failed", "No data to export.")
            return
        # Ask for file path
        path, _ = QFileDialog.getSaveFileName(self, "Export Calendar", "project_calendar.ics", "iCalendar Files (*.ics)")
        if not path:
            return
        # Build .ics content
        def escape_ics(text):
            return str(text).replace("\\", "\\\\").replace(";", "\\;").replace(",", "\\,").replace("\n", "\\n")
        ics_lines = [
            "BEGIN:VCALENDAR",
            "VERSION:2.0",
            "PRODID:-//Aja au Grimace//Project Calendar//EN"
        ]
        import re
        email_regex = r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+"
        for row in self.model.rows:
            part = row.get("Project Part", "(Unnamed)")
            start_str = row.get("Start Date", "")
            duration = row.get("Duration (days)", "")
            notes = row.get("Notes", "")
            pace_link = row.get("Pace Link", "")
            responsible = row.get("Responsible", "")
            type_ = row.get("Type", "")
            if not start_str or not duration:
                continue
            try:
                start_dt = datetime.datetime.strptime(start_str, "%m-%d-%Y")
                days = int(duration)
                # End date is exclusive in iCalendar, so add 1 day
                end_dt = start_dt + datetime.timedelta(days=days)
                dtstart = start_dt.strftime("%Y%m%d")
                dtend = end_dt.strftime("%Y%m%d")
            except Exception:
                continue
            # Compose description with all requested fields
            desc_lines = []
            if notes:
                desc_lines.append(notes)
            if pace_link:
                desc_lines.append(f"Pace Link: {pace_link}")
            if responsible:
                desc_lines.append(f"Responsible: {responsible}")
            if type_:
                desc_lines.append(f"Type: {type_}")
            description = "\n".join(desc_lines)
            # Find all email addresses in Responsible field
            attendee_lines = []
            if responsible:
                emails = re.findall(email_regex, responsible)
                for email in emails:
                    attendee_lines.append(f"ATTENDEE;CN={email}:mailto:{email}")
            ics_lines.extend([
                "BEGIN:VEVENT",
                f"SUMMARY:{escape_ics(part)}",
                f"DTSTART;VALUE=DATE:{dtstart}",
                f"DTEND;VALUE=DATE:{dtend}",
                f"DESCRIPTION:{escape_ics(description)}",
            ] + attendee_lines + [
                "END:VEVENT"
            ])
        ics_lines.append("END:VCALENDAR")
        try:
            with open(path, "w", encoding="utf-8") as f:
                f.write("\r\n".join(ics_lines))
            QMessageBox.information(self, "Export Complete", f"Calendar exported to {path}")
        except Exception as e:
            QMessageBox.critical(self, "Export Failed", f"Could not write file: {e}")

    def highlight_task_dates(self):
        if not self.model:
            return
        from PyQt5.QtGui import QTextCharFormat, QBrush, QColor
        fmt = QTextCharFormat()
        fmt.setBackground(QBrush(QColor("#ffe082")))  # Light yellow
        # Clear previous highlights
        self.calendar.setDateTextFormat(self.calendar.minimumDate(), QTextCharFormat())
        self.calendar.setDateTextFormat(self.calendar.maximumDate(), QTextCharFormat())
        # Highlight all dates with tasks
        dates_with_tasks = set()
        for row in getattr(self.model, 'rows', []):
            date_str = row.get("Start Date", "")
            if date_str:
                from PyQt5.QtCore import QDate
                date = QDate.fromString(date_str, "MM-dd-yyyy")
                if date.isValid():
                    dates_with_tasks.add(date)
        for date in dates_with_tasks:
            self.calendar.setDateTextFormat(date, fmt)

    def update_task_list(self):
        self.task_list.clear()
        if not self.model:
            return
        selected_date = self.calendar.selectedDate()
        date_str = selected_date.toString("MM-dd-yyyy")
        for row in getattr(self.model, 'rows', []):
            if row.get("Start Date", "") == date_str:
                part = row.get("Project Part", "(Unnamed)")
                self.task_list.addItem(part)

    def show_task_details(self, qdate):
        if not self.model:
            return
        date_str = qdate.toString("MM-dd-yyyy")
        tasks = [row for row in getattr(self.model, 'rows', []) if row.get("Start Date", "") == date_str]
        if not tasks:
            return
        msg = "Tasks for {}:\n".format(date_str)
        for row in tasks:
            msg += f"- {row.get('Project Part', '(Unnamed)')}\n"
        QMessageBox.information(self, "Tasks on {}".format(date_str), msg)

    def go_to_today(self):
        from PyQt5.QtCore import QDate
        self.calendar.setSelectedDate(QDate.currentDate())
        self.update_task_list()
        self.calendar.showSelectedDate()

class TimelineView(QWidget):
    def __init__(self, model=None):
        super().__init__()
        self.model = model
        layout = QVBoxLayout()
        layout.addWidget(QLabel("Project Timeline (Read-Only)"))
        from PyQt5.QtWidgets import QGraphicsView, QGraphicsScene
        self.scene = QGraphicsScene()
        self.view = QGraphicsView(self.scene)
        layout.addWidget(self.view)
        # Export buttons
        from PyQt5.QtWidgets import QHBoxLayout, QPushButton
        export_row = QHBoxLayout()
        export_png_btn = QPushButton("Export Timeline (PNG/PDF)")
        def _do_export():
            # Reuse GanttChartView helper through lightweight wrapper
            try:
                # Local import to avoid circular issues
                helper = getattr(self, '_export_helper', None)
                if helper is None:
                    helper = GanttChartView()  # temporary helper just for exporter
                    self._export_helper = helper
                helper._export_scene_with_header(self.scene, title="Timeline")
            except Exception as e:
                print(f"Timeline export failed: {e}")
        export_png_btn.clicked.connect(_do_export)
        export_row.addWidget(export_png_btn)
        layout.addLayout(export_row)
        self.preview_label = QLabel()
        self.preview_label.setFixedHeight(200)
        self.preview_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.preview_label)
        self.setLayout(layout)
        self.render_timeline()

    def render_timeline(self):
        # --- Critical Path Calculation ---
        def find_critical_path(rows):
            import datetime
            # Build graph: node = part name, edges = dependencies
            name_to_row = {row.get("Project Part", ""): row for row in rows}
            graph = {}
            for row in rows:
                name = row.get("Project Part", "")
                deps = row.get("Dependencies", "")
                dep_list = [d.strip() for d in deps.split(",") if d.strip()]
                graph[name] = dep_list
            # Topo sort
            visited = set()
            order = []
            def visit(n):
                if n in visited:
                    return
                for dep in graph.get(n, []):
                    visit(dep)
                visited.add(n)
                order.append(n)
            for n in graph:
                visit(n)
            # Calculate earliest start/finish
            est = {}
            eft = {}
            for n in order:
                row = name_to_row.get(n, {})
                duration = int(row.get("Duration (days)", 0) or 0)
                if not duration:
                    continue
                deps = graph.get(n, [])
                if not deps:
                    start = row.get("Start Date", "")
                    if start:
                        est[n] = datetime.datetime.strptime(start, "%m-%d-%Y")
                    else:
                        est[n] = datetime.datetime.min
                else:
                    est[n] = max([eft.get(dep, datetime.datetime.min) for dep in deps])
                eft[n] = est[n] + datetime.timedelta(days=duration)
            # Calculate latest finish/start
            lft = {n: max(eft.values()) for n in order}
            lst = {}
            for n in reversed(order):
                row = name_to_row.get(n, {})
                duration = int(row.get("Duration (days)", 0) or 0)
                deps = graph.get(n, [])
                if not deps:
                    lft[n] = lft[n]
                else:
                    lft[n] = min([lst.get(dep, lft[n]) for dep in deps])
                lst[n] = lft[n] - datetime.timedelta(days=duration)
            # Critical path: nodes where est==lst
            critical = set(n for n in order if est.get(n) == lst.get(n))
            return critical
        import datetime
        from PyQt5.QtGui import QBrush, QColor
        from PyQt5.QtCore import QDate
        self.scene.clear()
        if not self.model or not hasattr(self.model, 'rows'):
            return
        rows = [row for row in self.model.rows if row.get("Start Date") and row.get("Duration (days)")]
        # --- Critical Path ---
        critical_path = find_critical_path(rows)
        # ...existing code...
        def topo_sort(rows):
            name_to_row = {row.get("Project Part", ""): row for row in rows}
            visited = set()
            result = []
            def visit(row):
                name = row.get("Project Part", "")
                if name in visited:
                    return
                parent = row.get("Parent", "")
                if parent and parent in name_to_row:
                    visit(name_to_row[parent])
                visited.add(name)
                result.append(row)
            for row in rows:
                visit(row)
            return result
        def compute_parent_spans(rows):
            import datetime
            name_to_row = {row.get("Project Part", ""): row for row in rows}
            children = {}
            for row in rows:
                parent = row.get("Parent", "")
                if parent:
                    children.setdefault(parent, []).append(row)
            def update_span(row, visited=None):
                if visited is None:
                    visited = set()
                name = row.get("Project Part", "")
                if name in visited:
                    # Cycle detected, break recursion
                    return None, None
                visited.add(name)
                if name not in children:
                    try:
                        start = datetime.datetime.strptime(row.get("Start Date", ""), "%m-%d-%Y")
                        duration = int(row.get("Duration (days)", 0))
                        end = start + datetime.timedelta(days=duration)
                        return start, end
                    except Exception:
                        return None, None
                else:
                    child_spans = [update_span(child, visited.copy()) for child in children[row.get("Project Part")]]
                    child_starts = [s for s, e in child_spans if s]
                    child_ends = [e for s, e in child_spans if e]
                    if child_starts and child_ends:
                        min_start = min(child_starts)
                        max_end = max(child_ends)
                        row["_auto_start"] = min_start
                        row["_auto_end"] = max_end
                        return min_start, max_end
                    return None, None
            for row in rows:
                update_span(row)
        compute_parent_spans(rows)
        rows = topo_sort(rows)
        if not rows:
            return
        # Parse dates and durations
        bars = []
        name_to_idx = {}
        for idx, row in enumerate(rows):
            if "_auto_start" in row and "_auto_end" in row:
                start = row["_auto_start"]
                end = row["_auto_end"]
                duration = (end - start).days
            else:
                start_str = row.get("Start Date", "")
                duration = row.get("Duration (days)", 0)
                try:
                    start = datetime.datetime.strptime(start_str, "%m-%d-%Y")
                    duration = int(duration)
                    end = start + datetime.timedelta(days=duration)
                except Exception:
                    continue
            bars.append((row.get("Project Part", "(Unnamed)"), start, duration, row, idx))
            name_to_idx[row.get("Project Part", "(Unnamed)")] = idx
        if not bars:
            return
        # Find min and max dates
        min_date = min([b[1] for b in bars])
        max_date = max([b[1] + datetime.timedelta(days=b[2]) for b in bars])
        total_days = (max_date - min_date).days
        # Draw bars and record their positions for connectors
        bar_height = 24
        bar_gap = 12
        # (Reverted) Remove left-column label layout; use a fixed bar offset and put labels on bars.
        from PyQt5.QtGui import QFontMetrics
        font = self.font() if hasattr(self, 'font') else None
        fm = QFontMetrics(font) if font else None
        max_chars_fixed_tl = 32
        left_margin = 60
        bar_offset_x = left_margin
        y = 40
        bar_positions = {}  # idx -> (x, y, width)
        self._timeline_name_to_text = {}
        for name, start, duration, row, idx in bars:
            x = bar_offset_x + (start - min_date).days * 8
            width = max(8, duration * 8)
            # Highlight critical path bars in red
            color = QColor("red") if name in critical_path else QColor("#FF8200")
            # Add hoverable rect for image preview
            from PyQt5.QtWidgets import QGraphicsRectItem
            class HoverableTimelineBar(QGraphicsRectItem):
                def __init__(self, x, y, width, height, row, timeline_view):
                    super().__init__(x, y, width, height)
                    self.row = row
                    self.timeline_view = timeline_view
                    self.setAcceptHoverEvents(True)
                def get_preview_label(self):
                    # Try to get preview_label from parent widget
                    parent = self.timeline_view.parent()
                    if hasattr(parent, 'preview_label'):
                        return parent.preview_label
                    # Fallback: try timeline_view itself
                    if hasattr(self.timeline_view, 'preview_label'):
                        return self.timeline_view.preview_label
                    return None
                def hoverEnterEvent(self, event):
                    preview_label = self.get_preview_label()
                    if preview_label is None:
                        super().hoverEnterEvent(event)
                        return
                    img_path = self.row.get("Images", "")
                    if img_path and str(img_path).strip():
                        import os
                        from PyQt5.QtGui import QPixmap
                        if not os.path.isabs(img_path):
                            base_dir = os.path.dirname(os.path.abspath(__file__))
                            img_path_full = os.path.join(base_dir, img_path)
                        else:
                            img_path_full = img_path
                        pixmap = QPixmap(img_path_full)
                        if not pixmap.isNull():
                            preview_label.setPixmap(pixmap.scaledToHeight(180, Qt.SmoothTransformation))
                            preview_label.setText("")
                        else:
                            preview_label.setText("[Image not found]")
                            preview_label.setPixmap(QPixmap())
                    else:
                        preview_label.clear()
                    super().hoverEnterEvent(event)
                def hoverLeaveEvent(self, event):
                    preview_label = self.get_preview_label()
                    if preview_label is not None:
                        preview_label.clear()
                    super().hoverLeaveEvent(event)
            bar_item = HoverableTimelineBar(x, y, width, bar_height, row, self)
            bar_item.setBrush(QBrush(color))
            self.scene.addItem(bar_item)
            full_name = name
            display_name = full_name
            if len(display_name) > max_chars_fixed_tl:
                display_name = display_name[:max_chars_fixed_tl-1] + "…"
            text_item = self.scene.addText(display_name)
            from PyQt5.QtGui import QFont, QPen, QBrush
            text_item.setDefaultTextColor(QColor("white"))
            orig_font = text_item.font()
            text_item.setData(1, orig_font)
            text_item.setData(2, full_name)
            text_item.setToolTip(full_name)
            # Center vertically and place label to the right of the bar
            ty = y + (bar_height - text_item.boundingRect().height())/2
            gap = 6
            text_item.setPos(x + width + gap, ty)
            # Always-visible subtle contrasting background
            from PyQt5.QtGui import QPen as _LblPen2, QBrush as _LblBrush2, QColor as _LblColor2
            br = text_item.boundingRect().translated(text_item.pos())
            bg_color = _LblColor2(0,0,0,160)
            padded = br.adjusted(-3,-1,3,1)
            from PyQt5.QtGui import QPainterPath as _LblPath2
            path = _LblPath2()
            radius = 6
            path.addRoundedRect(padded, radius, radius)
            bg_rect = self.scene.addPath(path, _LblPen2(Qt.NoPen), _LblBrush2(bg_color))
            bg_rect.setZValue(text_item.zValue()-1)
            text_item.setData(3, bg_rect)
            self._timeline_name_to_text[name] = text_item
            bar_positions[idx] = (x, y, width)
            y += bar_height + bar_gap
        # Draw connector lines for parent-child relationships
        for name, start, duration, row, idx in bars:
            parent_name = row.get("Parent", "")
            if parent_name and parent_name in name_to_idx:
                parent_idx = name_to_idx[parent_name]
                if parent_idx in bar_positions and idx in bar_positions:
                    px, py, pwidth = bar_positions[parent_idx]
                    cx, cy, cwidth = bar_positions[idx]
                    parent_mid_x = px + pwidth // 2
                    child_mid_x = cx + cwidth // 2
                    parent_bottom = py + bar_height
                    child_top = cy
                    # Highlight critical path connectors in red
                    from PyQt5.QtGui import QPen
                    pen = QPen(QColor("red"), 2) if name in critical_path and parent_name in critical_path else QPen(QColor("#FF8200"), 2)
                    # Vertical line from parent to horizontal level
                    self.scene.addLine(parent_mid_x, parent_bottom, parent_mid_x, (parent_bottom + child_top) // 2, pen)
                    # Horizontal line to child
                    self.scene.addLine(parent_mid_x, (parent_bottom + child_top) // 2, child_mid_x, (parent_bottom + child_top) // 2, pen)
                    # Vertical line down to child
                    self.scene.addLine(child_mid_x, (parent_bottom + child_top) // 2, child_mid_x, child_top, pen)
        # Draw x-axis with date marks every 7 days
        axis_y = 20
        axis_x0 = bar_offset_x
        axis_x1 = bar_offset_x + total_days * 8 + 40
        self.scene.addLine(axis_x0, axis_y, axis_x1, axis_y)
        for d in range(0, total_days + 1, 7):
            tick_x = axis_x0 + d * 8
            self.scene.addLine(tick_x, axis_y - 5, tick_x, axis_y + 5)
            tick_date = min_date + datetime.timedelta(days=d)
            tick_label = self.scene.addText(tick_date.strftime("%m-%d-%Y"))
            tick_label.setDefaultTextColor(QColor("white"))
            tick_label.setPos(tick_x - 30, axis_y - 25)
        self.view.setSceneRect(0, 0, axis_x1 + 40, max(300, y + 40))
        # Extend hover bars to highlight labels (monkey patch hover events)
        for item in self.scene.items():
            if hasattr(item, 'row') and hasattr(item, 'hoverEnterEvent'):
                original_enter = item.hoverEnterEvent
                original_leave = item.hoverLeaveEvent
                def make_enter(orig, bar_item=item):
                    def _enter(ev):
                        try:
                            name = bar_item.row.get("Project Part", "")
                            ti = self._timeline_name_to_text.get(name)
                            if ti:
                                f = QFont(ti.font())
                                f.setBold(True)
                                ti.setFont(f)
                                bg = ti.data(3)
                                if bg:
                                    from PyQt5.QtGui import QColor as _QColorTL, QBrush as _QBrushTL
                                    bg.setBrush(_QBrushTL(_QColorTL(255,255,255,50)))
                        except Exception:
                            pass
                        return orig(ev)
                    return _enter
                def make_leave(orig_leave, bar_item=item):
                    def _leave(ev):
                        try:
                            name = bar_item.row.get("Project Part", "")
                            ti = self._timeline_name_to_text.get(name)
                            if ti:
                                base_font = ti.data(1)
                                if isinstance(base_font, QFont):
                                    ti.setFont(base_font)
                                bg = ti.data(3)
                                if bg:
                                    from PyQt5.QtGui import QBrush as _QBrushTL2
                                    bg.setBrush(_QBrushTL2(Qt.transparent))
                        except Exception:
                            pass
                        return orig_leave(ev)
                    return _leave
                item.hoverEnterEvent = make_enter(original_enter)
                item.hoverLeaveEvent = make_leave(original_leave)
        # Click-to-lock for timeline (reusing view mouse events)
        def lock_click_event(event):
            if event.button() == Qt.LeftButton:
                scene_pos = self.view.mapToScene(event.pos())
                for it in self.scene.items(scene_pos):
                    if hasattr(it, 'row'):
                        name = it.row.get("Project Part", "")
                        # Clear existing lock
                        if hasattr(self, '_timeline_locked') and self._timeline_locked and self._timeline_locked != name:
                            # Reset previous locked label
                            prev_ti = self._timeline_name_to_text.get(self._timeline_locked)
                            if prev_ti:
                                orig = prev_ti.data(1)
                                if isinstance(orig, QFont):
                                    prev_ti.setFont(orig)
                                bg = prev_ti.data(3)
                                if bg:
                                    from PyQt5.QtGui import QBrush
                                    bg.setBrush(QBrush(Qt.transparent))
                        self._timeline_locked = name
                        ti = self._timeline_name_to_text.get(name)
                        if ti:
                            f = QFont(ti.font()); f.setBold(True); ti.setFont(f)
                            bg = ti.data(3)
                            if bg:
                                from PyQt5.QtGui import QColor, QBrush
                                bg.setBrush(QBrush(QColor(255,255,255,70)))
                        break
            return original_mouse_press(event)
        if not hasattr(self.view, '_lock_click_installed'):
            original_mouse_press = self.view.mousePressEvent
            self.view.mousePressEvent = lock_click_event
            self.view._lock_click_installed = True


# New DatabaseView class
from PyQt5.QtWidgets import QTableWidget, QTableWidgetItem

from PyQt5.QtWidgets import QDateEdit
from PyQt5.QtCore import QDate

class DatabaseView(QWidget):
    DATE_FIELDS = {"Start Date", "Calculated End Date"}
    DROPDOWN_FIELDS = {
        "Internal/External": ["Internal", "External"],
    "Type": ["Milestone", "Phase", "Feature", "Item"],
    # Progress status field handled similarly
    "Status": ["Planned", "In Progress", "Blocked", "Done", "Deferred"]
    }
    PROGRESS_STATUSES = ["Planned", "In Progress", "Blocked", "Done", "Deferred"]

    def __init__(self, model, on_data_changed=None):
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
        export_btn = QPushButton("Export Database")
        export_btn.clicked.connect(self.export_database)
        btn_layout.addWidget(export_btn)
        import_btn = QPushButton("Import Data")
        import_btn.clicked.connect(self.import_data)
        btn_layout.addWidget(import_btn)
        layout.addLayout(btn_layout)

        self.setLayout(layout)
        self.refresh_table()
        self.table.cellChanged.connect(self.cell_edited)

    def import_data(self):
        from PyQt5.QtWidgets import QFileDialog, QMessageBox
        import csv
        path, _ = QFileDialog.getOpenFileName(self, "Import Data", "", "CSV Files (*.csv)")
        if not path:
            return
        try:
            with open(path, "r", encoding='utf-8') as f:
                reader = csv.DictReader(f)
                imported_rows = []
                for row in reader:
                    imported_row = {col: row.get(col, "") for col in ProjectDataModel.COLUMNS}
                    imported_rows.append(imported_row)
            # Replace current data with imported data
            self.model.rows = imported_rows
            self.model.save_to_db()
            self.refresh_table()
            QMessageBox.information(self, "Import Successful", f"Imported {len(imported_rows)} rows from {path}")
        except Exception as e:
            QMessageBox.critical(self, "Import Failed", f"Error importing data: {e}")
    def export_database(self):
        from PyQt5.QtWidgets import QFileDialog, QMessageBox
        import csv
        path, _ = QFileDialog.getSaveFileName(self, "Export Database", "database_export.csv", "CSV Files (*.csv)")
        if not path:
            return
        try:
            with open(path, "w", newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow(ProjectDataModel.COLUMNS)
                for row in self.model.rows:
                    writer.writerow([row.get(col, "") for col in ProjectDataModel.COLUMNS])
            QMessageBox.information(self, "Export Successful", f"Database exported to {path}")
        except Exception as e:
            QMessageBox.critical(self, "Export Failed", f"Error exporting database: {e}")

    def refresh_table(self):
        self.table.blockSignals(True)
        self.table.setRowCount(len(self.model.rows))
        for row, rowdata in enumerate(self.model.rows):
            # Determine if this row is a parent (has at least one child referencing its Project Part)
            part_name = rowdata.get("Project Part", "")
            has_children = any(r.get("Parent", "") == part_name for r in self.model.rows if r is not rowdata)
            for col, colname in enumerate(ProjectDataModel.COLUMNS):
                # Only use QDateEdit for editable date fields, not Calculated End Date
                if colname in self.DATE_FIELDS and colname != "Calculated End Date":
                    date_val = rowdata.get(colname, "")
                    date_edit = QDateEdit()
                    date_edit.setCalendarPopup(True)
                    min_blank = QDate(1753, 1, 1)
                    date_edit.setMinimumDate(min_blank)
                    date_edit.setSpecialValueText("")
                    # Prevent wheel events unless focused (clicked)
                    def block_wheel(event):
                        if not date_edit.hasFocus():
                            event.ignore()
                        else:
                            QDateEdit.wheelEvent(date_edit, event)
                    date_edit.wheelEvent = block_wheel
                    if date_val:
                        try:
                            date = QDate.fromString(date_val, "MM-dd-yyyy")
                            if date.isValid() and date != QDate(1752, 9, 14) and date != min_blank:
                                date_edit.setDate(date)
                            else:
                                if colname == "Start Date":
                                    date_edit.setDate(QDate.currentDate())
                                else:
                                    date_edit.clear()
                        except Exception:
                            if colname == "Start Date":
                                date_edit.setDate(QDate.currentDate())
                            else:
                                date_edit.clear()
                    else:
                        if colname == "Start Date":
                            date_edit.setDate(QDate.currentDate())
                        else:
                            date_edit.clear()
                    date_edit.dateChanged.connect(lambda d, r=row, c=col: self.date_changed(r, c, d))
                    self.table.setCellWidget(row, col, date_edit)
                    # Show blank in the table cell if value is empty or minimum blank
                    if not date_val or date_val == min_blank.toString("MM-dd-yyyy"):
                        self.table.setItem(row, col, QTableWidgetItem(""))
                    else:
                        self.table.setItem(row, col, QTableWidgetItem(date_val))
                elif colname == "Calculated End Date":
                    # Show as read-only text
                    val = rowdata.get(colname, "")
                    self.table.setItem(row, col, QTableWidgetItem(val))
                elif colname == "% Complete":
                    from PyQt5.QtWidgets import QSpinBox
                    spin = QSpinBox()
                    spin.setRange(0, 100)
                    try:
                        spin.setValue(int(rowdata.get(colname) or 0))
                    except Exception:
                        spin.setValue(0)
                    # Prevent wheel without focus
                    def block_wheel_spin(event, sb=spin):
                        if not sb.hasFocus():
                            event.ignore()
                        else:
                            QSpinBox.wheelEvent(sb, event)
                    spin.wheelEvent = block_wheel_spin
                    if has_children:
                        spin.setEnabled(False)
                        spin.setToolTip("Parent progress is rolled up automatically from children.")
                    else:
                        spin.valueChanged.connect(lambda val, r=row, c=col: self.percent_changed(r, c, val))
                    self.table.setCellWidget(row, col, spin)
                    self.table.setItem(row, col, QTableWidgetItem(str(spin.value())))
                elif colname in self.DROPDOWN_FIELDS or colname == "Parent":
                    from PyQt5.QtWidgets import QComboBox
                    combo = QComboBox()
                    # Prevent wheel events unless focused (clicked)
                    def block_wheel_combo(event):
                        if not combo.hasFocus():
                            event.ignore()
                        else:
                            QComboBox.wheelEvent(combo, event)
                    combo.wheelEvent = block_wheel_combo
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
                        if colname == "Status":
                            if has_children:
                                combo.setEnabled(False)
                                combo.setToolTip("Parent status is derived from child statuses.")
                            else:
                                combo.currentTextChanged.connect(lambda val, r=row, c=col: self.status_changed(r, c, val))
                        else:
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
                elif colname == "Pace Link":
                    link = rowdata.get(colname, "")
                    if link and (link.startswith("http://") or link.startswith("https://")):
                        label = QLabel(f'<a href="{link}">{link}</a>')
                        label.setOpenExternalLinks(True)
                        self.table.setCellWidget(row, col, label)
                        self.table.setItem(row, col, QTableWidgetItem(link))
                    else:
                        line_edit = QLineEdit(link)
                        def on_edit_finished(row=row, col=col, edit=line_edit):
                            val = edit.text()
                            self.model.rows[row][colname] = val
                            self.model.save_to_db()
                            self.refresh_table()
                            if self.on_data_changed:
                                self.on_data_changed()
                        line_edit.editingFinished.connect(on_edit_finished)
                        self.table.setCellWidget(row, col, line_edit)
                        self.table.setItem(row, col, QTableWidgetItem(link))
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

        # Automatically resize Project Part column to fit contents
        part_col = ProjectDataModel.COLUMNS.index("Project Part")
        self.table.resizeColumnToContents(part_col)

    def add_row(self):
        data = []
        for col in ProjectDataModel.COLUMNS:
            if col == "Duration (days)":
                data.append("1")
            elif col == "Internal/External":
                data.append("Internal")
            elif col == "% Complete":
                data.append("0")
            elif col == "Status":
                data.append("Planned")
            # Removed Deadline field
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
                date_val = widget.date().toString("MM-dd-yyyy")
                self.model.rows[row][colname] = date_val
        elif colname in self.DROPDOWN_FIELDS or colname == "Parent":
            widget = self.table.cellWidget(row, col)
            if widget:
                self.model.rows[row][colname] = widget.currentText()
        elif colname == "Pace Link":
            widget = self.table.cellWidget(row, col)
            if isinstance(widget, QLineEdit):
                val = widget.text()
                self.model.rows[row][colname] = val

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
        try:
            self.model.rows[row][colname] = value
            self.table.blockSignals(True)
            self.table.setItem(row, col, QTableWidgetItem(value))
            self.table.blockSignals(False)
            # Save & propagate roll-ups
            self.model.save_to_db()
            # Refresh to update parent rows (Children column / roll-ups)
            self.refresh_table()
            if self.on_data_changed:
                self.on_data_changed()
        except Exception as e:
            print(f"ERROR in dropdown_changed: {e}")
    def date_changed(self, row, col, qdate):
        colname = ProjectDataModel.COLUMNS[col]
        min_blank = QDate(1753, 1, 1)
        try:
            if qdate == min_blank:
                self.model.rows[row][colname] = ""
                date_val = ""
            else:
                date_val = qdate.toString("MM-dd-yyyy")
                self.model.rows[row][colname] = date_val
            self.table.blockSignals(True)
            self.table.setItem(row, col, QTableWidgetItem(date_val))
            self.table.blockSignals(False)
            self.model.save_to_db()
            self.refresh_table()
            if self.on_data_changed:
                self.on_data_changed()
        except Exception as e:
            print(f"ERROR in date_changed: {e}")

    # --- Progress field handlers ---
    def percent_changed(self, row, col, value):
        try:
            self.model.rows[row]["% Complete"] = int(value)
            # Auto-mark Done if 100%
            if int(value) >= 100 and self.model.rows[row].get("Status") != "Done":
                self.model.rows[row]["Status"] = "Done"
                # Set Actual Finish Date if missing
                import datetime
                if not self.model.rows[row].get("Actual Finish Date"):
                    self.model.rows[row]["Actual Finish Date"] = datetime.datetime.today().strftime("%m-%d-%Y")
                if not self.model.rows[row].get("Actual Start Date"):
                    self.model.rows[row]["Actual Start Date"] = datetime.datetime.today().strftime("%m-%d-%Y")
            self.model.save_to_db()
            self.refresh_table()
            if self.on_data_changed:
                self.on_data_changed()
        except Exception as e:
            print(f"ERROR in percent_changed: {e}")

    def status_changed(self, row, col, value):
        try:
            prev = self.model.rows[row].get("Status")
            self.model.rows[row]["Status"] = value
            import datetime
            today_str = datetime.datetime.today().strftime("%m-%d-%Y")
            if value == "In Progress":
                if not self.model.rows[row].get("Actual Start Date"):
                    self.model.rows[row]["Actual Start Date"] = today_str
                # If % Complete is 0, maybe bump to 1 for visibility? (skip for now)
            elif value == "Done":
                # Ensure 100% and finish date
                self.model.rows[row]["% Complete"] = 100
                if not self.model.rows[row].get("Actual Start Date"):
                    self.model.rows[row]["Actual Start Date"] = today_str
                if not self.model.rows[row].get("Actual Finish Date"):
                    self.model.rows[row]["Actual Finish Date"] = today_str
            # Do not clear actual dates if reverting; keep historical record
            self.model.save_to_db()
            self.refresh_table()
            if self.on_data_changed:
                self.on_data_changed()
        except Exception as e:
            print(f"ERROR in status_changed: {e}")


class MainWindow(QMainWindow):
    def on_data_changed(self):
        # Refresh all views when data changes
        if hasattr(self, 'project_tree_view'):
            self.project_tree_view.refresh()
        if hasattr(self, 'gantt_chart_view'):
            self.gantt_chart_view.render_gantt(self.model)
        if hasattr(self, 'timeline_view'):
            self.timeline_view.render_timeline()
        if hasattr(self, 'database_view'):
            self.database_view.refresh_table()
        if hasattr(self, 'progress_dashboard'):
            # Refresh metrics summary
            self.progress_dashboard.refresh()
    def display_view(self, index):
        self.views.setCurrentIndex(index)
        if index == 0:
            self.project_tree_view.refresh()
        elif index == 1:
            self.gantt_chart_view.render_gantt(self.model)
        elif index == 4:
            self.database_view.refresh_table()
        elif index == 5 and hasattr(self, 'progress_dashboard'):
            self.progress_dashboard.refresh()
    def __init__(self, model):
        try:
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

            # Header with centered header.png image
            header_layout = QHBoxLayout()
            header_layout.addStretch(1)
            header_label = QLabel()
            import sys
            if getattr(sys, 'frozen', False):
                header_path = os.path.join(os.path.dirname(sys.executable), "header.png")
            else:
                header_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "header.png")
            if os.path.exists(header_path):
                header_pixmap = QPixmap(header_path)
                # Double the previous height: 64 -> 128
                header_label.setPixmap(header_pixmap.scaledToHeight(128, Qt.SmoothTransformation))
            else:
                header_label.setText("[header.png not found]")
            header_layout.addWidget(header_label, alignment=Qt.AlignCenter)
            header_layout.addStretch(1)

            # Search / Jump field (affects Gantt view)
            from PyQt5.QtWidgets import QLineEdit, QPushButton
            self.search_input = QLineEdit()
            self.search_input.setPlaceholderText("Jump to part (substring)...")
            self.search_input.setFixedWidth(260)
            jump_btn = QPushButton("Jump")
            def do_jump():
                text = self.search_input.text().strip()
                if not text:
                    return
                # Find first matching part name (case-insensitive)
                lower = text.lower()
                match_name = None
                for r in self.model.rows:
                    name = r.get("Project Part", "")
                    if lower in name.lower():
                        match_name = name
                        break
                if match_name and hasattr(self.gantt_chart_view, 'highlight_bar'):
                    # Ensure Gantt view visible
                    if self.sidebar.currentRow() != 1:
                        self.sidebar.setCurrentRow(1)
                    self.gantt_chart_view.highlight_bar(match_name)
            jump_btn.clicked.connect(do_jump)
            self.search_input.returnPressed.connect(do_jump)
            header_layout.addWidget(self.search_input)
            header_layout.addWidget(jump_btn)

            # --- Filter Panel Dock (collapsible) ---
            from PyQt5.QtWidgets import QDockWidget, QWidget as _QW, QVBoxLayout as _QVBox, QLabel as _QL, QCheckBox, QGroupBox, QHBoxLayout as _QHBox, QLineEdit as _QLE, QPushButton as _QPB
            from PyQt5.QtCore import QSettings
            self.filter_dock = QDockWidget("Filters", self)
            self.filter_dock.setFeatures(QDockWidget.DockWidgetClosable | QDockWidget.DockWidgetMovable | QDockWidget.DockWidgetFloatable)
            filt_container = _QW()
            vbox = _QVBox(filt_container)
            vbox.setContentsMargins(8,8,8,8)
            vbox.setSpacing(6)
            # Status checkboxes
            status_group = QGroupBox("Status")
            sg_layout = _QVBox()
            self.chk_status = {}
            for st in ["Planned","In Progress","Blocked","Done"]:
                cb = QCheckBox(st)
                self.chk_status[st] = cb
                sg_layout.addWidget(cb)
            status_group.setLayout(sg_layout)
            vbox.addWidget(status_group)
            # Internal/External
            ie_group = QGroupBox("Internal / External")
            ie_layout = _QVBox()
            self.chk_internal = QCheckBox("Internal")
            self.chk_external = QCheckBox("External")
            ie_layout.addWidget(self.chk_internal)
            ie_layout.addWidget(self.chk_external)
            ie_group.setLayout(ie_layout)
            vbox.addWidget(ie_group)
            # Responsible substring
            resp_group = QGroupBox("Responsible Contains")
            rg_layout = _QVBox()
            self.resp_input = _QLE()
            self.resp_input.setPlaceholderText("Name substring...")
            rg_layout.addWidget(self.resp_input)
            resp_group.setLayout(rg_layout)
            vbox.addWidget(resp_group)
            # Critical & Risk toggles
            flags_group = QGroupBox("Special")
            fl_layout = _QVBox()
            self.chk_critical_only = QCheckBox("Critical Path Only")
            self.chk_risk_only = QCheckBox("Risk (Overdue / At-Risk) Only")
            fl_layout.addWidget(self.chk_critical_only)
            fl_layout.addWidget(self.chk_risk_only)
            flags_group.setLayout(fl_layout)
            vbox.addWidget(flags_group)
            # Active summary label
            self.filter_summary = _QL("No filters active")
            self.filter_summary.setStyleSheet("color:#ccc; font-size:11px")
            vbox.addWidget(self.filter_summary)
            # Buttons
            btn_row = _QHBox()
            apply_btn = _QPB("Apply")
            reset_btn = _QPB("Reset")
            btn_row.addWidget(apply_btn)
            btn_row.addWidget(reset_btn)
            vbox.addLayout(btn_row)
            vbox.addStretch(1)
            filt_container.setLayout(vbox)
            self.filter_dock.setWidget(filt_container)
            self.addDockWidget(Qt.RightDockWidgetArea, self.filter_dock)

            # Debounce timer for responsible input
            from PyQt5.QtCore import QTimer as _QTimer
            self._resp_timer = _QTimer(self)
            self._resp_timer.setInterval(500)
            self._resp_timer.setSingleShot(True)
            def resp_changed():
                self._resp_timer.start()
            self.resp_input.textChanged.connect(resp_changed)
            def apply_filters():
                statuses = [s for s, cb in self.chk_status.items() if cb.isChecked()]
                ie = []
                if self.chk_internal.isChecked():
                    ie.append("Internal")
                if self.chk_external.isChecked():
                    ie.append("External")
                resp = self.resp_input.text().strip()
                crit = self.chk_critical_only.isChecked()
                risk = self.chk_risk_only.isChecked()
                if hasattr(self, 'gantt_chart_view'):
                    self.gantt_chart_view.set_filters(
                        statuses=statuses if statuses else None,
                        internal_external=ie if ie else None,
                        responsible_substr=resp if resp else None,
                        critical_only=crit,
                        risk_only=risk
                    )
                # Update summary
                parts = []
                if statuses: parts.append(f"Status={len(statuses)}")
                if ie: parts.append(f"IE={','.join(ie)}")
                if resp: parts.append(f"Resp~{resp}")
                if crit: parts.append("Critical")
                if risk: parts.append("Risk")
                self.filter_summary.setText(" | ".join(parts) if parts else "No filters active")
                # Persist after each apply for immediate save
                try:
                    self.save_filter_settings()
                except Exception:
                    pass
            # expose for external calls
            self._apply_filters = apply_filters
            def timer_apply():
                apply_filters()
            self._resp_timer.timeout.connect(timer_apply)
            apply_btn.clicked.connect(apply_filters)
            def reset_filters():
                for cb in self.chk_status.values(): cb.setChecked(False)
                self.chk_internal.setChecked(False)
                self.chk_external.setChecked(False)
                self.resp_input.clear()
                self.chk_critical_only.setChecked(False)
                self.chk_risk_only.setChecked(False)
                apply_filters()
            reset_btn.clicked.connect(reset_filters)
            # Initialize filter storage in gantt view if available
            if hasattr(self, 'gantt_chart_view') and hasattr(self.gantt_chart_view, '_init_filters'):
                self.gantt_chart_view._init_filters()
            # Load persisted filter settings
            try:
                self.load_filter_settings()
            except Exception:
                pass

            # Sidebar for view selection (create and add to layout first)
            self.sidebar = QListWidget()
            self.sidebar.addItems([
                "Project Tree",
                "Gantt Chart",
                "Calendar",
                "Project Timeline",
                "Database",
                "Progress Dashboard"
            ])

            # Stacked widget for views
            self.project_tree_view = ProjectTreeView(self.model, on_part_selected=self.on_tree_part_selected)
            self.gantt_chart_view = GanttChartView()
            self.calendar_view = CalendarView(self.model)
            self.timeline_view = TimelineView(self.model)
            self.database_view = DatabaseView(self.model, on_data_changed=self.on_data_changed)
            self.progress_dashboard = ProgressDashboard(self.model)

            self.views = QStackedWidget()
            self.views.addWidget(self.project_tree_view)
            self.views.addWidget(self.gantt_chart_view)
            self.views.addWidget(self.calendar_view)
            self.views.addWidget(self.timeline_view)
            self.views.addWidget(self.database_view)
            self.views.addWidget(self.progress_dashboard)

            # Layout
            main_layout = QVBoxLayout()
            main_layout.addLayout(header_layout)
            content_layout = QHBoxLayout()
            content_layout.addWidget(self.sidebar)
            content_layout.addWidget(self.views, 1)
            main_layout.addLayout(content_layout)

            # Footer
            footer_label = QLabel("Copyright 2025 © LSI Graphics, LLC. All Rights Reserved.")
            footer_label.setAlignment(Qt.AlignCenter)
            footer_label.setStyleSheet("color: #888; font-size: 11px; margin-top: 8px;")
            main_layout.addWidget(footer_label)

            container = QWidget()
            container.setLayout(main_layout)
            self.setCentralWidget(container)

            # Now that all views are constructed, connect sidebar signals and set current row
            self.sidebar.currentRowChanged.connect(self.display_view)
            self.sidebar.setCurrentRow(4)  # Start on Database view for editing (Dashboard is index 5)
            # If Gantt tab is selected at startup, render it
            if self.sidebar.currentRow() == 1:
                if hasattr(self.gantt_chart_view, 'scene') and self.gantt_chart_view.scene is not None:
                    self.gantt_chart_view.render_gantt(self.model)
        except Exception as e:
            import traceback
            print("EXCEPTION in MainWindow.__init__:", e)
            traceback.print_exc()
    def on_tree_part_selected(self, part_name):
        # No automatic view switching. Optionally, highlight in Gantt if already there.
        if self.sidebar.currentRow() == 1 and hasattr(self.gantt_chart_view, 'highlight_bar'):
            self.gantt_chart_view.highlight_bar(part_name)
    # ---------------- Filter Settings Persistence ----------------
    def load_filter_settings(self):
        from PyQt5.QtCore import QSettings, QTimer
        s = QSettings("LSI", "ProjectPlanner")
        # Status
        for st, cb in self.chk_status.items():
            cb.setChecked(s.value(f"filters/status/{st}", False, type=bool))
        self.chk_internal.setChecked(s.value("filters/internal", False, type=bool))
        self.chk_external.setChecked(s.value("filters/external", False, type=bool))
        self.resp_input.setText(s.value("filters/responsible_substr", "", type=str))
        self.chk_critical_only.setChecked(s.value("filters/critical_only", False, type=bool))
        self.chk_risk_only.setChecked(s.value("filters/risk_only", False, type=bool))
        # Apply after UI settles
        QTimer.singleShot(100, lambda: getattr(self, '_apply_filters', lambda: None)())
    def save_filter_settings(self):
        from PyQt5.QtCore import QSettings
        s = QSettings("LSI", "ProjectPlanner")
        for st, cb in self.chk_status.items():
            s.setValue(f"filters/status/{st}", cb.isChecked())
        s.setValue("filters/internal", self.chk_internal.isChecked())
        s.setValue("filters/external", self.chk_external.isChecked())
        s.setValue("filters/responsible_substr", self.resp_input.text())
        s.setValue("filters/critical_only", self.chk_critical_only.isChecked())
        s.setValue("filters/risk_only", self.chk_risk_only.isChecked())
    def closeEvent(self, event):
        try:
            self.save_filter_settings()
        except Exception:
            pass
        super().closeEvent(event)

# ------------------------------------------------------------
# Application Entry Point (was missing; caused immediate exit)
# ------------------------------------------------------------
if __name__ == "__main__":
    try:
        import sys
        from PyQt5.QtWidgets import QApplication
        app = QApplication(sys.argv)
        model = ProjectDataModel()
        window = MainWindow(model)
        window.show()
        exit_code = app.exec_()
        sys.exit(exit_code)
    except Exception as e:
        import traceback, sys
        print("FATAL: Unhandled exception during startup:", e)
        traceback.print_exc()
        sys.exit(1)