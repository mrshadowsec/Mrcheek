from flask import Flask, render_template, request, jsonify
from PIL import Image, ImageOps, ImageEnhance
import pytesseract, re, io

app=Flask(__name__)
app.config["MAX_CONTENT_LENGTH"]=10*1024*1024

def extract(text):
    t=" ".join(text.split())
    d={"brand":None,"device":None,"model":None,"android":None,"os":None,
       "os_version":None,"build":None,"chipset":None,"ram":None,"storage":None}
    m=re.search(r"\b(CPH\d{4,6})\b",t,re.I)
    if m:d["model"]=m.group(1).upper()
    for brand in ["OPPO","Samsung","Xiaomi","Redmi","POCO","OnePlus","realme","vivo"]:
        if re.search(r"\b"+re.escape(brand)+r"\b",t,re.I):
            d["brand"]=brand; break
    pats=[r"(OPPO\s+Reno\d+\s+Pro\s*5G)",r"(Samsung\s+Galaxy\s+[A-Za-z0-9 +\-]+)",
          r"(Redmi\s+[A-Za-z0-9 +\-]+)",r"(POCO\s+[A-Za-z0-9 +\-]+)",
          r"(OnePlus\s+[A-Za-z0-9 +\-]+)",r"(realme\s+[A-Za-z0-9 +\-]+)",
          r"(vivo\s+[A-Za-z0-9 +\-]+)"]
    for p in pats:
        m=re.search(p,t,re.I)
        if m:d["device"]=m.group(1).strip();break
    m=re.search(r"\bAndroid\s*([0-9]+(?:\.[0-9]+)?)",t,re.I)
    if m:d["android"]=m.group(1)
    m=re.search(r"(ColorOS|One UI|MIUI|HyperOS|OxygenOS|realme UI|Funtouch OS)\s*([0-9.]+)?",t,re.I)
    if m:d["os"],d["os_version"]=m.group(1),m.group(2)
    m=re.search(r"(Dimensity\s+[A-Za-z0-9\-]+(?:\s+[A-Za-z0-9\-]+)*)",t,re.I)
    if m:d["chipset"]=m.group(1)
    m=re.search(r"RAM\s*([0-9]+(?:\.[0-9]+)?)\s*GB",t,re.I)
    if m:d["ram"]=m.group(1)+" GB"
    m=re.search(r"\b([0-9]+)\s*GB\s*(?:/|storage)",t,re.I)
    if m:d["storage"]=m.group(1)+" GB"
    m=re.search(r"\b([A-Z]{2,8}\d{3,8}_[A-Za-z0-9.()\-]+)\b",t)
    if m:d["build"]=m.group(1)
    return d

@app.get("/")
def home(): return render_template("index.html")

@app.post("/api/analyze")
def analyze():
    f=request.files.get("image")
    if not f:return jsonify(error="Image required"),400
    try:
        img=Image.open(io.BytesIO(f.read()))
        img=ImageOps.exif_transpose(img).convert("RGB")
        img=ImageOps.grayscale(img)
        img=ImageEnhance.Contrast(img).enhance(2)
        raw=pytesseract.image_to_string(img,config="--psm 6")
        d=extract(raw)
        checks=[
          ("Device identification","PASS" if d["model"] else "WARN",
           "Model code detected." if d["model"] else "Model code not confidently detected."),
          ("Software build","PASS" if d["build"] else "WARN",
           "Build detected." if d["build"] else "Exact build was not detected."),
          ("Bootloader","CHECK","Screenshot cannot prove bootloader unlock availability."),
          ("Root","CHECK","Root support must be verified for the exact model, region and build."),
          ("Magisk","CHECK","Compatibility is model/build dependent; screenshot alone cannot confirm it."),
          ("Firmware","CHECK","Matching stock firmware should be verified before modification.")
        ]
        return jsonify(device=d,confidence="High" if d["model"] and d["build"] else "Medium" if d["model"] else "Low",
                       checks=[{"name":a,"status":b,"detail":c} for a,b,c in checks])
    except Exception as e:return jsonify(error=str(e)),500

if __name__=="__main__": app.run(host="0.0.0.0",port=5000,debug=True)
