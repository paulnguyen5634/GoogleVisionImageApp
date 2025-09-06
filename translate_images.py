from __future__ import annotations

# --- Standard libs
import os
import re
import math
import time
from io import BytesIO
from pathlib import Path
from typing import List, Tuple, Optional
import textwrap
import sys

# --- Third-party
from pypdf import PdfReader, PdfWriter
import fitz  # PyMuPDF
from PIL import Image, ImageDraw, ImageFont
from google.cloud import vision
from google.oauth2 import service_account
from deep_translator import GoogleTranslator, single_detection
from deep_translator.exceptions import LanguageNotSupportedException
import requests
import nltk
from nltk.corpus import words

# --- Local
from functions import createFolder, folderfiles  # (kept if you use elsewhere)

# =========================
# Paths & Globals
# =========================
ROOT = Path(__file__).resolve().parent
DEFAULT_FONT_PATH = ROOT / "font" / "CC Wild Words Roman.ttf"  # works on Windows/Linux

# NLTK words fallback (avoid crashing if corpus missing)
try:
    NLTK_WORDS = set(words.words())
except LookupError:
    NLTK_WORDS = set()
    # If you want auto-download when internet is available, uncomment:
    # nltk.download('words')
    # NLTK_WORDS = set(words.words())

# =========================
# Auth / Vision Client
# =========================
def build_vision_client() -> vision.ImageAnnotatorClient:
    """
    Order of preference:
    1) Mounted /keys/*.json (docker -v $PWD/keys:/keys:ro)
    2) ./keys/*.json (repo-local)
    3) GOOGLE_APPLICATION_CREDENTIALS if it points to a valid file
    4) ADC (GCE/Cloud Run with ambient creds)
    """
    # Prefer mounted path first
    for cand_dir in (Path("/keys"), ROOT / "keys"):
        if cand_dir.is_dir():
            jsons = sorted(cand_dir.glob("*.json"))
            if jsons:
                creds = service_account.Credentials.from_service_account_file(str(jsons[0]))
                return vision.ImageAnnotatorClient(credentials=creds)

    # Respect env var if points to a real file (normalize slashes if user passed Windows path)
    env_path = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS")
    if env_path:
        fixed = str(Path(env_path))  # normalizes \ on POSIX too
        if Path(fixed).is_file():
            os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = fixed
            return vision.ImageAnnotatorClient()

    # Fall back to ADC (works on GCP with workload identity)
    return vision.ImageAnnotatorClient()

VISION_CLIENT = build_vision_client()

# =========================
# Console progress bar
# =========================
def print_progress(current: int, total: int, width: int = 40, prefix: str = "Progress") -> None:
    """
    Simple in-place progress bar in the console.
    """
    current = min(max(0, current), total)
    pct = 0.0 if total == 0 else current / total
    filled = int(width * pct)
    bar = "#" * filled + "-" * (width - filled)
    sys.stdout.write(f"\r{prefix}: [{bar}] {current}/{total} ({pct*100:5.1f}%)")
    sys.stdout.flush()
    if current >= total:
        sys.stdout.write("\n")

# =========================
# Fonts
# =========================
def load_font(size: int, fallback: bool = True) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    """Try project font; fallback to default if missing."""
    try:
        return ImageFont.truetype(str(DEFAULT_FONT_PATH), size=max(1, int(size)))
    except Exception:
        if fallback:
            return ImageFont.load_default()
        raise

# ---------- Text fitting helpers ----------
def _measure_wrapped(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.ImageFont, max_width_px: int) -> Tuple[str, Tuple[int, int, int, int]]:
    """
    Wrap `text` given a font and target max line width (pixels) using a char-width heuristic,
    then measure the multiline bounding box. Returns (wrapped_text, bbox).
    """
    # Heuristic: derive wrap width in characters from average char width
    bbox_single = font.getbbox(text)
    single_len = max(1, abs(bbox_single[2] - bbox_single[0]))
    avg_char_w = max(1, single_len / max(1, len(text)))
    max_chars = max(1, int(max_width_px / avg_char_w))
    wrapped = textwrap.fill(text=text, width=max_chars)
    multi_bbox = draw.multiline_textbbox((0, 0), wrapped, font=font, align="center")
    return wrapped, multi_bbox

