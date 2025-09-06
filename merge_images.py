import os
from pathlib import Path
from PIL import Image, ImageFile, ImageOps
from functions import human_sort

# --- Make Pillow resilient to imperfect images ---
ImageFile.LOAD_TRUNCATED_IMAGES = True            # allow truncated JPGs
# If you process extremely large images from untrusted sources, consider a limit instead:
# Image.MAX_IMAGE_PIXELS = 300_000_000

# ----- PDF backend compatibility layer -----
try:
    # Windows path (when PyPDF2 is installed)
    from PyPDF2 import PdfMerger as _PdfMerger
    BACKEND = "PyPDF2"
except Exception:
    _PdfMerger = None
    BACKEND = "pypdf"

if BACKEND == "pypdf":
    # pypdf >= 5: PdfMerger removed; use PdfWriter as an adapter
    from pypdf import PdfReader, PdfWriter

    class PdfMerger:
        def __init__(self):
            self._writer = PdfWriter()
            self._page_count = 0

        def append(self, path_or_stream):
            reader = PdfReader(path_or_stream)
            for page in reader.pages:
                self._writer.add_page(page)
                self._page_count += 1

        def write(self, out_path):
            with open(out_path, "wb") as f:
                self._writer.write(f)

        def close(self):
            pass
else:
    # PyPDF2 path (has native PdfMerger)
    PdfMerger = _PdfMerger


def _open_image_robust(path: str) -> Image.Image:
    """
    Open an image robustly, apply EXIF orientation, and return an RGB image.
    Handles truncated images and transparent PNGs gracefully.
    """
    img = Image.open(path)
    # Force the decode now so truncation handling applies
    img.load()

    # Apply EXIF orientation (phones/cameras)
    img = ImageOps.exif_transpose(img)

    # Ensure RGB; if transparency exists, composite onto white
    if img.mode in ("RGBA", "LA") or (img.mode == "P" and "transparency" in img.info):
        bg = Image.new("RGB", img.size, (255, 255, 255))
        alpha = img.split()[-1] if img.mode in ("RGBA", "LA") else None
        bg.paste(img.convert("RGBA"), mask=alpha)
        img = bg
    elif img.mode != "RGB":
        img = img.convert("RGB")

    return img


def mergeIMGS(path_fldr: str, desired_filename: str) -> None:
    """
    Merge images (jpg/jpeg/png) and PDFs in `path_fldr` into one PDF named `desired_filename`.pdf
    Output goes to ./Transformed/Merged/<desired_filename>.pdf
    """
    src_dir = Path(path_fldr)
    cwd = Path.cwd()
    out_dir = cwd / "Transformed" / "Merged"
    out_dir.mkdir(parents=True, exist_ok=True)
    save_location = out_dir / f"{desired_filename}.pdf"

    # Collect and naturally sort files
    try:
        files = [f for f in os.listdir(src_dir)]
        human_sort(files)
    except Exception:
        # Fallback sort if human_sort not available
        files = sorted(p.name for p in src_dir.iterdir())

    merger = PdfMerger()
    temp_files = []
    added_any = False  # track if we appended anything

    try:
        for name in files:
            file_path = src_dir / name
            if not file_path.is_file():
                continue

            ext = file_path.suffix.lower().lstrip(".")

            if ext in {"jpg", "jpeg", "png"}:
                # Convert image -> temp PDF, then append
                temp_pdf = src_dir / f"{file_path.name}.temp.pdf"
                try:
                    img = _open_image_robust(str(file_path))
                    # Saving to PDF via Pillow
                    img.save(str(temp_pdf), "PDF")
                    merger.append(str(temp_pdf))
                    temp_files.append(temp_pdf)
                    added_any = True
                except Exception as e:
                    print(f"[WARN] Skipping image '{file_path.name}' due to error: {e}")

            elif ext == "pdf":
                try:
                    merger.append(str(file_path))
                    added_any = True
                except Exception as e:
                    print(f"[WARN] Skipping PDF '{file_path.name}' due to error: {e}")

        if added_any:
            merger.write(str(save_location))
            print(f"Files merged successfully into {save_location}")
        else:
            print("No valid files found to merge.")

    finally:
        try:
            merger.close()
        except Exception:
            pass

        # Clean up temporary PDFs
        for tmp in temp_files:
            try:
                if tmp.exists():
                    tmp.unlink()
            except Exception:
                pass

    print("Files Merged!")
