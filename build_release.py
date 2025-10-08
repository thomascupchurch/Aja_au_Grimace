#!/usr/bin/env python3
"""
Enhanced build script with:
 - Multi-size icon generation from SVG (header.svg) or PNG fallback using Pillow (and optional cairosvg)
 - CLI flags for dry-run, custom icon source/output, skip icon, mac bundle toggle
 - Placeholder for future Pillow self-test & mac bundle logic
"""
import os, sys, shutil, subprocess, argparse, tempfile, datetime, hashlib

DEFAULT_ICON_SIZES = [16,24,32,48,64,128,256,512]

def log(msg):
    print(f"[build] {msg}")

def sha256_file(path):
    h = hashlib.sha256()
    with open(path,'rb') as f:
        for chunk in iter(lambda: f.read(65536), b''):
            h.update(chunk)
    return h.hexdigest()

def rasterize_svg_to_png_bytes(svg_path, size):
    """Return PNG bytes for the given square size.
    Tries cairosvg; falls back to Pillow via QImage-like approach not available here (so require cairosvg for SVG).
    """
    try:
        import cairosvg  # type: ignore
        return cairosvg.svg2png(url=svg_path, output_width=size, output_height=size)
    except Exception as e:
        raise RuntimeError(f"SVG rasterization requires cairosvg (size {size}): {e}")

def generate_multi_icon(source, out_path, sizes=DEFAULT_ICON_SIZES, dry_run=False):
    """Generate a multi-resolution .ico file from an SVG or raster image.
    If source is SVG -> per-size rasterization (cairosvg). If raster -> single open & resize.
    """
    from pathlib import Path
    src = Path(source)
    if not src.exists():
        raise FileNotFoundError(f"Icon source not found: {source}")
    ext = src.suffix.lower()
    from PIL import Image  # Pillow
    images = []
    if ext == '.svg':
        for sz in sizes:
            png_bytes = rasterize_svg_to_png_bytes(str(src), sz)
            with Image.open(tempfile.SpooledTemporaryFile()) as im:  # placeholder open to keep API consistent
                pass
            # Need to reopen from bytes realistically
            import io
            im = Image.open(io.BytesIO(png_bytes))
            im.load()
            if im.mode not in ('RGBA','LA'):
                im = im.convert('RGBA')
            images.append(im)
    else:
        base = Image.open(str(src))
        base.load()
        if base.mode not in ('RGBA','LA'):
            base = base.convert('RGBA')
        for sz in sizes:
            images.append(base.resize((sz,sz)))
    # First image save with .save and append sizes via save; Pillow collects sizes automatically if we pass sizes param.
    if dry_run:
        log(f"DRY-RUN would write icon with sizes: {[im.size for im in images]} -> {out_path}")
        return out_path
    out_dir = os.path.dirname(os.path.abspath(out_path))
    if out_dir and not os.path.exists(out_dir):
        os.makedirs(out_dir, exist_ok=True)
    # Pillow expects a single base image; pass sizes list to save
    base_im = images[0]
    other_sizes = [im.size for im in images[1:]]
    base_im.save(out_path, format='ICO', sizes=other_sizes)
    log(f"Icon generated: {out_path} ({len(images)} sizes)")
    return out_path

def parse_args(argv=None):
    p = argparse.ArgumentParser(description="Build ProjectPlanner with enhanced options.")
    p.add_argument('--name', default='ProjectPlanner', help='Executable/app name')
    p.add_argument('--onefile', action='store_true', help='Force one-file build')
    p.add_argument('--no-onefile', dest='onefile', action='store_false', help='Disable one-file build')
    p.set_defaults(onefile=True)
    p.add_argument('--mac-bundle', action='store_true', help='Create macOS .app bundle (on macOS only)')
    p.add_argument('--icon-source', default='header.svg', help='Path to SVG/PNG icon source')
    p.add_argument('--icon-out', default='build/generated/icon.ico', help='Output .ico path (Windows)')
    p.add_argument('--skip-icon', action='store_true', help='Skip icon generation step')
    p.add_argument('--dry-run', action='store_true', help='Print actions without executing PyInstaller or writing outputs')
    p.add_argument('--clean', action='store_true', help='Remove previous build/dist before building')
    p.add_argument('--extra-pyinstaller-arg', action='append', default=[], help='Additional arg(s) to pass to pyinstaller (repeatable)')
    p.add_argument('--noconsole', action='store_true', help='Add --noconsole to PyInstaller (Windows GUI)')
    p.add_argument('--skip-pillow-self-test', action='store_true', help='Skip the Pillow image pipeline self-test')
    p.add_argument('--force-pillow-self-test', action='store_true', help='Force running the Pillow self-test even if skipped elsewhere')
    return p.parse_args(argv)

