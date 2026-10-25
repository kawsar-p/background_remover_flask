# PixelForge Background Remover Studio 2.0

A Flask app for AI background removal with a redesigned 3D-style interface, solid background colors, and print-size cropping in inches.

## Features

- AI background removal powered by `rembg`.
- Export as PNG with a transparent background, or composite the subject onto a custom solid color.
- Optional crop frame that can be dragged over the image.
- Set crop width and height in inches and select 72, 96, 150, 200, 300, or 600 DPI.
- **Pixel-preserving crop:** the requested crop is calculated as `inches × DPI` pixels and cut directly from the image. No interpolation, resizing, or upscaling is performed.
- If the uploaded image does not contain enough pixels for the requested print crop, the app rejects that crop rather than upscaling it.
- With crop disabled, the original pixel dimensions are retained.
- Supports PNG, JPG/JPEG, and WEBP images (up to 25 MB).

> Cropping necessarily removes pixels outside the selected frame. It does not resample or blur the pixels inside the frame. For example, a 2 × 2 inch crop at 300 DPI requires at least 600 × 600 source pixels.

## Requirements

- Python 3.10 or newer
- Packages listed in `requirements.txt`

## Run locally

1. Extract the ZIP and open a terminal in the project folder.
2. Create and activate a virtual environment (recommended):

   ```bash
   python -m venv .venv
   ```

   Windows PowerShell:

   ```powershell
   .\.venv\Scripts\Activate.ps1
   ```

   macOS/Linux:

   ```bash
   source .venv/bin/activate
   ```

3. Install packages:

   ```bash
   pip install -r requirements.txt
   ```

4. Start the server:

   ```bash
   python app.py
   ```

5. Open `http://127.0.0.1:5000` in your browser.

The app creates `uploads/` and `outputs/` folders automatically. Generated PNGs are saved in `outputs/` for download.
