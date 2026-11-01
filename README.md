# ICONIC Beverages brand guidelines

A static site: open `index.html` in a browser, or host the folder on any static host (GitHub Pages works as-is).

## Editing
The root `*.html` pages are generated, so don't edit them directly. Instead:

1. Edit the page sources in `_build/src/pages/` (shared shell: `_build/src/layout.html`). Styles live in `assets/css/site.css`.
2. Rebuild:
   ```
   python3 _build/build.py
   ```

Needs `pip3 install --user fonttools uharfbuzz` and Sugar Magic Serif installed in `~/Library/Fonts`. Sugar Magic is set as outlined SVG at build time and is never served as a font file.

### Page source shortcuts
- `<sm>Text</sm>`: Sugar Magic, mixed case
- `<smc>Text</smc>`: Sugar Magic, caps, +100 tracking
- `<section id="x" data-nav="Label">`: adds a link in the sidebar

## Logo files and downloads
- `python3 _build/make_logos.py`: rebuilds every colourway in `assets/logo/svg/` from the masters in `_build/logo-src/` (exported from *Logo Development-v3.ai*).
- `python3 _build/make_aura.py`: renders the animated aura loop (`assets/video/aura-gold.mp4` and its poster). Needs Chrome and ffmpeg. `PREVIEW=1` writes four still frames only.
- `python3 _build/make_downloads.py`: rebuilds the PNGs, zip packs, ASE swatches, CSS tokens and Aileron pack in `assets/downloads/`. Needs Google Chrome.
