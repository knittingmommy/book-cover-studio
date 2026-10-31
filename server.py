#!/usr/bin/env python3
import os
import re
import io
import json
import time
import base64
import zipfile
import urllib.request
import urllib.error
from http.server import HTTPServer, SimpleHTTPRequestHandler
from socketserver import ThreadingMixIn

PORT = 8765
WORKSPACE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECTS_DIR = os.path.join(WORKSPACE_DIR, "projects")
TEMPLATES_DIR = os.path.join(WORKSPACE_DIR, "templates")
ENV_FILE = os.path.join(WORKSPACE_DIR, ".env")

os.makedirs(PROJECTS_DIR, exist_ok=True)
os.makedirs(TEMPLATES_DIR, exist_ok=True)

# Standard KDP spine width multipliers (inches per page)
KDP_SPINE_MULTIPLIERS = {
    "BW_CREAM": 0.0025,
    "BW_WHITE": 0.002252,
    "COLOR_STANDARD": 0.002252,
    "COLOR_PREMIUM": 0.002347,
}

# Model-specific supported parameter profiles on OpenRouter
MODEL_PROFILES = {
    "openai/gpt-image-2.5-sunburst": {
        "aspect_ratio": "2:3",
        "supports_quality": True,
        "supports_resolution": False,
        "input_ref_format": "content_part"
    },
    "openai/gpt-image-2.5-flare": {
        "aspect_ratio": "2:3",
        "supports_quality": True,
        "supports_resolution": False,
        "input_ref_format": "content_part"
    },
    "openai/gpt-image-1": {
        "aspect_ratio": "2:3",
        "supports_quality": True,
        "supports_resolution": False,
        "input_ref_format": "content_part"
    }
}


