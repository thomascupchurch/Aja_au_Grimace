import importlib
import json
import sys
from pathlib import Path

THIS_DIR = Path(__file__).resolve().parent
ROOT = THIS_DIR.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# List test module base names (without .py)
TEST_MODULES = [
    "test_layout_roundtrip",
    "test_lock_status",
    "test_selected_only_export",
    "test_xlsx_selected_subset",
]

def main():
    results = []
    for name in TEST_MODULES:
        fq = f"tests.{name}"
        try:
            m = importlib.import_module(fq)
            fn = getattr(m, "main", None)
            if callable(fn):
                fn()
            results.append({"module": name, "status": "ok"})
        except Exception as e:
            import traceback
            results.append({
                "module": name,
                "error": str(e),
                "trace": traceback.format_exc(),
            })
    print(json.dumps(results, indent=2))

if __name__ == "__main__":
    main()
