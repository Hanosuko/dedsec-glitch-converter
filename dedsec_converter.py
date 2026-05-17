#!/usr/bin/env python3
"""
██████╗ ███████╗██████╗ ███████╗███████╗ ██████╗
██╔══██╗██╔════╝██╔══██╗██╔════╝██╔════╝██╔════╝
██║  ██║█████╗  ██║  ██║███████╗█████╗  ██║
██║  ██║██╔══╝  ██║  ██║╚════██║██╔══╝  ██║
██████╔╝███████╗██████╔╝███████║███████╗╚██████╗
╚═════╝ ╚══════╝╚═════╝ ╚══════╝╚══════╝ ╚═════╝

DEDSEC / 1-BIT GLITCH STYLE CONVERTER
Bitmap cyberpunk aesthetic. Digital dystopia. Cyber rebellion.

Usage:
  python dedsec_converter.py --input <file> [options]
  python dedsec_converter.py --gui

Options:
  --input FILE          Input image or video file
  --output FILE         Output file path (auto-generated if not set)
  --output-format EXT   Output format, for example png, webp, mp4, avi
  --dither METHOD       Dithering: floyd, ordered, atkinson, none (default: floyd)
  --glitch LEVEL        Glitch intensity: 0.0–1.0 (default: 0.5)
  --scanlines           Enable CRT scanline overlay
  --vhs                 Enable VHS noise/distortion
  --dispersion          Enable pixel dispersion
  --datamosh            Enable datamosh artifacts
  --fps FPS             Output FPS for video (default: source FPS)
  --gui                 Launch local browser GUI
"""

import argparse

import os

import sys

import random

import time

import threading

from pathlib import Path

import cv2

import numpy as np

from PIL import Image, ImageFilter, ImageDraw, ImageOps

IMAGE_INPUT_EXTS = {
    ".jpg", ".jpeg", ".png", ".bmp", ".dib", ".tif", ".tiff", ".webp",
    ".jp2", ".j2k", ".pbm", ".pgm", ".ppm", ".pxm", ".pnm", ".sr",
    ".ras", ".tga", ".gif", ".ico", ".avif",
}

IMAGE_OUTPUT_EXTS = {
    ".jpg", ".jpeg", ".png", ".bmp", ".tif", ".tiff", ".webp",
    ".jp2", ".ppm", ".pgm", ".pbm", ".tga",
}

VIDEO_INPUT_EXTS = {
    ".mp4", ".avi", ".mov", ".mkv", ".webm", ".flv", ".m4v", ".mpg",
    ".mpeg", ".wmv", ".3gp", ".ts", ".mts", ".m2ts",
}

VIDEO_OUTPUT_CODECS = {
    ".mp4": "mp4v",
    ".m4v": "mp4v",
    ".mov": "mp4v",
    ".avi": "XVID",
    ".mkv": "XVID",
    ".webm": "VP80",
}

WEB_IMAGE_ACCEPT = ",".join(sorted(IMAGE_INPUT_EXTS)) + ",image/*"
WEB_VIDEO_ACCEPT = ",".join(sorted(VIDEO_INPUT_EXTS)) + ",video/*"

def normalize_ext(value: str, allowed: set, default: str) -> str:
    ext = (value or default).strip().lower()
    if not ext:
        ext = default
    if not ext.startswith("."):
        ext = f".{ext}"
    return ext if ext in allowed else default

def read_image_frame(input_path: str) -> np.ndarray:
    frame = cv2.imread(input_path, cv2.IMREAD_COLOR)
    if frame is not None:
        return frame
    try:
        with Image.open(input_path) as img:
            try:
                img.seek(0)
            except EOFError:
                pass
            img = ImageOps.exif_transpose(img).convert("RGB")
            return cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)
    except Exception as exc:
        raise ValueError(f"Cannot read image: {input_path}") from exc

def write_image_frame(output_path: str, frame: np.ndarray) -> None:
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    try:
        if cv2.imwrite(output_path, frame):
            return
    except cv2.error:
        pass
    ext = Path(output_path).suffix.lower()
    pil_format = {
        ".jpg": "JPEG",
        ".jpeg": "JPEG",
        ".png": "PNG",
        ".bmp": "BMP",
        ".tif": "TIFF",
        ".tiff": "TIFF",
        ".webp": "WEBP",
        ".tga": "TGA",
        ".gif": "GIF",
        ".ico": "ICO",
    }.get(ext)
    if not pil_format:
        raise ValueError(f"Unsupported output image format: {ext or '(no extension)'}")
    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    Image.fromarray(rgb).save(output_path, format=pil_format)

def apply_output_format(output_path: str, output_format: str, allowed: set, default: str) -> str:
    ext = normalize_ext(output_format, allowed, default)
    if output_path:
        return str(Path(output_path).with_suffix(ext))
    return ""

def to_grayscale(img_array: np.ndarray) -> np.ndarray:
    """Convert BGR/RGB numpy array to grayscale."""
    if len(img_array.shape) == 3:
        return cv2.cvtColor(img_array, cv2.COLOR_BGR2GRAY)
    return img_array

def apply_contrast_boost(gray: np.ndarray, strength: float = 1.8) -> np.ndarray:
    """Aggressive contrast stretch for high-impact monochrome."""
    mean = gray.mean()
    out = ((gray.astype(np.float32) - mean) * strength + mean)
    return np.clip(out, 0, 255).astype(np.uint8)

def dither_floyd_steinberg(gray: np.ndarray) -> np.ndarray:
    """Classic Floyd-Steinberg error-diffusion dithering."""
    h, w = gray.shape
    img = gray.astype(np.float32) / 255.0
    for y in range(h - 1):
        for x in range(1, w - 1):
            old = img[y, x]
            new = 1.0 if old >= 0.5 else 0.0
            img[y, x] = new
            err = old - new
            img[y,     x + 1] += err * 7 / 16
            img[y + 1, x - 1] += err * 3 / 16
            img[y + 1, x    ] += err * 5 / 16
            img[y + 1, x + 1] += err * 1 / 16
    return (np.clip(img, 0, 1) * 255).astype(np.uint8)

