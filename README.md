# Chrome Reference Drop

**Browser image → Blender reference empty.**  
Copy from Chrome, paste in the 3D View. No “save to Desktop” detour.

<p align="center">
  <a href="https://stephenshorton.github.io/chrome-ref-drop/">
    <img src="https://img.shields.io/badge/Drag%20%26%20Drop-into%20Blender-ea7600?style=for-the-badge&logo=blender&logoColor=white" alt="Drag and Drop into Blender" />
  </a>
  &nbsp;
  <a href="https://github.com/StephenSHorton/chrome-ref-drop/releases/latest">
    <img src="https://img.shields.io/github/v/release/StephenSHorton/chrome-ref-drop?style=for-the-badge&color=2f81f7" alt="Latest release" />
  </a>
  &nbsp;
  <a href="https://github.com/StephenSHorton/chrome-ref-drop/actions/workflows/build-plugin.yml">
    <img src="https://img.shields.io/github/actions/workflow/status/StephenSHorton/chrome-ref-drop/build-plugin.yml?branch=main&style=for-the-badge&label=CI" alt="CI" />
  </a>
</p>

---

## Install — drag into Blender

Same idea as [Blender Lab’s MCP Server page](https://www.blender.org/lab/mcp-server/): Blender accepts a **zip download URL** with extension metadata on the query string.

### Best UX (styled button)

Open the landing page, then **drag the orange button into Blender**:

### 👉 [stephenshorton.github.io/chrome-ref-drop](https://stephenshorton.github.io/chrome-ref-drop/)

### Drag this link (from GitHub too)

> **[⧉ Drag and Drop into Blender](https://stephenshorton.github.io/chrome-ref-drop/chrome_ref_drop-latest.zip?repository=https%3A%2F%2Fstephenshorton.github.io%2Fchrome-ref-drop%2Findex.json&blender_version_min=4.2.0)**

Click-hold the link above and drop it onto a Blender window (or Preferences → Get Extensions). You should get Blender’s install confirmation dialog.

**Why Pages, not GitHub Releases?** Release download URLs redirect through a CDN; the final URL no longer ends in `.zip` and drops `?repository=` query params, so Blender ignores the drop. The zip on GitHub Pages is a direct file.

**Tip:** like the official MCP add-on, you may need to **drop twice** — first to add the update repository, second to install the extension.

…or [download the zip](https://stephenshorton.github.io/chrome-ref-drop/chrome_ref_drop-latest.zip) and use **Install from Disk**.

**Requires** Blender **4.2+** (tested on **5.2 LTS**).  
For URL downloads: **Preferences → System → Network → Allow Online Access**.

---

## What you get

```
Chrome                              Blender
──────                              ───────
Right-click image                   3D View
  → Copy image          ──Ctrl+Shift+V──►   Reference empty
                                              (IMAGE empty, view-aligned)
```

| You try | Stock Blender | This add-on |
|---|---|---|
| Drop a file from Explorer | Reference empty ✓ | Also works |
| Chrome **Copy image** | Nothing | **Ctrl+Shift+V** |
| Paste image URL | Nothing | Downloads → reference |
| URL-only browser drag | No Python hook | Use paste / From URL |

### Menus & shortcuts

| Action | Where |
|---|---|
| Paste reference | **Ctrl+Shift+V** in the 3D View |
| Paste / URL / Import | **Object → Reference Images** |
| Clipboard from Add menu | **Add → Reference Image (Clipboard)** |

---

## Why not “just drag from Chrome”?

Blender’s Python `FileHandler` only sees **file paths**. When Chrome only offers a URL or HTML fragment, **nothing reaches the API** — there is no pure-Python fix.

What *does* work well:

1. **Copy image → Ctrl+Shift+V** (full pixels, best quality)  
2. **From URL…** when you have an `https://…` image address  
3. **Native file drop** when the OS actually hands Blender a temp `.png`/`.jpg`

This add-on owns (1) and (2). Stock Blender already owns a lot of (3).

---

## Preferences

**Edit → Preferences → Add-ons → Chrome Reference Drop**

| Setting | Purpose |
|---|---|
| Download Cache | Where URL / clipboard images are saved |
| Default Size | Empty display size |
| Align to View | Face the active viewport |
| Image Depth | Default / Front / Back |
| Also Handle File Drops | Optional extra FileHandler (off by default) |

---

## Develop / package

```bash
python scripts/package.py
# → dist/chrome_ref_drop-<version>.zip
# → dist/install-urls.json
# optional:
python scripts/package.py --repo-index docs/index.json
```

Print the official drag-install URL:

```bash
python scripts/package.py --drag-url-only
```

### CI

| Event | Result |
|---|---|
| Push / PR to `main` | Build zip → workflow artifact |
| Tag `v*` | GitHub Release + zip assets + refresh `index.json` on Pages |

```bash
git tag v0.2.0
git push origin v0.2.0
```

---

## Project layout

```
chrome-ref-drop/
  README.md
  docs/index.html                 # drag-and-drop landing page (GitHub Pages)
  docs/index.json                 # Blender static extension repository
  scripts/package.py
  .github/workflows/build-plugin.yml
  chrome_ref_drop/                # the extension package
```

---

## Known limits

- **URL-only OS drag** cannot be handled in pure Python  
- **`blob:` URLs** — use **Copy image** instead  
- **Google Images** thumbs are often redirects — prefer **Copy image**  
- Clipboard **pixel** paste is **Windows-first** (PNG + DIB); URL paste is cross-platform  

---

## License

GPL-3.0-or-later (Blender add-on norm).