def get_api_key():
    if os.path.exists(ENV_FILE):
        try:
            with open(ENV_FILE, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line.startswith("OPENROUTER_API_KEY="):
                        val = line.split("=", 1)[1].strip().strip("\"'")
                        if val and val != "sk-or-v1-your-key-here":
                            return val
        except Exception:
            pass
    return os.environ.get("OPENROUTER_API_KEY", "")


def save_api_key(new_key):
    new_key = new_key.strip()
    try:
        with open(ENV_FILE, "w", encoding="utf-8") as f:
            f.write(f'OPENROUTER_API_KEY="{new_key}"\n')
    except Exception as e:
        print(f"Warning: could not write API key to {ENV_FILE}: {e}")


def sanitize_slug(name):
    slug = re.sub(r"[^a-zA-Z0-9_\-\s]", "", name).strip()
    slug = re.sub(r"\s+", "_", slug)
    return slug or f"project_{int(time.time())}"


def save_data_url_to_file(data_url, filepath):
    if not data_url or not data_url.startswith("data:"):
        return False
    header, b64_data = data_url.split(",", 1)
    raw_bytes = base64.b64decode(b64_data)
    with open(filepath, "wb") as f:
        f.write(raw_bytes)
    return True


def file_to_data_url(filepath):
    if not os.path.exists(filepath):
        return None
    ext = os.path.splitext(filepath)[1].lower()
    mime = "image/jpeg" if ext in [".jpg", ".jpeg"] else "image/png"
    with open(filepath, "rb") as f:
        b64 = base64.b64encode(f.read()).decode("ascii")
    return f"data:{mime};base64,{b64}"


def parse_kdp_filename(filename, img_w, img_h):
    """
    Parse KDP template filenames like:
    PAPERBACK_5.000x8.000_224_BW_CREAM_en_US.png
    and calculate exact geometry in both 300 DPI and native template pixels.
    """
    base = os.path.basename(filename)
    m = re.search(r"(\d+(?:\.\d+)?)x(\d+(?:\.\d+)?)_(\d+)_([A-Z]+_[A-Z]+)", base)
    bleed_in = 0.125
    if m:
        trim_w_in = float(m.group(1))
        trim_h_in = float(m.group(2))
        pages = int(m.group(3))
        paper_code = m.group(4)
        mult = KDP_SPINE_MULTIPLIERS.get(paper_code, 0.0025)
        spine_w_in = round(pages * mult, 4)
    else:
        # Derive from image aspect / standard 8.25" height if filename wasn't standard KDP
        trim_h_in = round((img_h / 600.0) - 0.25, 3) if img_h > 3500 else round((img_h / 300.0) - 0.25, 3)
        if trim_h_in <= 0:
            trim_h_in = 8.0
        total_h_in = trim_h_in + 0.25
        dpi_est = img_h / total_h_in
        total_w_in = img_w / dpi_est
        # Guess trim width as 5.0 or 5.5 or 6.0
        trim_w_in = 5.0 if abs(trim_h_in - 8.0) < 0.1 else (5.5 if abs(trim_h_in - 8.5) < 0.1 else 6.0)
        spine_w_in = max(0.1, round(total_w_in - 2 * trim_w_in - 0.25, 4))
        pages = int(round(spine_w_in / 0.0025))
        paper_code = "BW_CREAM"

    total_w_in = 2 * trim_w_in + spine_w_in + 2 * bleed_in
    total_h_in = trim_h_in + 2 * bleed_in

    # Working canvas at 300 DPI (or scaled nicely so browser canvas is super crisp & fast)
    dpi_work = 300
    work_w = int(round(total_w_in * dpi_work))
    work_h = int(round(total_h_in * dpi_work))

    bleed_px = int(round(bleed_in * dpi_work))
    trim_w_px = int(round(trim_w_in * dpi_work))
    trim_h_px = int(round(trim_h_in * dpi_work))
    spine_w_px = work_w - 2 * (bleed_px + trim_w_px)

    spine_left_x = bleed_px + trim_w_px
    spine_right_x = spine_left_x + spine_w_px

    return {
        "name": os.path.splitext(base)[0],
        "native_w": img_w,
        "native_h": img_h,
        "work_w": work_w,
        "work_h": work_h,
        "dpi_work": dpi_work,
        "trim_w_in": trim_w_in,
        "trim_h_in": trim_h_in,
        "pages": pages,
        "paper_code": paper_code,
        "bleed_in": bleed_in,
        "spine_w_in": spine_w_in,
        "total_w_in": round(total_w_in, 4),
        "total_h_in": round(total_h_in, 4),
        "bleed_px": bleed_px,
        "trim_w_px": trim_w_px,
        "trim_h_px": trim_h_px,
        "spine_w_px": spine_w_px,
        "spine_left_x": spine_left_x,
        "spine_right_x": spine_right_x
    }


def extract_kdp_zip_or_png(raw_bytes, filename):
    """
    Accepts either a KDP .zip or a KDP .png, extracts/downscales the guide overlay PNG
    for smooth browser rendering, and returns metadata + guide_data_url.
    """
    from PIL import Image

    png_bytes = None
    png_name = filename

    if filename.lower().endswith(".zip") or raw_bytes[:4] == b"PK\x03\x04":
        with zipfile.ZipFile(io.BytesIO(raw_bytes), "r") as z:
            for member in z.namelist():
                if member.lower().endswith(".png") and not member.startswith("__MACOSX"):
                    png_bytes = z.read(member)
                    png_name = os.path.basename(member)
                    break
        if not png_bytes:
            raise ValueError("No PNG template file found inside the ZIP archive.")
    else:
        png_bytes = raw_bytes

    im = Image.open(io.BytesIO(png_bytes))
    orig_w, orig_h = im.size
    meta = parse_kdp_filename(png_name, orig_w, orig_h)

    # Resize the KDP guide image to match work_w x work_h (300 DPI) so it loads fast in the browser
    guide_im = im.convert("RGBA")
    if (orig_w, orig_h) != (meta["work_w"], meta["work_h"]):
        guide_im = guide_im.resize((meta["work_w"], meta["work_h"]), Image.Resampling.LANCZOS)

    out_buf = io.BytesIO()
    guide_im.save(out_buf, format="PNG", optimize=True)
    guide_b64 = base64.b64encode(out_buf.getvalue()).decode("ascii")
    meta["guide_data_url"] = f"data:image/png;base64,{guide_b64}"
    return meta


def format_references(raw_refs, fmt="content_part"):
    formatted = []
    for item in raw_refs:
        if isinstance(item, dict):
            if fmt == "string" and "image_url" in item:
                formatted.append(item["image_url"].get("url", ""))
            else:
                formatted.append(item)
        elif isinstance(item, str):
            if fmt == "content_part":
                formatted.append({
                    "type": "image_url",
                    "image_url": {"url": item}
                })
            else:
                formatted.append(item)
    return formatted


class ThreadingHTTPServer(ThreadingMixIn, HTTPServer):
    daemon_threads = True
    allow_reuse_address = True


class AppHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=WORKSPACE_DIR, **kwargs)

    def send_json(self, status_code, payload):
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path == "/api/config":
            key = get_api_key()
            self.send_json(200, {
                "has_key": bool(key),
                "masked_key": "••••••••••••" if key else ""
            })
            return

        if self.path == "/api/default_template":
            # Check if there is a default KDP zip/png in templates/
            for entry in sorted(os.listdir(TEMPLATES_DIR)):
                if entry.lower().endswith((".zip", ".png")):
                    fpath = os.path.join(TEMPLATES_DIR, entry)
                    try:
                        with open(fpath, "rb") as f:
                            meta = extract_kdp_zip_or_png(f.read(), entry)
                        self.send_json(200, {"has_template": True, "template": meta})
                        return
                    except Exception as e:
                        print(f"Warning loading default template {entry}: {e}")
            self.send_json(200, {"has_template": False})
            return

        if self.path == "/api/projects":
            projects = []
            if os.path.exists(PROJECTS_DIR):
                for entry in sorted(os.listdir(PROJECTS_DIR)):
                    p_dir = os.path.join(PROJECTS_DIR, entry)
                    meta_path = os.path.join(p_dir, "project.json")
                    if os.path.isdir(p_dir) and os.path.exists(meta_path):
                        try:
                            with open(meta_path, "r", encoding="utf-8") as f:
                                meta = json.load(f)
                            projects.append({
                                "slug": entry,
                                "name": meta.get("name", entry),
                                "app_mode": meta.get("app_mode", "ebook"),
                                "updated_at": meta.get("updated_at", ""),
                                "attempt_count": len(meta.get("history", [])),
                                "folder_path": p_dir
                            })
                        except Exception:
                            pass
            projects.sort(key=lambda x: x.get("updated_at", ""), reverse=True)
            self.send_json(200, {"projects": projects, "projects_dir": PROJECTS_DIR})
            return

        if self.path.startswith("/api/projects/"):
            slug = self.path.split("/api/projects/", 1)[1].strip("/")
            p_dir = os.path.join(PROJECTS_DIR, sanitize_slug(slug))
            meta_path = os.path.join(p_dir, "project.json")
            if not os.path.exists(meta_path):
                self.send_json(404, {"error": f"Project '{slug}' not found."})
                return
            try:
                with open(meta_path, "r", encoding="utf-8") as f:
                    meta = json.load(f)

                source_file = meta.get("source_file", "original.png")
                meta["source_data_url"] = file_to_data_url(os.path.join(p_dir, source_file))

                guide_file = meta.get("guide_file")
                if guide_file:
                    meta["guide_data_url"] = file_to_data_url(os.path.join(p_dir, guide_file))

                hydrated_history = []
                for h in meta.get("history", []):
                    top_url = file_to_data_url(os.path.join(p_dir, h.get("top_file", "")))
                    bot_url = file_to_data_url(os.path.join(p_dir, h.get("bottom_file", "")))
                    if top_url or bot_url:
                        hydrated_history.append({
                            "label": h.get("label", "Attempt"),
                            "topDataUrl": top_url or bot_url,
                            "bottomDataUrl": bot_url or top_url
                        })
                meta["hydrated_history"] = hydrated_history
                self.send_json(200, meta)
            except Exception as e:
                self.send_json(500, {"error": f"Failed to load project: {e}"})
            return

        if self.path == "/api/models":
            key = get_api_key()
            req = urllib.request.Request(
                "https://openrouter.ai/api/v1/images/models",
                headers={
                    "Authorization": f"Bearer {key}" if key else "",
                    "Accept": "application/json"
                }
            )
            try:
                with urllib.request.urlopen(req, timeout=15) as resp:
                    data = json.loads(resp.read().decode("utf-8"))
                    self.send_json(200, data)
            except urllib.error.HTTPError as e:
                err_body = e.read().decode("utf-8", errors="replace")
                self.send_json(e.code, {"error": f"HTTP {e.code}", "details": err_body})
            except Exception as e:
                self.send_json(500, {"error": str(e)})
            return

        return super().do_GET()

    def do_POST(self):
        content_length = int(self.headers.get("Content-Length", 0))
        raw_body = self.rfile.read(content_length) if content_length > 0 else b"{}"
        try:
            body = json.loads(raw_body.decode("utf-8"))
        except Exception as e:
            self.send_json(400, {"error": f"Invalid JSON: {e}"})
            return

        if self.path == "/api/config":
            new_key = body.get("api_key", "").strip()
            if not new_key:
                self.send_json(400, {"error": "API key cannot be empty."})
                return
            save_api_key(new_key)
            self.send_json(200, {"ok": True, "has_key": True, "masked_key": "••••••••••••"})
            return

        if self.path == "/api/kdp_template":
            filename = body.get("filename", "template.zip")
            data_b64 = body.get("data_b64", "")
            if "," in data_b64:
                data_b64 = data_b64.split(",", 1)[1]
            try:
                raw_bytes = base64.b64decode(data_b64)
                # Save a copy in templates/ so it's available next time too
                safe_name = re.sub(r"[^a-zA-Z0-9_.\-]", "_", os.path.basename(filename))
                with open(os.path.join(TEMPLATES_DIR, safe_name), "wb") as f:
                    f.write(raw_bytes)
                meta = extract_kdp_zip_or_png(raw_bytes, safe_name)
                self.send_json(200, {"ok": True, "template": meta})
            except Exception as e:
                self.send_json(400, {"error": f"Could not parse KDP template: {e}"})
            return

        if self.path == "/api/export_print_pdf":
            # Generates an exact KDP print-ready PDF at 300 DPI matching KDP's exact inch dimensions
            from PIL import Image
            data_url = body.get("image_data_url", "")
            filename = body.get("filename", "paperback_wrap")
            trim_w_in = float(body.get("total_w_in", 10.81))
            trim_h_in = float(body.get("total_h_in", 8.25))
            if not data_url or "," not in data_url:
                self.send_json(400, {"error": "Missing image data"})
                return
            try:
                raw_bytes = base64.b64decode(data_url.split(",", 1)[1])
                im = Image.open(io.BytesIO(raw_bytes)).convert("RGB")
                # Ensure at least 300 DPI pixel resolution and exact independent X/Y DPI so PDF MediaBox matches KDP inches to 0.001"
                min_w = int(round(trim_w_in * 300.0 + 0.5))
                min_h = int(round(trim_h_in * 300.0 + 0.5))
                if im.width < min_w or im.height < min_h:
                    im = im.resize((max(im.width, min_w), max(im.height, min_h)), Image.Resampling.LANCZOS)
                exact_dpi_x = float(im.width) / trim_w_in
                exact_dpi_y = float(im.height) / trim_h_in
                pdf_buf = io.BytesIO()
                im.save(pdf_buf, format="PDF", dpi=(exact_dpi_x, exact_dpi_y), quality=100)
                pdf_b64 = base64.b64encode(pdf_buf.getvalue()).decode("ascii")
                self.send_json(200, {
                    "ok": True,
                    "pdf_data_url": f"data:application/pdf;base64,{pdf_b64}",
                    "dpi": round(exact_dpi_x),
                    "width_in": round(trim_w_in, 3),
                    "height_in": round(trim_h_in, 3)
                })
            except Exception as e:
                self.send_json(500, {"error": f"PDF generation failed: {e}"})
            return

        if self.path == "/api/projects/save":
            name = body.get("name", "").strip() or "Untitled_Cover"
            slug = sanitize_slug(name)
            p_dir = os.path.join(PROJECTS_DIR, slug)
            os.makedirs(p_dir, exist_ok=True)

            try:
                source_data_url = body.get("source_data_url")
                if source_data_url:
                    save_data_url_to_file(source_data_url, os.path.join(p_dir, "original.png"))

                guide_data_url = body.get("guide_data_url")
                guide_file = None
                if guide_data_url:
                    guide_file = "kdp_guide.png"
                    save_data_url_to_file(guide_data_url, os.path.join(p_dir, guide_file))

                raw_history = body.get("history", [])
                saved_history_meta = []
                for idx, item in enumerate(raw_history):
                    num = idx + 1
                    top_data = item.get("topDataUrl")
                    bot_data = item.get("bottomDataUrl")
                    top_fname = f"attempt_{num}_top.png"
                    bot_fname = f"attempt_{num}_bottom.png"

                    if top_data:
                        save_data_url_to_file(top_data, os.path.join(p_dir, top_fname))
                    if bot_data:
                        if bot_data == top_data:
                            bot_fname = top_fname
                        else:
                            save_data_url_to_file(bot_data, os.path.join(p_dir, bot_fname))

                    saved_history_meta.append({
                        "label": item.get("label", f"Attempt {num}"),
                        "top_file": top_fname,
                        "bottom_file": bot_fname
                    })

                composite_data_url = body.get("composite_data_url")
                if composite_data_url:
                    save_data_url_to_file(composite_data_url, os.path.join(p_dir, f"{slug}_latest.png"))

                project_meta = {
                    "name": name,
                    "slug": slug,
                    "app_mode": body.get("app_mode", "ebook"),
                    "updated_at": time.strftime("%Y-%m-%d %H:%M:%S"),
                    "source_file": "original.png",
                    "guide_file": guide_file,
                    "source_file_name": body.get("source_file_name", slug),
                    "state": body.get("state", {}),
                    "active_history_index": body.get("active_history_index", len(saved_history_meta) - 1),
                    "history": saved_history_meta
                }

                with open(os.path.join(p_dir, "project.json"), "w", encoding="utf-8") as f:
                    json.dump(project_meta, f, indent=2)

                self.send_json(200, {
                    "ok": True,
                    "slug": slug,
                    "name": name,
                    "folder_path": p_dir
                })
            except Exception as e:
                self.send_json(500, {"error": f"Failed to save project: {e}"})
            return

        if self.path == "/api/expand":
            api_key = body.get("api_key", "").strip() or get_api_key()
            if not api_key:
                self.send_json(401, {
                    "error": "Missing OpenRouter API Key. Click 'API Key Settings' in the top bar to paste your key."
                })
                return

            model = body.get("model", "openai/gpt-image-2.5-sunburst")
            prompt = body.get("prompt", "").strip()
            raw_references = body.get("input_references", [])
            quality = body.get("quality", "high")
            requested_ar = body.get("aspect_ratio", "2:3")

            profile = MODEL_PROFILES.get(model, {
                "aspect_ratio": requested_ar,
                "supports_quality": False,
                "supports_resolution": False,
                "input_ref_format": "content_part"
            })

            payload = {
                "model": model,
                "prompt": prompt,
                "aspect_ratio": requested_ar or profile["aspect_ratio"],
                "n": 1
            }

            if profile.get("supports_quality") and quality:
                payload["quality"] = quality

            if raw_references:
                payload["input_references"] = format_references(raw_references, profile["input_ref_format"])

            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
                "HTTP-Referer": "http://localhost:8765",
                "X-Title": "Ebook & Paperback Cover Generative Fill Workspace"
            }

            def call_openrouter(req_payload):
                req_bytes = json.dumps(req_payload).encode("utf-8")
                req = urllib.request.Request(
                    "https://openrouter.ai/api/v1/images",
                    data=req_bytes,
                    headers=headers,
                    method="POST"
                )
                with urllib.request.urlopen(req, timeout=180) as resp:
                    return json.loads(resp.read().decode("utf-8"))

            try:
                print(f"[EXPAND] Calling OpenRouter model={model}, aspect_ratio={payload.get('aspect_ratio')}, quality={payload.get('quality')}, refs={len(raw_references)}")
                result = call_openrouter(payload)
                self.send_json(200, result)
            except urllib.error.HTTPError as e:
                err_text = e.read().decode("utf-8", errors="replace")
                print(f"[EXPAND ERROR 1] HTTP {e.code}: {err_text}")

                if e.code == 400 and raw_references:
                    try:
                        alt_payload = {
                            "model": model,
                            "prompt": prompt,
                            "aspect_ratio": requested_ar or "2:3",
                            "n": 1,
                            "input_references": format_references(raw_references, "string")
                        }
                        if profile.get("supports_quality") and quality:
                            alt_payload["quality"] = quality
                        print(f"[EXPAND RETRY] Trying string format for input_references...")
                        result = call_openrouter(alt_payload)
                        self.send_json(200, result)
                        return
                    except urllib.error.HTTPError as e2:
                        err_text = e2.read().decode("utf-8", errors="replace")
                        print(f"[EXPAND ERROR 2] HTTP {e2.code}: {err_text}")
                    except Exception as e2:
                        err_text = str(e2)

                try:
                    err_json = json.loads(err_text)
                except Exception:
                    err_json = {"raw": err_text}
                self.send_json(e.code, {
                    "error": f"OpenRouter API error (HTTP {e.code})",
                    "details": err_json
                })
            except Exception as e:
                print(f"[EXPAND EXCEPTION] {e}")
                self.send_json(500, {"error": f"Request failed: {str(e)}"})
            return

        self.send_json(404, {"error": "Endpoint not found"})


if __name__ == "__main__":
    server = ThreadingHTTPServer(("127.0.0.1", PORT), AppHandler)
    print(f"============================================================")
    print(f" Ebook & Paperback Cover Generative Expand App running at:")
    print(f" http://localhost:{PORT}")
    print(f"============================================================")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down server...")
        server.server_close()
