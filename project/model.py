"""Model extraction shim.

Tests historically imported ProjectDataModel from main.py (monolithic). During
modularization we provide this thin wrapper that re-exports the full
ProjectDataModel defined in main.py without duplicating thousands of lines of
logic. This keeps a single source of truth and preserves the expected no-arg
constructor used by existing tests (which set DB_FILE manually afterward).

If in the future the large class is relocated into this module permanently,
simply replace this shim with the actual implementation and remove the import.
"""

from importlib import import_module

_cached_cls = None

def _resolve():  # Lazy to break circular import during main module initialization
	global _cached_cls
	if _cached_cls is None:
		_main = import_module('main')
		_cached_cls = getattr(_main, 'ProjectDataModel')
	return _cached_cls

class ProjectDataModel:  # type: ignore
	def __new__(cls, *a, **k):
		real_cls = _resolve()
		obj = real_cls.__new__(real_cls)  # noqa: B020
		real_cls.__init__(obj, *a, **k)
		return obj

__all__ = ["ProjectDataModel"]