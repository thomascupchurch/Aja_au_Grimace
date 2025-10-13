# Make v2 a package so WSGI can import `v2.app:app`
from .app import app  # re-export for convenience
