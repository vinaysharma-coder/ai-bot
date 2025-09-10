import os
import io
from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
from werkzeug.utils import secure_filename
from PyPDF2 import PdfReader
from pdf2image import convert_from_path
import pytesseract
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from deep_translator import GoogleTranslator   # 👈 more reliable than googletrans

app = Flask(__name__)
CORS(app)

UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def extract_text_from_pdf(pdf_path):
    text = ""
    try:
        pdf = PdfReader(open(pdf_path, "rb"))
        for page in pdf.pages:
            if page.extract_text():
                text += page.extract_text() + "\n"
    except:
        pass
    return text

def ocr_from_scanned_pdf(pdf_path):
    text = ""
    images = convert_from_path(pdf_path)
    for img in images:
        text += pytesseract.image_to_string(img) + "\n"
    return text

def create_pdf_from_text(text, filename):
    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=letter)
    width, height = letter
    y = height - 40
    for line in text.split("\n"):
        c.drawString(40, y, line)
        y -= 20
        if y < 40:
            c.showPage()
            y = height - 40
    c.save()
    buffer.seek(0)
    return buffer

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return jsonify({'error': 'No file uploaded'}), 400

    file = request.files['file']
    target_lang = request.form.get('target_lang', 'en')
    download_pdf = request.form.get('download_pdf', 'false') == 'true'

    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400

    filepath = os.path.join(UPLOAD_FOLDER, secure_filename(file.filename))
    file.save(filepath)

    extracted_text = extract_text_from_pdf(filepath)
    if not extracted_text.strip():
        extracted_text = ocr_from_scanned_pdf(filepath)

    if not extracted_text.strip():
        return jsonify({'error': 'Could not extract text'}), 500

    # ✅ Use deep-translator instead of googletrans
    try:
        translated = GoogleTranslator(source="auto", target=target_lang).translate(extracted_text)
    except Exception as e:
        return jsonify({'error': f'Translation failed: {str(e)}'}), 500

    if download_pdf:
        pdf_buffer = create_pdf_from_text(translated, "translated.pdf")
        return send_file(pdf_buffer, as_attachment=True,
                         download_name="translated.pdf",
                         mimetype="application/pdf")

    return jsonify({'translated_text': translated})

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
