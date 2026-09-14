from flask import Flask, render_template, request, send_from_directory, redirect, url_for, flash
from werkzeug.utils import secure_filename
from PIL import Image
from rembg import remove
import os, uuid

app=Flask(__name__)
app.secret_key="background-remover-local"
BASE=os.path.dirname(os.path.abspath(__file__))
UPLOAD=os.path.join(BASE,"uploads"); OUTPUT=os.path.join(BASE,"outputs")
os.makedirs(UPLOAD,exist_ok=True); os.makedirs(OUTPUT,exist_ok=True)
ALLOWED={"png","jpg","jpeg","webp"}

@app.get("/")
def index():
    return render_template("index.html")

@app.post("/process")
def process():
    f=request.files.get("image")
    if not f or not f.filename:
        flash("Please choose an image."); return redirect(url_for("index"))
    ext=f.filename.rsplit(".",1)[-1].lower() if "." in f.filename else ""
    if ext not in ALLOWED:
        flash("PNG, JPG, JPEG and WEBP are supported."); return redirect(url_for("index"))
    uid=uuid.uuid4().hex
    inp=os.path.join(UPLOAD,uid+"."+ext); out=uid+".png"; outp=os.path.join(OUTPUT,out)
    f.save(inp)
    try:
        with Image.open(inp) as src:
            width,height=src.size
            rgba=src.convert("RGBA")
            result=remove(rgba)
            result.save(outp,"PNG",compress_level=6)
        return render_template("result.html",output_name=out,width=width,height=height,method="Automatic AI segmentation")
    except Exception as e:
        flash("Processing failed: "+str(e)); return redirect(url_for("index"))

@app.get("/download/<name>")
def download(name):
    return send_from_directory(OUTPUT,name,as_attachment=True,download_name=name)

if __name__=="__main__":
    app.run(debug=True)
