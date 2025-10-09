import os, sys, json, datetime

def resolve_resource_path(path: str) -> str:
    if not path: return path
    if os.path.isabs(path): return path
    meipass = getattr(sys, '_MEIPASS', None)
    candidates = []
    if meipass: candidates.append(os.path.join(meipass, path))
    candidates.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), path))
    for c in candidates:
        if os.path.exists(c):
            return c
    return candidates[0]

HOLIDAYS_FILE = "holidays.json"

def _holidays_path():
    try:
        from PyQt6.QtCore import QSettings
        db_path = QSettings('LSI','ProjectApp').value('DB/path','')
        if db_path:
            return os.path.join(os.path.dirname(os.path.abspath(db_path)), HOLIDAYS_FILE)
    except Exception:
        pass
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), HOLIDAYS_FILE)

def load_holiday_dates():
    out=set()
    p=_holidays_path()
    try:
        if os.path.exists(p):
            data=json.load(open(p,'r',encoding='utf-8'))
            for s in data:
                try: out.add(datetime.datetime.strptime(s,"%m-%d-%Y").date())
                except: pass
    except: pass
    return out

def save_holiday_dates(dates_iter):
    try:
        p=_holidays_path()
        json.dump(sorted(list(dates_iter)), open(p,'w',encoding='utf-8'), ensure_ascii=False, indent=2)
    except:
        pass

# ---------------------------------------------------------------------------
# Printing / Export helpers (PyQt6)
def build_printer(page_size: str, orientation: str, margins_mm: tuple[float, float, float, float], output_path: str):
    """Create and configure a QPrinter with unit-aware margins.

    Args:
        page_size: One of 'A4', 'Letter', 'Legal', 'Tabloid'.
        orientation: 'Portrait' or 'Landscape'.
        margins_mm: (left, top, right, bottom) in millimeters.
        output_path: File path for PDF output.

    Returns:
        Configured QPrinter instance ready for painting.
    """
    try:
        from PyQt6.QtPrintSupport import QPrinter
        from PyQt6.QtGui import QPageLayout, QPageSize
        from PyQt6.QtCore import QMarginsF
    except Exception as e:  # pragma: no cover
        raise RuntimeError(f"Printing not available: {e}")

    # Instantiate high-resolution printer
    try:
        printer = QPrinter(QPrinter.PrinterMode.HighResolution)
    except Exception:
        printer = QPrinter()  # Fallback

    # Map page sizes
    page_map = {
        'A4': QPageSize.PageSizeId.A4,
        'Letter': QPageSize.PageSizeId.Letter,
        'Legal': QPageSize.PageSizeId.Legal,
        'Tabloid': QPageSize.PageSizeId.Tabloid,
    }
    qps = QPageSize(page_map.get(page_size, QPageSize.PageSizeId.A4))

    orient = QPageLayout.Orientation.Landscape if orientation == 'Landscape' else QPageLayout.Orientation.Portrait
    ml, mt, mr, mb = margins_mm
    margins = QMarginsF(float(ml), float(mt), float(mr), float(mb))

    # Apply page layout with explicit millimeter units
    layout = QPageLayout(qps, orient, margins, QPageLayout.Unit.Millimeter)
    printer.setPageLayout(layout)

    # Output PDF
    try:
        printer.setOutputFormat(QPrinter.OutputFormat.PdfFormat)
    except Exception:
        # Older API name fallback
        printer.setOutputFormat(QPrinter.PdfFormat)  # type: ignore[attr-defined]
    printer.setOutputFileName(output_path)

    return printer