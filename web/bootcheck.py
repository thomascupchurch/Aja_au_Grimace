import os, sys, socket

def log_startup():
    # Print a concise line to the WSGI server's logs to help verify env and paths
    db = os.environ.get('PROJECT_DB_PATH', '(unset)')
    ro = os.environ.get('WEB_SQLITE_RO', '(unset)')
    wd = os.getcwd()
    host = socket.gethostname()
    py = sys.version.split()[0]
    print(f"[bootcheck] host={host} py={py} cwd={wd} PROJECT_DB_PATH={db} WEB_SQLITE_RO={ro}")
