from __future__ import annotations

from flask import Flask, render_template, request, send_from_directory, redirect, url_for, flash
from PIL import Image, ImageOps
from rembg import remove
from werkzeug.exceptions import RequestEntityTooLarge
import io
import os
import re
import uuid

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "background-remover-local-dev-key")
app.config["MAX_CONTENT_LENGTH"] = 25 * 1024 * 1024  # 25 MB upload limit

BASE = os.path.dirname(os.path.abspath(__file__))
UPLOAD = os.path.join(BASE, "uploads")
OUTPUT = os.path.join(BASE, "outputs")
os.makedirs(UPLOAD, exist_ok=True)
os.makedirs(OUTPUT, exist_ok=True)

ALLOWED = {"png", "jpg", "jpeg", "webp"}
HEX_COLOR = re.compile(r"^#[0-9a-fA-F]{6}$")


@app.get("/")
def index():
    return render_template("index.html")


@app.errorhandler(RequestEntityTooLarge)
def too_large(_error):
    flash("This image is larger than 25 MB. Please choose a smaller file.")
    return redirect(url_for("index")), 413


@app.post("/process")
def process():
    file = request.files.get("image")
    if not file or not file.filename:
        flash("Please choose an image first.")
        return redirect(url_for("index"))

    ext = file.filename.rsplit(".", 1)[-1].lower() if "." in file.filename else ""
    if ext not in ALLOWED:
        flash("Supported formats: PNG, JPG, JPEG and WEBP.")
        return redirect(url_for("index"))

    background_mode = request.form.get("background_mode", "transparent")
    if background_mode not in {"transparent", "color"}:
        background_mode = "transparent"

    background_color = request.form.get("background_color", "#ffffff")
    if not HEX_COLOR.fullmatch(background_color):
        background_color = "#ffffff"
    background_color = background_color.lower()

    crop_enabled = request.form.get("crop_enabled") == "on"
    try:
        dpi = int(request.form.get("dpi", "300"))
    except (TypeError, ValueError):
        dpi = 300
    if dpi not in {72, 96, 150, 200, 300, 600}:
        dpi = 300

    crop_width_px = crop_height_px = 0
    crop_x = crop_y = 0
    crop_width_in = crop_height_in = 0.0
    if crop_enabled:
        try:
            crop_width_in = float(request.form.get("crop_width_in", "2"))
            crop_height_in = float(request.form.get("crop_height_in", "2"))
            crop_x = int(float(request.form.get("crop_x", "0")))
            crop_y = int(float(request.form.get("crop_y", "0")))
        except (TypeError, ValueError):
            flash("Enter valid crop dimensions in inches.")
            return redirect(url_for("index"))

        if not (0.1 <= crop_width_in <= 40 and 0.1 <= crop_height_in <= 40):
            flash("Crop width and height must be between 0.1 and 40 inches.")
            return redirect(url_for("index"))
        crop_width_px = round(crop_width_in * dpi)
        crop_height_px = round(crop_height_in * dpi)
        if crop_width_px < 1 or crop_height_px < 1:
            flash("The selected crop size is too small.")
            return redirect(url_for("index"))

    uid = uuid.uuid4().hex
    input_path = os.path.join(UPLOAD, f"{uid}.{ext}")
    output_name = f"{uid}_background_removed.png"
    output_path = os.path.join(OUTPUT, output_name)
    file.save(input_path)

    try:
        with Image.open(input_path) as opened:
            source = ImageOps.exif_transpose(opened)
            source_info = dict(source.info)
            source_dpi = source_info.get("dpi", (300, 300))
            icc_profile = source_info.get("icc_profile")
            source_rgba = source.convert("RGBA")
            original_width, original_height = source_rgba.size

        if crop_enabled and (crop_width_px > original_width or crop_height_px > original_height):
            flash(
                f"This crop needs {crop_width_px} × {crop_height_px} pixels at {dpi} DPI, "
                f"but your image is {original_width} × {original_height} pixels. "
                "Choose a lower DPI or a smaller inch size to avoid upscaling."
            )
            return redirect(url_for("index"))

        # AI segmentation retains the source pixel dimensions; no resize is performed here.
        removed = remove(source_rgba)
        if isinstance(removed, bytes):
            with Image.open(io.BytesIO(removed)) as removed_image:
                result = removed_image.convert("RGBA")
        elif isinstance(removed, Image.Image):
            result = removed.convert("RGBA")
        else:
            raise RuntimeError("The background-removal engine returned an unsupported image format.")

        if result.size != (original_width, original_height):
            # Avoid silently stretching or resampling if a future engine version changes behavior.
            raise RuntimeError("The AI engine changed the image dimensions. The output was not resized.")

        if crop_enabled:
            # Coordinates are clamped on the server; crop() removes pixels without interpolation.
            crop_x = max(0, min(crop_x, original_width - crop_width_px))
            crop_y = max(0, min(crop_y, original_height - crop_height_px))
            result = result.crop((crop_x, crop_y, crop_x + crop_width_px, crop_y + crop_height_px))
            output_dpi = (dpi, dpi)
            crop_summary = f"{crop_width_in:g} × {crop_height_in:g} in"
        else:
            # Preserve the image's embedded print density when present.
            try:
                dx, dy = float(source_dpi[0]), float(source_dpi[1])
                if not (1 <= dx <= 12000 and 1 <= dy <= 12000):
                    raise ValueError
                output_dpi = (dx, dy)
            except (TypeError, ValueError, IndexError):
                output_dpi = (300, 300)
            crop_summary = "Not cropped"

        if background_mode == "color":
            rgb = tuple(int(background_color[i:i + 2], 16) for i in (1, 3, 5))
            solid_background = Image.new("RGBA", result.size, (*rgb, 255))
            result = Image.alpha_composite(solid_background, result)
            background_summary = f"Solid {background_color}"
        else:
            background_summary = "Transparent"

        save_options = {"format": "PNG", "compress_level": 6, "dpi": output_dpi}
        if icc_profile:
            save_options["icc_profile"] = icc_profile
        result.save(output_path, **save_options)

        output_width, output_height = result.size
        return render_template(
            "result.html",
            output_name=output_name,
            original_width=original_width,
            original_height=original_height,
            width=output_width,
            height=output_height,
            crop_summary=crop_summary,
            dpi_label=f"{output_dpi[0]:g} × {output_dpi[1]:g}",
            background_summary=background_summary,
            background_mode=background_mode,
            background_color=background_color,
        )
    except Exception:
        app.logger.exception("Image processing failed")
        flash("Processing failed. Please try another image or check that the required packages are installed.")
        return redirect(url_for("index"))
    finally:
        try:
            os.remove(input_path)
        except OSError:
            pass


@app.get("/download/<name>")
def download(name):
    # Only serve generated PNGs. This also prevents path traversal via this route.
    if not name.endswith("_background_removed.png") or os.path.basename(name) != name:
        return "Not found", 404
    return send_from_directory(OUTPUT, name, as_attachment=True, download_name=name)


if __name__ == "__main__":
    app.run(debug=True)
