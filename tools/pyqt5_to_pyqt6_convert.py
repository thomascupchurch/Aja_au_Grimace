import re
import sys
import argparse
from pathlib import Path

SKIP_DIRS = {".venv", "dist", "build", "__pycache__"}
PY_EXT = ".py"

# Ordered replacements (literal)
IMPORT_PATTERNS = [
    (r"\bfrom\s+PyQt5\s+import\s+", "from PyQt6 import "),
    (r"\bfrom\s+PyQt5\.(Qt\w+)\s+import\s+", r"from PyQt6.\1 import "),
    (r"\bimport\s+PyQt5\b", "import PyQt6"),
    (r"\bPyQt5\.", "PyQt6."),
]

# exec_ -> exec
EXEC_PATTERNS = [
    (r"(\bQApplication\s*\.\s*)exec_", r"\1exec"),
    (r"(\bQDialog\s*\.\s*)exec_", r"\1exec"),
    (r"\.exec_\s*\(", ".exec("),
]

# Enum mapping: PyQt5 flat constants -> PyQt6 grouped
ENUM_MAP = {
    # Alignment
    r"\bQt\.AlignLeft\b": "Qt.AlignmentFlag.AlignLeft",
    r"\bQt\.AlignRight\b": "Qt.AlignmentFlag.AlignRight",
    r"\bQt\.AlignHCenter\b": "Qt.AlignmentFlag.AlignHCenter",
    r"\bQt\.AlignVCenter\b": "Qt.AlignmentFlag.AlignVCenter",
    r"\bQt\.AlignCenter\b": "Qt.AlignmentFlag.AlignCenter",
    r"\bQt\.AlignTop\b": "Qt.AlignmentFlag.AlignTop",
    r"\bQt\.AlignBottom\b": "Qt.AlignmentFlag.AlignBottom",
    # Orientation
    r"\bQt\.Horizontal\b": "Qt.Orientation.Horizontal",
    r"\bQt\.Vertical\b": "Qt.Orientation.Vertical",
    # Mouse buttons
    r"\bQt\.LeftButton\b": "Qt.MouseButton.LeftButton",
    r"\bQt\.RightButton\b": "Qt.MouseButton.RightButton",
    r"\bQt\.MiddleButton\b": "Qt.MouseButton.MiddleButton",
    # Keyboard modifiers
    r"\bQt\.ControlModifier\b": "Qt.KeyboardModifier.ControlModifier",
    r"\bQt\.ShiftModifier\b": "Qt.KeyboardModifier.ShiftModifier",
    r"\bQt\.AltModifier\b": "Qt.KeyboardModifier.AltModifier",
    # Keys
    r"\bQt\.Key_([A-Z0-9_]+)\b": r"Qt.Key.Key_\1",
    # Cursor shape
    r"\bQt\.PointingHandCursor\b": "Qt.CursorShape.PointingHandCursor",
    r"\bQt\.ArrowCursor\b": "Qt.CursorShape.ArrowCursor",
    # CheckState
    r"\bQt\.Checked\b": "Qt.CheckState.Checked",
    r"\bQt\.Unchecked\b": "Qt.CheckState.Unchecked",
    r"\bQt\.PartiallyChecked\b": "Qt.CheckState.PartiallyChecked",
    # Pen style
    r"\bQt\.NoPen\b": "Qt.PenStyle.NoPen",
    # Aspect / transform
    r"\bQt\.KeepAspectRatio\b": "Qt.AspectRatioMode.KeepAspectRatio",
    r"\bQt\.SmoothTransformation\b": "Qt.TransformationMode.SmoothTransformation",
    # Window / dialog codes (if used)
    r"\bQDialog\.Accepted\b": "QDialog.DialogCode.Accepted",
    r"\bQDialog\.Rejected\b": "QDialog.DialogCode.Rejected",
}

# Remove migration shim (heuristic) if requested
SHIM_START = "# (PyQt6 Shim removed)"

def find_python_files(root: Path):
    for p in root.rglob("*.py"):
        parts = set(p.parts)
        if any(d in SKIP_DIRS for d in parts):
            continue
        yield p

def apply_patterns(text: str, patterns):
    changed = text
    for pat, repl in patterns:
        changed = re.sub(pat, repl, changed)
    return changed

def apply_enum_map(text: str):
    changed = text
    for pat, repl in ENUM_MAP.items():
        changed = re.sub(pat, repl, changed)
    return changed

def remove_shim(text: str):
    if SHIM_START in text and SHIM_END in text:
        pattern = re.compile(
            re.escape(SHIM_START) + r".+?" + re.escape(SHIM_END),
            re.DOTALL
        )
        text2, n = pattern.subn("# (PyQt6 Shim removed)", text)
        return text2, n > 0
    return text, False

def process_file(path: Path, args):
    original = path.read_text(encoding="utf-8")
    updated = original

    if args.remove_shim:
        updated, _ = remove_shim(updated)

    updated = apply_patterns(updated, IMPORT_PATTERNS)
    updated = apply_patterns(updated, EXEC_PATTERNS)
    updated = apply_enum_map(updated)

    if updated != original:
        if args.dry_run:
            print(f"[DRY] Would update: {path}")
        else:
            if not args.no_backup:
                bak = path.with_suffix(path.suffix + ".bak")
                if not bak.exists():
                    bak.write_text(original, encoding="utf-8")
            path.write_text(updated, encoding="utf-8")
            print(f"[OK ] Updated: {path}")
    else:
        if args.verbose:
            print(f"[SKIP] No changes: {path}")

def main():
    ap = argparse.ArgumentParser(description="Convert PyQt5 codebase to PyQt6.")
    ap.add_argument("--root", default=".", help="Root folder (default: .)")
    ap.add_argument("--apply", action="store_true", help="Apply changes (otherwise dry-run).")
    ap.add_argument("--remove-shim", action="store_true", help="Remove migration shim block.")
    ap.add_argument("--no-backup", action="store_true", help="Do not create .bak backups.")
    ap.add_argument("--verbose", action="store_true", help="Verbose unchanged info.")
    ap.add_argument("--include", nargs="*", default=[], help="Only process paths containing any of these substrings.")
    ap.add_argument("--exclude", nargs="*", default=[], help="Exclude files containing these substrings.")
    ap.add_argument("--ext", nargs="*", default=[PY_EXT], help="Extensions to process (default .py)")
    ap.add_argument("--dry-run", action="store_true", help="Alias for not specifying --apply.")
    args = ap.parse_args()

    if args.apply:
        args.dry_run = False
    else:
        args.dry_run = True

    root = Path(args.root).resolve()
    count = 0
    for f in find_python_files(root):
        if args.include and not any(s in str(f) for s in args.include):
            continue
        if args.exclude and any(s in str(f) for s in args.exclude):
            continue
        if f.suffix not in args.ext:
            continue
        process_file(f, args)
        count += 1
    print(f"Scanned {count} file(s). Mode={'APPLY' if not args.dry_run else 'DRY-RUN'}")

if __name__ == "__main__":
    main()