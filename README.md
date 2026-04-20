# Clipper

**Screenshot → annotate → copy.** A tiny Windows tool for grabbing a region of your screen, drawing on it, and pasting it anywhere — with one-click control over the output resolution so images never trip the 2000px limit in tools like Claude Code.

Built by [Flexibles AI](https://flexibles.ai).

---

## Download

| | What you get | When to use |
|---|---|---|
| **[Clipper-Setup-1.0.0.exe](./Clipper-Setup-1.0.0.exe)** | Installer (31 MB) | Normal install: Start Menu shortcut, optional auto-start, clean uninstall from Add/Remove Programs |
| **[Clipper.exe](./Clipper.exe)** | Portable single file (30 MB) | Just run it, no install. Good for a flash drive or a quick try |

> To download: click the file above, then click the **Download** button (or the download icon ⬇️) on the GitHub file page.

> **Windows will warn "unrecognized app" on first run.** That's because Clipper isn't code-signed yet (those certs cost money). Click **More info → Run anyway**. The source is in this repo — inspect anything you want.

---

## Install

**Option A — Installer (recommended)**

1. Download [Clipper-Setup-1.0.0.exe](./Clipper-Setup-1.0.0.exe).
2. Double-click it. If Windows SmartScreen warns you, click **More info → Run anyway**.
3. The wizard installs per-user (no admin prompt). Check the boxes if you want a **Desktop shortcut** or **Start with Windows**.
4. Click **Install → Finish**. Clipper will launch automatically.

**Option B — Portable**

1. Download [Clipper.exe](./Clipper.exe).
2. Put it anywhere (Desktop, `C:\Tools\`, a USB stick — your call).
3. Double-click to run. Same SmartScreen bypass on first run.

**Uninstalling**: if you used the installer, open **Settings → Apps → Installed apps**, find **Clipper**, click **Uninstall**. If you used the portable exe, just delete the file.

---

## How to use

### 1. Take a screenshot

Three ways to start a capture:

- Click **Capture screen** in the Clipper window, or
- Press **`Ctrl + Shift + S`** from anywhere on your system, or
- **Right-click the tray icon** (bottom-right of your taskbar) → **Capture screen**.

A dark overlay appears across all your monitors. **Click and drag** to select a region — the area inside the selection lights up so you can see exactly what you're grabbing. Press **`Esc`** to cancel.

### 2. Annotate (optional)

The editor opens with your snip. In the top toolbar:

- **Rect / Arrow / Text** — pick what to draw, then click-drag on the image (for Text, click where you want the text and type it into the popup).
- **Color swatch** — click to pick a color for new annotations.
- **Size S / M / L / XL** — stroke thickness for rectangles and arrows.
- **Undo** — remove the last annotation (or press `Ctrl+Z`).
- **Clear** — wipe all annotations.

### 3. Pick an output size

The bottom bar has three resolution modes:

- **Reduced** (default) — caps the longest side at 1900 px so it slips under Claude Code's 2000 px many-image limit. Aspect ratio is preserved.
- **Original** — keep the full captured resolution.
- **Custom** — type your own max dimension in the `max` box.

The **Output** label on the right shows exactly what size you'll get.

### 4. Copy or save

- **Copy** (or `Ctrl+C`) puts the image on your clipboard. Paste it into Claude Code, Slack, email, a GitHub comment, anywhere.
- **Save** (or `Ctrl+S`) writes a `.png` or `.jpg` file.

### 5. Keep it running in the background

When you close the Clipper window with the **×**, it hides to the system tray instead of quitting — so the `Ctrl+Shift+S` hotkey keeps working. To fully exit: right-click the tray icon → **Quit Clipper**.

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
