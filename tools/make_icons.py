#!/usr/bin/env python
"""
make_icons.py

Deterministically generate header.ico (multi-size) and optionally header.icns (macOS) from
header.svg (preferred) or header.png fallback.

Usage:
  python tools/make_icons.py [--force] [--icns] [--sizes 16,24,32,48,64,128,256]

Behavior:
- If header.svg exists it is rasterized at the requested sizes.
- Else if header.png exists it is resized/downsampled (maintaining aspect) to each size.
- Produces header.ico containing all sizes (nearest <= source size if using PNG fallback).
- With --icns (on macOS) creates AppIcon.iconset/ + header.icns.
- Skips regeneration if header.ico exists and is newer than source unless --force.

Dependencies:
- Pillow (required)
- cairosvg (optional) for higher fidelity SVG rasterization; falls back to QtSvg via PyQt6/5 if available then rsvg-convert if present in PATH.

Exit codes: 0 success, 1 recoverable (e.g., source missing), >1 unexpected error.
"""
from __future__ import annotations
import argparse, os, sys, io, time, subprocess, platform
from datetime import datetime

ICO_DEFAULT_SIZES = [16,24,32,48,64,128,256]

try:
    from PIL import Image
except Exception as e:  # pragma: no cover
    print("[make_icons] Pillow not installed; cannot proceed.", file=sys.stderr)
    sys.exit(2)

def svg_to_png_bytes(svg_path: str, size: int) -> bytes | None:
    """Attempt to rasterize an SVG to PNG bytes at square size.
    Tries cairosvg, then PyQt (QtSvg), then rsvg-convert command.
    Returns bytes or None on failure."""
    # 1. CairoSVG
    try:
        import cairosvg  # type: ignore
        return cairosvg.svg2png(url=svg_path, output_width=size, output_height=size)
    except Exception:
        pass
    # 2. PyQt QtSvg fallback
    try:
        from PyQt6 import QtSvg, QtGui
        from PyQt6.QtGui import QImage
        from PyQt6.QtCore import QSize, QRectF, QBuffer, QIODevice
        renderer = QtSvg.QSvgRenderer(svg_path)
        if renderer.isValid():
            img = QImage(size, size, QImage.Format.Format_ARGB32)
            img.fill(0)
            painter = QtGui.QPainter(img)
            renderer.render(painter, QRectF(0,0,size,size))
            painter.end()
            buf = QBuffer(); buf.open(QIODevice.OpenModeFlag.WriteOnly)
            img.save(buf, b"PNG")
            return bytes(buf.data())
    except Exception:
        pass
    # 3. rsvg-convert CLI
    try:
        cmd = ["rsvg-convert", "-w", str(size), "-h", str(size), svg_path]
        return subprocess.check_output(cmd)
    except Exception:
        return None

def timestamp(path: str) -> float:
    try: return os.path.getmtime(path)
    except OSError: return 0.0

def needs_rebuild(out_path: str, sources: list[str], force: bool) -> bool:
    if force or not os.path.exists(out_path):
        return True
    out_ts = timestamp(out_path)
    return any(timestamp(s) > out_ts for s in sources if os.path.exists(s))

def build_ico(svg_path: str | None, png_path: str | None, sizes: list[int], force: bool) -> bool:
    sources = [p for p in [svg_path, png_path] if p]
    if not needs_rebuild("header.ico", sources, force):
        print("[make_icons] header.ico up-to-date")
        return True
    if not sources:
        print("[make_icons] No header.svg or header.png found; skipping.")
        return False
    images: list[Image.Image] = []
    if svg_path and os.path.exists(svg_path):
        for sz in sizes:
            data = svg_to_png_bytes(svg_path, sz)
            if data is None:
                print(f"[make_icons] SVG rasterize failed at {sz}px; falling back to PNG if available.")
                break
            img = Image.open(io.BytesIO(data)).convert("RGBA")
            images.append(img)
        else:
            # Completed all sizes via SVG
            images.sort(key=lambda im: im.size[0])
            images[0].save("header.ico", sizes=[im.size for im in images])
            print(f"[make_icons] Wrote header.ico ({len(images)} sizes) from SVG")
            return True
        # Fallback continues to PNG logic below
    if png_path and os.path.exists(png_path):
        base = Image.open(png_path).convert("RGBA")
        w, h = base.size
        for sz in sizes:
            # Avoid upscaling by more than 2x excessively: we still allow for quality
            if sz > max(w,h)*2:
                continue
            img = base.copy()
            img.thumbnail((sz, sz), Image.LANCZOS)
            if img.size != (sz, sz):
                # pad to square
                canvas = Image.new("RGBA", (sz, sz), (0,0,0,0))
                ox = (sz - img.size[0])//2
                oy = (sz - img.size[1])//2
                canvas.paste(img, (ox, oy))
                img = canvas
            images.append(img)
        if not images:
            print("[make_icons] PNG too small to produce any sizes.")
            return False
        images.sort(key=lambda im: im.size[0])
        images[0].save("header.ico", sizes=[im.size for im in images])
        print(f"[make_icons] Wrote header.ico ({len(images)} sizes) from PNG fallback")
        return True
    print("[make_icons] No suitable source to build ICO.")
    return False

