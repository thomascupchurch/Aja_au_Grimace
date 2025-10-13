import os
import json
import re
import base64
import sqlite3
from datetime import datetime, timedelta
from flask import Flask, jsonify, render_template, send_from_directory, Response, abort
from typing import List, Dict, Any

# Optional SQLAlchemy for MySQL support (used if WEB_DB_URL is set)
try:
    from sqlalchemy import create_engine, text  # type: ignore
    _HAS_SA = True
except Exception:
    _HAS_SA = False

app = Flask(__name__)


# Columns order for the Database view (mirrors desktop ProjectDataModel.COLUMNS)
PROJECT_COLUMNS = [
    "Project Part", "Parent", "Children", "Start Date", "Duration (days)", "Internal/External", "Dependencies", "Type", "Calculated End Date", "Resources", "Notes", "Responsible", "Images", "Pace Link", "Attachments",
    # Progress tracking fields
    "% Complete",            # Integer 0-100 (leaf editable, parents rolled up in desktop)
    "Status",                 # Planned | In Progress | Blocked | Done | Deferred
    "Actual Start Date",      # Set when Status transitions to In Progress
    "Actual Finish Date",     # Set when Status transitions to Done
    "Baseline Start Date",    # Captured first time valid start/duration appear
    "Baseline End Date",      # Derived from baseline start + duration
    # Cost tracking fields
    "Production Cost",        # Internal estimated production cost (materials + fabrication labor)
    "Installation Cost",      # Internal estimated install cost (crew labor + equipment)
    "Production Price",       # Decimal number (price to be charged for production)
    "Installation Price",     # Decimal number (price to be charged for installation)
    # Extended cost breakdown (append-only)
    "Material Cost",          # Materials-only direct cost
    "Fabrication Labor Hours",# Hours for shop fabrication
    "Installation Labor Hours",# Hours for field install
    "Labor Rate",             # Default blended labor rate
    "Install Labor Rate",     # Field install labor rate
    "Equipment Cost",         # Lift / crane / equipment rental cost
    "Permit/Eng Cost",        # Permitting or engineering fees
    "Contingency %",          # Applied percentage buffer
    "Warranty Reserve %",     # Percentage of price allocated to warranty reserve
    "Risk Level",             # Low | Medium | High
    "Quote Version",          # Current working quote version label
    "Frozen Production Cost", # Snapshot baseline cost
    "Frozen Installation Cost",
    "Frozen Production Price",
    "Frozen Installation Price",
]


def get_db_path():
    # Reuse same override rules as desktop: env var or local file fallback
    db_path = os.environ.get("PROJECT_DB_PATH")
    if db_path and db_path.strip():
        return db_path.strip()
    # Resolve relative to repo root (parent of this web/ folder)
    repo_root = os.path.dirname(app.root_path)
    cfg_file = os.path.join(repo_root, "db_path.txt")
    if os.path.exists(cfg_file):
        with open(cfg_file, "r", encoding="utf-8") as f:
            p = f.read().strip()
            if p:
                return p
    return os.path.join(repo_root, "project_data.db")


def _parse_date(s: str):
    if not s or not isinstance(s, str):
        return None
    s = s.strip()
    if not s:
        return None
    # Try common formats encountered in the project DB
    fmts = [
        "%Y-%m-%d",
        "%m/%d/%Y",
        "%m-%d-%Y",
        "%Y/%m/%d",
    ]
    for f in fmts:
        try:
            return datetime.strptime(s, f).date()
        except Exception:
            continue
    return None


def _to_iso(d):
    return d.strftime("%Y-%m-%d") if d else ""


def _sqlite_connect(path: str):
    """Connect to SQLite. If WEB_SQLITE_RO is set (to '1' or 'true'),
    open the database in read-only mode using SQLite URI. This is helpful
    when the DB lives on a network share (SMB/OneDrive folder) and the web
    viewer should never write or lock the file.

    Env:
      WEB_SQLITE_RO=1|true  -> use mode=ro
    """
    ro = (os.environ.get('WEB_SQLITE_RO', '').lower() in ('1', 'true', 'yes'))
    if not ro:
        # Normal direct connection (default)
        return sqlite3.connect(path)

    # Build a file: URI with mode=ro that works on Windows and UNC paths
    # Examples:
    #   C:\data\db.sqlite -> file:///C:/data/db.sqlite?mode=ro
    #   \\server\share\db.sqlite -> file:////server/share/db.sqlite?mode=ro
    p = path.replace('\\', '/')
    if p.startswith('//'):
        # UNC path //server/share/...
        uri = f"file:{p}"
    else:
        # Drive letter path C:/...
        if ':' in p and not p.startswith('/'):
            p = '/' + p
        uri = f"file://{p}"
    uri += ("&" if "?" in uri else "?") + "mode=ro"
    return sqlite3.connect(uri, uri=True)


