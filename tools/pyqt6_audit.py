import re, sys, pathlib, json
ROOT = pathlib.Path('.')
SKIP = {'.venv','dist','build','__pycache__','tools'}
PATTERNS = {
    r'\bexec_\b': 'Use .exec()',
    r'QGraphicsView\.ScrollHandDrag': 'Use QGraphicsView.DragMode.ScrollHandDrag',
    r'\bNoEditTriggers\b': 'Use QAbstractItemView.EditTrigger.NoEditTriggers',
    r'\bSelectRows\b': 'Use SelectionBehavior.SelectRows',
    r'\bSingleSelection\b': 'Use SelectionMode.SingleSelection',
    r'QDialog\.(Accepted|Rejected)\b': 'Use QDialog.DialogCode.Accepted/Rejected',
    r'Qt\.Align[A-Z]\w*': 'Use Qt.AlignmentFlag.*',
    r'Qt\.(Checked|Unchecked|PartiallyChecked)\b': 'Use Qt.CheckState.*',
    r'Qt\.PointingHandCursor': 'Use Qt.CursorShape.PointingHandCursor',
    r'Qt\.ItemIs\w+': 'Use Qt.ItemFlag.*'
}
results=[]
for p in ROOT.rglob('*.py'):
    if any(part in SKIP for part in p.parts): continue
    text = p.read_text(encoding='utf-8', errors='ignore')
    for pat, msg in PATTERNS.items():
        for m in re.finditer(pat, text):
            line_no = text.count('\n', 0, m.start())+1
            results.append({'file': str(p), 'line': line_no, 'match': m.group(0), 'hint': msg})
print(json.dumps(results, indent=2))
if not results:
    print("No legacy patterns found.")