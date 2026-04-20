"""
Clipper by Flexibles AI
Screenshot · annotate · copy, with resolution control.
"""

import io
import math
import sys
import threading
import tkinter as tk
from tkinter import colorchooser, filedialog, messagebox

from PIL import Image, ImageDraw, ImageEnhance, ImageFont, ImageGrab, ImageTk

try:
    import win32clipboard
    import win32con
    HAS_WIN32 = True
except ImportError:
    HAS_WIN32 = False

try:
    import pystray
    HAS_TRAY = True
except ImportError:
    HAS_TRAY = False

try:
    import keyboard as kb
    HAS_HOTKEY = True
except ImportError:
    HAS_HOTKEY = False


APP_NAME        = "Clipper"
APP_BRAND       = "by Flexibles AI"
APP_TAGLINE     = "Snip · annotate · copy"
MAX_DIM_DEFAULT = 1900


# ============================================================ palette & typography

class C:
    BG          = "#0b0b0f"
    SURFACE     = "#141419"
    SURFACE_HI  = "#1c1c24"
    SURFACE_HI2 = "#25252e"
    BORDER      = "#262630"
    TEXT        = "#eceff4"
    TEXT_DIM    = "#9aa0aa"
    TEXT_MUTED  = "#6b6e77"
    ACCENT      = "#8b5cf6"
    ACCENT_HI   = "#a78bfa"
    ACCENT_LO   = "#7c3aed"
    ACCENT_SOFT = "#2a2140"
    DANGER      = "#ef4444"
    SUCCESS     = "#22c55e"
    LOGO_FROM   = "#a78bfa"
    LOGO_TO     = "#6366f1"


FONT_UI       = ("Segoe UI", 10)
FONT_UI_BOLD  = ("Segoe UI", 10, "bold")
FONT_TITLE    = ("Segoe UI", 24, "bold")
FONT_SUB      = ("Segoe UI", 10)
FONT_LABEL    = ("Segoe UI", 9, "bold")
FONT_SMALL    = ("Segoe UI", 9)
FONT_HINT     = ("Segoe UI", 9)


def _hex_to_rgb(c: str):
    return int(c[1:3], 16), int(c[3:5], 16), int(c[5:7], 16)


