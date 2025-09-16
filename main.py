print("DEBUG: VERY TOP OF FILE")

from PyQt5.QtWidgets import QDialog, QFormLayout, QLineEdit, QTextEdit, QComboBox, QDateEdit, QPushButton, QFileDialog, QLabel, QHBoxLayout
from PyQt5.QtWidgets import QMessageBox
from PyQt5.QtCore import QDate


# Minimal ImageCellWidget for image upload/preview in DatabaseView
from PyQt5.QtWidgets import QWidget, QHBoxLayout, QVBoxLayout, QLabel, QPushButton, QFileDialog, QMainWindow, QApplication, QListWidget, QTreeWidget, QGraphicsScene, QStackedWidget, QDialog
from PyQt5.QtWidgets import QTreeWidgetItem
import os
from PyQt5.QtGui import QPixmap
import shutil

print("ZZZ-TEST-123: This is the top of main.py you are editing!")

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
    COLUMNS = [
        "Project Part", "Parent", "Children", "Start Date", "Duration (days)", "Internal/External", "Dependencies", "Type", "Calculated End Date", "Resources", "Notes", "Responsible", "Images", "Pace Link"
    ]
    DB_FILE = "project_data.db"

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
                print(f"Loaded from DB: {row_dict}")
                self.rows.append(row_dict)
        self.update_calculated_end_dates()

    def save_to_db(self):
        import sqlite3
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

