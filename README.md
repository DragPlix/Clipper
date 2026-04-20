# Clipper

**Screenshot → annotate → copy.** A tiny Windows tool for grabbing a region of your screen, drawing on it, and pasting it anywhere — with one-click control over the output resolution so images never trip the 2000px limit in tools like Claude Code.

Built by [Flexibles AI](https://flexibles.ai).

---

## Download

| | What you get | When to use |
|---|---|---|
| **[Clipper-Setup-1.0.0.exe](./Clipper-Setup-1.0.0.exe)** | Installer (31 MB) | Normal install: Start Menu shortcut, optional auto-start, clean uninstall from Add/Remove Programs |
| **[Clipper.exe](./Clipper.exe)** | Portable single file (30 MB) | Just run it, no install. Good for a flash drive or a quick try |

> **Windows will warn "unrecognized app" on first run.** That's because Clipper isn't code-signed yet (those certs cost money). Click **More info → Run anyway**. The source is in this repo — inspect anything you want.

---

## Features

- **Region capture** across multiple monitors, with DPI awareness so the pixels match what you see.
- **Annotation tools**: rectangle, arrow, text, color picker, stroke size.
- **Resolution control**:
  - *Reduced* — caps the longest side at 1900 px (stays safely under Claude's 2000px many-image limit).
  - *Original* — no resize.
  - *Custom* — pick your own max dimension.
  - Aspect ratio is always preserved.
- **Clipboard copy** — paste straight into Claude, Slack, email, GitHub issues, anywhere that accepts images.
- **Always-on**: closes to the system tray, global hotkey `Ctrl+Shift+S` from anywhere.
- **Cleanly dimmed selection overlay** — Windows-Snipping-Tool style, with the selected region shown bright.

---

## Keyboard shortcuts

| Shortcut | Action |
|---|---|
| `Ctrl+Shift+S` (global) | New capture |
| `Ctrl+C` (in editor) | Copy to clipboard |
| `Ctrl+S` (in editor) | Save to file |
| `Ctrl+Z` (in editor) | Undo last annotation |
| `Esc` (in selector) | Cancel |

---

## Building from source

**Requirements:** Python 3.13+, Windows 10/11.

```bash
pip install pillow pywin32 pystray keyboard pyinstaller
```

**Run directly:**

```bash
python clipper.py
```

**Build the portable exe:**

```bash
python -m PyInstaller --noconfirm --onefile --windowed --name Clipper --collect-all pystray clipper.py
```

Output: `dist/Clipper.exe`.

**Build the installer** (requires [Inno Setup 6](https://jrsoftware.org/isinfo.php) at its default path):

```bash
"%LOCALAPPDATA%\Programs\Inno Setup 6\ISCC.exe" installer.iss
```

Output: `dist/Clipper-Setup-<version>.exe`.

---

## Project layout

```
clipper.py           Main application — single file, ~900 lines
installer.iss        Inno Setup script for the installer build
Clipper.exe          Prebuilt portable binary
Clipper-Setup-*.exe  Prebuilt installer
```

---

## License

[MIT](./LICENSE) — do what you want.
