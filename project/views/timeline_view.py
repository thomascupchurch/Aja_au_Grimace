"""Timeline view module.
Simplified timeline representation with export capability (PNG/PDF, margins, optional header).
"""
from project.qt_bindings import (
    QWidget, QVBoxLayout, QLabel, QPainter, QFileDialog, QMessageBox, Qt, QPixmap,
    QPen, QBrush, QColor
)
try:
    from PyQt6.QtPrintSupport import QPrinter
except Exception:  # pragma: no cover
    QPrinter = None  # type: ignore
try:
    from project.dialogs.export_settings import ExportSettingsDialog
except Exception:
    ExportSettingsDialog = None  # type: ignore

import datetime
from dataclasses import dataclass

@dataclass
class _TimelineEvent:
    name: str
    date: datetime.date

class TimelineView(QWidget):
    def __init__(self, model=None, parent=None):
        super().__init__(parent)
        self.model = model
        lay = QVBoxLayout(self)
        self._label = QLabel("Timeline (placeholder – logic WIP)")
        lay.addWidget(self._label)
        self._events: list[_TimelineEvent] = []
        self.refresh()

    def refresh(self):
        self._events.clear()
        if not self.model:
            return
        try:
            for row in self.model.parts:
                start = row.get('start_date') or row.get('start')
                if not start:
                    continue
                if isinstance(start, str):
                    start = datetime.date.fromisoformat(start)
                self._events.append(_TimelineEvent(name=row.get('name','Part'), date=start))
            self._events.sort(key=lambda e: e.date)
        except Exception as e:
            self._label.setText(f"Timeline load error: {e}")

    def export(self):
        if not self._events:
            QMessageBox.information(self, 'Export', 'Nothing to export')
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
            QMessageBox.warning(self,'Export','PDF export unavailable (QtPrintSupport missing). Falling back to PNG.')
            fmt = 'PNG'
        if fmt == 'PDF':
            fname_filter = 'PDF Files (*.pdf)'; default_name = 'timeline.pdf'
        else:
            fname_filter = 'PNG Files (*.png)'; default_name = 'timeline.png'
        path, _ = QFileDialog.getSaveFileName(self, 'Export Timeline', default_name, f"{fname_filter};;All Files (*)")
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
            QMessageBox.information(self,'Export', f'Exported to {path}')
        except Exception as e:  # pragma: no cover
            QMessageBox.warning(self,'Export Failed', str(e))

    def _render_pixmap(self, include_header: bool=True, margins=(8.0,8.0,8.0,8.0)) -> QPixmap:
        if not self._events:
            raise RuntimeError('No events')
        min_d = min(e.date for e in self._events)
        max_d = max(e.date for e in self._events)
        span = (max_d - min_d).days + 1
        # Layout metrics
        row_h = 26
        label_w = 180
        day_px = 14
        header_h = 60 if include_header else 0
        ml, mt, mr, mb = margins
        core_w = label_w + span * day_px
        core_h = len(self._events) * row_h + 20
        width = int(ml + core_w + mr)
        height = int(mt + header_h + core_h + mb)
        pix = QPixmap(width, height)
        pix.fill(Qt.white)
        p = QPainter(pix)
        try:
            y_offset = mt
            if include_header:
                p.setPen(Qt.black)
                font = p.font(); font.setPointSize(14); font.setBold(True); p.setFont(font)
                p.drawText(int(ml), int(y_offset + 28), 'Project Timeline')
                y_offset += header_h
            font = p.font(); font.setPointSize(8); font.setBold(False); p.setFont(font)
            pen_grid = QPen(QColor('#cccccc'))
            for d in range(span + 1):
                x = int(ml + label_w + d * day_px)
                p.setPen(pen_grid)
                p.drawLine(x, int(y_offset), x, int(y_offset + core_h))
            for idx, ev in enumerate(self._events):
                y = int(y_offset + idx * row_h + 6)
                p.setPen(Qt.black)
                p.drawText(int(ml + 4), y + 12, ev.name[:32])
                x = int(ml + label_w + (ev.date - min_d).days * day_px)
                p.setBrush(QBrush(QColor('#f1c232')))
                p.setPen(QPen(Qt.black))
                p.drawEllipse(x - 5, y + 4, 10, 10)
        finally:
            p.end()
        return pix

    def _export_pdf(self, path: str, page_size: str, orientation: str, margins, include_header: bool):
        if QPrinter is None:
            raise RuntimeError('QPrinter unavailable')
        printer = QPrinter(QPrinter.HighResolution)
        page_map = {
            'A4': QPrinter.A4,
            'Letter': QPrinter.Letter,
            'Legal': QPrinter.Legal,
            'Tabloid': QPrinter.Tabloid,
        }
        printer.setPageSize(page_map.get(page_size, QPrinter.A4))
        printer.setOrientation(QPrinter.Landscape if orientation == 'Landscape' else QPrinter.Portrait)
        printer.setOutputFormat(QPrinter.PdfFormat)
        printer.setOutputFileName(path)
        pix = self._render_pixmap(include_header=include_header, margins=margins)
        p = QPainter(printer)
        try:
            rect = printer.pageRect()
            scaled = pix.scaled(rect.width(), rect.height(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
            x = rect.x() + (rect.width() - scaled.width()) // 2
            y = rect.y() + (rect.height() - scaled.height()) // 2
            p.drawPixmap(x, y, scaled)
        finally:
            p.end()