def dither_ordered(gray: np.ndarray, matrix_size: int = 8) -> np.ndarray:
    """Ordered (Bayer) dithering — sharp bitmap texture."""
    bayer_8 = np.array([
        [ 0, 32,  8, 40,  2, 34, 10, 42],
        [48, 16, 56, 24, 50, 18, 58, 26],
        [12, 44,  4, 36, 14, 46,  6, 38],
        [60, 28, 52, 20, 62, 30, 54, 22],
        [ 3, 35, 11, 43,  1, 33,  9, 41],
        [51, 19, 59, 27, 49, 17, 57, 25],
        [15, 47,  7, 39, 13, 45,  5, 37],
        [63, 31, 55, 23, 61, 29, 53, 21],
    ], dtype=np.float32) / 64.0
    h, w = gray.shape
    tiled = np.tile(bayer_8, (h // 8 + 1, w // 8 + 1))[:h, :w]
    norm = gray.astype(np.float32) / 255.0
    out = (norm > tiled).astype(np.uint8) * 255
    return out

def dither_atkinson(gray: np.ndarray) -> np.ndarray:
    """Atkinson dithering — Apple Mac classic look."""
    h, w = gray.shape
    img = gray.astype(np.float32) / 255.0
    for y in range(h):
        for x in range(w):
            old = img[y, x]
            new = 1.0 if old >= 0.5 else 0.0
            img[y, x] = new
            err = (old - new) / 8.0
            for dy, dx in [(0,1),(0,2),(1,-1),(1,0),(1,1),(2,0)]:
                ny, nx = y + dy, x + dx
                if 0 <= ny < h and 0 <= nx < w:
                    img[ny, nx] += err
    return (np.clip(img, 0, 1) * 255).astype(np.uint8)

def apply_dither(gray: np.ndarray, method: str = "floyd") -> np.ndarray:
    methods = {
        "floyd":    dither_floyd_steinberg,
        "ordered":  dither_ordered,
        "atkinson": dither_atkinson,
        "none":     lambda g: (g > 128).astype(np.uint8) * 255,
    }
    fn = methods.get(method, dither_floyd_steinberg)
    return fn(gray)

def apply_glitch_distortion(img: np.ndarray, intensity: float = 0.5) -> np.ndarray:
    """Horizontal slice displacement — core glitch effect."""
    h, w = img.shape[:2]
    out = img.copy()
    n_slices = int(intensity * 40) + 3
    for _ in range(n_slices):
        y = random.randint(0, h - 1)
        slice_h = random.randint(1, max(1, int(h * intensity * 0.1)))
        shift = random.randint(-int(w * intensity * 0.15), int(w * intensity * 0.15))
        y2 = min(y + slice_h, h)
        if shift > 0:
            out[y:y2, shift:] = img[y:y2, :w - shift]
            out[y:y2, :shift] = img[y:y2, w - shift:]
        elif shift < 0:
            out[y:y2, :w + shift] = img[y:y2, -shift:]
            out[y:y2, w + shift:] = img[y:y2, :-shift]
    return out

def apply_pixel_dispersion(img: np.ndarray, intensity: float = 0.5) -> np.ndarray:
    """Scatter bright pixels outward — dissolving bitmap effect."""
    h, w = img.shape[:2]
    out = img.copy()
    if len(img.shape) == 2:
        bright = np.argwhere(img > 200)
    else:
        bright = np.argwhere(img[:, :, 0] > 200)
    max_disp = int(intensity * 12) + 1
    n_pixels = min(len(bright), int(len(bright) * intensity * 0.3))
    chosen = bright[np.random.choice(len(bright), n_pixels, replace=False)] if n_pixels > 0 else []
    for (y, x) in chosen:
        ny = np.clip(y + random.randint(-max_disp, max_disp), 0, h - 1)
        nx = np.clip(x + random.randint(-max_disp, max_disp), 0, w - 1)
        if len(img.shape) == 2:
            out[ny, nx] = 255
        else:
            out[ny, nx] = [255, 255, 255]
    return out

def apply_crt_scanlines(img: np.ndarray, spacing: int = 3, opacity: float = 0.45) -> np.ndarray:
    """CRT horizontal scanlines — retro terminal feel."""
    h, w = img.shape[:2]
    mask = np.ones((h, w), dtype=np.float32)
    mask[::spacing] = 1.0 - opacity
    if len(img.shape) == 3:
        mask = mask[:, :, np.newaxis]
    return np.clip(img.astype(np.float32) * mask, 0, 255).astype(np.uint8)

def apply_vhs_noise(img: np.ndarray, intensity: float = 0.5) -> np.ndarray:
    """VHS tape noise: grain + chroma bleed simulation."""
    h, w = img.shape[:2]
    out = img.copy().astype(np.float32)
    grain = np.random.normal(0, intensity * 30, (h, w))
    if len(img.shape) == 3:
        grain = grain[:, :, np.newaxis]
    out += grain
    n_lines = int(intensity * 8)
    for _ in range(n_lines):
        y = random.randint(0, h - 1)
        lh = random.randint(1, 3)
        alpha = random.uniform(0.3, 0.8)
        out[y:y+lh] = out[y:y+lh] * (1 - alpha) + (255 * alpha)
    return np.clip(out, 0, 255).astype(np.uint8)

def apply_datamosh(img: np.ndarray, prev_frame: np.ndarray = None, intensity: float = 0.5) -> np.ndarray:
    """Datamosh: blend/warp with previous frame, block corruption."""
    h, w = img.shape[:2]
    out = img.copy()
    n_blocks = int(intensity * 20)
    block_size = max(4, int(intensity * 32))
    for _ in range(n_blocks):
        bx = random.randint(0, w - block_size)
        by = random.randint(0, h - block_size)
        sx = random.randint(0, w - block_size)
        sy = random.randint(0, h - block_size)
        out[by:by+block_size, bx:bx+block_size] = img[sy:sy+block_size, sx:sx+block_size]
    if prev_frame is not None and prev_frame.shape == img.shape:
        alpha = intensity * 0.4
        out = cv2.addWeighted(out, 1 - alpha, prev_frame, alpha, 0)
    return out

def apply_bitmap_noise(img: np.ndarray, density: float = 0.03) -> np.ndarray:
    """Sprinkle random black/white bitmap pixels — digital corruption."""
    h, w = img.shape[:2]
    out = img.copy()
    n = int(h * w * density)
    ys = np.random.randint(0, h, n)
    xs = np.random.randint(0, w, n)
    vals = np.random.choice([0, 255], n)
    if len(img.shape) == 3:
        out[ys, xs] = np.column_stack([vals, vals, vals])
    else:
        out[ys, xs] = vals
    return out

def process_frame(
    frame: np.ndarray,
    dither_method: str = "floyd",
    glitch: float = 0.5,
    scanlines: bool = True,
    vhs: bool = True,
    dispersion: bool = True,
    datamosh: bool = False,
    prev_frame: np.ndarray = None,

) -> np.ndarray:
    """Apply full DEDSEC glitch pipeline to a single frame."""
    gray = to_grayscale(frame)
    gray = apply_contrast_boost(gray, strength=1.8 + glitch * 0.6)
    dithered = apply_dither(gray, dither_method)
    bgr = cv2.cvtColor(dithered, cv2.COLOR_GRAY2BGR)
    if glitch > 0:
        bgr = apply_glitch_distortion(bgr, glitch)
    if dispersion:
        bgr = apply_pixel_dispersion(bgr, glitch * 0.7)
    if datamosh:
        bgr = apply_datamosh(bgr, prev_frame, glitch)
    bgr = apply_bitmap_noise(bgr, density=0.01 + glitch * 0.04)
    if vhs:
        bgr = apply_vhs_noise(bgr, glitch * 0.8)
        bgr_gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
        _, thresh = cv2.threshold(bgr_gray, 128, 255, cv2.THRESH_BINARY)
        bgr = cv2.cvtColor(thresh, cv2.COLOR_GRAY2BGR)
    if scanlines:
        bgr = apply_crt_scanlines(bgr, spacing=3, opacity=0.35 + glitch * 0.2)
    return bgr

def process_image(
    input_path: str,
    output_path: str,
    output_format: str = "",
    dither_method: str = "floyd",
    glitch: float = 0.5,
    scanlines: bool = True,
    vhs: bool = True,
    dispersion: bool = True,
    datamosh: bool = False,
    verbose: bool = True,

) -> str:
    if verbose:
        print(f"\n[DEDSEC] Loading image: {input_path}")
    frame = read_image_frame(input_path)
    if verbose:
        print(f"[DEDSEC] Applying glitch pipeline (intensity={glitch:.2f}, dither={dither_method})")
    result = process_frame(
        frame,
        dither_method=dither_method,
        glitch=glitch,
        scanlines=scanlines,
        vhs=vhs,
        dispersion=dispersion,
        datamosh=datamosh,
    )
    if not output_path:
        p = Path(input_path)
        suffix = normalize_ext(output_format or p.suffix, IMAGE_OUTPUT_EXTS, ".png")
        output_path = str(p.parent / f"{p.stem}_dedsec{suffix}")
    else:
        output_path = apply_output_format(output_path, output_format, IMAGE_OUTPUT_EXTS, Path(output_path).suffix or ".png")
    write_image_frame(output_path, result)
    if verbose:
        print(f"[DEDSEC] ✓ Saved: {output_path}")
    return output_path

def process_video(
    input_path: str,
    output_path: str,
    output_format: str = "",
    dither_method: str = "floyd",
    glitch: float = 0.5,
    scanlines: bool = True,
    vhs: bool = True,
    dispersion: bool = True,
    datamosh: bool = False,
    target_fps: float = None,
    progress_cb=None,
    verbose: bool = True,

) -> str:
    if verbose:
        print(f"\n[DEDSEC] Loading video: {input_path}")
    cap = cv2.VideoCapture(input_path)
    if not cap.isOpened():
        raise ValueError(f"Cannot open video: {input_path}")
    src_fps = cap.get(cv2.CAP_PROP_FPS) or 25
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fps = target_fps or src_fps
    if not output_path:
        p = Path(input_path)
        suffix = normalize_ext(output_format, set(VIDEO_OUTPUT_CODECS), ".mp4")
        output_path = str(p.parent / f"{p.stem}_dedsec{suffix}")
    else:
        output_path = apply_output_format(output_path, output_format, set(VIDEO_OUTPUT_CODECS), Path(output_path).suffix or ".mp4")
    codec = VIDEO_OUTPUT_CODECS.get(Path(output_path).suffix.lower(), "mp4v")
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    fourcc = cv2.VideoWriter_fourcc(*codec)
    writer = cv2.VideoWriter(output_path, fourcc, fps, (w, h))
    if not writer.isOpened():
        cap.release()
        raise ValueError(f"Cannot create video writer for {output_path} with codec {codec}")
    if verbose:
        print(f"[DEDSEC] {w}x{h} @ {fps:.1f}fps — {total_frames} frames")
    prev_frame = None
    frame_idx = 0
    while True:
        ret, frame = cap.read()
        if not ret:
            break
        result = process_frame(
            frame,
            dither_method=dither_method,
            glitch=glitch,
            scanlines=scanlines,
            vhs=vhs,
            dispersion=dispersion,
            datamosh=datamosh,
            prev_frame=prev_frame,
        )
        writer.write(result)
        if datamosh:
            prev_frame = result.copy()
        frame_idx += 1
        pct = frame_idx / max(total_frames, 1) * 100
        if progress_cb:
            progress_cb(pct)
        elif verbose and frame_idx % 30 == 0:
            print(f"[DEDSEC]   {pct:.1f}% ({frame_idx}/{total_frames})", end="\r")
    cap.release()
    writer.release()
    if verbose:
        print(f"\n[DEDSEC] ✓ Saved: {output_path}")
    return output_path

def run_cli(args):
    ext = Path(args.input).suffix.lower()
    is_video = ext in VIDEO_INPUT_EXTS
    output = args.output or ""
    kwargs = dict(
        dither_method=args.dither,
        glitch=args.glitch,
        scanlines=args.scanlines,
        vhs=args.vhs,
        dispersion=args.dispersion,
        datamosh=args.datamosh,
    )
    if is_video:
        process_video(args.input, output, output_format=args.output_format, target_fps=args.fps, **kwargs)
    else:
        process_image(args.input, output, output_format=args.output_format, **kwargs)

def run_gui():
    import tkinter as tk
    from tkinter import ttk, filedialog, messagebox
    from PIL import ImageTk
    BG       = "#000000"
    FG       = "#00ff41"
    FG2      = "#ffffff"
    ACCENT   = "#ff0033"
    PANEL    = "#0a0a0a"
    BTN_BG   = "#111111"
    FONT_MON = ("Courier", 10, "bold")
    FONT_BIG = ("Courier", 13, "bold")
    FONT_HDR = ("Courier", 15, "bold")
    root = tk.Tk()
    root.title("DEDSEC // GLITCH CONVERTER v1.0")
    root.configure(bg=BG)
    root.resizable(True, True)
    root.geometry("860x720")
    input_var    = tk.StringVar()
    output_var   = tk.StringVar()
    dither_var   = tk.StringVar(value="floyd")
    glitch_var   = tk.DoubleVar(value=0.5)
    scanlines_v  = tk.BooleanVar(value=True)
    vhs_v        = tk.BooleanVar(value=True)
    dispersion_v = tk.BooleanVar(value=True)
    datamosh_v   = tk.BooleanVar(value=False)
    progress_v   = tk.DoubleVar(value=0.0)
    status_v     = tk.StringVar(value="// SYSTEM READY — AWAITING INPUT //")
    preview_label = None
    preview_img   = None
    def label(parent, text, **kw):
        return tk.Label(parent, text=text, bg=BG, fg=FG, font=FONT_MON, **kw)
    def check(parent, text, var):
        return tk.Checkbutton(
            parent, text=text, variable=var,
            bg=BG, fg=FG, selectcolor=BTN_BG,
            activebackground=BG, activeforeground=FG,
            font=FONT_MON,
        )
    def btn(parent, text, cmd, color=None):
        b = tk.Button(
            parent, text=text, command=cmd,
            bg=BTN_BG, fg=color or FG, font=FONT_MON,
            relief="flat", bd=0,
            activebackground=ACCENT, activeforeground=FG2,
            padx=10, pady=6, cursor="hand2",
        )
        b.bind("<Enter>", lambda e: b.config(bg="#1a1a1a"))
        b.bind("<Leave>", lambda e: b.config(bg=BTN_BG))
        return b
    hdr = tk.Frame(root, bg=BG)
    hdr.pack(fill="x", padx=20, pady=(16, 0))
    tk.Label(
        hdr, text="██████╗ DEDSEC GLITCH ENGINE",
        bg=BG, fg=ACCENT, font=("Courier", 16, "bold"),
    ).pack(anchor="w")
    tk.Label(
        hdr, text="1-BIT CYBERPUNK CONVERTER // bitmap.dither.corrupt",
        bg=BG, fg=FG, font=("Courier", 9),
    ).pack(anchor="w")
    ttk.Separator(root, orient="horizontal").pack(fill="x", padx=20, pady=8)
    body = tk.Frame(root, bg=BG)
    body.pack(fill="both", expand=True, padx=20)
    left = tk.Frame(body, bg=BG, width=380)
    left.pack(side="left", fill="y", padx=(0, 16))
    left.pack_propagate(False)
    label(left, "[ INPUT FILE ]").pack(anchor="w", pady=(0, 2))
    f_row = tk.Frame(left, bg=BG)
    f_row.pack(fill="x", pady=(0, 8))
    tk.Entry(
        f_row, textvariable=input_var, bg=PANEL, fg=FG2,
        font=FONT_MON, relief="flat", insertbackground=FG,
    ).pack(side="left", fill="x", expand=True)
    def browse_input():
        f = filedialog.askopenfilename(
            title="Select image or video",
            filetypes=[
                ("All supported", "*.jpg *.jpeg *.png *.bmp *.dib *.tif *.tiff *.webp *.jp2 *.j2k *.pbm *.pgm *.ppm *.pnm *.tga *.gif *.ico *.avif *.mp4 *.avi *.mov *.mkv *.webm *.flv *.m4v *.mpg *.mpeg *.wmv *.3gp *.ts *.mts *.m2ts"),
                ("Images", "*.jpg *.jpeg *.png *.bmp *.dib *.tif *.tiff *.webp *.jp2 *.j2k *.pbm *.pgm *.ppm *.pnm *.tga *.gif *.ico *.avif"),
                ("Videos", "*.mp4 *.avi *.mov *.mkv *.webm *.flv *.m4v *.mpg *.mpeg *.wmv *.3gp *.ts *.mts *.m2ts"),
            ],
        )
        if f:
            input_var.set(f)
            auto_output(f)
            update_preview(f)
    btn(f_row, " BROWSE ", browse_input).pack(side="left", padx=(4, 0))
    label(left, "[ OUTPUT FILE ]").pack(anchor="w", pady=(0, 2))
    o_row = tk.Frame(left, bg=BG)
    o_row.pack(fill="x", pady=(0, 12))
    tk.Entry(
        o_row, textvariable=output_var, bg=PANEL, fg=FG2,
        font=FONT_MON, relief="flat", insertbackground=FG,
    ).pack(side="left", fill="x", expand=True)
    def browse_output():
        f = filedialog.asksaveasfilename(title="Save as…", defaultextension=".png")
        if f:
            output_var.set(f)
    btn(o_row, " BROWSE ", browse_output).pack(side="left", padx=(4, 0))
    def auto_output(path):
        p = Path(path)
        output_var.set(str(p.parent / f"{p.stem}_dedsec{p.suffix}"))
    label(left, "[ DITHER ALGORITHM ]").pack(anchor="w", pady=(0, 2))
    d_row = tk.Frame(left, bg=BG)
    d_row.pack(fill="x", pady=(0, 10))
    for method, lbl in [("floyd", "Floyd-Steinberg"), ("ordered", "Bayer Ordered"),
                         ("atkinson", "Atkinson"), ("none", "Hard Threshold")]:
        tk.Radiobutton(
            d_row, text=lbl, variable=dither_var, value=method,
            bg=BG, fg=FG, selectcolor=PANEL, activebackground=BG,
            activeforeground=FG2, font=FONT_MON, indicatoron=True,
        ).pack(anchor="w")
    label(left, "[ GLITCH INTENSITY ]").pack(anchor="w", pady=(6, 0))
    g_row = tk.Frame(left, bg=BG)
    g_row.pack(fill="x", pady=(0, 10))
    tk.Scale(
        g_row, variable=glitch_var, from_=0.0, to=1.0,
        resolution=0.05, orient="horizontal", length=260,
        bg=BG, fg=FG, troughcolor=PANEL, highlightthickness=0,
        activebackground=ACCENT, font=("Courier", 8),
    ).pack(side="left")
    tk.Label(g_row, textvariable=glitch_var, bg=BG, fg=ACCENT, font=FONT_MON, width=4).pack(side="left")
    label(left, "[ EFFECT MODULES ]").pack(anchor="w", pady=(4, 2))
    efx = tk.Frame(left, bg=BG)
    efx.pack(fill="x", pady=(0, 10))
    check(efx, " CRT Scanlines",    scanlines_v ).pack(anchor="w")
    check(efx, " VHS Noise",        vhs_v       ).pack(anchor="w")
    check(efx, " Pixel Dispersion", dispersion_v).pack(anchor="w")
    check(efx, " Datamosh Corrupt", datamosh_v  ).pack(anchor="w")
    ttk.Separator(left, orient="horizontal").pack(fill="x", pady=8)
    tk.Label(left, textvariable=status_v, bg=BG, fg=FG, font=("Courier", 8),
             wraplength=360, justify="left").pack(anchor="w")
    prog_bar = ttk.Progressbar(left, variable=progress_v, maximum=100, length=350)
    prog_bar.pack(fill="x", pady=(4, 8))
    style = ttk.Style()
    style.theme_use("clam")
    style.configure("TProgressbar", troughcolor=PANEL, background=FG, thickness=8)
    def start_convert():
        inp = input_var.get().strip()
        if not inp or not os.path.exists(inp):
            messagebox.showerror("ERROR", "Select a valid input file.")
            return
        out = output_var.get().strip() or ""
        progress_v.set(0)
        def run():
            ext = Path(inp).suffix.lower()
            is_video = ext in {".mp4", ".avi", ".mov", ".mkv", ".webm", ".flv"}
            kwargs = dict(
                dither_method=dither_var.get(),
                glitch=glitch_var.get(),
                scanlines=scanlines_v.get(),
                vhs=vhs_v.get(),
                dispersion=dispersion_v.get(),
                datamosh=datamosh_v.get(),
                verbose=False,
            )
            try:
                status_v.set("// PROCESSING — DO NOT UNPLUG //")
                if is_video:
                    def cb(pct):
                        progress_v.set(pct)
                        status_v.set(f"// ENCODING FRAME {pct:.1f}% //")
                    result = process_video(inp, out, progress_cb=cb, **kwargs)
                else:
                    result = process_image(inp, out, **kwargs)
                    progress_v.set(100)
                status_v.set(f"// OUTPUT: {result} //")
                messagebox.showinfo("DEDSEC", f"Conversion complete:\n{result}")
                update_preview(result)
            except Exception as e:
                status_v.set(f"// ERROR: {e} //")
                messagebox.showerror("ERROR", str(e))
        threading.Thread(target=run, daemon=True).start()
    btn(left, "[ EXECUTE CONVERSION ]", start_convert, color=ACCENT).pack(
        fill="x", pady=(4, 0), ipady=4
    )
    right = tk.Frame(body, bg=PANEL, relief="flat", bd=1)
    right.pack(side="left", fill="both", expand=True)
    tk.Label(right, text="[ PREVIEW ]", bg=PANEL, fg=FG,
             font=FONT_MON).pack(anchor="nw", padx=8, pady=4)
    preview_canvas = tk.Label(
        right, bg=PANEL, fg=FG, text="\n\n\n\n[ NO INPUT ]\n\n\n\n",
        font=("Courier", 10), relief="flat",
    )
    preview_canvas.pack(fill="both", expand=True, padx=4, pady=4)
    def update_preview(path: str):
        nonlocal preview_img
        ext = Path(path).suffix.lower()
        if ext in VIDEO_INPUT_EXTS:
            cap = cv2.VideoCapture(path)
            ret, frame = cap.read()
            cap.release()
            if not ret:
                return
            img = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
        else:
            try:
                img = Image.open(path)
            except Exception:
                return
        max_w, max_h = 420, 500
        img.thumbnail((max_w, max_h), Image.NEAREST)
        preview_img = ImageTk.PhotoImage(img)
        preview_canvas.config(image=preview_img, text="")
    ttk.Separator(root, orient="horizontal").pack(fill="x", padx=20, pady=(8, 4))
    tk.Label(
        root,
        text="DEDSEC // WE ARE WATCHING // 1-BIT GLITCH ENGINE // ANTI-CORPORATE PROPAGANDA TOOL",
        bg=BG, fg="#333333", font=("Courier", 7),
    ).pack(pady=(0, 8))
    root.mainloop()

def run_web_gui(host: str = "127.0.0.1", port: int = 8765):
    """Launch a local browser UI. This avoids macOS/Tkinter runtime crashes."""
    from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
    from urllib.parse import parse_qs, quote, unquote, urlparse
    import html
    import json
    import mimetypes
    import re
    import uuid
    import webbrowser
    output_dir = Path.cwd() / "dedsec_outputs"
    uploads_dir = output_dir / "uploads"
    output_dir.mkdir(exist_ok=True)
    uploads_dir.mkdir(exist_ok=True)
    image_exts = IMAGE_INPUT_EXTS | IMAGE_OUTPUT_EXTS
    video_exts = VIDEO_INPUT_EXTS | set(VIDEO_OUTPUT_CODECS)
    jobs = {}
    jobs_lock = threading.Lock()
    def clamp_glitch(raw: str) -> float:
        try:
            return min(1.0, max(0.0, float(raw)))
        except (TypeError, ValueError):
            return 0.5
    def parse_fps(raw: str):
        try:
            value = float(raw)
            return min(120.0, max(1.0, value)) if value > 0 else None
        except (TypeError, ValueError):
            return None
    def default_output_path(input_path: str, mode: str, output_format: str = "") -> str:
        p = Path(input_path)
        if mode == "video":
            suffix = normalize_ext(output_format, set(VIDEO_OUTPUT_CODECS), ".mp4")
        else:
            suffix = normalize_ext(output_format or p.suffix, IMAGE_OUTPUT_EXTS, ".png")
        return str(output_dir / f"{p.stem}_dedsec{suffix}")
    def parse_form(content_type: str, raw: bytes) -> dict:
        if content_type.startswith("multipart/form-data"):
            boundary_match = re.search(r"boundary=([^;]+)", content_type)
            if not boundary_match:
                return {}
            boundary = boundary_match.group(1).strip('"').encode("utf-8")
            fields = {}
            for part in raw.split(b"--" + boundary):
                part = part.strip()
                if not part or part == b"--":
                    continue
                if part.endswith(b"--"):
                    part = part[:-2].strip()
                if b"\r\n\r\n" not in part:
                    continue
                header_blob, value = part.split(b"\r\n\r\n", 1)
                value = value.rstrip(b"\r\n")
                headers = header_blob.decode("utf-8", errors="replace")
                disposition = next(
                    (line for line in headers.split("\r\n") if line.lower().startswith("content-disposition:")),
                    "",
                )
                name_match = re.search(r'name="([^"]+)"', disposition)
                if not name_match:
                    continue
                name = name_match.group(1)
                filename_match = re.search(r'filename="([^"]*)"', disposition)
                if filename_match and value:
                    filename = Path(filename_match.group(1).replace("\\", "/")).name
                    safe_name = re.sub(r"[^A-Za-z0-9А-Яа-яЁё._ -]+", "_", filename).strip()
                    safe_name = safe_name or "upload"
                    upload_path = uploads_dir / f"{int(time.time())}_{safe_name}"
                    upload_path.write_bytes(value)
                    fields[name] = str(upload_path)
                    fields["input"] = str(upload_path)
                elif not filename_match:
                    fields[name] = value.decode("utf-8", errors="replace")
            return fields
        decoded = raw.decode("utf-8", errors="replace")
        return {k: v[-1] for k, v in parse_qs(decoded, keep_blank_values=True).items()}
    def page(result: str = "", error: str = "", values=None, mode: str = "image") -> bytes:
        values = values or {}
        is_video_page = mode == "video"
        input_value = html.escape(values.get("input", ""))
        output_value = html.escape(values.get("output", ""))
        glitch_value = html.escape(values.get("glitch", "0.5"))
        dither_value = values.get("dither", "floyd")
        output_format_value = values.get("output_format", ".mp4" if is_video_page else ".png")
        action = "/convert-video" if is_video_page else "/convert"
        accept_value = html.escape(WEB_VIDEO_ACCEPT if is_video_page else WEB_IMAGE_ACCEPT)
        upload_title = "VIDEO FILE" if is_video_page else "IMAGE FILE"
        path_placeholder = "/Users/stepazilin/Desktop/video.mp4" if is_video_page else "/Users/stepazilin/Desktop/photo.jpg"
        output_placeholder = "auto: dedsec_outputs/video_dedsec.mp4" if is_video_page else "auto: dedsec_outputs/photo_dedsec.png"
        page_title = "DEDSEC VIDEO CONVERTER" if is_video_page else "DEDSEC IMAGE CONVERTER"
        page_subtitle = "VIDEO FORMAT // FPS // DITHER // CORRUPT" if is_video_page else "PHOTO FORMAT // DITHER // CORRUPT"
        video_active = "active" if is_video_page else ""
        image_active = "" if is_video_page else "active"
        def selected(name: str) -> str:
            return "selected" if dither_value == name else ""
        def selected_format(name: str) -> str:
            return "selected" if output_format_value == name else ""
        def checked(name: str, default: bool = True) -> str:
            if name not in values:
                return "checked" if default else ""
            return "checked" if values.get(name) == "on" else ""
        if is_video_page:
            format_options = f"""
            <option value=".mp4" {selected_format(".mp4")}>MP4</option>
            <option value=".avi" {selected_format(".avi")}>AVI</option>
            <option value=".mov" {selected_format(".mov")}>MOV</option>
            <option value=".mkv" {selected_format(".mkv")}>MKV</option>
            <option value=".webm" {selected_format(".webm")}>WEBM</option>
            """
            fps_field = f"""
        <div class="field">
          <label for="fps">OUTPUT FPS</label>
          <input id="fps" name="fps" type="number" min="1" max="120" step="1" value="{html.escape(values.get("fps", ""))}" placeholder="auto">
        </div>
            """
        else:
            format_options = f"""
            <option value=".png" {selected_format(".png")}>PNG</option>
            <option value=".jpg" {selected_format(".jpg")}>JPG</option>
            <option value=".webp" {selected_format(".webp")}>WEBP</option>
            <option value=".tiff" {selected_format(".tiff")}>TIFF</option>
            <option value=".bmp" {selected_format(".bmp")}>BMP</option>
            <option value=".tga" {selected_format(".tga")}>TGA</option>
            <option value=".jp2" {selected_format(".jp2")}>JP2</option>
            """
            fps_field = ""
        progress_block = ""
        script_block = ""
        if is_video_page:
            progress_block = """
    <section id="render_progress" class="result progress-panel" hidden>
      <div class="status" id="render_status">RENDER 0%</div>
      <progress id="render_bar" value="0" max="100"></progress>
      <div class="hint" id="render_hint">Идет обработка видео...</div>
    </section>
    <section id="async_result"></section>
            """
            script_block = """
  <script>
    const form = document.querySelector("form");
    const panel = document.getElementById("render_progress");
    const bar = document.getElementById("render_bar");
    const statusText = document.getElementById("render_status");
    const hint = document.getElementById("render_hint");
    const asyncResult = document.getElementById("async_result");
    const button = document.querySelector("button[type=submit]");

    function setProgress(value, status) {
      const pct = Math.max(0, Math.min(100, Number(value) || 0));
      panel.hidden = false;
      bar.value = pct;
      statusText.textContent = `${status || "RENDER"} ${pct.toFixed(1)}%`;
    }

    function showResult(data) {
      const url = `/file?path=${encodeURIComponent(data.result)}`;
      asyncResult.innerHTML = `
        <section class="result ok">
          <div class="status">DONE</div>
          <a href="${url}" target="_blank">${data.result}</a>
          <video class="preview" src="${url}" controls></video>
        </section>
      `;
    }

    function showError(message) {
      asyncResult.innerHTML = `
        <section class="result error">
          <div class="status">ERROR</div>
          <pre>${message}</pre>
        </section>
      `;
    }

    async function pollJob(id) {
      const response = await fetch(`/progress?id=${encodeURIComponent(id)}`);
      const data = await response.json();
      setProgress(data.progress, data.status);
      if (data.status === "done") {
        setProgress(100, "DONE");
        hint.textContent = "Рендер завершен.";
        button.disabled = false;
        showResult(data);
        return;
      }
      if (data.status === "error") {
        hint.textContent = "Рендер остановлен.";
        button.disabled = false;
        showError(data.error || "Unknown error");
        return;
      }
      setTimeout(() => pollJob(id), 500);
    }

    form.addEventListener("submit", async (event) => {
      event.preventDefault();
      button.disabled = true;
      asyncResult.innerHTML = "";
      hint.textContent = "Файл отправлен, начинаю рендер...";
      setProgress(0, "QUEUE");
      try {
        const response = await fetch("/convert-video/start", {
          method: "POST",
          body: new FormData(form)
        });
        const data = await response.json();
        if (!response.ok || data.error) {
          throw new Error(data.error || "Cannot start render");
        }
        pollJob(data.job_id);
      } catch (error) {
        button.disabled = false;
        setProgress(0, "ERROR");
        hint.textContent = "Не удалось запустить рендер.";
        showError(error.message);
      }
    });
  </script>
            """
        result_block = ""
        if result:
            escaped_result = html.escape(result)
            file_url = f"/file?path={quote(result)}"
            ext = Path(result).suffix.lower()
            preview = ""
            if ext in image_exts:
                preview = f'<img class="preview" src="{file_url}" alt="preview">'
            elif ext in video_exts:
                preview = f'<video class="preview" src="{file_url}" controls></video>'
            result_block = f"""
                <section class="result ok">
                    <div class="status">DONE</div>
                    <a href="{file_url}" target="_blank">{escaped_result}</a>
                    {preview}
                </section>
            """
        error_block = ""
        if error:
            error_block = f"""
                <section class="result error">
                    <div class="status">ERROR</div>
                    <pre>{html.escape(error)}</pre>
                </section>
            """
        html_doc = f"""<!doctype html>
<html lang="ru">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>DEDSEC // Glitch Converter</title>
  <style>
    :root {{
      color-scheme: dark;
      --bg: #050505;
      --panel: #101010;
      --line: #242424;
      --green: #00ff41;
      --red: #ff0033;
      --text: #f3f3f3;
      --muted: #8b8b8b;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      min-height: 100vh;
      background: var(--bg);
      color: var(--text);
      font: 14px/1.45 Courier, monospace;
    }}
    main {{
      width: min(980px, calc(100vw - 32px));
      margin: 0 auto;
      padding: 28px 0;
    }}
    header {{
      border-bottom: 1px solid var(--line);
      padding-bottom: 14px;
      margin-bottom: 22px;
    }}
    h1 {{
      margin: 0;
      color: var(--red);
      font-size: clamp(22px, 4vw, 36px);
      letter-spacing: 0;
    }}
    .sub {{ color: var(--green); margin-top: 4px; }}
    nav {{
      display: flex;
      gap: 8px;
      margin-top: 16px;
      flex-wrap: wrap;
    }}
    nav a {{
      color: var(--text);
      border: 1px solid var(--line);
      border-radius: 6px;
      padding: 8px 10px;
      text-decoration: none;
    }}
    nav a.active {{
      color: #000;
      background: var(--green);
      border-color: var(--green);
    }}
    form {{
      display: grid;
      grid-template-columns: 1fr 280px;
      gap: 16px;
    }}
    .panel {{
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 8px;
      padding: 16px;
    }}
    label {{
      display: block;
      color: var(--green);
      font-weight: 700;
      margin: 0 0 8px;
    }}
    input[type="text"], input[type="number"], select {{
      width: 100%;
      min-height: 42px;
      background: #050505;
      color: var(--text);
      border: 1px solid #333;
      border-radius: 6px;
      padding: 10px;
      font: inherit;
    }}
    input[type="range"] {{ width: 100%; accent-color: var(--red); }}
    .field {{ margin-bottom: 16px; }}
    .toggles label {{
      display: flex;
      gap: 8px;
      align-items: center;
      color: var(--text);
      margin: 9px 0;
      font-weight: 400;
    }}
    button {{
      width: 100%;
      min-height: 46px;
      border: 0;
      border-radius: 6px;
      background: var(--red);
      color: white;
      cursor: pointer;
      font: 700 14px Courier, monospace;
    }}
    .hint {{
      color: var(--muted);
      font-size: 12px;
      margin-top: 8px;
      overflow-wrap: anywhere;
    }}
    .result {{
      margin-top: 16px;
      border-radius: 8px;
      border: 1px solid var(--line);
      padding: 14px;
      background: var(--panel);
    }}
    .result a {{ color: var(--green); overflow-wrap: anywhere; }}
    .status {{ color: var(--red); font-weight: 700; margin-bottom: 8px; }}
    progress {{
      width: 100%;
      height: 16px;
      accent-color: var(--green);
    }}
    button:disabled {{
      opacity: 0.55;
      cursor: wait;
    }}
    pre {{ white-space: pre-wrap; color: #ff7a92; margin: 0; }}
    .preview {{
      display: block;
      width: 100%;
      max-height: 520px;
      object-fit: contain;
      margin-top: 14px;
      background: #000;
      border: 1px solid var(--line);
      border-radius: 6px;
    }}
    @media (max-width: 760px) {{
      form {{ grid-template-columns: 1fr; }}
    }}
  </style>
</head>
<body>
  <main>
    <header>
      <h1>{page_title}</h1>
      <div class="sub">{page_subtitle}</div>
      <nav>
        <a class="{image_active}" href="/">Фото</a>
        <a class="{video_active}" href="/video">Видео</a>
      </nav>
    </header>
    <form method="post" action="{action}" enctype="multipart/form-data">
      <section class="panel">
        <div class="field">
          <label for="upload">{upload_title}</label>
          <input id="upload" name="upload" type="file" accept="{accept_value}">
        </div>
        <div class="field">
          <label for="input">INPUT FILE PATH</label>
          <input id="input" name="input" type="text" value="{input_value}" placeholder="{path_placeholder}">
          <div class="hint">Можно выбрать файл выше или вставить полный путь вручную.</div>
        </div>
        <div class="field">
          <label for="output">OUTPUT FILE PATH</label>
          <input id="output" name="output" type="text" value="{output_value}" placeholder="{output_placeholder}">
        </div>
        <div class="field">
          <label for="output_format">OUTPUT FORMAT</label>
          <select id="output_format" name="output_format">
            {format_options}
          </select>
        </div>
      </section>
      <aside class="panel">
        {fps_field}
        <div class="field">
          <label for="dither">DITHER</label>
          <select id="dither" name="dither">
            <option value="floyd" {selected("floyd")}>Floyd-Steinberg</option>
            <option value="ordered" {selected("ordered")}>Bayer Ordered</option>
            <option value="atkinson" {selected("atkinson")}>Atkinson</option>
            <option value="none" {selected("none")}>Hard Threshold</option>
          </select>
        </div>
        <div class="field">
          <label for="glitch">GLITCH INTENSITY</label>
          <input id="glitch" name="glitch" type="range" min="0" max="1" step="0.05" value="{glitch_value}">
        </div>
        <div class="toggles">
          <label><input type="checkbox" name="scanlines" {checked("scanlines")}> CRT Scanlines</label>
          <label><input type="checkbox" name="vhs" {checked("vhs")}> VHS Noise</label>
          <label><input type="checkbox" name="dispersion" {checked("dispersion")}> Pixel Dispersion</label>
          <label><input type="checkbox" name="datamosh" {checked("datamosh", False)}> Datamosh</label>
        </div>
        <button type="submit">EXECUTE CONVERSION</button>
      </aside>
    </form>
    {progress_block}
    {error_block}
    {result_block}
  </main>
  {script_block}
</body>
</html>"""
        return html_doc.encode("utf-8")
    def start_video_job(values: dict) -> str:
        input_path = values.get("input", "").strip().strip("'\"")
        output_format = values.get("output_format", ".mp4")
        output_path = values.get("output", "").strip().strip("'\"") or default_output_path(input_path, "video", output_format)
        if not input_path:
            raise ValueError("Input file path is empty.")
        if not Path(input_path).exists():
            raise ValueError(f"Input file does not exist: {input_path}")
        ext = Path(input_path).suffix.lower()
        if ext not in VIDEO_INPUT_EXTS:
            raise ValueError(f"Unsupported video input format: {ext or '(no extension)'}")
        job_id = uuid.uuid4().hex
        job_values = dict(values)
        job_values["output"] = output_path
        with jobs_lock:
            jobs[job_id] = {
                "status": "queued",
                "progress": 0.0,
                "result": "",
                "error": "",
                "values": job_values,
            }
        kwargs = dict(
            dither_method=values.get("dither", "floyd"),
            glitch=clamp_glitch(values.get("glitch", "0.5")),
            scanlines=values.get("scanlines") == "on",
            vhs=values.get("vhs") == "on",
            dispersion=values.get("dispersion") == "on",
            datamosh=values.get("datamosh") == "on",
            verbose=False,
        )
        def update(**changes):
            with jobs_lock:
                if job_id in jobs:
                    jobs[job_id].update(changes)
        def run():
            try:
                update(status="rendering", progress=0.0)
                def cb(pct):
                    update(status="rendering", progress=round(float(pct), 2))
                result = process_video(
                    input_path,
                    output_path,
                    output_format=output_format,
                    target_fps=parse_fps(values.get("fps", "")),
                    progress_cb=cb,
                    **kwargs,
                )
                job_values["output"] = result
                update(status="done", progress=100.0, result=result, values=job_values)
            except Exception as exc:
                update(status="error", error=str(exc))
        threading.Thread(target=run, daemon=True).start()
        return job_id
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, fmt, *args):
            return
        def send_bytes(self, data: bytes, content_type: str = "text/html; charset=utf-8"):
            self.send_response(200)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)
        def send_json(self, data: dict, status: int = 200):
            payload = json.dumps(data).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)
        def do_GET(self):
            parsed = urlparse(self.path)
            if parsed.path == "/":
                self.send_bytes(page(mode="image"))
                return
            if parsed.path == "/video":
                self.send_bytes(page(mode="video"))
                return
            if parsed.path == "/progress":
                params = parse_qs(parsed.query)
                job_id = params.get("id", [""])[0]
                with jobs_lock:
                    job = dict(jobs.get(job_id, {}))
                if not job:
                    self.send_json({"status": "error", "progress": 0, "error": "Job not found"}, status=404)
                    return
                self.send_json({
                    "status": job.get("status", "queued"),
                    "progress": job.get("progress", 0),
                    "result": job.get("result", ""),
                    "error": job.get("error", ""),
                })
                return
            if parsed.path == "/file":
                params = parse_qs(parsed.query)
                raw_path = unquote(params.get("path", [""])[0])
                path = Path(raw_path)
                if not path.exists() or not path.is_file():
                    self.send_error(404, "File not found")
                    return
                content_type = mimetypes.guess_type(str(path))[0] or "application/octet-stream"
                data = path.read_bytes()
                self.send_bytes(data, content_type)
                return
            self.send_error(404, "Not found")
        def do_POST(self):
            post_path = urlparse(self.path).path
            if post_path == "/convert-video/start":
                length = int(self.headers.get("Content-Length", "0"))
                content_type = self.headers.get("Content-Type", "")
                values = parse_form(content_type, self.rfile.read(length))
                try:
                    job_id = start_video_job(values)
                    self.send_json({"job_id": job_id})
                except Exception as exc:
                    self.send_json({"error": str(exc)}, status=400)
                return
            if post_path not in {"/convert", "/convert-video"}:
                self.send_error(404, "Not found")
                return
            requested_mode = "video" if post_path == "/convert-video" else "image"
            length = int(self.headers.get("Content-Length", "0"))
            content_type = self.headers.get("Content-Type", "")
            values = parse_form(content_type, self.rfile.read(length))
            input_path = values.get("input", "").strip().strip("'\"")
            output_format = values.get("output_format", ".mp4" if requested_mode == "video" else ".png")
            output_path = values.get("output", "").strip().strip("'\"") or default_output_path(input_path, requested_mode, output_format)
            try:
                if not input_path:
                    raise ValueError("Input file path is empty.")
                if not Path(input_path).exists():
                    raise ValueError(f"Input file does not exist: {input_path}")
                kwargs = dict(
                    dither_method=values.get("dither", "floyd"),
                    glitch=clamp_glitch(values.get("glitch", "0.5")),
                    scanlines=values.get("scanlines") == "on",
                    vhs=values.get("vhs") == "on",
                    dispersion=values.get("dispersion") == "on",
                    datamosh=values.get("datamosh") == "on",
                    verbose=False,
                )
                ext = Path(input_path).suffix.lower()
                if requested_mode == "video":
                    if ext not in VIDEO_INPUT_EXTS:
                        raise ValueError(f"Unsupported video input format: {ext or '(no extension)'}")
                    result = process_video(
                        input_path,
                        output_path,
                        output_format=output_format,
                        target_fps=parse_fps(values.get("fps", "")),
                        **kwargs,
                    )
                else:
                    if ext in VIDEO_INPUT_EXTS:
                        raise ValueError("Для видео открой страницу /video.")
                    else:
                        result = process_image(input_path, output_path, output_format=output_format, **kwargs)
                values["output"] = result
                self.send_bytes(page(result=result, values=values, mode=requested_mode))
            except Exception as exc:
                self.send_bytes(page(error=str(exc), values=values, mode=requested_mode))
    server = None
    for candidate in range(port, port + 20):
        try:
            server = ThreadingHTTPServer((host, candidate), Handler)
            port = candidate
            break
        except OSError:
            continue
    if server is None:
        raise RuntimeError("No free local port found for web UI.")
    url = f"http://{host}:{port}"
    print(f"[DEDSEC] Web UI running: {url}", flush=True)
    print("[DEDSEC] Press Ctrl+C to stop.", flush=True)
    webbrowser.open(url)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n[DEDSEC] Web UI stopped.")
    finally:
        server.server_close()