def fit_text_to_box(
    image: Image.Image,
    text: str,
    box: Tuple[int, int, int, int],
    margin_ratio: float = 0.02,
    size_min: int = 8,
    size_max: int = 600,
) -> Tuple[str, ImageFont.ImageFont]:
    """
    Find the largest font size that fits the text (wrapped) *fully inside* the bounding box.
    Uses binary search for speed and accuracy. Returns (wrapped_text, font).
    """
    draw = ImageDraw.Draw(image)
    left, top, right, bottom = box
    width = max(1, right - left)
    height = max(1, bottom - top)

    # Apply a small margin so text doesn't touch the edges
    max_w = int(width * (1 - 2 * margin_ratio))
    max_h = int(height * (1 - 2 * margin_ratio))

    if max_w <= 1 or max_h <= 1 or not text.strip():
        return text.strip(), load_font(size_min)

    lo, hi = size_min, size_max
    best_font = load_font(lo)
    best_wrapped = text

    while lo <= hi:
        mid = (lo + hi) // 2
        font = load_font(mid)
        wrapped, bbox = _measure_wrapped(draw, text, font, max_w)
        w = abs(bbox[2] - bbox[0])
        h = abs(bbox[3] - bbox[1])

        # Fits if both width and height are within box
        if w <= max_w and h <= max_h:
            best_font = font
            best_wrapped = wrapped
            lo = mid + 1  # try bigger
        else:
            hi = mid - 1  # too big, try smaller

    return best_wrapped, best_font

# =========================
# Vision: Detection Helpers
# =========================
def detect_text_file(path: str | Path) -> List[vision.TextAnnotation]:
    """Detects text in an image file path."""
    client = VISION_CLIENT
    with open(path, "rb") as f:
        content = f.read()
    image = vision.Image(content=content)
    response = client.text_detection(image=image)
    if response.error.message:
        raise RuntimeError(f"Vision API Error: {response.error.message}")
    return list(response.text_annotations)

def new_detect_text(image_bytes: bytes) -> Tuple[List[vision.TextAnnotation], Optional[str]]:
    """Detects text in raw image bytes; returns (annotations, detected_language)."""
    client = VISION_CLIENT
    image = vision.Image(content=image_bytes)
    response = client.text_detection(image=image)
    if response.error.message:
        raise RuntimeError(f"Vision API Error: {response.error.message}")
    texts = list(response.text_annotations)
    detected_language = texts[0].locale if texts else None
    if detected_language:
        if detected_language == "zh":
            print("Detected language: Chinese")
        elif detected_language == "ja":
            print("Detected language: Japanese")
        else:
            print(f"Detected language: {detected_language}")
    return texts, detected_language

# =========================
# Geometry utils
# =========================
def is_box_inside(outer_box: List[int], inner_box: List[int]) -> bool:
    x1o, y1o, x2o, y2o = outer_box
    x1i, y1i, x2i, y2i = inner_box
    return (x1o <= x1i <= x2o and y1o <= y1i <= y2o and
            x1o <= x2i <= x2o and y1o <= y2i <= y2o)

def find_enclosing_box(combined_boxes: List[List[int]], given_box: List[int]) -> Optional[List[int]]:
    for box in combined_boxes:
        if is_box_inside(box, given_box):
            return box
    return None

# =========================
# Gibberish filter
# =========================
def is_sentence_gibberish(sentence: str, threshold: float = 0.5) -> bool:
    """
    Very rough heuristic: % of tokens that are real words or common interjections.
    """
    common_interjections = {"uh", "huh", "woo", "oh", "ah", "...", "hmm"}
    tokens = sentence.split()
    if not tokens:
        return True
    valid = sum(1 for w in tokens if w.lower() in NLTK_WORDS or w.lower() in common_interjections)
    return valid < len(tokens) * threshold

# =========================
# PDF/Image I/O
# =========================
def split_pdf_to_png_in_memory(path: str | Path) -> List[BytesIO]:
    with open(path, "rb") as f:
        pdf_bytes = f.read()

    pdf_reader = PdfReader(BytesIO(pdf_bytes))
    images: List[BytesIO] = []

    for page_num in range(len(pdf_reader.pages)):
        writer = PdfWriter()
        writer.add_page(pdf_reader.pages[page_num])

        page_bytes = BytesIO()
        writer.write(page_bytes)
        page_bytes.seek(0)

        pdf_document = fitz.open(stream=page_bytes, filetype="pdf")
        page = pdf_document.load_page(0)
        pix = page.get_pixmap()
        img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)

        image_bytes = BytesIO()
        img.save(image_bytes, format="PNG")
        image_bytes.seek(0)
        images.append(image_bytes)

    return images

