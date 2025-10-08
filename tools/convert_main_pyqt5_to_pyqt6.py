"""Automated one-off converter to replace inline 'from PyQt5.*' imports in main.py with PyQt6.

Safe approach:
 - Reads main.py
 - Replaces occurrences of 'from PyQt5.' with 'from PyQt6.'
 - Does NOT touch other text (logging/history)
 - Writes back only if changes occurred.
"""
from __future__ import annotations
import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[1]
TARGET = ROOT / 'main.py'

def main():
    text = TARGET.read_text(encoding='utf-8')
    new_text = text.replace('from PyQt5.', 'from PyQt6.')
    # Also handle rare 'import PyQt5' forms if any (not expected in main.py now)
    new_text = new_text.replace('import PyQt5', 'import PyQt6')
    if new_text != text:
        TARGET.write_text(new_text, encoding='utf-8')
        print('[convert] Updated main.py PyQt5->PyQt6 inline imports.')
    else:
        print('[convert] No changes needed.')

if __name__ == '__main__':
    main()
