import os
import sqlite3
from datetime import datetime, timedelta
from typing import Any, Dict, List
from flask import Flask, jsonify, render_template, send_from_directory, Response, abort

# Optional SQLAlchemy for MySQL
try:
    from sqlalchemy import create_engine, text  # type: ignore
    _HAS_SA = True
except Exception:
    _HAS_SA = False

app = Flask(__name__)

# --- Config helpers ---

def repo_root() -> str:
    # app.root_path is <repo>/web/v2; project root is two levels up
    return os.path.abspath(os.path.join(app.root_path, os.pardir, os.pardir))

def get_db_path() -> str:
    p = os.environ.get('PROJECT_DB_PATH', '').strip()
    if p:
        return p
    cfg = os.path.join(repo_root(), 'db_path.txt')
    if os.path.exists(cfg):
        try:
            with open(cfg, 'r', encoding='utf-8') as f:
                s = f.read().strip()
                if s:
                    return s
        except Exception:
            pass
    return os.path.join(repo_root(), 'project_data.db')

def _sqlite_connect(path: str):
    ro = (os.environ.get('WEB_SQLITE_RO', '').lower() in ('1','true','yes'))
    if not ro:
        return sqlite3.connect(path)
    p = path.replace('\\','/')
    if p.startswith('//'):
        uri = f"file:{p}"
    else:
        if ':' in p and not p.startswith('/'):
            p = '/' + p
        uri = f"file://{p}"
    uri += ("&" if "?" in uri else "?") + "mode=ro"
    return sqlite3.connect(uri, uri=True)

# --- Data helpers mirrored from desktop ---

def _parse_date(s: str):
    if not s: return None
    s = str(s).strip()
    if not s: return None
    for fmt in ("%Y-%m-%d","%m/%d/%Y","%m-%d-%Y","%Y/%m/%d"):
        try:
            return datetime.strptime(s, fmt).date()
        except Exception:
            pass
    return None

def _to_iso(d):
    return d.strftime('%Y-%m-%d') if d else ''

PROJECT_COLUMNS = [
    "Project Part", "Parent", "Children", "Start Date", "Duration (days)", "Internal/External", "Dependencies", "Type", "Calculated End Date", "Resources", "Notes", "Responsible", "Images", "Pace Link", "Attachments",
    "% Complete","Status","Actual Start Date","Actual Finish Date","Baseline Start Date","Baseline End Date",
    "Production Cost","Installation Cost","Production Price","Installation Price",
    "Material Cost","Fabrication Labor Hours","Installation Labor Hours","Labor Rate","Install Labor Rate","Equipment Cost","Permit/Eng Cost","Contingency %","Warranty Reserve %","Risk Level","Quote Version","Frozen Production Cost","Frozen Installation Cost","Frozen Production Price","Frozen Installation Price",
]

# --- DB fetch ---

def _fetch_rows() -> List[Dict[str, Any]]:
    db_url = os.environ.get('WEB_DB_URL', '').strip()
    if db_url and _HAS_SA:
        engine = create_engine(db_url, pool_pre_ping=True)
        try:
            with engine.connect() as conn:
                rs = conn.execute(text('SELECT * FROM project_parts'))
                return [dict(r._mapping) for r in rs]
        except Exception:
            pass
    db = get_db_path()
    if not os.path.exists(db):
        return []
    con = _sqlite_connect(db)
    try:
        cur = con.cursor(); cur.execute('SELECT * FROM project_parts')
        rows = cur.fetchall(); cols = [d[0] for d in cur.description]
        return [{k:v for k,v in zip(cols, r)} for r in rows]
    finally:
        con.close()

# --- Mapping for views ---