def _fetch_rows_any() -> List[Dict[str, Any]]:
    """Fetch all rows from project_parts as a list of dicts using either
    MySQL (if WEB_DB_URL set) or SQLite fallback. Column names are preserved
    exactly as in the table to avoid changing downstream logic.

    Env:
      WEB_DB_URL: SQLAlchemy URL (e.g., mysql+pymysql://user:pass@host/user$db?charset=utf8mb4)
    """
    db_url = os.environ.get("WEB_DB_URL", "").strip()
    if db_url and _HAS_SA:
        # MySQL/other via SQLAlchemy
        engine = create_engine(db_url, pool_pre_ping=True)
        try:
            with engine.connect() as conn:
                result = conn.execute(text("SELECT * FROM project_parts"))
                # SQLAlchemy Row -> mapping for column-name access
                return [dict(r._mapping) for r in result]
        except Exception as e:
            # Fall back to SQLite only if PROJECT_DB_PATH exists; otherwise re-raise
            # This keeps the site usable if MySQL is temporarily unavailable
            pass

    # SQLite fallback
    db = get_db_path()
    if not os.path.exists(db):
        return []
    con = _sqlite_connect(db)
    try:
        cur = con.cursor()
        cur.execute("SELECT * FROM project_parts")
        all_rows = cur.fetchall()
        all_cols = [d[0] for d in cur.description]
        return [{k: v for k, v in zip(all_cols, row)} for row in all_rows]
    finally:
        con.close()


