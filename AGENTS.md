# AI Agent Instructions for Book Cover Studio

Welcome! If an author has asked you (an AI coding assistant such as Antigravity, Cursor, Claude Code, or Windsurf) to set up, launch, or customize **Book Cover Studio**, follow the instructions below.

---

## 1. Quick Setup & Launch Workflow

When the user asks you to **"Set this up"** or **"Start the Book Cover Studio"**:

1. **Install Dependencies:**
   - Ensure Python 3.9+ is installed.
   - Create a local virtual environment (`.venv`) if one does not exist, or install `Pillow` from `requirements.txt`:
     ```bash
     python3 -m venv .venv
     .venv/bin/pip install -r requirements.txt
     ```
     *(On Windows, use `python -m venv .venv` and `.venv\Scripts\pip install -r requirements.txt`.)*
2. **API Key Configuration:**
   - Check if `.env` exists and has a valid `OPENROUTER_API_KEY`.
   - If not, let the user know they can either give you their OpenRouter API key to save into `.env`, **or** simply click the **"API Key"** button in the top-right corner of the web interface once it opens.
3. **Start the Server:**
   - Run `server.py`:
     ```bash
     .venv/bin/python server.py
     ```
   - The app runs at **`http://localhost:8765`**. Tell the user to open `http://localhost:8765` in their browser.

---

## 2. Architecture Overview (For Customizations)

The entire application consists of two self-contained files with zero frontend build step required:

### `server.py` (Python HTTP Backend)
- Serves static files from the project root on port `8765` (`PORT = 8765`).
- **`GET / POST /api/config`**: Reads and saves `OPENROUTER_API_KEY` to `.env`.
- **`POST /api/kdp_template` & `GET /api/default_template`**: Parses official Amazon KDP `.zip` or `.png` cover calculator templates, extracts trim size, page count, paper type, spine width, and bleed dimensions, and generates a 300 DPI transparent guide overlay.
- **`POST /api/expand`**: Proxies image outpainting/expansion requests to `https://openrouter.ai/api/v1/images` using the prepared reference canvas and user prompt.
- **`POST /api/export_print_pdf`**: Uses `Pillow` (`PIL.Image`) to generate a 300 DPI print-ready PDF with exact physical inch dimensions matching KDP's MediaBox requirements.
- **`GET /api/projects` & `POST /api/projects/save`**: Saves and loads complete multi-attempt cover projects inside the local `projects/` directory.

### `index.html` (Single-File HTML5 Canvas Studio)
- **Two Modes**:
  1. **Ebook Cover Mode (`1600 × 2560` • 5:8 aspect ratio)**:
     - Takes 3:4 or 4:5 character/cover art (e.g., from Leonardo, Midjourney, or Flux) and expands the top, bottom, or both to fit standard 5:8 ebook dimensions.
     - Supports **Partial Fine-Tune** (`Keep Top • Redo Bottom` or `Keep Bottom • Redo Top`) and mix-and-match history across attempts.
  2. **Paperback Full Wrap Mode (KDP Template)**:
     - Places the front cover on the right side (aligned to the right spine fold and bleed) and uses AI outpainting to seamlessly extend the artwork across the spine and back cover on the left.
     - Includes a live **KDP Calculator** (Trim size, page count, paper type) and official KDP `.zip`/`.png` template dropzone.
     - Includes a built-in **Back Cover Blurb & Spine Typography Studio** with live Google Fonts, readability vignette/scrim, drop shadow, rotated spine title/author, and upright series numbering.

---

## 3. Common Customizations Authors May Request

If the user asks you to customize their studio, here is where to look:

- **Add New Google Fonts for Back Cover Blurb & Spine:**
  1. Update the `<link href="https://fonts.googleapis.com/css2?...">` tag in the `<head>` of `index.html`.
  2. Add a matching `<option>` to `#blurbFontSelect` in `index.html`.
- **Add New KDP Trim Sizes:**
  1. Add an `<option value="WxH">` to `#kdpTrimSelect` in `index.html` (e.g., `<option value="5x7">5" × 7"</option>`).
- **Add or Change Default OpenRouter Image Models:**
  1. Update `#modelSelect` in `index.html`.
  2. Optionally add model parameter profiles to `MODEL_PROFILES` in `server.py`.
- **Change Ebook Target Resolution:**
  1. Update `TARGET_W = 1600` and `TARGET_H = 2560` in `index.html` (both at initialization and inside `setAppMode("ebook")`).
