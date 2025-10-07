import re, json, pathlib

ROOT = pathlib.Path('.')
SKIP_DIRS = {'.venv','dist','build','__pycache__','tools'}  # skip tooling scripts themselves
RESULTS = []

# Patterns target only legacy forms (not already using Enum groups)
CHECKS = {
    r'QGraphicsView\.(?!DragMode\.)ScrollHandDrag': "Use QGraphicsView.DragMode.ScrollHandDrag",
    r'(?<!EditTrigger\.)\bNoEditTriggers\b': "Use QAbstractItemView.EditTrigger.NoEditTriggers",
    r'(?<!SelectionBehavior\.)\bSelectRows\b': "Use QAbstractItemView.SelectionBehavior.SelectRows",
    r'(?<!SelectionMode\.)\bSingleSelection\b': "Use QAbstractItemView.SelectionMode.SingleSelection",
    r'\bexec_\b': "Replace exec_() with exec() (remove comments too)",
    r'Qt\.ScrollBarAlwaysOff\b': "Use Qt.ScrollBarPolicy.ScrollBarAlwaysOff",
    r'Qt\.ScrollBarAlwaysOn\b': "Use Qt.ScrollBarPolicy.ScrollBarAlwaysOn",
    r'Qt\.ScrollBarAsNeeded\b': "Use Qt.ScrollBarPolicy.ScrollBarAsNeeded",
}

def scan_file(p: pathlib.Path):
    text = p.read_text(encoding='utf-8', errors='ignore')
    lines = text.splitlines()
    for idx, line in enumerate(lines, 1):
        stripped = line.strip()
        if stripped.startswith('#'):  # ignore pure comments
            continue
        for pat, hint in CHECKS.items():
            for m in re.finditer(pat, line):
                RESULTS.append({
                    "file": str(p),
                    "line": idx,
                    "match": m.group(0),
                    "hint": hint
                })

for py in ROOT.rglob('*.py'):
    if any(d in SKIP_DIRS for d in py.parts):
        continue
    scan_file(py)

if RESULTS:
    print(json.dumps(RESULTS, indent=2))
else:
    print("[]")