import os
import sqlite3
from datetime import datetime, timedelta
from typing import Any, Dict, List, Tuple
from flask import Flask, jsonify, render_template, send_from_directory, Response, abort
from flask import request

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
        # Heroku sets DATABASE_URL to 'postgres://...' (deprecated); SQLAlchemy expects 'postgresql://...'
        if db_url.startswith('postgres://'):
            db_url = 'postgresql://' + db_url[len('postgres://'):]
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

# --- Write helpers (optional edit support) ---

ALLOWED_UPDATE_COLS = {
    "% Complete",
    "Status",
    "Start Date",
    "Duration (days)",
    "Notes",
    "Pace Link",
    "Responsible",
    "Type",
    "Internal/External",
    "Dependencies",
}

def _using_mysql() -> Tuple[bool, str]:
    db_url = os.environ.get('WEB_DB_URL', '').strip()
    return (bool(db_url and _HAS_SA), db_url)

def _deny_if_ro_sqlite():
    if (os.environ.get('WEB_SQLITE_RO', '').lower() in ('1','true','yes')):
        abort(403, description='SQLite is in read-only mode (WEB_SQLITE_RO=1)')

@app.post('/api/task/update')
def api_task_update():
    # Optional token auth
    token_env = os.environ.get('WEB_EDIT_TOKEN', '').strip()
    if token_env:
        tok = (request.json or {}).get('edit_token', '').strip()
        if tok != token_env:
            abort(403, description='Invalid edit token')
    data = request.get_json(silent=True) or {}
    name = (data.get('project_part') or '').strip()
    updates_in = data.get('updates') or {}
    if not name:
        abort(400, description='project_part is required')
    # Filter allowed columns only
    updates = { k: v for k, v in updates_in.items() if k in ALLOWED_UPDATE_COLS }
    if not updates:
        abort(400, description='No allowed columns to update')
    using_mysql, db_url = _using_mysql()
    rows_affected = 0
    if using_mysql:
        # Use SQLAlchemy text with backtick-quoted identifiers
        engine = create_engine(db_url, pool_pre_ping=True)
        sets = []
        params: Dict[str, Any] = {}
        for i,(k,v) in enumerate(updates.items(), start=1):
            p = f"v{i}"
            sets.append(f"`{k}` = :{p}")
            params[p] = v
        params['name'] = name
        sql = text(f"UPDATE `project_parts` SET {', '.join(sets)} WHERE `Project Part` = :name")
        try:
            with engine.begin() as conn:
                res = conn.execute(sql, params)
                rows_affected = res.rowcount or 0
        except Exception as e:
            abort(500, description=f'MySQL update failed: {e}')
    else:
        # SQLite direct update (deny if RO)
        _deny_if_ro_sqlite()
        db = get_db_path()
        if not os.path.exists(db):
            abort(404, description='SQLite DB not found')
        try:
            con = sqlite3.connect(db)
            cur = con.cursor()
            sets = []
            vals: List[Any] = []
            for k, v in updates.items():
                sets.append(f'"{k}" = ?')
                vals.append(v)
            vals.append(name)
            sql = f'UPDATE project_parts SET {", ".join(sets)} WHERE "Project Part" = ?'
            cur.execute(sql, vals)
            rows_affected = cur.rowcount or 0
            con.commit()
        except Exception as e:
            try:
                con.rollback()
            except Exception:
                pass
            abort(500, description=f'SQLite update failed: {e}')
        finally:
            try:
                con.close()
            except Exception:
                pass
    # Return the updated row (best-effort)
    rows = _fetch_rows()
    row = next((r for r in rows if (r.get('Project Part') or '').strip() == name), None)
    return jsonify({ 'ok': True, 'rows_affected': rows_affected, 'row': row })

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
                # Business-day addition: skip Sat/Sun
                days = max(1, dur) if dur else 1
                cur = sd
                added = 0
                while added < days:
                    cur = cur + timedelta(days=1)
                    if cur.weekday() < 5:  # 0=Mon..4=Fri
                        added += 1
                row['Calculated End Date'] = cur.strftime('%m-%d-%Y')
        try: pc = int(row.get('% Complete') or 0)
        except Exception: pc = 0
        st = (row.get('Status') or '').lower()
        if 'done' in st and pc < 100: pc = 100
        row['% Complete'] = pc
        out.append(row)
    # Roll-up parent progress/status similar to desktop
    name_to_row = { (r.get('Project Part') or '').strip(): r for r in out }
    children_map: Dict[str, List[Dict[str, Any]]] = {}
    for r in out:
        p = (r.get('Parent') or '').strip()
        if p:
            children_map.setdefault(p, []).append(r)
    visited = set()
    def dfs(name: str):
        if not name or name in visited:
            return
        visited.add(name)
        kids = children_map.get(name)
        row = name_to_row.get(name)
        if not row:
            return
        if not kids:
            # ensure numeric % and done normalization
            try:
                pc = int(row.get('% Complete') or 0)
            except Exception:
                pc = 0
            row['% Complete'] = max(0, min(100, pc))
            if (row.get('Status') or '').strip() == 'Done' and row['% Complete'] < 100:
                row['% Complete'] = 100
            return
        # Recurse
        for k in kids:
            dfs((k.get('Project Part') or '').strip())
        # Weighted by child duration when available; else average
        total_weight = 0; weighted = 0; all_done = True; any_in_prog = False; any_blocked = False
        for ch in kids:
            try: dur = int(ch.get('Duration (days)') or 0)
            except Exception: dur = 0
            try: cpc = int(ch.get('% Complete') or 0)
            except Exception: cpc = 0
            weighted += cpc * max(0, dur)
            total_weight += max(0, dur)
            st = (ch.get('Status') or 'Planned').strip() or 'Planned'
            if st != 'Done':
                all_done = False
            if st == 'In Progress':
                any_in_prog = True
            if st == 'Blocked':
                any_blocked = True
        if total_weight > 0:
            row['% Complete'] = int(round(weighted / total_weight))
        else:
            vals = []
            for ch in kids:
                try: vals.append(int(ch.get('% Complete') or 0))
                except Exception: pass
            row['% Complete'] = int(round(sum(vals)/len(vals))) if vals else 0
        if all_done and kids:
            row['Status'] = 'Done'
            row['% Complete'] = 100
        else:
            if any_blocked and not any_in_prog:
                row['Status'] = 'Blocked'
            elif any_in_prog:
                row['Status'] = 'In Progress'
            else:
                row['Status'] = row.get('Status') or 'Planned'
    # Start from roots (no Parent)
    for r in out:
        if not (r.get('Parent') or '').strip():
            dfs((r.get('Project Part') or '').strip())
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
    # Build a one-time images index for efficient lookup by base name (case-insensitive)
    img_root = images_root()
    img_index: Dict[str, str] = {}
    try:
        exts = {'.png','.jpg','.jpeg','.gif','.webp','.bmp','.svg'}
        for root, _dirs, files in os.walk(img_root):
            for name in files:
                ext = os.path.splitext(name)[1].lower()
                if ext in exts:
                    rel = os.path.relpath(os.path.join(root, name), img_root)
                    img_index[name.lower()] = rel.replace('\\','/')
    except Exception:
        img_index = {}

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
        # Desktop parity: bars are dark gray; progress overlay is orange.
        # Risk is indicated via outline (red for overdue, orange for at-risk), not by changing fill.
        today = datetime.today().date()
        # Determine risk flags similar to desktop logic
        risk = ''
        try:
            if progress < 100 and end and today > end:
                risk = 'overdue'
            else:
                st = (r.get('Status') or '').strip()
                if progress == 0 and start and today > start and st in ('Planned','Blocked'):
                    risk = 'at_risk'
        except Exception:
            risk = ''
        color, color_prog = ('#333333', '#FF8200')
        # Images: include files from Images field; fall back to image-type Attachments
        def images_list(images_val: str, attachments_val: Any) -> List[Dict[str, str]]:
            import json, re
            out: List[Dict[str,str]] = []
            seen = set()
            parts: List[str] = []
            # Split Images field by common separators
            if images_val:
                for ch in re.split(r"[\n;,]", str(images_val)):
                    p = ch.strip()
                    if p:
                        parts.append(p)
            # Parse Attachments JSON array and add image-like entries if Images empty or to augment
            try:
                if attachments_val:
                    att_list = attachments_val
                    if isinstance(att_list, str):
                        att_list = json.loads(att_list)
                    if isinstance(att_list, list):
                        for a in att_list:
                            if not isinstance(a, str):
                                continue
                            parts.append(a)
            except Exception:
                pass
            exts = {'.png','.jpg','.jpeg','.gif','.webp','.bmp','.svg'}
            for p in parts:
                name = os.path.basename(str(p))
                key = name.lower()
                ext = os.path.splitext(key)[1].lower()
                if ext not in exts or key in seen:
                    continue
                seen.add(key)
                rel = img_index.get(key)
                if rel:
                    out.append({'name': name, 'url': f"/images/{rel}"})
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
            'color': color, 'color_progress': color_prog, 'risk': risk,
            'parent_id': parent_id,
            'images': images_list(r.get('Images') or '', r.get('Attachments')),
            'raw': r,
        })
    # Compute critical path using dependencies and durations (IDs graph)
    try:
        # Build graph: task_id -> list of predecessor IDs
        id_to_task = {t['id']: t for t in tasks if t.get('id')}
        graph = {}
        duration = {}
        for t in tasks:
            tid = t.get('id')
            if not tid:
                continue
            preds = [p.strip() for p in (t.get('dependencies') or '').split(',') if p.strip()]
            graph[tid] = [p for p in preds if p in id_to_task]
            try:
                duration[tid] = int(t.get('duration') or 0)
            except Exception:
                duration[tid] = 0
        # Topo order
        visited = set(); order = []
        def dfs(n):
            if n in visited:
                return
            visited.add(n)
            for p in graph.get(n, []):
                dfs(p)
            order.append(n)
        for n in graph.keys():
            dfs(n)
        # Forward pass: earliest finish in abstract time (days)
        es = {}; ef = {}
        for n in order:
            preds = graph.get(n, [])
            if not preds:
                es[n] = 0
            else:
                es[n] = max(ef.get(p, 0) for p in preds)
            ef[n] = es[n] + max(0, duration.get(n,0))
        proj_finish = max(ef.values()) if ef else 0
        # Backward pass: latest start
        ls = {}; lf = {}
        # Build successors map once
        succs = {k: [] for k in graph.keys()}
        for s, preds in graph.items():
            for p in preds:
                succs.setdefault(p, []).append(s)
        for n in reversed(order):
            s_list = succs.get(n, [])
            lf[n] = min(ls[s] for s in s_list) if s_list else proj_finish
            dur = max(0, duration.get(n,0))
            ls[n] = lf[n] - dur
        crit_ids = {n for n in order if abs((es.get(n,0) - ls.get(n,0))) <= 0}
        for t in tasks:
            tid = t.get('id')
            is_crit = bool(tid in crit_ids)
            t['critical'] = is_crit
            # Mirror desktop nuance: critical tasks use a golden progress overlay color
            if is_crit:
                t['color_progress'] = '#DAA520'
    except Exception:
        for t in tasks:
            t['critical'] = False
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
        for dirpath, _dirnames, filenames in os.walk(root):
            for name in filenames:
                if name.startswith('.'):
                    continue
                if os.path.splitext(name)[1].lower() not in exts:
                    continue
                full = os.path.join(dirpath, name)
                rel = os.path.relpath(full, root).replace('\\','/')
                out.append({'name': rel, 'url': f"/images/{rel}", 'size': os.path.getsize(full)})
        out.sort(key=lambda x: x['name'].lower())
    except Exception:
        pass
    return jsonify(out)