def fetch_tasks():
    tasks = []
    # Fetch all columns so we can expose the original row in task["raw"] for full details
    rows = _fetch_rows_any()
    # Helper: slugify names to ID-safe strings usable in CSS selectors
    def slugify(text: str) -> str:
        if text is None:
            text = ""
        # Normalize whitespace
        text = str(text).strip()
        # Replace any non-alphanumeric with underscore
        s = re.sub(r"[^A-Za-z0-9_-]+", "_", text)
        # Collapse multiple underscores and trim
        s = re.sub(r"_+", "_", s).strip("_")
        return s or "task"

    # Build unique id map for names to ensure no collisions after slugify
    name_to_id = {}
    used = set()
    # Heuristic color mapping using status, % complete, and schedule
    def choose_colors(status: str, progress: int, start_dt, end_dt):
        s = (status or "").strip().lower()
        today = datetime.today().date()
        # Normalize common synonyms
        is_done = any(k in s for k in ("done", "complete", "completed", "finished")) or progress >= 100
        is_on_hold = any(k in s for k in ("on hold", "hold", "paused", "defer", "deferred"))
        is_blocked = any(k in s for k in ("blocked", "at risk", "risk", "overdue"))
        is_active_status = any(k in s for k in (
            "in progress", "in-progress", "inprogress", "active", "working", "ongoing", "started", "start"
        ))

        # Date-based signals
        has_started = bool(start_dt and start_dt <= today)
        in_window = bool(start_dt and end_dt and start_dt <= today <= end_dt)
        overdue = bool(end_dt and end_dt < today and progress < 100)
        has_progress = 0 < progress < 100

        # Priority order
        # Keep bar backgrounds mostly neutral (white/gray) and use color on progress only.
        if is_done:
            return {"color": "#ffffff", "color_progress": "#10b981"}  # green progress
        if overdue or is_blocked:
            return {"color": "#ffffff", "color_progress": "#ef4444"}  # red progress
        if is_on_hold:
            return {"color": "#ffffff", "color_progress": "#94a3b8"}  # slate progress
        # Active if explicit status OR progress in (0,100) OR currently within window
        if is_active_status or has_progress or in_window or (has_started and progress < 100 and not end_dt):
            return {"color": "#ffffff", "color_progress": "#FF8200"}  # UT orange progress
        # Planned / not started yet
        return {"color": "#e5e7eb", "color_progress": "#9ca3af"}  # gray bar, light progress

    def parse_images_field(val: str):
        root = _images_root()
        out = []
        if not val:
            return out
        # Split by common separators: comma, semicolon, newline
        parts = []
        for chunk in re.split(r"[\n;,]", str(val)):
            p = chunk.strip()
            if p:
                parts.append(p)
        exts = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp", ".svg"}
        seen = set()
        for p in parts:
            name = os.path.basename(p)
            ext = os.path.splitext(name)[1].lower()
            if ext not in exts:
                continue
            if name in seen:
                continue
            seen.add(name)
            # Only include if the file exists under images/
            try:
                if os.path.isfile(os.path.join(root, name)):
                    out.append({"name": name, "url": f"/images/{name}"})
            except Exception:
                continue
        return out

    for rec in rows:
        name = (rec.get("Project Part") or "").strip()
        base = slugify(name)
        candidate = base
        i = 2
        while candidate in used:
            candidate = f"{base}_{i}"
            i += 1
        name_to_id[name] = candidate
        used.add(candidate)

    for rec in rows:
        name = (rec.get("Project Part") or "").strip()
        # Normalize fields
        # Start date fallback order: Start Date -> Actual Start Date -> Baseline Start Date
        start_dt = _parse_date(rec.get("Start Date") or "") or \
                   _parse_date(rec.get("Actual Start Date") or "") or \
                   _parse_date(rec.get("Baseline Start Date") or "")
        # End date fallback order: Calculated End Date -> Actual Finish Date -> Baseline End Date
        end_dt = _parse_date(rec.get("Calculated End Date") or "") or \
                 _parse_date(rec.get("Actual Finish Date") or "") or \
                 _parse_date(rec.get("Baseline End Date") or "")
        # Duration
        try:
            duration = int(rec.get("Duration (days)") or 0)
        except Exception:
            duration = 0
        # If end missing but we have start, derive from duration (min 1 day)
        if not end_dt and start_dt:
            days = max(1, duration) if duration else 1
            end_dt = start_dt + timedelta(days=days)
        # If start missing but we have end and duration, derive start
        if not start_dt and end_dt and duration:
            days = max(1, duration)
            start_dt = end_dt - timedelta(days=days)

        # If still no valid dates, skip (can't draw a bar)
        if not start_dt or not end_dt:
            continue

        # Progress
        try:
            progress = int(rec.get("% Complete") or 0)
        except Exception:
            progress = 0
        # Dependencies -> map original names to our sanitized IDs
        deps_raw = (rec.get("Dependencies") or "").strip()
        deps_list = [d.strip() for d in deps_raw.split(",") if d.strip()]
        deps_ids = [name_to_id.get(d, slugify(d)) for d in deps_list]
        # Build task record with safe id
        colors = choose_colors(rec.get("Status"), progress, start_dt, end_dt)

        # Parent mapping (for tree view)
        parent_name = (rec.get("Parent") or "").strip()
        parent_id = name_to_id.get(parent_name) if parent_name else None

        tasks.append({
            "id": name_to_id.get(name, slugify(name)),
            "name": name,
            "start": _to_iso(start_dt),  # YYYY-MM-DD
            "end": _to_iso(end_dt),      # YYYY-MM-DD
            "progress": progress,
            "dependencies": ",".join(deps_ids),
            "type": (rec.get("Type") or "").strip(),
            "status": (rec.get("Status") or "").strip(),
            "internal_external": (rec.get("Internal/External") or "").strip(),
            "duration": duration,
            "color": colors["color"],
            "color_progress": colors["color_progress"],
            "parent_id": parent_id,
            "images": parse_images_field(rec.get("Images") or ""),
            # Expose full original row for details panel across views
            "raw": rec,
        })
    return tasks


