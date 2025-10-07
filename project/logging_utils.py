import json, os, datetime, socket, getpass, threading

def log_event(category: str, event: str, **fields):
    try:
        rec = {
            "ts": datetime.datetime.utcnow().isoformat(timespec='seconds')+'Z',
            "user": getpass.getuser(),
            "host": socket.gethostname(),
            "pid": os.getpid(),
            "thread": threading.current_thread().name,
            "category": category,
            "event": event
        }
        rec.update({k:(v if isinstance(v,(int,float,str,bool)) else repr(v)) for k,v in fields.items()})
        base = os.path.dirname(os.path.abspath(__file__))
        log_path = os.path.join(base, '..', 'app.log')
        if os.path.exists(log_path) and os.path.getsize(log_path) > 1_000_000:
            bak = log_path + '.1'
            try:
                if os.path.exists(bak): os.remove(bak)
                os.replace(log_path, bak)
            except Exception:
                pass
        with open(log_path, 'a', encoding='utf-8') as f:
            f.write(json.dumps(rec, ensure_ascii=False)+'\n')
    except Exception:
        pass