def _normalize_db_rows(rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    name_ix = {(r.get('Project Part') or '').strip(): i for i,r in enumerate(rows)}
    children = {n: [] for n in name_ix.keys()}
    for r in rows:
        parent = (r.get('Parent') or '').strip(); child = (r.get('Project Part') or '').strip()
        if parent and child and parent in children and parent != child:
            children[parent].append(child)
    out = []
    for r in rows:
        row = dict(r)
        name = (row.get('Project Part') or '').strip()
        row['Children'] = ', '.join(children.get(name, []))
        if not (row.get('Calculated End Date') or '').strip():
            sd = _parse_date(row.get('Start Date') or '')
            try: dur = int(row.get('Duration (days)') or 0)
            except Exception: dur = 0
            if sd:
                de = sd + timedelta(days=max(1, dur) if dur else 1)
                row['Calculated End Date'] = de.strftime('%m-%d-%Y')
        try: pc = int(row.get('% Complete') or 0)
        except Exception: pc = 0
        st = (row.get('Status') or '').lower()
        if 'done' in st and pc < 100: pc = 100
        row['% Complete'] = pc
        out.append(row)
    return out

# --- Routes ---

@app.route('/')
def index():
    wm = os.environ.get('WEB_WATERMARK_TEXT', 'For internal use only · Read‑only viewer')
    return render_template('index.html', watermark=wm)

@app.route('/api/tasks')
def api_tasks():
    rows = _fetch_rows()
    # Build name->id map
    def slug(t):
        import re
        s = re.sub(r"[^A-Za-z0-9_-]+", "_", (t or '').strip());
        s = re.sub(r"_+","_", s).strip('_');
        return s or 'task'
    used = set(); name_to_id = {}
    for r in rows:
        base = slug(r.get('Project Part') or '') or 'task'; c = base; i = 2
        while c in used: c = f"{base}_{i}"; i += 1
        used.add(c); name_to_id[(r.get('Project Part') or '').strip()] = c
    tasks = []
    for r in rows:
        start = _parse_date(r.get('Start Date') or '') or _parse_date(r.get('Actual Start Date') or '') or _parse_date(r.get('Baseline Start Date') or '')
        end = _parse_date(r.get('Calculated End Date') or '') or _parse_date(r.get('Actual Finish Date') or '') or _parse_date(r.get('Baseline End Date') or '')
        try: dur = int(r.get('Duration (days)') or 0)
        except Exception: dur = 0
        if not end and start:
            end = start + timedelta(days=max(1, dur) if dur else 1)
        if not start and end and dur:
            start = end - timedelta(days=max(1, dur))
        if not start or not end:
            continue
        try: progress = int(r.get('% Complete') or 0)
        except Exception: progress = 0
        deps = [d.strip() for d in (r.get('Dependencies') or '').split(',') if d.strip()]
        deps_ids = [name_to_id.get(d) or slug(d) for d in deps]
        parent_id = name_to_id.get((r.get('Parent') or '').strip()) if r.get('Parent') else None
        # Colors similar to desktop heuristics
        status = (r.get('Status') or '').lower(); today = datetime.today().date()
        is_done = 'done' in status or progress >= 100
        is_blocked = ('blocked' in status) or ('risk' in status) or ('overdue' in status)
        is_hold = ('hold' in status) or ('defer' in status)
        has_started = bool(start and start <= today)
        in_window = bool(start and end and start <= today <= end)
        overdue = bool(end and end < today and progress < 100)
        has_prog = 0 < progress < 100
        if is_done:
            color, color_prog = ('#ffffff', '#10b981')
        elif overdue or is_blocked:
            color, color_prog = ('#ffffff', '#ef4444')
        elif is_hold:
            color, color_prog = ('#ffffff', '#94a3b8')
        elif has_prog or in_window or (has_started and progress < 100 and not end):
            color, color_prog = ('#ffffff', '#FF8200')
        else:
            color, color_prog = ('#e5e7eb', '#9ca3af')
        # Images: only include files that exist in images root
        def images_list(val: str):
            import os, re
            root = images_root(); out = []
            if not val: return out
            parts = []
            for ch in re.split(r"[\n;,]", str(val)):
                p = ch.strip();
                if p: parts.append(p)
            exts = {'.png','.jpg','.jpeg','.gif','.webp','.bmp','.svg'}; seen = set()
            for p in parts:
                name = os.path.basename(p); ext = os.path.splitext(name)[1].lower()
                if ext not in exts or name in seen: continue
                seen.add(name)
                if os.path.isfile(os.path.join(root, name)):
                    out.append({'name': name, 'url': f"/images/{name}"})
            return out
        tasks.append({
            'id': name_to_id.get((r.get('Project Part') or '').strip()),
            'name': (r.get('Project Part') or '').strip(),
            'start': _to_iso(start), 'end': _to_iso(end), 'progress': progress,
            'dependencies': ','.join([d for d in deps_ids if d]),
            'type': (r.get('Type') or '').strip(),
            'status': (r.get('Status') or '').strip(),
            'internal_external': (r.get('Internal/External') or '').strip(),
            'duration': dur,
            'color': color, 'color_progress': color_prog,
            'parent_id': parent_id,
            'images': images_list(r.get('Images') or ''),
            'raw': r,
        })
    return jsonify(tasks)

@app.route('/api/database')
def api_database():
    rows = _normalize_db_rows(_fetch_rows())
    def project_row(r: Dict[str, Any]):
        return { col: r.get(col, '') for col in PROJECT_COLUMNS }
    data = [project_row(r) for r in rows]
    return jsonify({'columns': PROJECT_COLUMNS, 'rows': data, 'stats': {'row_count': len(data)}})

@app.route('/api/images')
def api_images():
    root = images_root(); out = []
    if not os.path.isdir(root):
        return jsonify(out)
    exts = {'.png','.jpg','.jpeg','.gif','.webp','.bmp','.svg'}
    try:
        for name in sorted(os.listdir(root)):
            if name.startswith('.'):
                continue
            p = os.path.join(root, name)
            if os.path.isfile(p) and os.path.splitext(name)[1].lower() in exts:
                out.append({'name': name, 'url': f"/images/{name}", 'size': os.path.getsize(p)})
    except Exception:
        pass
    return jsonify(out)

@app.route('/api/debug')
def api_debug():
    db_url = os.environ.get('WEB_DB_URL','').strip()
    using_mysql = bool(db_url and _HAS_SA)
    db = get_db_path()
    img_root = images_root()
    info = {
        'db_backend': 'mysql' if using_mysql else 'sqlite',
        'db_path': db if not using_mysql else db_url.split('@')[-1],
        'db_exists': os.path.exists(db) if not using_mysql else True,
        'table': 'project_parts',
        'row_count': 0,
        'images_root': img_root,
    }
    try:
        if using_mysql:
            engine = create_engine(db_url, pool_pre_ping=True)
            with engine.connect() as conn:
                info['row_count'] = conn.execute(text('SELECT COUNT(*) FROM project_parts')).scalar_one()
        else:
            if os.path.exists(db):
                con = _sqlite_connect(db); cur = con.cursor(); cur.execute('SELECT COUNT(*) FROM project_parts'); info['row_count'] = cur.fetchone()[0]; con.close()
    except Exception as e:
        info['error'] = str(e)
    return jsonify(info)

# Images root + serving

def images_root():
    o = os.environ.get('WEB_IMAGES_ROOT','').strip()
    return o or os.path.join(repo_root(), 'images')

@app.route('/images/<path:filename>')
def serve_image(filename: str):
    if '..' in filename or filename.startswith('/'):
        abort(400)
    return send_from_directory(images_root(), filename)

# Header assets
@app.route('/static/header.png')
def static_header_png():
    return send_from_directory(repo_root(), 'header.png')

@app.route('/static/header.svg')
def static_header_svg():
    parent = repo_root()
    svg = os.path.join(parent, 'header.svg')
    if os.path.exists(svg):
        return send_from_directory(parent, 'header.svg', mimetype='image/svg+xml')
    return send_from_directory(parent, 'header.png', mimetype='image/png')

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='127.0.0.1', port=port, debug=True)
