import os
import json
import sqlite3
from datetime import datetime, timedelta
from flask import Flask, jsonify, render_template, send_from_directory, Response

app = Flask(__name__)


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


def fetch_tasks():
    db = get_db_path()
    cols = [
        "Project Part", "Parent", "Children", "Start Date", "Duration (days)", "Internal/External",
        "Dependencies", "Type", "Calculated End Date", "Resources", "Notes", "Responsible",
        "Images", "Pace Link", "Attachments", "% Complete", "Status", "Actual Start Date",
        "Actual Finish Date", "Baseline Start Date", "Baseline End Date"
    ]
    tasks = []
    if not os.path.exists(db):
        return tasks
    con = sqlite3.connect(db)
    try:
        cur = con.cursor()
        cur.execute("SELECT {} FROM project_parts".format(
            ", ".join([f'"{c}"' for c in cols])
        ))
        for row in cur.fetchall():
            rec = {k: v for k, v in zip(cols, row)}
            # Normalize fields
            name = (rec.get("Project Part") or "").strip()
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

            tasks.append({
                "id": name,  # simple id; could be improved to a stable unique key
                "name": name,
                "start": _to_iso(start_dt),  # YYYY-MM-DD
                "end": _to_iso(end_dt),      # YYYY-MM-DD
                "progress": progress,
                "dependencies": (rec.get("Dependencies") or "").strip(),
                "type": (rec.get("Type") or "").strip(),
                "status": (rec.get("Status") or "").strip(),
                "duration": duration,
            })
    finally:
        con.close()
    return tasks


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/tasks")
def api_tasks():
    return jsonify(fetch_tasks())


# Serve the top-level header.png via /static/header.png for the template header image
@app.route("/static/header.png")
def static_header_png():
    parent_dir = os.path.dirname(app.root_path)
    return send_from_directory(parent_dir, "header.png")

# Serve local copies of frappe-gantt assets to avoid CDN issues in embedded browsers
@app.route("/static/frappe-gantt.css")
def static_frappe_gantt_css():
    # Ship a minimal CSS if CDN not available (fallback)
    content = (
        ".gantt .bar { fill: #7db3ff; }\n"
        ".gantt .bar-progress { fill: #4a90e2; }\n"
        ".gantt .grid .row { stroke: #eee; }\n"
        ".gantt .today-highlight { fill: #f8faff; }\n"
    )
    return app.response_class(content_type="text/css", response=content)

@app.route("/static/vendor/frappe-gantt.css")
def static_vendor_frappe_gantt_css():
    vendor_dir = os.path.join(app.root_path, "static", "vendor")
    filename = "frappe-gantt.css"
    path = os.path.join(vendor_dir, filename)
    try:
        if os.path.exists(path) and os.path.getsize(path) >= 10 * 1024:
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
        "      pre.textContent = 'frappe-gantt missing. Tasks preview:\n' + JSON.stringify(tasks.slice(0,5), null, 2);\n"
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
    db = get_db_path()
    info = {
        "db_path": db,
        "db_exists": os.path.exists(db),
        "table": "project_parts",
        "row_count": 0,
        "sample": [],
        "error": None,
    }
    if not os.path.exists(db):
        return jsonify(info)
    try:
        con = sqlite3.connect(db)
        cur = con.cursor()
        cur.execute("SELECT count(*) FROM project_parts")
        info["row_count"] = cur.fetchone()[0]
        cur.execute("SELECT * FROM project_parts LIMIT 3")
        cols = [d[0] for d in cur.description]
        for r in cur.fetchall():
            info["sample"].append({k: v for k, v in zip(cols, r)})
    except Exception as e:
        info["error"] = str(e)
    finally:
        try:
            con.close()
        except Exception:
            pass
    return jsonify(info)


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="127.0.0.1", port=port, debug=True)