def main():
    parser = argparse.ArgumentParser(
        description="DEDSEC 1-Bit Glitch Converter",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("--input",      "-i", help="Input image or video file")
    parser.add_argument("--output",     "-o", help="Output file path", default="")
    parser.add_argument("--output-format", help="Output format, for example png, webp, mp4, avi", default="")
    parser.add_argument("--dither",     "-d", choices=["floyd","ordered","atkinson","none"],
                        default="floyd", help="Dithering algorithm")
    parser.add_argument("--glitch",     "-g", type=float, default=0.5,
                        help="Glitch intensity 0.0–1.0")
    parser.add_argument("--scanlines",  "-s", action="store_true", default=True,
                        help="Enable CRT scanlines")
    parser.add_argument("--vhs",        "-v", action="store_true", default=True,
                        help="Enable VHS noise")
    parser.add_argument("--dispersion", action="store_true", default=True,
                        help="Enable pixel dispersion")
    parser.add_argument("--datamosh",   action="store_true", default=False,
                        help="Enable datamosh artifacts")
    parser.add_argument("--fps",        type=float, default=None,
                        help="Output video FPS")
    parser.add_argument("--gui",        action="store_true",
                        help="Launch local browser GUI")
    args = parser.parse_args()
    if args.gui or not args.input:
        run_web_gui()
    else:
        run_cli(args)

if __name__ == "__main__":
    main()