def _rounded_rect_points(x1, y1, x2, y2, r):
    r = max(0, min(r, (x2 - x1) // 2, (y2 - y1) // 2))
    return [
        x1 + r, y1,
        x2 - r, y1, x2, y1,
        x2, y1 + r, x2, y2 - r, x2, y2,
        x2 - r, y2, x1 + r, y2, x1, y2,
        x1, y2 - r, x1, y1 + r, x1, y1,
    ]


# ============================================================ platform helpers

def enable_dpi_awareness():
    """Tell Windows we handle DPI so ImageGrab pixels match tk pixels."""
    if sys.platform != "win32":
        return
    import ctypes
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(2)  # PER_MONITOR_DPI_AWARE
        return
    except (AttributeError, OSError):
        pass
    try:
        ctypes.windll.user32.SetProcessDPIAware()
    except (AttributeError, OSError):
        pass


def get_virtual_screen():
    if sys.platform != "win32":
        import tkinter as _tk
        r = _tk.Tk(); r.withdraw()
        w, h = r.winfo_screenwidth(), r.winfo_screenheight()
        r.destroy()
        return 0, 0, w, h
    import ctypes
    u = ctypes.windll.user32
    return (u.GetSystemMetrics(76), u.GetSystemMetrics(77),
            u.GetSystemMetrics(78), u.GetSystemMetrics(79))


def _apply_tk_scaling(root: tk.Misc):
    try:
        dpi = root.winfo_fpixels("1i")
        root.tk.call("tk", "scaling", dpi / 72.0)
    except tk.TclError:
        pass


# ============================================================ clipboard

def copy_image_to_clipboard(img: Image.Image) -> None:
    if not HAS_WIN32:
        raise RuntimeError("pywin32 is required for clipboard copy on Windows.")
    output = io.BytesIO()
    img.convert("RGB").save(output, "BMP")
    data = output.getvalue()[14:]  # strip BMP file header -> DIB
    output.close()
    win32clipboard.OpenClipboard()
    try:
        win32clipboard.EmptyClipboard()
        win32clipboard.SetClipboardData(win32con.CF_DIB, data)
    finally:
        win32clipboard.CloseClipboard()


# ============================================================ custom widgets

class RoundedButton(tk.Canvas):
    VARIANTS = {
        "primary":   (C.ACCENT,     C.ACCENT_HI,   "#ffffff",  None),
        "secondary": (C.SURFACE_HI, C.SURFACE_HI2, C.TEXT,     C.BORDER),
        "ghost":     (None,         C.SURFACE_HI,  C.TEXT_DIM, None),
        "danger":    (C.DANGER,     "#f87171",     "#ffffff",  None),
    }

    def __init__(self, parent, text="", command=None, *, variant="primary",
                 font=FONT_UI_BOLD, padx=18, pady=10, radius=10,
                 min_width=0, height=None, bg_parent=None):
        bg_col, hover_col, fg_col, border_col = self.VARIANTS[variant]
        pbg = bg_parent or parent.cget("bg")

        tmp = tk.Label(parent, text=text, font=font)
        tmp.update_idletasks()
        tw = max(min_width, tmp.winfo_reqwidth())
        th = tmp.winfo_reqheight()
        tmp.destroy()

        w = tw + padx * 2
        h = height if height is not None else th + pady * 2
        super().__init__(parent, width=w, height=h,
                         bg=pbg, highlightthickness=0, bd=0, cursor="hand2")
        # Note: avoid `self._w` — that's Tk's internal widget command name.
        self._btn_w, self._btn_h = w, h
        self._bg_col = bg_col
        self._hover_col = hover_col
        self._border_col = border_col
        self._command = command
        self._hovering = False
        self._pressed = False
        self._parent_bg = pbg

        fill = bg_col if bg_col is not None else pbg
        outline = border_col or fill
        pts = _rounded_rect_points(1, 1, w - 1, h - 1, radius)
        self._shape = self.create_polygon(pts, smooth=True, fill=fill,
                                          outline=outline, width=1)
        self.create_text(w // 2, h // 2, text=text, fill=fg_col, font=font)

        self.bind("<Enter>", self._on_enter)
        self.bind("<Leave>", self._on_leave)
        self.bind("<ButtonPress-1>", self._on_press)
        self.bind("<ButtonRelease-1>", self._on_release)

    def _on_enter(self, _):
        self._hovering = True
        self.itemconfigure(self._shape, fill=self._hover_col, outline=self._hover_col)

    def _on_leave(self, _):
        self._hovering = False
        self._pressed = False
        fill = self._bg_col if self._bg_col is not None else self._parent_bg
        self.itemconfigure(self._shape, fill=fill,
                           outline=self._border_col or fill)

    def _on_press(self, _):
        self._pressed = True

    def _on_release(self, _):
        if self._pressed and self._hovering and self._command:
            self._command()
        self._pressed = False


class SegmentedControl(tk.Canvas):
    """Pill-shaped segmented picker bound to a Tk variable."""

    def __init__(self, parent, options, variable, *, on_change=None,
                 font=FONT_UI_BOLD, padx=14, pady=7, radius=9,
                 height=None, bg_parent=None):
        self._var = variable
        self._on_change = on_change

        tmp = tk.Label(parent, font=font)
        tmp.update_idletasks()
        widths, max_h = [], 0
        for label, _ in options:
            tmp.configure(text=label)
            tmp.update_idletasks()
            widths.append(tmp.winfo_reqwidth())
            max_h = max(max_h, tmp.winfo_reqheight())
        tmp.destroy()

        seg_h = max_h + pady * 2
        seg_ws = [w + padx * 2 for w in widths]
        inner_pad = 4
        total_w = sum(seg_ws) + inner_pad * 2
        natural_total_h = seg_h + inner_pad * 2
        total_h = height if height is not None else natural_total_h
        pill_top = (total_h - seg_h) // 2

        pbg = bg_parent or parent.cget("bg")
        super().__init__(parent, width=total_w, height=total_h, bg=pbg,
                         highlightthickness=0, bd=0)

        bg_pts = _rounded_rect_points(0, 0, total_w, total_h,
                                      min(radius + inner_pad, total_h // 2))
        self.create_polygon(bg_pts, smooth=True, fill=C.SURFACE_HI, outline="")

        self._segments = []
        x = inner_pad
        for (label, value), sw in zip(options, seg_ws):
            x1, y1, x2, y2 = x, pill_top, x + sw, pill_top + seg_h
            pts = _rounded_rect_points(x1, y1, x2, y2, radius)
            pill = self.create_polygon(pts, smooth=True, fill=C.SURFACE_HI, outline="")
            txt = self.create_text((x1 + x2) // 2, (y1 + y2) // 2,
                                   text=label, fill=C.TEXT_DIM, font=font)
            self._segments.append({"value": value, "pill": pill, "txt": txt,
                                   "bbox": (x1, y1, x2, y2)})
            x += sw

        self.bind("<Motion>", self._on_motion)
        self.bind("<Leave>", lambda e: self._refresh())
        self.bind("<Button-1>", self._on_click)
        self._refresh()

    def _find(self, x, y):
        for s in self._segments:
            x1, y1, x2, y2 = s["bbox"]
            if x1 <= x <= x2 and y1 <= y <= y2:
                return s
        return None

    def _on_motion(self, event):
        hovered = self._find(event.x, event.y)
        self.configure(cursor="hand2" if hovered else "")
        self._refresh(hovered)

    def _on_click(self, event):
        s = self._find(event.x, event.y)
        if s and self._var.get() != s["value"]:
            self._var.set(s["value"])
            if self._on_change:
                self._on_change()
            self._refresh()

    def _refresh(self, hovered=None):
        selected = self._var.get()
        for s in self._segments:
            is_sel = s["value"] == selected
            is_hov = hovered is s and not is_sel
            if is_sel:
                self.itemconfigure(s["pill"], fill=C.ACCENT)
                self.itemconfigure(s["txt"], fill="#ffffff")
            elif is_hov:
                self.itemconfigure(s["pill"], fill=C.SURFACE_HI2)
                self.itemconfigure(s["txt"], fill=C.TEXT)
            else:
                self.itemconfigure(s["pill"], fill=C.SURFACE_HI)
                self.itemconfigure(s["txt"], fill=C.TEXT_DIM)


class ColorSwatch(tk.Canvas):
    def __init__(self, parent, initial="#ff3b30", size=32, command=None, bg_parent=None):
        pbg = bg_parent or parent.cget("bg")
        super().__init__(parent, width=size, height=size, bg=pbg,
                         highlightthickness=0, bd=0, cursor="hand2")
        self._size = size
        self._color = initial
        self._draw()
        if command:
            self.bind("<Button-1>", lambda e: command())

    def _draw(self):
        s = self._size
        self.delete("all")
        ring = _rounded_rect_points(1, 1, s - 1, s - 1, 8)
        self.create_polygon(ring, smooth=True, fill=C.BORDER, outline="")
        pts = _rounded_rect_points(3, 3, s - 3, s - 3, 6)
        self.create_polygon(pts, smooth=True, fill=self._color, outline="")

    def set_color(self, color):
        self._color = color
        self._draw()


class LogoMark(tk.Canvas):
    """Rounded-square brand mark with a gradient fill and 'C' glyph."""

    def __init__(self, parent, size=72, bg_parent=None):
        pbg = bg_parent or parent.cget("bg")
        super().__init__(parent, width=size, height=size, bg=pbg,
                         highlightthickness=0, bd=0)
        img = self._render(size, pbg)
        self._photo = ImageTk.PhotoImage(img)
        self.create_image(size // 2, size // 2, image=self._photo)

    @staticmethod
    def _render(size, pbg):
        r1, g1, b1 = _hex_to_rgb(C.LOGO_FROM)
        r2, g2, b2 = _hex_to_rgb(C.LOGO_TO)
        pb = _hex_to_rgb(pbg)
        img = Image.new("RGBA", (size, size), pb + (255,))
        grad = Image.new("RGB", (size, size))
        for y in range(size):
            t = y / max(1, size - 1)
            rr = int(r1 + (r2 - r1) * t)
            gg = int(g1 + (g2 - g1) * t)
            bb = int(b1 + (b2 - b1) * t)
            for x in range(size):
                grad.putpixel((x, y), (rr, gg, bb))
        mask = Image.new("L", (size, size), 0)
        ImageDraw.Draw(mask).rounded_rectangle(
            (0, 0, size - 1, size - 1), radius=size // 4, fill=255,
        )
        img.paste(grad, (0, 0), mask)

        # Draw the "C" glyph in PIL with precise bbox centering — avoids the
        # 1-2px drift you get from tk Canvas text with proportional fonts.
        d = ImageDraw.Draw(img)
        fnt = None
        for face in ("seguibd.ttf", "segoeuib.ttf", "arialbd.ttf"):
            try:
                fnt = ImageFont.truetype(face, int(size * 0.55))
                break
            except OSError:
                continue
        if fnt is None:
            fnt = ImageFont.load_default()
        d.text((size / 2, size / 2), "C", fill="white", font=fnt, anchor="mm")
        return img


# ============================================================ region selector

class RegionSelector:
    def __init__(self, on_done):
        self.on_done = on_done
        self.start = None
        self.rect_id = None
        self.hint_id = None

        self.vx, self.vy, self.vw, self.vh = get_virtual_screen()
        self.screen = ImageGrab.grab(all_screens=True)
        if self.screen.size != (self.vw, self.vh):
            self.screen = self.screen.resize((self.vw, self.vh), Image.LANCZOS)

        self.root = tk.Toplevel()
        self.root.overrideredirect(True)
        self.root.attributes("-topmost", True)
        self.root.geometry(f"{self.vw}x{self.vh}+{self.vx}+{self.vy}")
        self.root.configure(bg="black")

        # A neutral dim of the screen (no green cast, no stipple pattern).
        dim = ImageEnhance.Brightness(self.screen.convert("RGB")).enhance(0.38)
        self.tk_dim = ImageTk.PhotoImage(dim)
        self.tk_bright = ImageTk.PhotoImage(self.screen)

        self.canvas = tk.Canvas(self.root, cursor="cross",
                                highlightthickness=0, bg="black",
                                width=self.vw, height=self.vh)
        self.canvas.pack(fill=tk.BOTH, expand=True)
        self.canvas.create_image(0, 0, image=self.tk_dim, anchor="nw", tags="dim")
        self.bright_id = None  # shown inside the selection while dragging

        hint_text = "Drag to select   ·   Esc to cancel"
        hint_font = ("Segoe UI", 11, "bold")
        hx = self.vw // 2
        # Draw text first (hidden), measure its real bbox, size the pill to fit,
        # then layer pill below and raise text above it.
        text_id = self.canvas.create_text(hx, 38, text=hint_text,
                                          fill="#e8e8ec", font=hint_font)
        x1, y1, x2, y2 = self.canvas.bbox(text_id)
        pad_x, pad_y = 22, 12
        pill_pts = _rounded_rect_points(
            x1 - pad_x, y1 - pad_y, x2 + pad_x, y2 + pad_y, 14,
        )
        pill_id = self.canvas.create_polygon(
            pill_pts, smooth=True, fill="#18181d",
            outline=C.BORDER, width=1,
        )
        self.canvas.tag_raise(text_id, pill_id)

        self.canvas.bind("<ButtonPress-1>", self._on_press)
        self.canvas.bind("<B1-Motion>", self._on_drag)
        self.canvas.bind("<ButtonRelease-1>", self._on_release)
        self.root.bind("<Escape>", lambda e: self._cancel())
        self.root.after(30, self.root.focus_force)

    def _on_press(self, event):
        self.start = (event.x, event.y)
        self.rect_id = self.canvas.create_rectangle(
            event.x, event.y, event.x, event.y,
            outline=C.ACCENT_HI, width=2,
        )

    def _on_drag(self, event):
        if self.rect_id is None or self.start is None:
            return
        x1, y1 = self.start
        x2, y2 = event.x, event.y
        self.canvas.coords(self.rect_id, x1, y1, x2, y2)

        lx, rx = sorted((x1, x2))
        ty, by = sorted((y1, y2))
        if self.bright_id is not None:
            self.canvas.delete(self.bright_id)
            self.bright_id = None
        if rx - lx > 2 and by - ty > 2:
            crop = self.screen.crop((lx, ty, rx, by))
            self._bright_crop_pm = ImageTk.PhotoImage(crop)
            self.bright_id = self.canvas.create_image(
                lx, ty, image=self._bright_crop_pm, anchor="nw",
            )
            self.canvas.tag_raise(self.rect_id)

    def _on_release(self, event):
        if self.start is None:
            return
        x1, x2 = sorted((self.start[0], event.x))
        y1, y2 = sorted((self.start[1], event.y))
        if x2 - x1 < 5 or y2 - y1 < 5:
            self._cancel(); return
        x1 = max(0, min(x1, self.vw)); x2 = max(0, min(x2, self.vw))
        y1 = max(0, min(y1, self.vh)); y2 = max(0, min(y2, self.vh))
        cropped = self.screen.crop((x1, y1, x2, y2))
        self.root.destroy()
        self.on_done(cropped)

    def _cancel(self):
        self.root.destroy()
        self.on_done(None)


# ============================================================ editor

class Shape:
    __slots__ = ("kind", "coords", "color", "width", "text", "font_size", "canvas_ids")

    def __init__(self, kind, coords, color, width, text="", font_size=24):
        self.kind = kind
        self.coords = list(coords)
        self.color = color
        self.width = width
        self.text = text
        self.font_size = font_size
        self.canvas_ids = []


class EditorWindow:
    def __init__(self, image: Image.Image, on_close=None):
        self.original = image
        self.on_close = on_close

        self.shapes: list[Shape] = []
        self.current_shape: Shape | None = None
        self.tool = tk.StringVar(value="rect")
        self.color = "#f5365c"
        self.stroke = tk.IntVar(value=4)
        self.resize_mode = tk.StringVar(value="reduced")
        self.custom_max = tk.IntVar(value=MAX_DIM_DEFAULT)

        self.win = tk.Toplevel()
        self.win.title(f"{APP_NAME} — Editor")
        self.win.configure(bg=C.BG)
        self.win.protocol("WM_DELETE_WINDOW", self._close)

        self._build_toolbar()
        self._build_canvas()
        self._build_statusbar()

        self._fit_window()
        self.win.after(50, self.win.focus_force)

    # ---------- layout ----------

    TOOLBAR_H = 68
    ITEM_H = 38

    def _build_toolbar(self):
        bar = tk.Frame(self.win, bg=C.SURFACE, height=self.TOOLBAR_H)
        bar.pack(side=tk.TOP, fill=tk.X)
        bar.pack_propagate(False)

        left = tk.Frame(bar, bg=C.SURFACE)
        left.pack(side=tk.LEFT, padx=16, fill=tk.Y)

        H = self.ITEM_H
        SegmentedControl(
            left,
            [("Rect", "rect"), ("Arrow", "arrow"), ("Text", "text")],
            variable=self.tool, bg_parent=C.SURFACE,
            padx=16, pady=6, font=FONT_UI_BOLD, height=H,
        ).pack(side=tk.LEFT, anchor="center")

        self._vsep(left)

        self.color_swatch = ColorSwatch(
            left, initial=self.color, size=H,
            command=self._pick_color, bg_parent=C.SURFACE,
        )
        self.color_swatch.pack(side=tk.LEFT, padx=(0, 10), anchor="center")

        tk.Label(left, text="Size", bg=C.SURFACE, fg=C.TEXT_MUTED,
                 font=FONT_SMALL).pack(side=tk.LEFT, padx=(0, 6), anchor="center")
        SegmentedControl(
            left,
            [("S", 2), ("M", 4), ("L", 7), ("XL", 11)],
            variable=self.stroke, bg_parent=C.SURFACE,
            padx=11, pady=6, font=FONT_UI_BOLD, height=H,
        ).pack(side=tk.LEFT, anchor="center")

        self._vsep(left)

        RoundedButton(left, text="Undo", variant="ghost",
                      command=self._undo, padx=14, radius=8,
                      height=H, bg_parent=C.SURFACE
                      ).pack(side=tk.LEFT, padx=2, anchor="center")
        RoundedButton(left, text="Clear", variant="ghost",
                      command=self._clear, padx=14, radius=8,
                      height=H, bg_parent=C.SURFACE
                      ).pack(side=tk.LEFT, padx=2, anchor="center")

        right = tk.Frame(bar, bg=C.SURFACE)
        right.pack(side=tk.RIGHT, padx=16, fill=tk.Y)

        RoundedButton(right, text="Copy", variant="primary",
                      command=self._copy, padx=24, radius=10,
                      height=H, bg_parent=C.SURFACE
                      ).pack(side=tk.RIGHT, padx=(6, 0), anchor="center")
        RoundedButton(right, text="Save", variant="secondary",
                      command=self._save, padx=18, radius=10,
                      height=H, bg_parent=C.SURFACE
                      ).pack(side=tk.RIGHT, padx=(0, 8), anchor="center")

        tk.Frame(self.win, bg=C.BORDER, height=1).pack(side=tk.TOP, fill=tk.X)

    def _vsep(self, parent):
        wrap = tk.Frame(parent, bg=C.SURFACE)
        wrap.pack(side=tk.LEFT, padx=14, anchor="center")
        sep = tk.Frame(wrap, bg=C.BORDER, width=1, height=self.ITEM_H - 10)
        sep.pack()

    def _build_canvas(self):
        body = tk.Frame(self.win, bg=C.BG)
        body.pack(fill=tk.BOTH, expand=True)

        self.canvas = tk.Canvas(body, bg=C.BG, highlightthickness=0, cursor="cross")
        self.canvas.pack(fill=tk.BOTH, expand=True, padx=12, pady=12)

        self.canvas.bind("<ButtonPress-1>", self._on_press)
        self.canvas.bind("<B1-Motion>", self._on_drag)
        self.canvas.bind("<ButtonRelease-1>", self._on_release)

        self.win.bind("<Control-z>", lambda e: self._undo())
        self.win.bind("<Control-c>", lambda e: self._copy())
        self.win.bind("<Control-s>", lambda e: self._save())

        self.display_img = None
        self.display_scale = 1.0
        self.win.bind("<Configure>", self._on_resize)
        self._render_base()

    def _build_statusbar(self):
        tk.Frame(self.win, bg=C.BORDER, height=1).pack(side=tk.BOTTOM, fill=tk.X)

        bar = tk.Frame(self.win, bg=C.SURFACE, height=self.TOOLBAR_H)
        bar.pack(side=tk.BOTTOM, fill=tk.X)
        bar.pack_propagate(False)

        H = self.ITEM_H

        left = tk.Frame(bar, bg=C.SURFACE)
        left.pack(side=tk.LEFT, padx=16, fill=tk.Y)

        w, h = self.original.size
        tk.Label(left, text=f"Source  {w}×{h}", bg=C.SURFACE,
                 fg=C.TEXT_MUTED, font=FONT_SMALL
                 ).pack(side=tk.LEFT, padx=(0, 14), anchor="center")

        tk.Label(left, text="Resolution", bg=C.SURFACE, fg=C.TEXT_DIM,
                 font=FONT_LABEL).pack(side=tk.LEFT, padx=(0, 8), anchor="center")

        SegmentedControl(
            left,
            [("Reduced", "reduced"), ("Original", "original"), ("Custom", "custom")],
            variable=self.resize_mode, on_change=self._update_output_label,
            bg_parent=C.SURFACE, padx=14, pady=6, font=FONT_UI_BOLD, height=H,
        ).pack(side=tk.LEFT, anchor="center")

        tk.Label(left, text="max", bg=C.SURFACE, fg=C.TEXT_MUTED,
                 font=FONT_SMALL).pack(side=tk.LEFT, padx=(14, 6), anchor="center")
        spin_wrap = tk.Frame(left, bg=C.SURFACE)
        spin_wrap.pack(side=tk.LEFT, anchor="center")
        spin = tk.Spinbox(
            spin_wrap, from_=200, to=4000, increment=100,
            textvariable=self.custom_max, width=5,
            bg=C.SURFACE_HI, fg=C.TEXT,
            relief=tk.FLAT, bd=0,
            insertbackground=C.TEXT,
            buttonbackground=C.SURFACE_HI,
            highlightthickness=1, highlightbackground=C.BORDER,
            highlightcolor=C.ACCENT,
            font=FONT_SMALL,
            command=self._update_output_label,
        )
        spin.pack(ipady=6)

        right = tk.Frame(bar, bg=C.SURFACE)
        right.pack(side=tk.RIGHT, padx=16, fill=tk.Y)

        self.output_label = tk.Label(right, text="", bg=C.SURFACE,
                                     fg=C.SUCCESS, font=FONT_UI_BOLD)
        self.output_label.pack(side=tk.RIGHT, anchor="center")
        self._update_output_label()

    def _fit_window(self):
        sw = self.win.winfo_screenwidth()
        sh = self.win.winfo_screenheight()
        w = min(1400, int(sw * 0.85))
        h = min(900, int(sh * 0.85))
        w = max(w, 860); h = max(h, 580)
        x = max(0, (sw - w) // 2)
        y = max(0, (sh - h) // 2)
        self.win.geometry(f"{w}x{h}+{x}+{y}")

    # ---------- rendering ----------

    def _render_base(self):
        self.win.update_idletasks()
        cw = max(self.canvas.winfo_width(), 100)
        ch = max(self.canvas.winfo_height(), 100)
        iw, ih = self.original.size
        scale = min(cw / iw, ch / ih, 1.0)
        dw, dh = max(1, int(iw * scale)), max(1, int(ih * scale))
        self.display_scale = scale

        preview = self.original.resize((dw, dh), Image.LANCZOS)
        self.display_img = ImageTk.PhotoImage(preview)
        self.canvas.delete("all")
        ox = (cw - dw) // 2
        oy = (ch - dh) // 2
        self._img_offset = (ox, oy)
        self.canvas.create_image(ox, oy, image=self.display_img, anchor="nw", tags="base")
        for shape in self.shapes:
            self._draw_shape_on_canvas(shape)

    def _on_resize(self, event):
        if event.widget is self.win:
            self._render_base()

    def _c(self, x, y):
        ox, oy = self._img_offset
        return x * self.display_scale + ox, y * self.display_scale + oy

    def _i(self, x, y):
        ox, oy = self._img_offset
        return (x - ox) / self.display_scale, (y - oy) / self.display_scale

    def _draw_shape_on_canvas(self, shape: Shape):
        shape.canvas_ids = []
        if shape.kind == "rect":
            x1, y1, x2, y2 = shape.coords
            cx1, cy1 = self._c(x1, y1); cx2, cy2 = self._c(x2, y2)
            cid = self.canvas.create_rectangle(
                cx1, cy1, cx2, cy2, outline=shape.color,
                width=max(1, shape.width * self.display_scale),
            )
            shape.canvas_ids.append(cid)
        elif shape.kind == "arrow":
            x1, y1, x2, y2 = shape.coords
            cx1, cy1 = self._c(x1, y1); cx2, cy2 = self._c(x2, y2)
            cid = self.canvas.create_line(
                cx1, cy1, cx2, cy2, fill=shape.color,
                width=max(1, shape.width * self.display_scale),
                arrow=tk.LAST, arrowshape=(14, 16, 6),
            )
            shape.canvas_ids.append(cid)
        elif shape.kind == "text":
            x, y = shape.coords[:2]
            cx, cy = self._c(x, y)
            cid = self.canvas.create_text(
                cx, cy, text=shape.text, anchor="nw", fill=shape.color,
                font=("Segoe UI", max(8, int(shape.font_size * self.display_scale)), "bold"),
            )
            shape.canvas_ids.append(cid)

    # ---------- drawing events ----------

    def _on_press(self, event):
        tool = self.tool.get()
        ix, iy = self._i(event.x, event.y)
        if tool == "text":
            self._insert_text(ix, iy); return
        self.current_shape = Shape(
            kind=tool, coords=[ix, iy, ix, iy],
            color=self.color, width=self.stroke.get(),
        )
        self._draw_shape_on_canvas(self.current_shape)

    def _on_drag(self, event):
        if self.current_shape is None:
            return
        ix, iy = self._i(event.x, event.y)
        self.current_shape.coords[2] = ix
        self.current_shape.coords[3] = iy
        for cid in self.current_shape.canvas_ids:
            self.canvas.delete(cid)
        self._draw_shape_on_canvas(self.current_shape)

    def _on_release(self, event):
        if self.current_shape is None:
            return
        x1, y1, x2, y2 = self.current_shape.coords
        if abs(x2 - x1) < 3 and abs(y2 - y1) < 3:
            for cid in self.current_shape.canvas_ids:
                self.canvas.delete(cid)
        else:
            self.shapes.append(self.current_shape)
        self.current_shape = None

    def _insert_text(self, ix, iy):
        popup = tk.Toplevel(self.win)
        popup.title("Add text")
        popup.configure(bg=C.SURFACE)
        popup.transient(self.win); popup.grab_set()
        popup.resizable(False, False)

        frame = tk.Frame(popup, bg=C.SURFACE, padx=22, pady=20)
        frame.pack()

        tk.Label(frame, text="TEXT", bg=C.SURFACE, fg=C.TEXT_DIM,
                 font=FONT_LABEL).pack(anchor="w")
        entry = tk.Entry(frame, width=36, bg=C.SURFACE_HI, fg=C.TEXT,
                         relief=tk.FLAT, bd=0, insertbackground=C.TEXT,
                         highlightthickness=1, highlightbackground=C.BORDER,
                         highlightcolor=C.ACCENT, font=FONT_UI)
        entry.pack(fill=tk.X, pady=(6, 14), ipady=8, ipadx=8)
        entry.focus_set()

        size_var = tk.IntVar(value=24)
        row = tk.Frame(frame, bg=C.SURFACE)
        row.pack(fill=tk.X, pady=(0, 16))
        tk.Label(row, text="SIZE", bg=C.SURFACE, fg=C.TEXT_DIM,
                 font=FONT_LABEL).pack(side=tk.LEFT)
        tk.Spinbox(row, from_=10, to=96, textvariable=size_var, width=5,
                   bg=C.SURFACE_HI, fg=C.TEXT, relief=tk.FLAT, bd=0,
                   insertbackground=C.TEXT, buttonbackground=C.SURFACE_HI,
                   highlightthickness=1, highlightbackground=C.BORDER,
                   highlightcolor=C.ACCENT, font=FONT_SMALL
                   ).pack(side=tk.LEFT, padx=10, ipady=4)

        def commit():
            val = entry.get().strip()
            if val:
                shape = Shape(kind="text", coords=[ix, iy], color=self.color,
                              width=self.stroke.get(), text=val,
                              font_size=size_var.get())
                self.shapes.append(shape)
                self._draw_shape_on_canvas(shape)
            popup.destroy()

        entry.bind("<Return>", lambda e: commit())

        btn_row = tk.Frame(frame, bg=C.SURFACE)
        btn_row.pack(fill=tk.X)
        RoundedButton(btn_row, text="Add", variant="primary",
                      command=commit, padx=16, pady=8, radius=8,
                      bg_parent=C.SURFACE).pack(side=tk.RIGHT)
        RoundedButton(btn_row, text="Cancel", variant="secondary",
                      command=popup.destroy, padx=16, pady=8, radius=8,
                      bg_parent=C.SURFACE).pack(side=tk.RIGHT, padx=(0, 8))

    # ---------- toolbar actions ----------

    def _pick_color(self):
        _, hexcode = colorchooser.askcolor(color=self.color, parent=self.win)
        if hexcode:
            self.color = hexcode
            self.color_swatch.set_color(hexcode)

    def _undo(self):
        if not self.shapes:
            return
        shape = self.shapes.pop()
        for cid in shape.canvas_ids:
            self.canvas.delete(cid)

    def _clear(self):
        for shape in self.shapes:
            for cid in shape.canvas_ids:
                self.canvas.delete(cid)
        self.shapes.clear()

    # ---------- output ----------

    def _output_size(self):
        iw, ih = self.original.size
        mode = self.resize_mode.get()
        if mode == "original":
            return iw, ih
        if mode == "reduced":
            cap = MAX_DIM_DEFAULT
        else:
            cap = max(100, self.custom_max.get())
        big = max(iw, ih)
        if big <= cap:
            return iw, ih
        scale = cap / big
        return max(1, int(iw * scale)), max(1, int(ih * scale))

    def _update_output_label(self):
        ow, oh = self._output_size()
        self.output_label.configure(text=f"Output  {ow}×{oh}", fg=C.TEXT_DIM)

    def _compose_image(self) -> Image.Image:
        img = self.original.convert("RGBA").copy()
        draw = ImageDraw.Draw(img)
        for shape in self.shapes:
            self._draw_shape_on_pil(draw, shape)
        ow, oh = self._output_size()
        if (ow, oh) != img.size:
            img = img.resize((ow, oh), Image.LANCZOS)
        return img

    def _draw_shape_on_pil(self, draw, shape):
        if shape.kind == "rect":
            x1, y1, x2, y2 = shape.coords
            x1, x2 = sorted((x1, x2)); y1, y2 = sorted((y1, y2))
            draw.rectangle((x1, y1, x2, y2), outline=shape.color, width=shape.width)
        elif shape.kind == "arrow":
            x1, y1, x2, y2 = shape.coords
            draw.line((x1, y1, x2, y2), fill=shape.color, width=shape.width)
            self._draw_arrowhead(draw, x1, y1, x2, y2, shape.color, shape.width)
        elif shape.kind == "text":
            x, y = shape.coords[:2]
            try:
                fnt = ImageFont.truetype("seguibd.ttf", shape.font_size)
            except OSError:
                try:
                    fnt = ImageFont.truetype("arialbd.ttf", shape.font_size)
                except OSError:
                    fnt = ImageFont.load_default()
            draw.text((x, y), shape.text, fill=shape.color, font=fnt)

    @staticmethod
    def _draw_arrowhead(draw, x1, y1, x2, y2, color, width):
        angle = math.atan2(y2 - y1, x2 - x1)
        length = max(12, width * 4)
        spread = math.radians(28)
        lx = x2 - length * math.cos(angle - spread)
        ly = y2 - length * math.sin(angle - spread)
        rx = x2 - length * math.cos(angle + spread)
        ry = y2 - length * math.sin(angle + spread)
        draw.polygon([(x2, y2), (lx, ly), (rx, ry)], fill=color)

    def _copy(self):
        try:
            img = self._compose_image()
            copy_image_to_clipboard(img)
            self._flash_status("Copied to clipboard", C.SUCCESS)
        except Exception as exc:
            messagebox.showerror("Copy failed", str(exc), parent=self.win)

    def _save(self):
        path = filedialog.asksaveasfilename(
            parent=self.win,
            defaultextension=".png",
            filetypes=[("PNG", "*.png"), ("JPEG", "*.jpg"), ("All files", "*.*")],
            initialfile="clip.png",
        )
        if not path:
            return
        try:
            img = self._compose_image()
            if path.lower().endswith((".jpg", ".jpeg")):
                img.convert("RGB").save(path, quality=92)
            else:
                img.save(path)
            self._flash_status("Saved", C.SUCCESS)
        except Exception as exc:
            messagebox.showerror("Save failed", str(exc), parent=self.win)

    def _flash_status(self, msg, color):
        self.output_label.configure(text=msg, fg=color)
        self.win.after(1800, self._update_output_label)

    def _close(self):
        if self.on_close:
            self.on_close()
        self.win.destroy()


# ============================================================ launcher

class App:
    def __init__(self):
        self.root = tk.Tk()
        _apply_tk_scaling(self.root)
        self.root.title(APP_NAME)
        self.root.configure(bg=C.BG)
        self.root.protocol("WM_DELETE_WINDOW", self._hide_to_tray)

        w, h = 420, 400
        sw = self.root.winfo_screenwidth()
        sh = self.root.winfo_screenheight()
        self.root.geometry(f"{w}x{h}+{(sw - w) // 2}+{(sh - h) // 3}")
        self.root.resizable(False, False)

        # Column layout via grid — a single column, all cells sticky="" so
        # children sit centered horizontally regardless of their intrinsic width.
        outer = tk.Frame(self.root, bg=C.BG)
        outer.pack(fill=tk.BOTH, expand=True, padx=36, pady=28)
        outer.columnconfigure(0, weight=1)

        row = 0
        LogoMark(outer, size=76, bg_parent=C.BG).grid(
            row=row, column=0, pady=(4, 16)); row += 1

        tk.Label(outer, text=APP_NAME, bg=C.BG, fg=C.TEXT,
                 font=FONT_TITLE).grid(row=row, column=0); row += 1
        tk.Label(outer, text=APP_BRAND, bg=C.BG, fg=C.ACCENT_HI,
                 font=("Segoe UI", 10, "bold")
                 ).grid(row=row, column=0, pady=(2, 0)); row += 1
        tk.Label(outer, text=APP_TAGLINE, bg=C.BG, fg=C.TEXT_MUTED,
                 font=FONT_SMALL).grid(row=row, column=0, pady=(12, 0)); row += 1

        RoundedButton(outer, text="Capture screen", variant="primary",
                      command=self.new_snip, padx=30, pady=13, radius=12,
                      font=("Segoe UI", 11, "bold"),
                      bg_parent=C.BG).grid(row=row, column=0, pady=(20, 10))
        row += 1

        hint = tk.Frame(outer, bg=C.BG)
        hint.grid(row=row, column=0, pady=(6, 0))
        tk.Label(hint, text="or press", bg=C.BG, fg=C.TEXT_MUTED,
                 font=FONT_HINT).pack(side=tk.LEFT)

        kc = tk.Canvas(hint, width=138, height=26, bg=C.BG,
                       highlightthickness=0, bd=0)
        kc.pack(side=tk.LEFT, padx=8)
        kp = _rounded_rect_points(1, 1, 137, 25, 6)
        kc.create_polygon(kp, smooth=True, fill=C.SURFACE_HI,
                          outline=C.BORDER, width=1)
        kc.create_text(69, 13, text="Ctrl  +  Shift  +  S",
                       fill=C.TEXT_DIM, font=FONT_UI_BOLD)

        self.root.bind_all("<Control-Shift-S>", lambda e: self.new_snip())
        self.root.bind_all("<Control-Shift-s>", lambda e: self.new_snip())

        self.tray = None
        self._was_visible = True
        self._setup_tray()
        self._register_global_hotkey()

    # ---------- capture flow ----------

    def new_snip(self):
        self._was_visible = bool(self.root.winfo_viewable())
        self.root.withdraw()
        self.root.after(180, self._begin_selection)

    def _begin_selection(self):
        def done(img):
            if self._was_visible:
                self.root.deiconify()
            if img is not None:
                EditorWindow(img)
        RegionSelector(done)

    # ---------- tray + always-on ----------

    def _tray_icon_image(self, size=64):
        r1, g1, b1 = _hex_to_rgb(C.LOGO_FROM)
        r2, g2, b2 = _hex_to_rgb(C.LOGO_TO)
        grad = Image.new("RGB", (size, size))
        for y in range(size):
            t = y / max(1, size - 1)
            rr = int(r1 + (r2 - r1) * t)
            gg = int(g1 + (g2 - g1) * t)
            bb = int(b1 + (b2 - b1) * t)
            for x in range(size):
                grad.putpixel((x, y), (rr, gg, bb))
        img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
        mask = Image.new("L", (size, size), 0)
        ImageDraw.Draw(mask).rounded_rectangle(
            (0, 0, size - 1, size - 1), radius=size // 4, fill=255)
        img.paste(grad, (0, 0), mask)
        d = ImageDraw.Draw(img)
        try:
            fnt = ImageFont.truetype("seguibd.ttf", int(size * 0.55))
        except OSError:
            fnt = ImageFont.load_default()
        bbox = d.textbbox((0, 0), "C", font=fnt)
        tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
        d.text(((size - tw) // 2 - bbox[0], (size - th) // 2 - bbox[1] - 1),
               "C", fill="white", font=fnt)
        return img

    def _setup_tray(self):
        if not HAS_TRAY:
            return
        Item = pystray.MenuItem
        menu = pystray.Menu(
            Item("Capture screen", self._tray_capture, default=True),
            Item("Show window", self._tray_show),
            pystray.Menu.SEPARATOR,
            Item("Quit Clipper", self._tray_quit),
        )
        self.tray = pystray.Icon(
            "Clipper", self._tray_icon_image(),
            "Clipper by Flexibles AI  ·  Ctrl+Shift+S", menu,
        )
        threading.Thread(target=self.tray.run, daemon=True).start()

    def _register_global_hotkey(self):
        if not HAS_HOTKEY:
            return
        try:
            kb.add_hotkey("ctrl+shift+s",
                          lambda: self.root.after(0, self.new_snip))
        except Exception as exc:
            # Non-fatal: the in-window binding still works.
            sys.stderr.write(f"[Clipper] global hotkey disabled: {exc}\n")

    def _hide_to_tray(self):
        # Only hide if we have a tray to return from.
        if self.tray is not None:
            self.root.withdraw()
        else:
            self._tray_quit()

    def _tray_capture(self, icon=None, item=None):
        self.root.after(0, self.new_snip)

    def _tray_show(self, icon=None, item=None):
        self.root.after(0, self._show_window)

    def _show_window(self):
        self.root.deiconify()
        self.root.lift()
        self.root.focus_force()
        self.root.attributes("-topmost", True)
        self.root.after(200, lambda: self.root.attributes("-topmost", False))

    def _tray_quit(self, icon=None, item=None):
        if HAS_HOTKEY:
            try:
                kb.unhook_all_hotkeys()
            except Exception:
                pass
        if self.tray is not None:
            try:
                self.tray.stop()
            except Exception:
                pass
        self.root.after(0, self.root.destroy)

    def run(self):
        self.root.mainloop()


if __name__ == "__main__":
    if sys.platform != "win32":
        print("This tool targets Windows (clipboard uses pywin32).")
    enable_dpi_awareness()
    App().run()