def build_icns(svg_path: str | None, png_path: str | None, sizes: list[int], force: bool) -> bool:
    if platform.system() != "Darwin":
        print("[make_icons] --icns requested but not on macOS; skipping.")
        return False
    if not (svg_path and os.path.exists(svg_path)) and not (png_path and os.path.exists(png_path)):
        print("[make_icons] No source image for icns.")
        return False
    if not needs_rebuild("header.icns", [p for p in [svg_path, png_path] if p], force):
        print("[make_icons] header.icns up-to-date")
        return True
    import shutil
    iconset = "AppIcon.iconset"
    if os.path.isdir(iconset):
        shutil.rmtree(iconset)
    os.makedirs(iconset, exist_ok=True)
    # Use ICO build logic intermediate images (rasterize once per size)
    tmp_imgs: list[tuple[int, Image.Image]] = []
    if svg_path and os.path.exists(svg_path):
        for sz in sizes:
            data = svg_to_png_bytes(svg_path, sz)
            if data is None:
                break
            tmp_imgs.append((sz, Image.open(io.BytesIO(data)).convert("RGBA")))
    if not tmp_imgs and png_path and os.path.exists(png_path):
        base = Image.open(png_path).convert("RGBA")
        for sz in sizes:
            img = base.copy(); img.thumbnail((sz, sz), Image.LANCZOS)
            canvas = Image.new("RGBA", (sz, sz), (0,0,0,0))
            ox = (sz - img.size[0])//2; oy = (sz - img.size[1])//2
            canvas.paste(img, (ox, oy)); tmp_imgs.append((sz, canvas))
    if not tmp_imgs:
        print("[make_icons] Could not produce any PNGs for icns.")
        return False
    for sz, img in tmp_imgs:
        img.save(f"{iconset}/icon_{sz}x{sz}.png")
        if sz in (16,32,64,128,256,512):
            # Provide @2x variants
            x2 = img.resize((sz*2, sz*2), Image.LANCZOS)
            x2.save(f"{iconset}/icon_{sz}x{sz}@2x.png")
    try:
        subprocess.check_call(["iconutil", "-c", "icns", iconset])
        if os.path.exists("AppIcon.icns"):
            os.replace("AppIcon.icns", "header.icns")
        print("[make_icons] Wrote header.icns")
        return True
    except Exception as e:
        print(f"[make_icons] iconutil failed: {e}")
        return False

def main():
    ap = argparse.ArgumentParser(description="Generate multi-size header.ico and optionally header.icns")
    ap.add_argument("--force", action="store_true", help="Force regeneration even if up-to-date")
    ap.add_argument("--icns", action="store_true", help="Also build header.icns (macOS only)")
    ap.add_argument("--sizes", default=','.join(map(str, ICO_DEFAULT_SIZES)), help="Comma list of square sizes")
    args = ap.parse_args()
    try:
        sizes = [int(s.strip()) for s in args.sizes.split(',') if s.strip()]
    except ValueError:
        print("[make_icons] Invalid --sizes list", file=sys.stderr)
        return 2
    svg_path = 'header.svg' if os.path.exists('header.svg') else None
    png_path = 'header.png' if os.path.exists('header.png') else None
    ok_ico = build_ico(svg_path, png_path, sizes, args.force)
    ok_icns = True
    if args.icns:
        ok_icns = build_icns(svg_path, png_path, sizes, args.force)
    return 0 if (ok_ico and (ok_icns or not args.icns)) else 1

if __name__ == '__main__':
    sys.exit(main())
