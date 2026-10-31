# 🎨 Book Cover Studio (Ebook 5:8 & KDP Paperback Full Wrap)

A local, browser-based generative outpainting and typography studio built for indie authors. Turn your 3:4 or 4:5 cover artwork into a full **1600×2560 (5:8) Ebook Cover**, or turn your front cover into a complete **300 DPI Amazon KDP Paperback Wrap** with spine lettering, back-cover blurb formatting, and one-click Print-Ready PDF export.

---

## 🚀 Quickstart Option A: Let Your AI Set It Up For You

If you use an AI coding assistant (**Antigravity**, **Cursor**, **Claude Code**, **Windsurf**, etc.), just download or clone this repository, open the folder in your AI assistant, and paste this prompt:

> **"Please read `AGENTS.md`, set up the Python environment, install the requirements, and launch the Book Cover Studio for me."**

Your AI will automatically set everything up and give you a link to open **`http://localhost:8765`**.

### Want to customize your studio?
Because this repo includes an `AGENTS.md` blueprint, you can also ask your AI things like:
* *"Add the Google Font 'Cinzel Decorative' to the back-cover font dropdown."*
* *"Add 5.06 × 7.81 to the KDP trim size list."*
* *"Change the default spine text colors to silver and white."*

---

## 🖥️ Quickstart Option B: One-Click Launch (No AI Needed)

1. Make sure **Python 3.9+** is installed on your computer.
2. **Mac / Linux:** Double-click or run `./start_mac_linux.sh` in your terminal.
3. **Windows:** Double-click `start_windows.bat`.
4. Your browser will open to **`http://localhost:8765`**.
5. Click the **`API Key`** button in the top-right corner and paste your [OpenRouter API Key](https://openrouter.ai/keys).

---

## ✨ Features for Authors

### 📱 Mode 1: Ebook Cover Studio (5:8 • 1600 × 2560)
* **Convert 3:4 or 4:5 Art to 5:8:** Drop in artwork from Leonardo, Midjourney, or Flux and choose **Expand Top** (for title headroom), **Expand Bottom** (for author name space), or **Expand Both**.
* **Lock Original Pixels + Feathered Seam Blending:** Keeps 100% of your original character faces, lighting, and front-cover typography crisp while smoothly feathering the seam into the AI-expanded edges.
* **Partial Fine-Tune ("Keep Good Half!"):** Love the top expansion but want to re-roll the bottom? Click **🔒 Keep Top • Redo Bottom** (or vice versa), or mix-and-match the best top and bottom halves from your **Attempts History** bar at the bottom.
* **Fine-Tune Position Nudge:** Nudge your cover in 15px steps or shrink by `-2%` to rescue text from trim edges.

### 📖 Mode 2: KDP Paperback Full Wrap Studio
* **Official KDP Template Support:** Drop your official Amazon KDP Cover Calculator `.zip` or `.png` template directly onto the page—or use the built-in KDP Calculator (Trim Size, Page Count, and Paper Type: B&W Cream, B&W White, Standard/Premium Color).
* **Automatic Spine & Back Cover Outpainting:** Snaps your front cover to the right side of the wrap and uses AI to seamlessly extend your background atmosphere across the spine and back cover while keeping the back cover clean for your blurb.
* **Back Cover Blurb & Spine Typography Studio:**
  * Format your **Hook/Tagline** and **Back Cover Blurb** with book-ready Google Fonts, custom colors, line spacing, and alignment (Left, Centered, or Full Justified).
  * Add a customizable **Readability Vignette (Scrim)** and drop shadow behind your blurb so text is effortless to read over illustrated backgrounds.
  * Add **Spine Book Title**, **Spine Author Name** (automatically rotated 90° and centered on the spine), and an upright **Series Number**.
* **One-Click 300 DPI Print-Ready PDF:** Exports a print-ready `.pdf` sized to your exact KDP trim + spine + bleed dimensions (with all guide lines automatically hidden).

### 💾 Project Save & Portable Backups
* Save your cover projects (including original artwork, KDP template, typography settings, and every generated attempt) to your local `projects/` folder, or export a portable `.coverproj.json` file.