class ProjectTreeView(QWidget):
    def __init__(self, model, on_part_selected=None):
        print("ProjectTreeView: __init__ called")
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
                line = QLineEdit(val)
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
                    elif isinstance(widget, QDateEdit):
                        d = widget.date()
                        min_blank = QDate(1753, 1, 1)
                        # Defensive: treat invalid or minimum date as blank
                        if not d.isValid() or d == min_blank:
                            row[col] = ""
                        else:
                            # Defensive: always output in MM-dd-yyyy
                            row[col] = d.toString("MM-dd-yyyy")
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
        # Open file dialog for PNG
        path, _ = QFileDialog.getSaveFileName(self, "Export Gantt Chart", "gantt_chart.png", "PNG Files (*.png)")
        if not path:
            return
        # Render scene to QPixmap
        rect = self.scene.sceneRect().toRect()
        if rect.width() == 0 or rect.height() == 0:
            print("Gantt chart scene is empty, nothing to export.")
            return
        gantt_pixmap = QPixmap(rect.size())
        gantt_pixmap.fill()
        from PyQt5.QtGui import QPainter
        painter = QPainter(gantt_pixmap)
        self.scene.render(painter)
        painter.end()

        # Load header image (adjust path as needed)
        header_path = os.path.join(os.path.dirname(__file__), "header.png")
        if not os.path.exists(header_path):
            print(f"Header image not found at {header_path}, exporting without header.")
            combined_pixmap = gantt_pixmap
        else:
            header_pixmap = QPixmap(header_path)
            # Create a new pixmap tall enough for header + gantt
            combined_width = max(header_pixmap.width(), gantt_pixmap.width())
            combined_height = header_pixmap.height() + gantt_pixmap.height()
            combined_pixmap = QPixmap(combined_width, combined_height)
            combined_pixmap.fill()
            painter = QPainter(combined_pixmap)
            # Center header at top
            header_x = (combined_width - header_pixmap.width()) // 2
            painter.drawPixmap(header_x, 0, header_pixmap)
            # Draw gantt below header, left-aligned
            painter.drawPixmap(0, header_pixmap.height(), gantt_pixmap)
            painter.end()

        combined_pixmap.save(path, "PNG")
        print(f"Gantt chart exported to {path}")
    def __init__(self):
        print("GanttChartView: __init__ called")
        super().__init__()
        layout = QVBoxLayout()
        layout.addWidget(QLabel("Gantt Chart (Read-Only)"))
        self.view = ZoomableGraphicsView()
        self.scene = QGraphicsScene()
        self.view.setScene(self.scene)
        layout.addWidget(self.view)

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


    def render_gantt(self, model):
        print("DEBUG: Entered render_gantt")
        self.model = model  # Store model for use in other methods
        self.scene.clear()
        self.preview_label.clear()
        # Get all rows with valid start date and duration
        print(f"DEBUG: model.rows = {model.rows}")
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
                print(f"ERROR: Cycle detected at {name}, breaking recursion.")
                return None, None
            visited.add(name)
            if name not in children:
                try:
                    start_str = row.get("Start Date", "")
                    duration_val = row.get("Duration (days)", 0)
                    print(f"DEBUG: update_span leaf {name}, start_str={start_str}, duration_val={duration_val}")
                    if not start_str or not duration_val:
                        return None, None
                    start = datetime.datetime.strptime(start_str, "%m-%d-%Y")
                    duration = int(duration_val)
                    end = start + datetime.timedelta(days=duration)
                    return start, end
                except Exception as e:
                    print(f"ERROR in update_span leaf {name}: {e}")
                    return None, None
            else:
                print(f"DEBUG: update_span parent {name}, children={[c.get('Project Part', '') for c in children[name]]}")
                child_spans = [update_span(child, visited.copy()) for child in children[name]]
                child_starts = [s for s, e in child_spans if s]
                child_ends = [e for s, e in child_spans if e]
                if child_starts and child_ends:
                    min_start = min(child_starts)
                    max_end = max(child_ends)
                    row["_auto_start"] = min_start
                    row["_auto_end"] = max_end
                    # Update parent's Start Date and Calculated End Date fields
                    row["Start Date"] = min_start.strftime("%m-%d-%Y")
                    row["Calculated End Date"] = max_end.strftime("%m-%d-%Y")
                    return min_start, max_end
                return None, None
            for row in rows:
                update_span(row)
        # Include all rows that have either real or auto-calculated dates
        rows = list(model.rows)  # Use all rows
        compute_parent_spans(rows)
        rows = topo_sort(rows)
        print(f"DEBUG: rows for Gantt = {rows}")
        if not rows:
            print("DEBUG: No rows to render in Gantt chart.")
            return
        # Parse dates and durations
        import datetime
        from PyQt5.QtGui import QPixmap
        bar_height = 24
        bar_gap = 10
        min_date = None
        max_date = None
        bars = []
        name_to_bar = {}
        bar_items = []
        for i, row in enumerate(rows):
            # Use auto-calculated span for parents if present
            if "_auto_start" in row and "_auto_end" in row:
                start = row["_auto_start"]
                end = row["_auto_end"]
                duration = (end - start).days
            else:
                try:
                    start_str = row.get("Start Date", "")
                    duration_val = row.get("Duration (days)", 0)
                    if not start_str or not duration_val:
                        continue
                    start = datetime.datetime.strptime(start_str, "%m-%d-%Y")
                    duration = int(duration_val)
                    end = start + datetime.timedelta(days=duration)
                except Exception as e:
                    print(f"DEBUG: Failed to parse row {row}: {e}")
                    continue
            if not start or not end:
                continue
            if min_date is None or start < min_date:
                min_date = start
            if max_date is None or end > max_date:
                max_date = end
            bars.append((row["Project Part"], start, duration, i, row))
            print(f"DEBUG: Added bar: {row['Project Part']}, start={start}, duration={duration}, end={end}")
        if not bars:
            print("DEBUG: No bars to draw in Gantt chart.")
            return

        # Set chart_min_date to the actual earliest start date (no cushion)
        chart_min_date = min_date
        # Draw bars and record their positions
        from PyQt5.QtGui import QColor
        gantt_color = QColor("#FF8200")
        from PyQt5.QtWidgets import QGraphicsRectItem
        class ClickableBar(QGraphicsRectItem):
            def __init__(self, x, y, width, height, row, preview_label, *args, **kwargs):
                super().__init__(x, y, width, height, *args, **kwargs)
                self.row = row
                self.preview_label = preview_label
                self.setAcceptHoverEvents(True)
            def mousePressEvent(self, event):
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
                        self.preview_label.setPixmap(pixmap.scaledToHeight(90, Qt.SmoothTransformation))
                        self.preview_label.setText("")
                    else:
                        self.preview_label.setText("[Image not found]")
                        self.preview_label.setPixmap(QPixmap())
                else:
                    self.preview_label.setText("")
                # Show edit dialog for the clicked bar
                try:
                    parent_widget = self.preview_label.parentWidget()
                    if parent_widget and hasattr(parent_widget, 'show_edit_dialog'):
                        parent_widget.show_edit_dialog(self.row)
                except Exception as e:
                    print(f"ERROR in ClickableBar.mousePressEvent: {e}")
                # Do not call super().mousePressEvent(event) after dialog, prevents RuntimeError

            def hoverEnterEvent(self, event):
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
                        self.preview_label.setPixmap(pixmap.scaledToHeight(90, Qt.SmoothTransformation))
                        self.preview_label.setText("")
                    else:
                        self.preview_label.setText("[Image not found]")
                        self.preview_label.setPixmap(QPixmap())
                else:
                    self.preview_label.setText("")

            def hoverLeaveEvent(self, event):
                self.preview_label.clear()

        # Place labels at a fixed position well to the left of the earliest bar (e.g., x=10)
        from PyQt5.QtGui import QColor
        label_x = 10
        for name, start, duration, idx, row in bars:
            x = (start - chart_min_date).days * 10 + 100  # 10px per day, offset for bars
            y = idx * (bar_height + bar_gap) + 40
            width = max(duration * 10, 10)
            print(f"DEBUG: Drawing bar {name} at x={x}, y={y}, width={width}")
            rect = ClickableBar(x, y, width, bar_height, row, self.preview_label)
            rect.setBrush(gantt_color)
            self.scene.addItem(rect)
            # Place label at fixed x=10, vertically centered on the bar
            label = self.scene.addText(name)
            label.setDefaultTextColor(QColor("white"))
            label.setPos(label_x, y + (bar_height - label.boundingRect().height()) / 2)
            name_to_bar[name] = (x, y, width, bar_height)
            # Store bar rect and row for selection/edit events
            bar_items.append((rect, row))

        # Draw parent-child connector lines (tree lines)
        for name, start, duration, idx, row in bars:
            parent_name = row.get("Parent", "")
            if parent_name and parent_name in name_to_bar:
                px, py, pwidth, pheight = name_to_bar[parent_name]
                cx, cy, cwidth, cheight = name_to_bar[name]
                parent_mid_x = px + pwidth // 2
                child_mid_x = cx + cwidth // 2
                parent_bottom = py + bar_height
                child_top = cy
                # Vertical line from parent to horizontal level
                self.scene.addLine(parent_mid_x, parent_bottom, parent_mid_x, (parent_bottom + child_top) // 2)
                # Horizontal line to child
                self.scene.addLine(parent_mid_x, (parent_bottom + child_top) // 2, child_mid_x, (parent_bottom + child_top) // 2)
                # Vertical line down to child
                self.scene.addLine(child_mid_x, (parent_bottom + child_top) // 2, child_mid_x, child_top)

            # Draw dependency arrows in #FF8200 orange
            from PyQt5.QtCore import QPointF
            dep_names = row.get("Dependencies", "")
            if dep_names:
                from PyQt5.QtGui import QPen, QPolygonF
                dep_list = [d.strip() for d in dep_names.split(",") if d.strip()]
                for dep in dep_list:
                    if dep in name_to_bar:
                        dx, dy, dwidth, dheight = name_to_bar[dep]
                        # Arrow from end of dependency bar to start of this bar
                        start_x = dx + dwidth
                        start_y = dy + dheight // 2
                        end_x = cx
                        end_y = cy + cheight // 2
                        # Check for dependency conflict: dependency end >= dependent start
                        dep_row = None
                        for bname, bstart, bduration, bidx, brow in bars:
                            if bname == dep:
                                dep_row = brow
                                break
                        dep_end = None
                        if dep_row:
                            try:
                                dep_start_str = dep_row.get("Start Date", "")
                                dep_duration_val = dep_row.get("Duration (days)", 0)
                                if dep_start_str and dep_duration_val:
                                    import datetime
                                    dep_start = datetime.datetime.strptime(dep_start_str, "%m-%d-%Y")
                                    dep_end = dep_start + datetime.timedelta(days=int(dep_duration_val))
                            except Exception:
                                dep_end = None
                        # Get this bar's start
                        this_start = None
                        try:
                            this_start_str = row.get("Start Date", "")
                            if this_start_str:
                                import datetime
                                this_start = datetime.datetime.strptime(this_start_str, "%m-%d-%Y")
                        except Exception:
                            this_start = None
                        # If dependency ends after or at this bar's start, it's a conflict
                        if dep_end and this_start and dep_end >= this_start:
                            pen = QPen(QColor("red"), 2)
                            arrow_color = QColor("red")
                        else:
                            pen = QPen(QColor("#FF8200"), 2)
                            arrow_color = QColor("#FF8200")
                        self.scene.addLine(start_x, start_y, end_x, end_y, pen)
                        # Draw arrowhead
                        arrow_size = 8
                        import math
                        angle = math.atan2(end_y - start_y, end_x - start_x)
                        arrow_p1 = end_x - arrow_size * math.cos(angle - math.pi / 6)
                        arrow_p2 = end_y - arrow_size * math.sin(angle - math.pi / 6)
                        arrow_p3 = end_x - arrow_size * math.cos(angle + math.pi / 6)
                        arrow_p4 = end_y - arrow_size * math.sin(angle + math.pi / 6)
                        arrow_head = QPolygonF([
                            QPointF(end_x, end_y),
                            QPointF(arrow_p1, arrow_p2),
                            QPointF(arrow_p3, arrow_p4)
                        ])
                        self.scene.addPolygon(arrow_head, pen, arrow_color)
            # Removed image indicator ellipse for image association

        # Add mouse click events to bars
        from PyQt5.QtWidgets import QGraphicsItem
        self._bar_rect_to_row = {}
        for rect, row in bar_items:
            rect.setFlag(QGraphicsItem.ItemIsSelectable, True)
            self._bar_rect_to_row[rect] = row

        # Connect selection change to open edit dialog
        def on_selection_changed():
            selected = [item for item in self.scene.selectedItems() if item in self._bar_rect_to_row]
            if selected:
                bar = selected[0]
                # Check if the item is still valid and not deleted
                try:
                    if bar.scene() is not None:
                        row = self._bar_rect_to_row[bar]
                        self.show_edit_dialog(row)
                        bar.setSelected(False)
                except RuntimeError:
                    # The item was deleted, ignore
                    pass
        try:
            self.scene.selectionChanged.disconnect()
        except TypeError:
            pass
        self.scene.selectionChanged.connect(on_selection_changed)

        # Draw x-axis with date marks
        if min_date and max_date:
            axis_y = 30
            axis_x0 = 100
            axis_x1 = (max_date - chart_min_date).days * 10 + 100 + 40
            self.scene.addLine(axis_x0, axis_y, axis_x1, axis_y)
            # Draw tick marks and date labels every 7 days
            tick_interval = 7
            total_days = (max_date - chart_min_date).days
            for d in range(0, total_days + 1, tick_interval):
                tick_x = axis_x0 + d * 10
                self.scene.addLine(tick_x, axis_y - 5, tick_x, axis_y + 5)
                tick_date = chart_min_date + datetime.timedelta(days=d)
                tick_label = self.scene.addText(tick_date.strftime("%m-%d-%Y"))
                tick_label.setDefaultTextColor(QColor("white"))
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
            def save():
                import sys
                import traceback
                print("DEBUG: Entered save() in GanttChartView")
                sys.stdout.flush()
                try:
                    for col in self.model.COLUMNS:
                        widget = edits[col]
                        print(f"DEBUG: Processing column {col} with widget {type(widget)}")
                        sys.stdout.flush()
                        if isinstance(widget, QLineEdit):
                            row[col] = widget.text()
                        elif isinstance(widget, QComboBox):
                            row[col] = widget.currentText()
                        elif isinstance(widget, QDateEdit):
                            d = widget.date()
                            min_blank = QDate(1753, 1, 1)
                            print(f"DEBUG: QDateEdit value for {col}: {d.toString('MM-dd-yyyy')}, isValid={d.isValid()}, min_blank={d == min_blank}")
                            sys.stdout.flush()
                            if not d.isValid() or d == min_blank:
                                row[col] = ""
                            else:
                                row[col] = d.toString("MM-dd-yyyy")
                        elif isinstance(widget, QTextEdit):
                            row[col] = widget.toPlainText()
                    print("DEBUG: About to call self.model.save_to_db()")
                    sys.stdout.flush()
                    self.model.save_to_db()
                    print("DEBUG: About to call self.render_gantt()")
                    sys.stdout.flush()
                    self.render_gantt(self.model)
                    print("DEBUG: About to accept dialog")
                    sys.stdout.flush()
                    dialog.accept()
                except Exception as e:
                    print(f"ERROR in GanttChartView.save(): {e}")
                    traceback.print_exc()
                    sys.stdout.flush()
                    QMessageBox.critical(dialog, "Save Error", f"An error occurred while saving: {e}")

    # ClickableBar.mousePressEvent should be inside its class, not dedented here

        # Removed stray indented block after exception handler
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
    def __init__(self, model=None):
        print("CalendarView: __init__ called")
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
        print("TimelineView: __init__ called")
        super().__init__()
        self.model = model
        layout = QVBoxLayout()
        layout.addWidget(QLabel("Project Timeline (Read-Only)"))
        from PyQt5.QtWidgets import QGraphicsView, QGraphicsScene
        self.scene = QGraphicsScene()
        self.view = QGraphicsView(self.scene)
        layout.addWidget(self.view)
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
                    child_spans = [update_span(child, visited.copy()) for child in children[name]]
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
        y = 40
        bar_positions = {}  # idx -> (x, y, width)
        for name, start, duration, row, idx in bars:
            x = 100 + (start - min_date).days * 8
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
            self.scene.addText(name).setPos(10, y)
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
        axis_x0 = 100
        axis_x1 = 100 + total_days * 8 + 40
        self.scene.addLine(axis_x0, axis_y, axis_x1, axis_y)
        for d in range(0, total_days + 1, 7):
            tick_x = axis_x0 + d * 8
            self.scene.addLine(tick_x, axis_y - 5, tick_x, axis_y + 5)
            tick_date = min_date + datetime.timedelta(days=d)
            self.scene.addText(tick_date.strftime("%m-%d-%Y")).setPos(tick_x - 30, axis_y - 25)
        self.view.setSceneRect(0, 0, axis_x1 + 40, max(300, y + 40))


# New DatabaseView class
from PyQt5.QtWidgets import QTableWidget, QTableWidgetItem

from PyQt5.QtWidgets import QDateEdit
from PyQt5.QtCore import QDate

class DatabaseView(QWidget):
    DATE_FIELDS = {"Start Date", "Calculated End Date"}
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
        export_btn = QPushButton("Export Database")
        export_btn.clicked.connect(self.export_database)
        btn_layout.addWidget(export_btn)
        layout.addLayout(btn_layout)

        self.setLayout(layout)
        self.refresh_table()
        self.table.cellChanged.connect(self.cell_edited)
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
            # Add Export button
            export_btn = QPushButton("Export Gantt Chart")
            export_btn.clicked.connect(self.export_gantt_chart)
            layout.addWidget(export_btn)
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
    
        def export_gantt_chart(self):
            # Open file dialog for PNG
            path, _ = QFileDialog.getSaveFileName(self, "Export Gantt Chart", "gantt_chart.png", "PNG Files (*.png)")
            if not path:
                return
            # Render scene to QPixmap
            rect = self.scene.sceneRect().toRect()
            if rect.width() == 0 or rect.height() == 0:
                print("Gantt chart scene is empty, nothing to export.")
                return
            gantt_pixmap = QPixmap(rect.size())
            gantt_pixmap.fill()
            painter = QPainter(gantt_pixmap)
            self.scene.render(painter)
            painter.end()

            # Load header image (adjust path as needed)
            header_path = os.path.join(os.path.dirname(__file__), "header.png")
            if not os.path.exists(header_path):
                print(f"Header image not found at {header_path}, exporting without header.")
                combined_pixmap = gantt_pixmap
            else:
                header_pixmap = QPixmap(header_path)
                # Create a new pixmap tall enough for header + gantt
                combined_width = max(header_pixmap.width(), gantt_pixmap.width())
                combined_height = header_pixmap.height() + gantt_pixmap.height()
                combined_pixmap = QPixmap(combined_width, combined_height)
                combined_pixmap.fill()
                painter = QPainter(combined_pixmap)
                # Draw header at top
                painter.drawPixmap(0, 0, header_pixmap)
                # Draw gantt below header
                painter.drawPixmap(0, header_pixmap.height(), gantt_pixmap)
                painter.end()

            combined_pixmap.save(path, "PNG")
            print(f"Gantt chart exported to {path}")

    def dropdown_changed(self, row, col, value):
        colname = ProjectDataModel.COLUMNS[col]
        print(f"DEBUG: dropdown_changed row={row}, col={col}, value={value}")
        try:
            self.model.rows[row][colname] = value
            self.table.blockSignals(True)
            self.table.setItem(row, col, QTableWidgetItem(value))
            self.table.blockSignals(False)
            if self.on_data_changed:
                self.on_data_changed()
        except Exception as e:
            print(f"ERROR in dropdown_changed: {e}")
    def date_changed(self, row, col, qdate):
        colname = ProjectDataModel.COLUMNS[col]
        min_blank = QDate(1753, 1, 1)
        print(f"DEBUG: date_changed row={row}, col={col}, qdate={qdate}")
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
            if self.on_data_changed:
                self.on_data_changed()
        except Exception as e:
            print(f"ERROR in date_changed: {e}")


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
    def display_view(self, index):
        print(f"DEBUG: display_view called with index={index}")
        self.views.setCurrentIndex(index)
        if index == 0:
            self.project_tree_view.refresh()
        elif index == 1:
            print("DEBUG: About to call render_gantt from display_view")
            self.gantt_chart_view.render_gantt(self.model)
        elif index == 4:
            self.database_view.refresh_table()
    def __init__(self, model):
        try:
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

            # Header with centered header.png image
            header_layout = QHBoxLayout()
            header_layout.addStretch(1)
            header_label = QLabel()
            header_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "header.png")
            if os.path.exists(header_path):
                header_pixmap = QPixmap(header_path)
                # Double the previous height: 64 -> 128
                header_label.setPixmap(header_pixmap.scaledToHeight(128, Qt.SmoothTransformation))
            else:
                header_label.setText("[header.png not found]")
            header_layout.addWidget(header_label, alignment=Qt.AlignCenter)
            header_layout.addStretch(1)
            print("DEBUG: Header layout created")

            # Sidebar for view selection (create and add to layout first)
            self.sidebar = QListWidget()
            self.sidebar.addItems([
                "Project Tree",
                "Gantt Chart",
                "Calendar",
                "Project Timeline",
                "Database"
            ])
            print("DEBUG: Sidebar created and items added")

            # Stacked widget for views
            self.project_tree_view = ProjectTreeView(self.model, on_part_selected=self.on_tree_part_selected)
            print("DEBUG: ProjectTreeView created")
            self.gantt_chart_view = GanttChartView()
            print("DEBUG: GanttChartView created")
            self.calendar_view = CalendarView(self.model)
            print("DEBUG: CalendarView created")
            self.timeline_view = TimelineView(self.model)
            print("DEBUG: TimelineView created")
            self.database_view = DatabaseView(self.model, on_data_changed=self.on_data_changed)
            print("DEBUG: DatabaseView created")

            self.views = QStackedWidget()
            self.views.addWidget(self.project_tree_view)
            self.views.addWidget(self.gantt_chart_view)
            self.views.addWidget(self.calendar_view)
            self.views.addWidget(self.timeline_view)
            self.views.addWidget(self.database_view)
            print("DEBUG: QStackedWidget created and all views added")

            # Layout
            main_layout = QVBoxLayout()
            main_layout.addLayout(header_layout)
            content_layout = QHBoxLayout()
            content_layout.addWidget(self.sidebar)
            content_layout.addWidget(self.views, 1)
            main_layout.addLayout(content_layout)
            print("DEBUG: Main layout and content layout created")

            # Footer
            footer_label = QLabel("Copyright 2025 © LSI Graphics, LLC. All Rights Reserved.")
            footer_label.setAlignment(Qt.AlignCenter)
            footer_label.setStyleSheet("color: #888; font-size: 11px; margin-top: 8px;")
            main_layout.addWidget(footer_label)

            container = QWidget()
            container.setLayout(main_layout)
            self.setCentralWidget(container)
            print("DEBUG: Central widget set")

            # Now that all views are constructed, connect sidebar signals and set current row
            self.sidebar.currentRowChanged.connect(self.display_view)
            self.sidebar.setCurrentRow(4)  # Start on Database view for editing
            print("DEBUG: Sidebar signal connected and current row set")
            # If Gantt tab is selected at startup, render it
            if self.sidebar.currentRow() == 1:
                if hasattr(self.gantt_chart_view, 'scene') and self.gantt_chart_view.scene is not None:
                    self.gantt_chart_view.render_gantt(self.model)
            print("DEBUG: MainWindow __init__ complete")
        except Exception as e:
            import traceback
            print("EXCEPTION in MainWindow.__init__:", e)
            traceback.print_exc()
    def on_tree_part_selected(self, part_name):
        # No automatic view switching. Optionally, highlight in Gantt if already there.
        if self.sidebar.currentRow() == 1 and hasattr(self.gantt_chart_view, 'highlight_bar'):
            self.gantt_chart_view.highlight_bar(part_name)


if __name__ == "__main__":
    print('DEBUG: Entered __main__ block')
    print('ZZZ-TEST-123: About to instantiate MainWindow')
    import sys
    from PyQt5.QtWidgets import QApplication
    app = QApplication(sys.argv)
    model = ProjectDataModel()
    window = MainWindow(model)
    print('ZZZ-TEST-123: MainWindow instantiated')
    window.show()
    print('DEBUG: window.show() called')
    sys.exit(app.exec_())