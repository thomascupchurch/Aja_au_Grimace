"""Gantt chart view module.
Contains GanttChartView responsible for rendering project parts across a timeline
and exporting to PNG/PDF using export settings dialog.
"""

from project.qt_bindings import (
    QWidget, QVBoxLayout, QLabel, QPainter, QFileDialog, QMessageBox, Qt, QPixmap,
    QPen, QBrush, QColor
)
try:
    # QPrinter may not be present in very minimal environments
    from PyQt6.QtPrintSupport import QPrinter
except Exception:  # pragma: no cover
    QPrinter = None  # type: ignore
from project.helpers import resolve_resource_path, load_holiday_dates
try:
    from project.dialogs.export_settings import ExportSettingsDialog
except Exception:  # Fallback if dialog not yet extracted
    ExportSettingsDialog = None  # type: ignore

from dataclasses import dataclass
import math, datetime


@dataclass
class _BarItem:
    part_id: int
    name: str
    start: datetime.date
    end: datetime.date
    progress: float


class GanttChartView(QWidget):
    """Simplified Gantt chart view.

    Rendering approach:
      - Convert each part (with start/end) into horizontal bar rows.
      - Horizontal axis: days between min(start) and max(end)
      - Vertical axis: one row per part (basic ordering for now)
    """

    def __init__(self, model=None, parent=None):
        super().__init__(parent)
        self.model = model
        lay = QVBoxLayout(self)
        self._label = QLabel("Gantt (placeholder – logic WIP)")
        lay.addWidget(self._label)
        self.setMinimumHeight(240)
        self._bars: list[_BarItem] = []
        self._date_min: datetime.date | None = None
        self._date_max: datetime.date | None = None
        self.refresh()

    # ------------------------------------------------------------------
    # Data binding / refresh
    def refresh(self):
        self._bars.clear()
        self._date_min = None
        self._date_max = None
        if not self.model:
            return
        try:
            for row in self.model.parts:  # Expect model.parts list of dicts
                start = row.get('start_date') or row.get('start')
                end = row.get('end_date') or row.get('end')
                if not (start and end):
                    continue
                if isinstance(start, str):
                    start = datetime.date.fromisoformat(start)
                if isinstance(end, str):
                    end = datetime.date.fromisoformat(end)
                bi = _BarItem(part_id=row.get('id', 0),
                              name=row.get('name', 'Part'),
                              start=start, end=end,
                              progress=float(row.get('progress', 0.0)))
                self._bars.append(bi)
                if not self._date_min or start < self._date_min:
                    self._date_min = start
                if not self._date_max or end > self._date_max:
                    self._date_max = end
        except Exception as e:
            self._label.setText(f"Gantt load error: {e}")

    # ------------------------------------------------------------------
    # Simple export logic (placeholder for full scene-based rendering)
    def export(self, parent=None):
        if not self._bars:
            QMessageBox.information(self, "Export", "Nothing to export")
            return
        fmt = 'PNG'
        page_size = 'A4'
        orientation = 'Portrait'
        margins = (8.0,8.0,8.0,8.0)
        include_header = True
        if ExportSettingsDialog:
            dlg = ExportSettingsDialog(self)
            if dlg.exec() != dlg.Accepted:
                return
            # pull values back from QSettings instead of relying on dialog properties
            try:
                from project.qt_bindings import QSettings
                s = QSettings('LSI','ProjectPlanner')
                fmt = s.value('Export/format','PNG')
                page_size = s.value('Export/page_size','A4')
                orientation = s.value('Export/orientation','Portrait')
                ml = float(s.value('Export/margin_left_mm',8.0)); mt = float(s.value('Export/margin_top_mm',8.0))
                mr = float(s.value('Export/margin_right_mm',8.0)); mb = float(s.value('Export/margin_bottom_mm',8.0))
                include_header = bool(s.value('Export/include_header', True))
                margins = (ml,mt,mr,mb)
            except Exception:
                pass
        if fmt == 'PDF' and QPrinter is None:
            QMessageBox.warning(self, 'Export', 'PDF export unavailable (QtPrintSupport missing). Falling back to PNG.')
            fmt = 'PNG'
        if fmt == 'PDF':
            fname_filter = "PDF Files (*.pdf)"
            default_name = 'gantt.pdf'
        else:
            fname_filter = "PNG Files (*.png)"
            default_name = 'gantt.png'
        path, _ = QFileDialog.getSaveFileName(self, 'Export Gantt', default_name, f"{fname_filter};;All Files (*)")
        if not path:
            return
        try:
            if fmt == 'PDF':
                self._export_pdf(path, page_size, orientation, margins, include_header)
            else:
                pix = self._render_pixmap(include_header=include_header, margins=margins)
                if not path.lower().endswith('.png'):
                    path += '.png'
                pix.save(path, 'PNG')
            QMessageBox.information(self, 'Export', f'Exported to {path}')
        except Exception as e:  # pragma: no cover
            QMessageBox.warning(self, 'Export Failed', str(e))

    def _render_pixmap(self, include_header: bool=True, margins=(8.0,8.0,8.0,8.0)) -> QPixmap:
        if not (self._date_min and self._date_max):
            raise RuntimeError('No date range')
        day_span = (self._date_max - self._date_min).days + 1
        row_h = 24
        left_label_w = 160
        day_px = 18
        header_h = 60 if include_header else 0
        ml, mt, mr, mb = margins
        core_w = left_label_w + day_span * day_px
        core_h = len(self._bars) * row_h + 20
        width = int(ml + core_w + mr)
        height = int(mt + header_h + core_h + mb)
        pix = QPixmap(width, height)
        pix.fill(Qt.white)
        p = QPainter(pix)
        try:
            y_offset = mt
            # Header
            if include_header:
                p.setPen(Qt.black)
                font = p.font(); font.setPointSize(14); font.setBold(True); p.setFont(font)
                p.drawText(int(ml), int(y_offset + 28), 'Project Gantt')
                y_offset += header_h
            # Body font
            font = p.font(); font.setPointSize(8); font.setBold(False); p.setFont(font)
            # Grid + bars
            pen_grid = QPen(QColor('#dddddd'))
            for d in range(day_span + 1):
                x = int(ml + left_label_w + d * day_px)
                p.setPen(pen_grid)
                p.drawLine(x, int(y_offset), x, int(y_offset + core_h))
            for idx, bar in enumerate(self._bars):
                y = int(y_offset + idx * row_h + 6)
                p.setPen(Qt.black)
                p.drawText(int(ml + 4), y + 12, bar.name[:30])
                start_off = (bar.start - self._date_min).days
                end_off = (bar.end - self._date_min).days + 1
                x1 = int(ml + left_label_w + start_off * day_px)
                x2 = int(ml + left_label_w + end_off * day_px)
                pen = QPen(Qt.black); pen.setWidth(1); p.setPen(pen)
                p.setBrush(QBrush(QColor('#6fa8dc')))
                p.drawRect(x1, y, max(6, x2 - x1 - 2), row_h - 8)
                prog_w = int((x2 - x1 - 4) * max(0.0, min(1.0, bar.progress)))
                if prog_w > 0:
                    p.setBrush(QBrush(QColor('#38761d')))
                    p.drawRect(x1 + 1, y + 1, prog_w, row_h - 10)
        finally:
            p.end()
        return pix

    def _export_pdf(self, path: str, page_size: str, orientation: str, margins, include_header: bool):
        if QPrinter is None:
            raise RuntimeError('QPrinter unavailable')
        printer = QPrinter(QPrinter.HighResolution)
        # Map page size
        page_map = {
            'A4': QPrinter.A4,
            'Letter': QPrinter.Letter,
            'Legal': QPrinter.Legal,
            'Tabloid': QPrinter.Tabloid,
        }
        printer.setPageSize(page_map.get(page_size, QPrinter.A4))
        if orientation == 'Landscape':
            printer.setOrientation(QPrinter.Landscape)
        else:
            printer.setOrientation(QPrinter.Portrait)
        printer.setOutputFormat(QPrinter.PdfFormat)
        printer.setOutputFileName(path)
        ml, mt, mr, mb = margins
        # Render to pixmap first (simpler than direct painter coordinate math w/ scaling)
        pix = self._render_pixmap(include_header=include_header, margins=margins)
        # Start painting
        p = QPainter(printer)
        try:
            page_rect = printer.pageRect()
            target = page_rect
            # scale maintaining aspect
            try:
                _smooth = Qt.TransformationMode.SmoothTransformation
            except Exception:
                _smooth = getattr(Qt, 'SmoothTransformation', 1)
            try:
                _keep_ar = Qt.AspectRatioMode.KeepAspectRatio
            except Exception:
                _keep_ar = getattr(Qt, 'KeepAspectRatio', 1)
            scaled = pix.scaled(target.width(), target.height(), _keep_ar, _smooth)
            x = target.x() + (target.width() - scaled.width()) // 2
            y = target.y() + (target.height() - scaled.height()) // 2
            p.drawPixmap(x, y, scaled)
        finally:
            p.end()

    # Hook for external refresh triggers
    def model_changed(self):
        self.refresh()

__all__ = ["GanttChartView"]