def _normalize_db_rows(rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Prepare rows for the Database view without mutating the source DB.

    - Ensure Children is a derived, comma-separated list of child names.
    - If Calculated End Date is missing, derive from Start Date + Duration (days).
    - Normalize % Complete to int (default 0); if Status is Done then cap to 100.
    """
    name_index = { (r.get("Project Part") or "").strip(): i for i, r in enumerate(rows) }
    children_map = { name: [] for name in name_index.keys() }
    for r in rows:
        parent = (r.get("Parent") or "").strip()
        child = (r.get("Project Part") or "").strip()
        if parent and child and parent in children_map and parent != child:
            children_map[parent].append(child)

    out: List[Dict[str, Any]] = []
    for r in rows:
        row = dict(r)  # shallow copy
        name = (row.get("Project Part") or "").strip()
        # Children
        try:
            row["Children"] = ", ".join(children_map.get(name, []))
        except Exception:
            row["Children"] = row.get("Children", "")
        # Calculated End Date fallback: Start + Duration
        ced = (row.get("Calculated End Date") or "").strip()
        if not ced:
            sd = _parse_date(row.get("Start Date") or "")
            dur = 0
            try:
                dur = int(row.get("Duration (days)") or 0)
            except Exception:
                dur = 0
            if sd:
                try:
                    de = sd + timedelta(days=max(1, dur) if dur else 1)
                    row["Calculated End Date"] = de.strftime("%m-%d-%Y")
                except Exception:
                    pass
        # % Complete normalization
        pc = 0
        try:
            pc = int(row.get("% Complete") or 0)
        except Exception:
            pc = 0
        status = (row.get("Status") or "").strip().lower()
        if "done" in status and pc < 100:
            pc = 100
        row["% Complete"] = pc
        out.append(row)
    return out


@app.route("/api/database")
def api_database():
    rows = _fetch_rows_any()
    rows_n = _normalize_db_rows(rows)
    # Project only known columns (preserving order); include unknowns in a side payload if needed later
    def project_row(r: Dict[str, Any]) -> Dict[str, Any]:
        return { col: r.get(col, "") for col in PROJECT_COLUMNS }
    data = [project_row(r) for r in rows_n]
    return jsonify({
        "columns": PROJECT_COLUMNS,
        "rows": data,
        "stats": {"row_count": len(rows)}
    })


@app.route("/")
def index():
    watermark = os.environ.get("WEB_WATERMARK_TEXT", "For internal use only · Read‑only viewer")
    return render_template("index.html", watermark=watermark)


@app.route("/api/tasks")
def api_tasks():
    return jsonify(fetch_tasks())


# Serve the top-level header.png via /static/header.png for the template header image
@app.route("/static/header.png")
def static_header_png():
    parent_dir = os.path.dirname(app.root_path)
    return send_from_directory(parent_dir, "header.png")

# Serve repo-root header.svg via /static/header.svg (with PNG fallback)
@app.route("/static/header.svg")
def static_header_svg():
    parent_dir = os.path.dirname(app.root_path)
    svg_path = os.path.join(parent_dir, "header.svg")
    if os.path.exists(svg_path):
        return send_from_directory(parent_dir, "header.svg", mimetype='image/svg+xml')
    # Fallback to PNG if SVG not present
    png_path = os.path.join(parent_dir, "header.png")
    if os.path.exists(png_path):
        return send_from_directory(parent_dir, "header.png", mimetype='image/png')
    abort(404)

# Serve a favicon to avoid 404s; prefer header.png, else tiny transparent PNG
@app.route('/favicon.ico')
def favicon():
    parent_dir = os.path.dirname(app.root_path)
    header_path = os.path.join(parent_dir, 'header.png')
    if os.path.exists(header_path):
        return send_from_directory(parent_dir, 'header.png', mimetype='image/png')
    # 1x1 transparent PNG
    tiny_png_b64 = (
        'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR4nGMAAQAABQAB'
        'JzQnWQAAAABJRU5ErkJggg=='
    )
    data = base64.b64decode(tiny_png_b64)
    return Response(data, mimetype='image/png')

# Serve local copies of frappe-gantt assets to avoid CDN issues in embedded browsers
@app.route("/static/frappe-gantt.css")
def static_frappe_gantt_css():
    # Ship a compact but complete-enough CSS so the chart looks reasonable without the full vendored CSS
    content = (
        ":root{--g-arrow-color:#1f2937;--g-bar-color:#fff;--g-bar-border:#fff;--g-tick-color-thick:#ededed;--g-tick-color:#f3f3f3;--g-actions-background:#f3f3f3;--g-border-color:#ebeff2;--g-text-muted:#7c7c7c;--g-text-light:#fff;--g-text-dark:#171717;--g-progress-color:#dbdbdb;--g-handle-color:#37352f;--g-weekend-label-color:#dcdce4;--g-expected-progress:#c4c4e9;--g-header-background:#fff;--g-row-color:#fdfdfd;--g-row-border-color:#c7c7c7;--g-today-highlight:#37352f;--g-popup-actions:#ebeff2;--g-weekend-highlight-color:#f7f7f7;}\n"
        ".gantt-container{position:relative;overflow:auto;font-size:12px;line-height:14.5px;height:var(--gv-grid-height);width:100%;border-radius:8px;}\n"
        ".gantt-container .grid-header{height:calc(var(--gv-lower-header-height) + var(--gv-upper-header-height) + 10px);background:var(--g-header-background);position:sticky;top:0;left:0;border-bottom:1px solid var(--g-row-border-color);z-index:1000;}\n"
        ".gantt-container .upper-header{height:var(--gv-upper-header-height);}\n"
        ".gantt-container .lower-header{height:var(--gv-lower-header-height);}\n"
        ".gantt-container .lower-text,.gantt-container .upper-text{text-anchor:middle;}\n"
        ".gantt-container .lower-text{font-size:12px;position:absolute;width:calc(var(--gv-column-width)*.8);height:calc(var(--gv-lower-header-height)*.8);margin:0 calc(var(--gv-column-width)*.1);align-content:center;text-align:center;color:var(--g-text-muted);}\n"
        ".gantt-container .upper-text{position:absolute;width:fit-content;font-weight:500;font-size:14px;color:var(--g-text-dark);height:calc(var(--gv-lower-header-height)*.66);}\n"
        ".gantt-container .current-highlight{position:absolute;background:var(--g-today-highlight);width:1px;z-index:999;}\n"
        ".gantt{user-select:none;-webkit-user-select:none;position:absolute;}\n"
        ".gantt .grid-background{fill:none;}\n"
        ".gantt .grid-row{fill:var(--g-row-color);}\n"
        ".gantt .row-line{stroke:var(--g-border-color);}\n"
        ".gantt .tick{stroke:var(--g-tick-color);stroke-width:.4;}\n"
        ".gantt .tick.thick{stroke:var(--g-tick-color-thick);stroke-width:.7;}\n"
        ".gantt .arrow{fill:none;stroke:var(--g-arrow-color);stroke-width:1.5;}\n"
        ".gantt .bar-wrapper .bar{fill:var(--g-bar-color);stroke:var(--g-bar-border);stroke-width:0;outline:1px solid var(--g-row-border-color);border-radius:3px;}\n"
        ".gantt .bar-progress{fill:var(--g-progress-color);border-radius:4px;}\n"
        ".gantt .bar-expected-progress{fill:var(--g-expected-progress);}\n"
        ".gantt .bar-label{fill:var(--g-text-dark);dominant-baseline:central;font-family:Helvetica,Arial,sans-serif;font-size:13px;font-weight:400;}\n"
        ".gantt .bar-label.big{fill:var(--g-text-dark);text-anchor:start;}\n"
        ".gantt .handle{fill:var(--g-handle-color);opacity:0;transition:opacity .3s ease;}\n"
        ".gantt .handle.active,.gantt .handle.visible{cursor:ew-resize;opacity:1;}\n"
        ".gantt .bar-invalid{fill:transparent;stroke:var(--g-bar-border);stroke-width:1;stroke-dasharray:5;}\n"
    )
    return app.response_class(content_type="text/css", response=content)

@app.route("/static/vendor/frappe-gantt.css")
def static_vendor_frappe_gantt_css():
    vendor_dir = os.path.join(app.root_path, "static", "vendor")
    filename = "frappe-gantt.css"
    path = os.path.join(vendor_dir, filename)
    try:
        if os.path.exists(path) and os.path.getsize(path) >= 1 * 1024:
            return send_from_directory(vendor_dir, filename)
    except Exception:
        pass
    # No vendored CSS, respond with 404 so the fallback link remains
    return Response("", status=404)

@app.route("/static/frappe-gantt.umd.js")
def static_frappe_gantt_js():
    # Tiny stub loader that warns if CDN failed; user can refresh
    fallback = (
        "(function(){\n"
        "  if (!window.Gantt) {\n"
        "    console.error('frappe-gantt not loaded; using minimal stub');\n"
        "    window.Gantt = function(container, tasks){\n"
        "      const pre = document.createElement('pre');\n"
        "      pre.textContent = 'frappe-gantt missing. Tasks preview:\\n' + JSON.stringify(tasks.slice(0,5), null, 2);\n"
        "      container.appendChild(pre);\n"
        "    };\n"
        "    window.Gantt.prototype = { change_view_mode: function(){} };\n"
        "  }\n"
        "})();\n"
    )
    return app.response_class(content_type="application/javascript", response=fallback)


# Serve vendored frappe-gantt if present under web/static/vendor
@app.route("/static/vendor/frappe-gantt.umd.js")
def static_vendor_frappe_gantt_js():
    vendor_dir = os.path.join(app.root_path, "static", "vendor")

    def serve_if_valid(filename: str, min_size: int = 20 * 1024):
        path = os.path.join(vendor_dir, filename)
        try:
            if os.path.exists(path) and os.path.getsize(path) >= min_size:
                return send_from_directory(vendor_dir, filename)
        except Exception:
            pass
        return None

    # Prefer UMD build, then minified; only if file is reasonably sized (avoid truncated files)
    resp = serve_if_valid("frappe-gantt.umd.js", min_size=40 * 1024) or \
           serve_if_valid("frappe-gantt.min.js", min_size=20 * 1024)
    if resp:
        return resp

    # If not present or invalid/truncated, return a small JS that notifies missing vendor file
    msg = (
        "console.warn('Local vendor frappe-gantt not found or invalid at /static/vendor; ' +\
        'falling back to CDN or stub.');\n"
    )
    return Response(msg, mimetype="application/javascript")


@app.route("/api/debug")
def api_debug():
    db_url = os.environ.get("WEB_DB_URL", "").strip()
    using_mysql = bool(db_url and _HAS_SA)
    db = get_db_path()
    img_root = _images_root()
    img_count = 0
    try:
        if os.path.isdir(img_root):
            img_count = sum(
                1 for n in os.listdir(img_root)
                if os.path.isfile(os.path.join(img_root, n))
            )
    except Exception:
        pass
    info = {
        "db_backend": "mysql" if using_mysql else "sqlite",
        "db_path": db if not using_mysql else db_url.split("@")[-1],
        "db_exists": os.path.exists(db) if not using_mysql else True,
        "table": "project_parts",
        "row_count": 0,
        "sample": [],
        "error": None,
        "images_root": img_root,
        "images_count": img_count,
    }
    try:
        if using_mysql:
            engine = create_engine(db_url, pool_pre_ping=True)
            with engine.connect() as conn:
                info["row_count"] = conn.execute(text("SELECT COUNT(*) FROM project_parts")).scalar_one()
                result = conn.execute(text("SELECT * FROM project_parts LIMIT 3"))
                for r in result:
                    info["sample"].append(dict(r._mapping))
        else:
            if not os.path.exists(db):
                return jsonify(info)
            con = _sqlite_connect(db)
            try:
                cur = con.cursor()
                cur.execute("SELECT count(*) FROM project_parts")
                info["row_count"] = cur.fetchone()[0]
                cur.execute("SELECT * FROM project_parts LIMIT 3")
                cols = [d[0] for d in cur.description]
                for r in cur.fetchall():
                    info["sample"].append({k: v for k, v in zip(cols, r)})
            finally:
                try:
                    con.close()
                except Exception:
                    pass
    except Exception as e:
        info["error"] = str(e)
    return jsonify(info)

@app.route("/health")
def health():
    # Lightweight health check endpoint for load balancers/monitors
    return Response("ok", mimetype="text/plain")


# Images: list and serve from repo_root/images (with optional override via WEB_IMAGES_ROOT)
def _images_root():
    """Compute the images root directory.

    If WEB_IMAGES_ROOT is set, use that value as-is. Otherwise, default to
    the repo root "images" folder (parent of this web/ directory).
    """
    override = os.environ.get("WEB_IMAGES_ROOT", "").strip()
    if override:
        return override
    return os.path.join(os.path.dirname(app.root_path), "images")


@app.route("/api/images")
def api_images():
    root = _images_root()
    out = []
    if not os.path.isdir(root):
        return jsonify(out)
    exts = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp", ".svg"}
    try:
        for name in sorted(os.listdir(root)):
            # Skip hidden/system files
            if name.startswith("."):
                continue
            p = os.path.join(root, name)
            if os.path.isfile(p) and os.path.splitext(name)[1].lower() in exts:
                out.append({
                    "name": name,
                    "url": f"/images/{name}",
                    "size": os.path.getsize(p)
                })
    except Exception:
        pass
    return jsonify(out)


@app.route("/images/<path:filename>")
def serve_image(filename: str):
    root = _images_root()
    # Basic path safety: prevent directory traversal
    if ".." in filename or filename.startswith("/"):
        abort(400)
    return send_from_directory(root, filename)


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    debug_env = os.environ.get("WEB_DEBUG", "1").lower()
    debug = debug_env not in ("0", "false", "no")
    app.run(host="127.0.0.1", port=port, debug=debug)