@app.route('/api/debug')
def api_debug():
    db_url = os.environ.get('WEB_DB_URL','').strip()
    # Heroku sets DATABASE_URL to 'postgres://...' (deprecated); SQLAlchemy expects 'postgresql://...'
    if db_url.startswith('postgres://'):
        db_url = 'postgresql://' + db_url[len('postgres://'):]
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

# --- Metrics and Costs (to mirror desktop views) ---

def _leaf_rows(rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    names = {(r.get('Project Part') or '').strip() for r in rows}
    has_child = set()
    for r in rows:
        p = (r.get('Parent') or '').strip()
        if p:
            has_child.add(p)
    out = []
    for r in rows:
        n = (r.get('Project Part') or '').strip()
        if n and n not in has_child:
            out.append(r)
    return out

def _parse_mmddyyyy(s: str):
    try:
        import datetime as _dt
        return _dt.datetime.strptime(s, '%m-%d-%Y').date()
    except Exception:
        return None

@app.route('/api/metrics')
def api_metrics():
    import datetime as _dt
    rows = _normalize_db_rows(_fetch_rows())
    leafs = _leaf_rows(rows)
    # Status counts (leaf only)
    status_counts: Dict[str,int] = {}
    for r in leafs:
        st = (r.get('Status') or 'Planned').strip() or 'Planned'
        status_counts[st] = status_counts.get(st, 0) + 1
    # Percent complete weighted by duration
    sum_w = 0; sum_wp = 0; done = 0
    today = _dt.date.today(); overdue = 0; at_risk = 0
    for r in leafs:
        try: dur = int(r.get('Duration (days)') or 0)
        except Exception: dur = 0
        try: pc = int(r.get('% Complete') or 0)
        except Exception: pc = 0
        st = (r.get('Status') or '').strip()
        sum_w += max(0, dur)
        sum_wp += pc * max(0, dur)
        if st == 'Done':
            done += 1
        # Overdue / at-risk (mirror desktop logic)
        end_s = (r.get('Calculated End Date') or '').strip()
        start_s = (r.get('Start Date') or '').strip()
        end_dt = _parse_mmddyyyy(end_s)
        start_dt = _parse_mmddyyyy(start_s)
        if pc < 100 and end_dt and today > end_dt:
            overdue += 1
        elif pc == 0 and start_dt and today > start_dt and st in ('Planned','Blocked'):
            at_risk += 1
    overall = (sum_wp / sum_w) if sum_w else 0.0
    # Critical path (quick pass similar to desktop)
    try:
        name_to_row = { (r.get('Project Part') or '').strip(): r for r in rows }
        graph: Dict[str, List[str]] = {}
        duration: Dict[str, int] = {}
        min_date = None
        import datetime as _dt2
        for r in rows:
            n = (r.get('Project Part') or '').strip()
            deps = [d.strip() for d in (r.get('Dependencies') or '').split(',') if d.strip()]
            graph[n] = deps
            try: duration[n] = int(r.get('Duration (days)') or 0)
            except Exception: duration[n] = 0
            sd = _parse_mmddyyyy(r.get('Start Date') or '')
            if sd and (min_date is None or sd < min_date):
                min_date = sd
        visited=set(); order=[]
        def dfs(n):
            if n in visited: return
            for d in graph.get(n, []): dfs(d)
            visited.add(n); order.append(n)
        for n in graph: dfs(n)
        base_min = min_date or _dt2.date.today()
        earliest_finish: Dict[str, _dt2.date] = {}
        earliest_start: Dict[str, _dt2.date] = {}
        for n in order:
            deps = graph.get(n, [])
            if not deps:
                s = _parse_mmddyyyy(name_to_row.get(n, {}).get('Start Date') or '')
                earliest_start[n] = s or base_min
            else:
                earliest_start[n] = max([earliest_finish.get(d, base_min) for d in deps]) if deps else base_min
            earliest_finish[n] = earliest_start[n] + _dt2.timedelta(days=max(0, duration.get(n,0)))
        project_finish = max(earliest_finish.values()) if earliest_finish else base_min
        latest_start: Dict[str, _dt2.date] = {}
        latest_finish: Dict[str, _dt2.date] = {}
        for n in reversed(order):
            succ = [k for k, v in graph.items() if n in v]
            latest_finish[n] = min([latest_start[s] for s in succ]) if succ else project_finish
            latest_start[n] = latest_finish[n] - _dt2.timedelta(days=max(0, duration.get(n,0)))
        critical_path = [n for n in order if abs((earliest_start[n]-latest_start[n]).days) <= 0]
        # Critical percent (leaf-only intersect critical)
        crit_leafs = [r for r in leafs if (r.get('Project Part') or '').strip() in set(critical_path)]
        c_w = 0; c_wp = 0
        for r in crit_leafs:
            try: dur = int(r.get('Duration (days)') or 0)
            except Exception: dur = 0
            try: pc = int(r.get('% Complete') or 0)
            except Exception: pc = 0
            c_w += max(0, dur)
            c_wp += pc * max(0, dur)
        critical_percent = (c_wp / c_w) if c_w else 0.0
    except Exception:
        critical_path = []
        critical_percent = 0.0
    data = {
        'overall_percent': round(overall, 1),
        'critical_percent': round(critical_percent, 1),
        'leaf_count': len(leafs),
        'done_count': done,
        'overdue': overdue,
        'at_risk': at_risk,
        'critical_leaf_count': len(crit_leafs) if 'crit_leafs' in locals() else 0,
        'status_counts': status_counts,
        'overdue_list': [],
        'at_risk_list': [],
        'critical_path': critical_path,
    }
    # Lists (limit to names)
    overdue_list=[]; at_risk_list=[]
    for r in leafs:
        name = (r.get('Project Part') or '').strip()
        if not name: continue
        try: dur = int(r.get('Duration (days)') or 0)
        except Exception: dur = 0
        try: pc = int(r.get('% Complete') or 0)
        except Exception: pc = 0
        st = (r.get('Status') or '').strip()
        end_s = (r.get('Calculated End Date') or '').strip()
        start_s = (r.get('Start Date') or '').strip()
        end_dt = _parse_mmddyyyy(end_s)
        start_dt = _parse_mmddyyyy(start_s)
        if pc < 100 and end_dt and _dt.date.today() > end_dt:
            overdue_list.append(name)
        elif pc == 0 and start_dt and _dt.date.today() > start_dt and st in ('Planned','Blocked'):
            at_risk_list.append(name)
    data['overdue_list'] = overdue_list
    data['at_risk_list'] = at_risk_list
    return jsonify(data)

@app.route('/api/costs')
def api_costs():
    rows = _normalize_db_rows(_fetch_rows())
    leafs = _leaf_rows(rows)
    out = []
    # Compute totals
    total_price_sum = 0.0
    for r in leafs:
        try: pcost = float(r.get('Production Cost') or 0)
        except Exception: pcost = 0.0
        try: icost = float(r.get('Installation Cost') or 0)
        except Exception: icost = 0.0
        try: pprice = float(r.get('Production Price') or 0)
        except Exception: pprice = 0.0
        try: iprice = float(r.get('Installation Price') or 0)
        except Exception: iprice = 0.0
        total_price_sum += (pprice + iprice)
    for r in leafs:
        name = (r.get('Project Part') or '').strip()
        parent = (r.get('Parent') or '').strip()
        try: pcost = float(r.get('Production Cost') or 0)
        except Exception: pcost = 0.0
        try: icost = float(r.get('Installation Cost') or 0)
        except Exception: icost = 0.0
        try: pprice = float(r.get('Production Price') or 0)
        except Exception: pprice = 0.0
        try: iprice = float(r.get('Installation Price') or 0)
        except Exception: iprice = 0.0
        total_cost = pcost + icost
        total_price = pprice + iprice
        profit = total_price - total_cost
        margin_pct = (profit / total_price * 100.0) if total_price else 0.0
        pct_of_total = (total_price / total_price_sum * 100.0) if total_price_sum else 0.0
        out.append({
            'Project Part': name,
            'Parent': parent,
            'Prod Cost': round(pcost,2),
            'Inst Cost': round(icost,2),
            'Total Cost': round(total_cost,2),
            'Prod Price': round(pprice,2),
            'Inst Price': round(iprice,2),
            'Total Price': round(total_price,2),
            'Profit $': round(profit,2),
            'Margin %': round(margin_pct,1),
            '% of Total Price': round(pct_of_total,1),
        })
    return jsonify({ 'columns': ['Project Part','Parent','Prod Cost','Inst Cost','Total Cost','Prod Price','Inst Price','Total Price','Profit $','Margin %','% of Total Price'], 'rows': out })

# Images root + serving

def images_root():
    o = os.environ.get('WEB_IMAGES_ROOT','').strip()
    return o or os.path.join(repo_root(), 'images')

@app.route('/images/<path:filename>')
def serve_image(filename: str):
    # Securely serve files from images_root, allowing subfolders; reject traversal
    if filename.startswith('/') or '\\' in filename or '..' in filename.split('/'):
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