def build(args):
    platform = 'Windows' if sys.platform.startswith('win') else 'Mac'
    out_release_dir = os.path.join('release', platform)
    # --- Pillow self-test ---
    def pillow_self_test():
        try:
            from PIL import Image, ImageDraw
            import io, tempfile
            im = Image.new('RGBA', (64,64), (10,20,30,255))
            d = ImageDraw.Draw(im)
            d.rectangle([8,8,56,56], outline=(200,180,40,255), width=3)
            d.text((12,24), 'PP', fill=(255,255,255,255))
            bio = io.BytesIO()
            im.save(bio, format='PNG')
            bio.seek(0)
            im2 = Image.open(bio)
            im2.load()
            if im2.size != (64,64):
                raise RuntimeError('Round-trip size mismatch')
            # Disk write test (ensures filesystem path OK)
            tmp_dir = os.path.join('build','selftest')
            os.makedirs(tmp_dir, exist_ok=True)
            tmp_png = os.path.join(tmp_dir,'selftest.png')
            im2.save(tmp_png, format='PNG')
            if not os.path.exists(tmp_png):
                raise RuntimeError('Failed to write self-test image to disk')
            log('Pillow self-test passed')
        except Exception as e:
            log(f'ERROR: Pillow self-test failed: {e}')
            raise
    run_self_test = (not args.skip_pillow_self_test) or args.force_pillow_self_test
    if run_self_test:
        try:
            if args.dry_run:
                log('DRY-RUN: would execute Pillow self-test')
            else:
                pillow_self_test()
        except Exception:
            log('Aborting build due to Pillow self-test failure')
            if not args.dry_run:
                raise
    if args.clean and not args.dry_run:
        for d in ('build','dist'):
            if os.path.exists(d):
                log(f"Removing {d}/")
                shutil.rmtree(d)
    # Icon generation (Windows focus; still produce .ico for consistency even on mac for potential cross-packaging)
    icon_path = None
    if not args.skip_icon:
        try:
            icon_path = generate_multi_icon(args.icon_source, args.icon_out, dry_run=args.dry_run)
        except Exception as e:
            log(f"WARN: Icon generation failed ({e}); continuing without custom icon.")
            icon_path = None
    # Construct PyInstaller command
    cmd = ['pyinstaller']
    if args.onefile:
        cmd.append('--onefile')
    else:
        # onedir mode implicit
        pass
    if platform == 'Windows':
        cmd.append('--windowed')
    name = args.name
    cmd += ['--name', name]
    if icon_path and platform == 'Windows':
        cmd += ['--icon', icon_path]
    if args.noconsole:
        cmd.append('--noconsole')
    cmd += args.extra_pyinstaller_arg
    cmd.append('main.py')
    log(f"PyInstaller command: {' '.join(cmd)}")
    if not args.dry_run:
        subprocess.run(cmd, check=True)
    else:
        log("DRY-RUN: skipping PyInstaller execution")
    # Output relocation
    if not args.dry_run:
        os.makedirs(out_release_dir, exist_ok=True)
        if platform == 'Windows':
            exe_src = os.path.join('dist', f'{name}.exe')
            if os.path.exists(exe_src):
                shutil.copy2(exe_src, out_release_dir)
        else:
            # For mac builds, copy .app (if created)
            app_src = os.path.join('dist', f'{name}.app')
            if os.path.exists(app_src):
                dest_app = os.path.join(out_release_dir, f'{name}.app')
                if os.path.exists(dest_app):
                    shutil.rmtree(dest_app)
                shutil.copytree(app_src, dest_app)
        # Copy version file if present
        if os.path.exists('VERSION'):
            shutil.copy2('VERSION', out_release_dir)
        log(f"Build artifacts staged in {out_release_dir}")
    else:
        log(f"DRY-RUN: would stage build artifacts in {out_release_dir}")

def main(argv=None):
    args = parse_args(argv)
    build(args)

if __name__ == '__main__':
    main()