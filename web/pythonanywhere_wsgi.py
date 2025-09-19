import os, sys

# Expected repo layout on PythonAnywhere
#   ~/Aja_au_Grimace/           (project root)
#   ~/Aja_au_Grimace/web        (Flask app dir)
#   ~/Aja_au_Grimace/project_data.db (optional local DB)

PROJECT_ROOT = os.path.expanduser('~/Aja_au_Grimace')
WEB_DIR = os.path.join(PROJECT_ROOT, 'web')

if PROJECT_ROOT not in sys.path:
    sys.path.append(PROJECT_ROOT)
if WEB_DIR not in sys.path:
    sys.path.append(WEB_DIR)

# Optionally pin DB location here (or use PA Env Vars page)
# os.environ['PROJECT_DB_PATH'] = '/home/youruser/path/to/project_data.db'
# os.environ['WEB_SQLITE_RO'] = '1'

os.chdir(WEB_DIR)
try:
    from bootcheck import log_startup
    log_startup()
except Exception as e:
    # Avoid breaking app on bootcheck issues
    print(f"[bootcheck] skipped: {e}")
from app import app as application
