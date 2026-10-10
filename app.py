from flask import Flask, render_template, request
import requests
import os
import pytesseract
from pdf2image import convert_from_path
from PIL import Image
import uuid

app = Flask(__name__)

# -----------------------------
# CONFIG
# -----------------------------

OLLAMA_URL = "http://localhost:11434/api/chat"

UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

ALLOWED_EXTENSIONS = {"pdf", "png", "jpg", "jpeg"}

# If needed on Windows:
# pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"


# -----------------------------
# UTIL
# -----------------------------

def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


# -----------------------------
# OCR FUNCTIONS
# -----------------------------

def extract_text_from_pdf(pdf_path):
    text = ""
    try:
        pages = convert_from_path(pdf_path)

        print("PDF pages:", len(pages))

        for page in pages:
            page_text = pytesseract.image_to_string(page, config="--psm 6")
            text += page_text + "\n"

    except Exception as e:
        print("PDF OCR ERROR:", e)

    return text


def extract_text_from_image(image_path):
    try:
        img = Image.open(image_path).convert("RGB")
        text = pytesseract.image_to_string(img, config="--psm 6")
        return text
    except Exception as e:
        print("IMAGE OCR ERROR:", e)
        return ""


# -----------------------------
# SYSTEM PROMPT (CLEAN)
# -----------------------------

SYSTEM_PROMPT = """
You are a Senior ICU Consultant.

Generate a structured ICU discharge summary.

RULES:
- Do NOT repeat instructions
- Do NOT explain steps
- Only output final discharge summary
- If info missing write "Not Available"

FORMAT:
DIAGNOSIS
ICU COURSE
PROCEDURES
INVESTIGATIONS
ORGAN SUPPORT
COMPLICATIONS
DISCHARGE STATUS
MEDICATIONS
FOLLOW-UP
RED FLAGS
"""


# -----------------------------
# ROUTE
# -----------------------------

@app.route("/", methods=["GET", "POST"])
def index():

    summary = ""
    extracted_text = ""

    if request.method == "POST":

        patient_data = request.form.get("patient_data", "")
        uploaded_files = request.files.getlist("report_file")

        for file in uploaded_files:

            if file and allowed_file(file.filename):

                filename = str(uuid.uuid4()) + "_" + file.filename
                file_path = os.path.join(UPLOAD_FOLDER, filename)

                file.save(file_path)

                print("Saved:", file_path)
                print("Exists:", os.path.exists(file_path))
                print("Size:", os.path.getsize(file_path))

                ext = file.filename.rsplit(".", 1)[1].lower()

                if ext == "pdf":
                    extracted_text += extract_text_from_pdf(file_path)
                else:
                    extracted_text += extract_text_from_image(file_path)

        combined_data = (patient_data + "\n\n" + extracted_text).strip()

        print("FINAL OCR LENGTH:", len(combined_data))

        # -----------------------------
        # OLLAMA CALL
        # -----------------------------

        payload = {
            "model": "llama3",
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": combined_data}
            ],
            "stream": False,
            "options": {"temperature": 0.1}
        }

        try:
            response = requests.post(
                OLLAMA_URL,
                json=payload,
                timeout=180
            )

            if response.status_code != 200:
                summary = response.text
            else:
                data = response.json()
                summary = data["message"]["content"]

        except Exception as e:
            summary = f"ERROR: {str(e)}"

    return render_template(
        "index.html",
        summary=summary,
        extracted_text=extracted_text
    )


# -----------------------------
# RUN
# -----------------------------

if __name__ == "__main__":
    app.run(debug=True)