def convert_image_to_bytes(image: Image.Image) -> bytes:
    buf = BytesIO()
    image.save(buf, format="PNG")
    buf.seek(0)
    return buf.getvalue()

def get_png_images_from_folder(folder_path: str | Path,
                               extensions: Tuple[str, ...] = ("png", "jpg", "jpeg")) -> List[BytesIO]:
    """Read images from folder into in-memory PNGs (BytesIO). Natural sort by number tokens."""
    folder_path = str(folder_path)
    images: List[BytesIO] = []
    if not os.path.exists(folder_path):
        print(f"Folder does not exist: {folder_path}")
        return images

    print(f"Reading files from folder: {folder_path}")

    def numerical_sort_key(filename: str):
        return [int(part) if part.isdigit() else part for part in re.split(r"(\d+)", filename)]

    for filename in sorted(os.listdir(folder_path), key=numerical_sort_key):
        if any(filename.lower().endswith(ext) for ext in extensions):
            image_path = os.path.join(folder_path, filename)
            with open(image_path, "rb") as img_file:
                img_bytes = BytesIO(img_file.read())
                img_bytes.seek(0)
                images.append(img_bytes)
    return images

# =========================
# Main translate pipeline
# =========================
def translate_images(path: str | Path, filename: str) -> List[Image.Image]:
    # If the file is a PDF, split into PNGs; else read folder of images.
    if filename.lower().endswith(".pdf"):
        print("Translating PDF")
        png_images = split_pdf_to_png_in_memory(path)
    else:
        print("Translating Folder of Images")
        png_images = get_png_images_from_folder(path)

    total = len(png_images)
    modified_png_lst: List[Image.Image] = []
    print(f"Total PNG images created: {total}")

    # progress start
    print_progress(0, total, prefix="Processing pages")

    for idx, page in enumerate(png_images, start=1):
        print(f"\nPage {idx}/{total}")

        # Load image (BytesIO) -> PIL -> bytes -> detect
        pil_img = Image.open(page).convert("RGB")
        img_bytes = convert_image_to_bytes(pil_img)

        # Detect text with simple retry
        texts: List[vision.TextAnnotation] = []
        detected_language: Optional[str] = None
        last_err = None
        for attempt in range(3):
            try:
                texts, detected_language = new_detect_text(img_bytes)
                break
            except Exception as e:
                last_err = e
                print(f"Vision detect attempt {attempt+1}/3 failed: {e}")
                time.sleep(2)
        if not texts:
            raise RuntimeError(f"Text detection failed: {last_err}")

        img = Image.open(BytesIO(img_bytes))
        draw = ImageDraw.Draw(img)

        # Build merged boxes (skip index 0 = full text)
        merged_boxes: List[List[int]] = []
        for t in texts[1:]:
            vertices = t.bounding_poly.vertices
            x_min, y_min = vertices[0].x, vertices[0].y
            x_max, y_max = vertices[2].x, vertices[2].y

            # normalize ordering
            if y_min > y_max:
                y_min, y_max = y_max, y_min
            if x_min > x_max:
                x_min, x_max = x_max, x_min

            # merge with existing boxes where close/overlapping
            merged = False
            for mbox in merged_boxes:
                pix_len = 50
                if (mbox[0] <= x_max + pix_len and mbox[2] >= x_min - pix_len) and \
                   (mbox[1] <= y_max + pix_len and mbox[3] >= y_min - pix_len):
                    mbox[0] = min(x_min, mbox[0])
                    mbox[1] = min(y_min, mbox[1])
                    mbox[2] = max(x_max, mbox[2])
                    mbox[3] = max(y_max, mbox[3])
                    merged = True
                    break
            if not merged:
                merged_boxes.append([x_min, y_min, x_max, y_max])

        # remove boxes fully contained in another
        combined_boxes: List[List[int]] = []
        for box in merged_boxes:
            if not any(
                box[0] >= cb[0] and box[1] >= cb[1] and box[2] <= cb[2] and box[3] <= cb[3]
                for cb in combined_boxes
            ):
                combined_boxes.append(box)

        # Map each char/word to its enclosing merged box
        boxes_to_text: dict[Tuple[int, int, int, int], List[str]] = {tuple(b): [] for b in combined_boxes}

        for t in texts[1:]:
            vertices = t.bounding_poly.vertices
            x_min, y_min = vertices[0].x, vertices[0].y
            x_max, y_max = vertices[2].x, vertices[2].y
            char = t.description
            characterBB = [x_min, y_min, x_max, y_max]

            enclosing = find_enclosing_box(combined_boxes, characterBB)
            if enclosing is None:
                continue
            boxes_to_text[tuple(enclosing)].append(char)

        # For each box, translate and render
        for box, text_list in boxes_to_text.items():
            left, top, right, bottom = box
            width = max(1, right - left)
            height = max(1, bottom - top)

            # Expand extremely tall/narrow boxes horizontally a bit (optional visual smoothing)
            if 10 * width < height:
                width_increase = width * 2
                left -= int(0.5 * width_increase)
                right += int(0.5 * width_increase)
                width = max(1, right - left)
                height = max(1, bottom - top)
                box = (left, top, right, bottom)
            elif width < (0.5 * height):
                width_increase = int(width * 0.25)
                left -= int(0.5 * width_increase)
                right += int(0.5 * width_increase)
                width = max(1, right - left)
                height = max(1, bottom - top)
                box = (left, top, right, bottom)

            original_text = " ".join(text_list).strip()
            if not original_text:
                continue

            # Translate with resilience
            translated: Optional[str] = None
            for _ in range(3):
                try:
                    src_lang = detected_language or "auto"
                    if src_lang == "zh":
                        src_lang = "chinese (simplified)"
                    translated = GoogleTranslator(source=src_lang, target="english").translate(original_text)
                    break
                except requests.exceptions.ConnectionError:
                    print("Translate: connection error, retrying...")
                    time.sleep(2)
                except LanguageNotSupportedException:
                    if detected_language == "zh":
                        translated = GoogleTranslator(source="chinese (simplified)", target="english").translate(original_text)
                        break
                    print(f"Translate: not supported source language: {detected_language}")
                    break
                except Exception as e:
                    print(f"Translate error: {e}")
                    time.sleep(1)

            # Filters
            if not translated:
                continue
            translated = translated.strip()
            if len(translated) < 4:
                continue
            if translated.isdigit():
                continue
            if is_sentence_gibberish(translated):
                continue

            # Paint white box over original text
            draw.rectangle(box, outline="white", fill="white", width=2)

            # --- NEW: Fit text exactly to the box using binary search ---
            wrapped, font = fit_text_to_box(img, translated, box, margin_ratio=0.02)

            # Center text in box
            draw.multiline_text(
                xy=((left + right) / 2, (top + bottom) / 2),
                text=wrapped,
                font=font,
                fill="black",
                anchor="mm",
                align="center",
            )

        modified_png_lst.append(img)

        # progress update per page
        print_progress(idx, total, prefix="Processing pages")

    return modified_png_lst

# =========================
# PDF Merge
# =========================
def image_to_pdf_in_memory(image: Image.Image) -> BytesIO:
    pdf_bytes = BytesIO()
    image.save(pdf_bytes, format="PDF", resolution=100.0)
    pdf_bytes.seek(0)
    return pdf_bytes

def convert_images_to_pdf_and_merge(modified_png_lst: List[Image.Image],
                                    filename: str,
                                    output_path: str | Path) -> BytesIO:
    """
    Convert images to a single PDF and write to output_path.
    Returns the in-memory merged PDF (BytesIO) as well.
    """
    if not filename.lower().endswith(".pdf"):
        filename += ".pdf"

    writer = PdfWriter()
    for image in modified_png_lst:
        if not isinstance(image, Image.Image):
            raise TypeError("List contains a non-image object.")
        pdf_stream = image_to_pdf_in_memory(image)
        reader = PdfReader(pdf_stream)
        writer.add_page(reader.pages[0])

    merged_pdf = BytesIO()
    writer.write(merged_pdf)
    merged_pdf.seek(0)

    with open(output_path, "wb") as f:
        f.write(merged_pdf.getvalue())

    return merged_pdf
