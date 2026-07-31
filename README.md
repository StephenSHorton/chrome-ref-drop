# Chrome Reference Drop

Blender add-on that turns **browser images** into **reference image empties** in the current scene.

Target: **Blender 4.2+ / 5.x** (tested on **5.2 LTS**).

## Download

Installable zips are built by GitHub Actions:

| Channel | Where |
|---|---|
| **Latest release** | [Releases](https://github.com/StephenSHorton/chrome-ref-drop/releases/latest) — grab `chrome_ref_drop-*.zip` |
| **Every main commit** | [Actions → Build plugin](https://github.com/StephenSHorton/chrome-ref-drop/actions/workflows/build-plugin.yml) → latest run → Artifacts → `chrome-ref-drop-plugin` |

Tag a version to publish a Release:

```bash
git tag v0.1.0
git push origin v0.1.0
```

## The problem

| Source | What Blender gets | Stock Blender |
|---|---|---|
| File Explorer image drop | Local path | Already creates a reference empty |
| Chrome drag (temp file) | Local path | Already works |
| Chrome drag (URL / HTML only) | Not a file | **Nothing** — Python never sees a path |
| Chrome **Copy image** | PNG/DIB on clipboard | **Nothing** (text clipboard only) |
| Image address URL | Text | **Nothing** |

This add-on fills the browser gaps: **clipboard paste** and **URL download**.

## Install

1. Download `chrome_ref_drop-*.zip` from [Releases](https://github.com/StephenSHorton/chrome-ref-drop/releases/latest) (or build locally — see below).
2. Blender → **Edit → Preferences → Extensions** (or Add-ons) → **Install from Disk**
3. Pick the zip
4. Enable **Chrome Reference Drop**
5. For URL downloads: **Preferences → System → Network → Allow Online Access**

### Build the zip locally

```bash
python scripts/package.py
# → dist/chrome_ref_drop-<version>.zip
```

Dev load without install: put the parent of `chrome_ref_drop` on `sys.path` and `import chrome_ref_drop; chrome_ref_drop.register()`.

## Usage (recommended workflow)

### Best quality — Copy image → paste

1. Chrome: **right-click image → Copy image**
2. Blender 3D View: **Ctrl+Shift+V**

Also available as:

- **Object → Reference Images → Paste from Clipboard**
- **Add → Reference Image (Clipboard)**

### From URL

**Object → Reference Images → From URL…**  
(Dialog pre-fills from the text clipboard when it looks like a URL.)

### Import files

**Object → Reference Images → Import File(s)…**

### Drag-and-drop

- **Local / temp files:** use Blender’s built-in image empty drop (already reference empties).
- **Optional override:** Preferences → Chrome Reference Drop → **Also Handle File Drops**  
  Registers our FileHandler (may show a drop chooser next to the built-in).

## Preferences

| Setting | Purpose |
|---|---|
| Download Cache | Where URL / clipboard images are saved |
| Default Size | Empty display size |
| Align to View | Face the active viewport |
| Image Depth | Default / Front / Back |
| Also Handle File Drops | Optional competing FileHandler |

## Project layout

```
chrome-ref-drop/
  README.md
  LICENSE
  scripts/package.py              # builds installable zip
  .github/workflows/build-plugin.yml
  chrome_ref_drop/
    __init__.py
    blender_manifest.toml
    util.py            # resolve path/URL, download, create empty
    operators.py       # path / URL / clipboard / file browser
    drop.py            # optional FileHandler
    clipboard_win.py   # Windows PNG + DIB clipboard
    prefs.py           # preferences + menus
```

## CI

On every push/PR to `main`, Actions builds `chrome_ref_drop-<version>.zip` and uploads it as a workflow artifact.

Pushing a tag `v*` (e.g. `v0.1.0`) also creates a **GitHub Release** with the zip attached for public download.

## Smoke tests (already verified in Blender 5.2)

- Local PNG → IMAGE empty  
- `data:image/png;base64,…` → cached file + empty  
- `https://…png` download → empty  
- Clipboard paste operator → empty  

## Known limits

- **URL-only OS drag** is not available to `bpy.types.FileHandler`. No pure-Python fix; paste/URL is the reliable path.
- **`blob:` URLs** cannot be fetched from Blender — use **Copy image**.
- **Google Images** grid thumbs are often redirects/thumbnails; prefer **Copy image** or open the full image first.
- Clipboard **pixel** paste is **Windows-only** for now (PNG + DIB). Text/URL paste works everywhere Blender runs.

## Roadmap

- [ ] macOS / Linux clipboard image paste  
- [ ] Place under mouse when drop coords exist  
- [ ] Modes: reference empty / background / image-as-plane  
- [ ] Pack into `.blend` on import  
- [ ] Optional Chrome helper extension that force-saves then drops a real file  

## License

GPL-3.0-or-later.
