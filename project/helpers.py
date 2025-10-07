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