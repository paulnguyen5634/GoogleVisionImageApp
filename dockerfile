# ---- Base image -------------------------------------------------------------
FROM python:3.11-slim

# ---- Environment ------------------------------------------------------------
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    NLTK_DATA=/usr/local/nltk_data

# ---- System packages for OpenCV, pdf2image, PyMuPDF, OCR, etc. --------------
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    poppler-utils \
    tesseract-ocr \
    ghostscript \
    libglib2.0-0 \
    libgl1 \
    libsm6 \
    libxext6 \
    libxrender1 \
 && rm -rf /var/lib/apt/lists/*

# ---- App setup --------------------------------------------------------------
WORKDIR /app

# Copy only requirements first to leverage Docker layer caching
COPY requirements.txt ./

# Install Python deps
RUN python -m pip install --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# ---- Pre-download NLTK data (words corpus) ----------------------------------
RUN python - <<'PY'
import nltk, os
dl_dir = os.environ.get("NLTK_DATA", "/usr/local/nltk_data")
nltk.download('words', download_dir=dl_dir)
# If you later need more, add them here too (uncomment as needed):
# for pkg in ['punkt','stopwords','wordnet','omw-1.4','averaged_perceptron_tagger']:
#     nltk.download(pkg, download_dir=dl_dir)
PY

# ---- Copy the rest of the application ---------------------------------------
COPY . .

# ---- Default command --------------------------------------------------------
# Adjust if your entrypoint is different
CMD ["python", "main.py"]


